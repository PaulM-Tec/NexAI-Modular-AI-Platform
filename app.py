import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

sys.path.append(os.getcwd())

load_dotenv()
 
# NEW imports for this step
import requests
import numpy as np
import jwt
 
# Import your NLP engine

from nlp_engine import get_response
 
# -------------------------
# Config (kept compatible)
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, future=True)
 
metadata = MetaData()
metadata.reflect(bind=engine)
 
# Table refs as per your current DB
Users = metadata.tables.get("users")
InteractionLogs = metadata.tables.get("interactionlogs")
Recommendations = metadata.tables.get("recommendations")
 
# NLP microservice endpoint (from nlp_app.py)
NLP_URL = os.getenv("NLP_URL", "http://localhost:8081/v1/nlp/embeddings")
 
# Dev JWT secret (HS256) for new routes only
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
 
app = Flask(__name__)
 
# -------------------------
# Dev JWT helpers (inline)
# -------------------------
def verify_scope(authorization_header: str, required_scope: str) -> dict:
    """
    Verify 'Bearer <token>' and ensure 'required_scope' is present.
    Raises ValueError if invalid/missing. Used only on the new /v1/... routes.
    """
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
 
def issue_service_token(scope: str, minutes: int = 15) -> str:
    """
    Issue a short-lived service token for calling the NLP microservice.
    """
    import datetime
    payload = {
        "sub": "recommend-service",
        "scope": scope,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
 
# -------------------------
# Existing endpoints
# -------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
 
@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    message = (data.get("message") or "").strip()
 
    if not message:
        return jsonify({"error": "message is required"}), 400
 
    # Fallback for missing user_id
    if user_id is None:
        # Option A: Hardcode for dev/testing
        user_id = 1
        # Option B: Query session owner from DB if available
        # with engine.begin() as conn:
        #     result = conn.execute(select(Sessions.c.user_id).where(Sessions.c.id == data.get("session_id"))).fetchone()
        #     user_id = result[0] if result else 1
 
    reply = get_response(message)
 
    # Log both user message and bot reply
    if InteractionLogs is not None:
        try:
            with engine.begin() as conn:
                conn.execute(InteractionLogs.insert().values(user_id=user_id, query=message, timestamp=datetime.utcnow()))
                conn.execute(InteractionLogs.insert().values(user_id=user_id, query=reply, timestamp=datetime.utcnow()))
        except SQLAlchemyError as e:
            return jsonify({"response": reply, "log_error": str(e)}), 200
 
    return jsonify({"response": reply}), 200
 
@app.post("/recommend")
def recommend_legacy():
    """
    Your original endpoint remains unchanged for backwards compatibility.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    top_n = int(data.get("top_n", 3))
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400
 
    # Generate simple static recommendations
    recs = ["Oil change", "Brake check", "Tire rotation"][:top_n]
 
    if Recommendations is not None:
        try:
            with engine.begin() as conn:
                for r in recs:
                    conn.execute(Recommendations.insert().values(
                        user_id=user_id,
                        recommendation=r,
                        created_at=datetime.utcnow()
                    ))
        except SQLAlchemyError as e:
            return jsonify({"recommendations": recs, "log_error": str(e)}), 200
 
    return jsonify({"recommendations": recs}), 200
 
# -------------------------
# NEW helpers for v2 recs
# -------------------------
CANDIDATES = [
    "Oil change",
    "Brake pad replacement",
    "Tyre rotation",
    "Wheel alignment",
    "Battery replacement",
    "Air filter change",
    "Spark plug service",
    "Coolant flush",
    "Transmission service",
    "Diagnostic check"
]
 
def _latest_user_text_for(user_id: int) -> str | None:
    """
    Retrieve the latest 'query' text from interactionlogs for a user.
    (Your schema does not store a 'direction', so we read the latest row.)
    """
    if InteractionLogs is None:
        return None
    try:
        with engine.connect() as conn:
            stmt = (
                select(InteractionLogs.c.query)
                .where(InteractionLogs.c.user_id == user_id)
                .order_by(InteractionLogs.c.timestamp.desc())
                .limit(1)
            )
            row = conn.execute(stmt).fetchone()
            return (row[0].strip() if row and isinstance(row[0], str) else None)
    except Exception:
        return None
 
def _cosine_top_k(target_vec, corpus_vecs, labels, k: int):
    t = np.array(target_vec)
    C = np.array(corpus_vecs)
    t_norm = np.linalg.norm(t) + 1e-12
    C_norms = np.linalg.norm(C, axis=1) + 1e-12
    sims = (C @ t) / (C_norms * t_norm)
    idxs = np.argsort(sims)[::-1][:k]
    return [(labels[i], float(sims[i])) for i in idxs]
 
# -------------------------
# NEW: v2 endpoints
# -------------------------
@app.post("/v1/recommend")
def recommend_v2():
    """
    Content-based recommendations using the NLP microservice embeddings.
    Writes to `recommendations` (user_id, recommendation, created_at) exactly as before.
    Auth: Bearer token with scope 'rec:generate'
    """
    # Auth check
    auth = request.headers.get("Authorization", "")
    try:
        verify_scope(auth, "rec:generate")
    except ValueError as e:
        code = 401 if ("Missing" in str(e) or "Invalid" in str(e)) else 403
        return jsonify({"error": str(e)}), code
 
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    top_n = int(data.get("top_n", 3))
    text = (data.get("text") or "").strip()  # optional: allow explicit text override
    candidates = data.get("candidates") or CANDIDATES
 
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400
 
    # Use provided text or fall back to latest interaction message
    source_text = text or _latest_user_text_for(user_id)
    if not source_text:
        return jsonify({"error": "No source text available (provide 'text' or ensure interactionlogs has entries)."}), 400
 
    # Call NLP microservice to embed [source] + candidates
    try:
        svc_token = issue_service_token("nlp:vectorize", minutes=10)
        headers = {"Authorization": f"Bearer {svc_token}", "Content-Type": "application/json"}
        payload = {"texts": [source_text] + candidates, "model": "tfidf_v1", "normalize": True}
        r = requests.post(NLP_URL, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        vectors = r.json().get("vectors") or []
        if len(vectors) < 2:
            return jsonify({"error": "Embedding service returned insufficient vectors"}), 502
        target_vec, corpus_vecs = vectors[0], vectors[1:]
    except requests.RequestException as e:
        return jsonify({"error": f"NLP service error: {e}"}), 502
 
    # Rank by cosine similarity
    ranked = _cosine_top_k(target_vec, corpus_vecs, candidates, top_n)
    recs = [label for (label, score) in ranked]
 
    # Persist to your 'recommendations' (same columns you already use)
    if Recommendations is not None:
        try:
            with engine.begin() as conn:
                for r_label in recs:
                    conn.execute(Recommendations.insert().values(
                        user_id=user_id,
                        recommendation=r_label,
                        created_at=datetime.utcnow()
                    ))
        except SQLAlchemyError as e:
            # Return recs even if DB write fails, plus the error
            return jsonify({"recommendations": recs, "log_error": str(e)}), 200
 
    return jsonify({
        "recommendations": recs,
        "top_n": top_n,
        "source_text": source_text,
        "method": "content_based",
        "written_to_table": (Recommendations is not None)
    }), 200
 
@app.get("/v1/recommendations/<int:user_id>")
def read_recommendations_v2(user_id: int):
    """
    Read persisted recommendations for the given user_id.
    Auth: Bearer token with scope 'rec:read'
    """
    # Auth check
    auth = request.headers.get("Authorization", "")
    try:
        verify_scope(auth, "rec:read")
    except ValueError as e:
        code = 401 if ("Missing" in str(e) or "Invalid" in str(e)) else 403
        return jsonify({"error": str(e)}), code
 
    if Recommendations is None:
        return jsonify({"items": [], "warning": "recommendations table not available"}), 200
 
    try:
        with engine.connect() as conn:
            stmt = (
                select(
                    Recommendations.c.user_id,
                    Recommendations.c.recommendation,
                    Recommendations.c.created_at
                )
                .where(Recommendations.c.user_id == user_id)
                .order_by(Recommendations.c.created_at.desc())
            )
            rows = conn.execute(stmt).fetchall()
            items = [
                {
                    "user_id": int(r[0]),
                    "recommendation": r[1],
                    "created_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2])
                }
                for r in rows
            ]
            return jsonify({"user_id": user_id, "items": items}), 200
    except SQLAlchemyError as e:
        return jsonify({"user_id": user_id, "items": [], "error": str(e)}), 200
 
# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)