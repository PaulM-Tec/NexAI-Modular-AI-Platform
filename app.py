import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# LOAD ENV VARIABLES
# -------------------------
load_dotenv()
 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT FUNCTION (CONTROLLED DOMAIN)
# -------------------------
def ask_gpt(user_message):
 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NexAI, an automotive assistant.\n"
                        "You ONLY answer questions related to vehicles, cars, repairs, maintenance, and automotive systems.\n\n"
                        "If the question is NOT related to cars or vehicles, respond with:\n"
                        "'NexAI: I can only assist with vehicle-related queries.'\n\n"
                        "Provide clear, concise and professional answers."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=150
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("GPT ERROR:", e)
        return "NexAI: I'm unable to retrieve that information right now."
 
 
# Fix import path
sys.path.append(os.getcwd())
 
# -------------------------
# DATABASE CONFIG
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
metadata = MetaData()
 
from sqlalchemy import Column, Integer, String, DateTime, Boolean
 
Users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)
 
InteractionLogs = Table(
    "interaction_logs", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String),
    Column("direction", String),
    Column("message", String),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("is_deleted", Boolean),
)
 
metadata.create_all(engine)

Bookings = Table(
    "bookings", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String),
    Column("service_type", String),
    Column("booking_date", String),
    Column("booking_time", String),
    Column("status", String),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("is_deleted", Boolean),
)
 
# -------------------------
# FLASK APP
# -------------------------
app = Flask(__name__)
CORS(app)
 
# -------------------------
# SESSION MEMORY
# -------------------------
user_sessions = {}
 
def generate_days():
    days = []
    current = datetime.now()
 
    while len(days) < 5:
        current += timedelta(days=1)
        if current.weekday() <= 4:
            days.append(current.strftime("%A"))
 
    return days
 
def generate_times():
    return ["08:00", "10:00", "14:00", "16:00"]
 
# -------------------------
# ROUTES
# -------------------------
@app.get("/")
def serve_frontend():
    return send_from_directory(".", "index.html")
 
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
 
# -------------------------
# CHAT ENGINE
# -------------------------
@app.post("/chat")
def chat():
 
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
 
    if not message:
        return jsonify({"error": "message is required"}), 400
 
    session_id = data.get("session_id") or "default"
 
    if session_id not in user_sessions:
        user_sessions[session_id] = {"state": None}
 
    session = user_sessions[session_id]
    msg = message.lower()
 
    reply = None
 
    # =====================================================
    # 1. INTELLIGENCE (CONTROLLED)
    # =====================================================
    if any(msg.startswith(q) for q in ["why", "what", "how"]) and "how much" not in msg:
 
        if any(term in msg for term in ["brake", "braking", "brakes"]):
            reply = (
                "NexAI: Braking systems work by applying friction through brake pads to slow the vehicle.\n\n"
                "If performance is reduced, a brake inspection is recommended."
            )
 
        elif "oil" in msg:
            reply = (
                "NexAI: Engine oil lubricates moving components and reduces heat and friction.\n\n"
                "Regular oil changes are essential for engine health."
            )
 
    # =====================================================
    # 2. DOMAIN RICHNESS
    # =====================================================
    elif any(word in msg for word in ["price", "cost", "how much"]):
 
        reply = (
            "NexAI: Estimated service costs:\n\n"
            "- Oil Change: R800 – R1,500\n"
            "- Brake Service: R2,500 – R5,500\n"
            "- General Service: R1,200 – R3,000\n\n"
            "Would you like to book a service?"
        )
 
    elif any(word in msg for word in ["recommend", "suggest", "advice"]):
 
        reply = (
            "NexAI: Maintenance recommendations:\n\n"
            "- Oil change every 5,000 – 10,000 km\n"
            "- Brake inspection every 10,000 km\n"
            "- Tire rotation every 8,000 km\n\n"
            "Would you like to schedule a service?"
        )
 
    # =====================================================
    # 3. BOOKING FLOW
    # =====================================================
    elif any(x in msg for x in ["book", "service", "fix", "maintenance"]):
 
        if "brake" in msg:
            service_type = "Brake Service"
        elif "oil" in msg:
            service_type = "Oil Change"
        else:
            service_type = "General Service"
 
        session["service_type"] = service_type
 
        days = generate_days()
        session["state"] = "awaiting_date"
        session["days"] = days
 
        day_list = "\n".join([f"{i+1}. {d}" for i, d in enumerate(days)])
 
        reply = (
            f"NexAI: I understand you need a {service_type.lower()}.\n\n"
            f"Please choose a service date:\n\n{day_list}"
        )
 
    elif session.get("state") == "awaiting_date" and message.isdigit():
 
        index = int(message) - 1
 
        if 0 <= index < len(session["days"]):
            selected_day = session["days"][index]
            session["selected_day"] = selected_day
            session["state"] = "awaiting_time"
 
            times = generate_times()
            session["times"] = times
 
            time_list = "\n".join([f"{i+1}. {t}" for i, t in enumerate(times)])
 
            reply = f"NexAI: Available time slots for {selected_day}:\n\n{time_list}"
        else:
            reply = "NexAI: Invalid selection."
 
    elif session.get("state") == "awaiting_time" and message.isdigit():
 
        index = int(message) - 1
 
        if 0 <= index < len(session["times"]):
 
            selected_time = session["times"][index]
            selected_day = session["selected_day"]
 
            session["state"] = None
 
            reply = f"NexAI: Booking confirmed!\n\n{selected_day} at {selected_time}"
 
    # =====================================================
    # 4. GPT FALLBACK (CONTROLLED DOMAIN)
    # =====================================================
    if reply is None:
        gpt_response = ask_gpt(message)
        reply = f"NexAI: {gpt_response}"
 
    # =====================================================
    # LOGGING
    # =====================================================
    try:
        with engine.begin() as conn:
            now = datetime.utcnow()
 
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
 
    except Exception as e:
        print("LOG ERROR:", e)
 
    return jsonify({"response": reply}), 200
 
 
# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))