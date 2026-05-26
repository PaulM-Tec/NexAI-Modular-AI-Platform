import os
from datetime import datetime, timedelta
from pathlib import Path
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT
# -------------------------
def ask_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NexAI.\n"
                        "- Automotive assistant\n"
                        "- Enterprise IT assistant\n"
                        "Give structured, practical responses."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print("GPT ERROR:", e)
        return "Unable to retrieve information."
 
# -------------------------
# DB
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
engine = create_engine(f"sqlite:///{DB_PATH}")
metadata = MetaData()
 
InteractionLogs = Table(
    "interaction_logs", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String),
    Column("message", String),
    Column("created_at", DateTime)
)
 
metadata.create_all(engine)
 
# -------------------------
# APP
# -------------------------
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# ROUTER
# -------------------------
def detect_module(msg):
    msg = msg.lower()
 
    if any(k in msg for k in [
        "password", "mailbox", "exchange",
        "aad", "azure", "vpn", "network"
    ]):
        return "it"
 
    return "vehicle"
 
# -------------------------
# VEHICLE
# -------------------------
def handle_vehicle(msg, session):
 
    msg = msg.lower()
 
    if "price" in msg or "cost" in msg:
        return "Brake Service: R2,500 – R5,500"
 
    if "book" in msg:
        return "Booking started..."
 
    return ask_gpt(msg)
 
# -------------------------
# IT (FIXED)
# -------------------------
def handle_it(msg):
 
    msg = msg.lower()
 
    if "distribution group" in msg:
        return "New-DistributionGroup -Name 'GroupName'"
 
    if "enable mailbox" in msg:
        return "Enable-RemoteMailbox -Identity user"
 
    # GPT handles MOST QUESTIONS
    return f"NexAI IT: {ask_gpt(msg)}"
 
# -------------------------
# ROUTES
# -------------------------
@app.get("/")
def home():
    return "Use /vehicle or /it"
 
@app.get("/vehicle")
def vehicle_ui():
    return send_from_directory(".", "index_vehicle.html")
 
@app.get("/it")
def it_ui():
    return send_from_directory(".", "index_it.html")
 
@app.post("/chat")
def chat():
 
    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
 
    module = detect_module(message)
 
    if module == "vehicle":
        reply = handle_vehicle(message, {})
 
    else:
        reply = handle_it(message)
 
    return jsonify({"response": reply})
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))