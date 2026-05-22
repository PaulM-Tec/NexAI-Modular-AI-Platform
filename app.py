import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from pathlib import Path
 
# Fix import path
sys.path.append(os.getcwd())
 
load_dotenv()
 
# External libs
import requests
import numpy as np
import jwt
 
# NLP
from nlp_engine import get_response
 
# -------------------------
# Config (FINAL DB FIX)
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
 
metadata = MetaData()
 
# Load tables explicitly
Users = Table("users", metadata, autoload_with=engine)
InteractionLogs = Table("interaction_logs", metadata, autoload_with=engine)
Recommendations = Table("recommendations", metadata, autoload_with=engine)
 
print("Tables loaded successfully:", metadata.tables.keys())
 
NLP_URL = os.getenv("NLP_URL", "http://localhost:8081/v1/nlp/embeddings")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
 
app = Flask(__name__)
 
# -------------------------
# Health
# -------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
 
 
# -------------------------
# CHAT (FINAL FIXED)
# -------------------------
@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
 
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400
 
    # Default session (we improve later)
    session_id = data.get("session_id") or 1
 
    # NLP response
    reply = get_response(message)
 
    # FINAL CORRECT LOGGING (aligned with DB schema)
    try:
        with engine.begin() as conn:
            now = datetime.utcnow()
 
            # incoming message
            conn.execute(
                InteractionLogs.insert().values(
                    session_id=session_id,
                    direction="incoming",
                    message=message,
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
            )
 
            # outgoing response
            conn.execute(
                InteractionLogs.insert().values(
                    session_id=session_id,
                    direction="outgoing",
                    message=reply,
                    created_at=now,
                    updated_at=now,
		    is_deleted=False
                )
            )
 
    except SQLAlchemyError as e:
        print("LOG ERROR:", e)
 
    return jsonify({"response": reply}), 200
 
 
# -------------------------
# LEGACY RECOMMEND
# -------------------------
@app.post("/recommend")
def recommend_legacy():
    data = request.get_json(silent=True) or {}
 
    user_id = data.get("user_id")
    top_n = int(data.get("top_n", 3))
 
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400
 
    recs = ["Oil change", "Brake check", "Tire rotation"][:top_n]
 
    try:
        with engine.begin() as conn:
            for r in recs:
                conn.execute(
                    Recommendations.insert().values(
                        user_id=user_id,
                        recommendation=r,
                        created_at=datetime.utcnow()
                    )
                )
 
    except SQLAlchemyError as e:
        return jsonify({"recommendations": recs, "log_error": str(e)}), 200
 
    return jsonify({"recommendations": recs}), 200
 
 
# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)