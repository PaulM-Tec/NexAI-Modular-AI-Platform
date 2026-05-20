# nlp_app.py
import os
from flask import Flask, jsonify, request
 
# reuse your TF-IDF function
from nlp_engine import vectorize_texts
 
# (inline) dev JWT verify – keeps things in one file for now
import jwt, datetime
 
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
 
def verify_scope(authorization_header: str, required_scope: str) -> dict:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise ValueError("Missing token")
    token = authorization_header.split(" ", 1)[1]
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")
    scopes = claims.get("scope", "").split()
    if required_scope not in scopes:
        raise ValueError("Insufficient scope")
    return claims
 
app = Flask(__name__)
 
@app.get("/health")
def health():
    return jsonify({"status":"ok"}), 200
 
@app.post("/v1/nlp/embeddings")
def embeddings():
    # optional JWT check (keeps it simple but secure enough locally)
    auth = request.headers.get("Authorization", "")
    try:
        verify_scope(auth, "nlp:vectorize")
    except ValueError as e:
        # 401 for missing/invalid token, 403 for insufficient scope
        code = 401 if ("Missing" in str(e) or "Invalid" in str(e)) else 403
        return jsonify({"error": str(e)}), code
 
    body = request.get_json(force=True)
    texts = body.get("texts", [])
    model = body.get("model", "tfidf_v1")
    normalize = bool(body.get("normalize", True))
 
    if not isinstance(texts, list) or not texts:
        return jsonify({"error":"texts must be a non-empty list"}), 400
    if model != "tfidf_v1":
        return jsonify({"error":"Unsupported model"}), 400
 
    X = vectorize_texts(texts, normalize=normalize, max_features=1024)
    return jsonify({"model": "tfidf_v1", "dim": int(X.shape[1]), "vectors": X.tolist()})
 
if __name__ == "__main__":
    port = int(os.getenv("NLP_PORT", "8081"))
    app.run(host="0.0.0.0", port=port)