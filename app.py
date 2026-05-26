import os
from datetime import datetime, timedelta
from pathlib import Path
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
 
from sqlalchemy import (
    create_engine, MetaData, Table,
    Column, Integer, String, DateTime, Boolean
)
 
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# LOAD ENV
# -------------------------
load_dotenv()
 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT FUNCTION
# -------------------------
def ask_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NexAI, an assistant for:\n"
                        "- Automotive services\n"
                        "- Enterprise IT (Azure AD, Exchange, Microsoft 365)\n\n"
                        "If unrelated, respond:\n"
                        "'I can only assist with vehicle or enterprise IT queries.'\n\n"
                        "Be concise, structured and practical."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
 
    except Exception as e:
        print("GPT ERROR:", e)
        return "NexAI: Unable to retrieve information."
 
# -------------------------
# DATABASE
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
metadata = MetaData()
 
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
 
# Create tables if not exists
metadata.create_all(engine)
 
# -------------------------
# FLASK
# -------------------------
app = Flask(__name__)
CORS(app)
 
# -------------------------
# SESSION MEMORY
# -------------------------
user_sessions = {}
 
# -------------------------
# ROUTER
# -------------------------
def detect_module(message):
    msg = message.lower()
 
    if any(word in msg for word in [
        "password", "login", "aad", "azure",
        "exchange", "mailbox", "outlook",
        "vpn", "network", "server",
        "app registration", "enterprise app",
        "dynamics"
    ]):
        return "it"
 
    return "vehicle"
 
# -------------------------
# VEHICLE MODULE
# -------------------------
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
 
def handle_vehicle_module(message, session):
    msg = message.lower()
    reply = None
 
    if any(word in msg for word in ["price", "cost", "how much"]):
        reply = (
            "Estimated costs:\n\n"
            "- Oil Change: R800 – R1,500\n"
            "- Brake Service: R2,500 – R5,500\n"
            "- General Service: R1,200 – R3,000\n"
        )
 
    elif any(word in msg for word in ["book", "service"]):
 
        service_type = "General Service"
        if "brake" in msg:
            service_type = "Brake Service"
        elif "oil" in msg:
            service_type = "Oil Change"
 
        session["service_type"] = service_type
        session["state"] = "awaiting_date"
        session["days"] = generate_days()
 
        reply = "Select a service date:\n" + "\n".join(
            [f"{i+1}. {d}" for i, d in enumerate(session["days"])]
        )
 
    elif session.get("state") == "awaiting_date" and message.isdigit():
        idx = int(message) - 1
 
        if 0 <= idx < len(session["days"]):
            session["selected_day"] = session["days"][idx]
            session["state"] = "awaiting_time"
            session["times"] = generate_times()
 
            reply = "Select a time:\n" + "\n".join(
                [f"{i+1}. {t}" for i, t in enumerate(session["times"])]
            )
 
    elif session.get("state") == "awaiting_time" and message.isdigit():
        idx = int(message) - 1
 
        if 0 <= idx < len(session["times"]):
            selected_time = session["times"][idx]
            reply = f"Booking Confirmed\n{session['selected_day']} at {selected_time}"
            session["state"] = None
 
    if reply is None:
        reply = f"NexAI: {ask_gpt(message)}"
 
    return reply
 
# -------------------------
# IT MODULE
# -------------------------
def handle_it_module(message):
    msg = message.lower()
 
    if "distribution" in msg or "dl" in msg:
        return (
            "**Exchange Online:**\n\n"
            "New-DistributionGroup -Name 'GroupName' "
            "-PrimarySmtpAddress group@company.com"
        )
 
    elif "mailbox" in msg:
        return (
            "**Hybrid Mailbox:**\n\n"
            "Enable-RemoteMailbox -Identity user "
            "-RemoteRoutingAddress user@tenant.mail.onmicrosoft.com"
        )
 
    elif "password" in msg:
        return "**Password Reset:**\nUse Azure AD portal or PowerShell"
 
    elif "app registration" in msg:
        return (
            "**App Registration:**\n"
            "Azure Portal → App Registrations → New"
        )
 
    return f"NexAI IT: {ask_gpt(message)}"
 
# -------------------------
# ROUTES
# -------------------------
 
# Default (optional)
@app.get("/")
def home():
    return "NexAI is running. Use /vehicle or /it"
 
# VEHICLE FRONTEND
@app.get("/vehicle")
def vehicle_ui():
    return send_from_directory(".", "index_vehicle.html")
 
# IT FRONTEND
@app.get("/it")
def it_ui():
    return send_from_directory(".", "index_it.html")
 
# CHAT API
@app.post("/chat")
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
 
    session_id = data.get("session_id", "default")
 
    if session_id not in user_sessions:
        user_sessions[session_id] = {}
 
    session = user_sessions[session_id]
 
    module = detect_module(message)
 
    if module == "vehicle":
        reply = handle_vehicle_module(message, session)
    else:
        reply = handle_it_module(message)
 
    return jsonify({"response": reply})
 
# HEALTH
@app.get("/health")
def health():
    return jsonify({"status": "ok"})
 
# -------------------------
# MAIN (RENDER)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))