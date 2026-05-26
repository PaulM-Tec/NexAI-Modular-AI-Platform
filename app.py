import os
from pathlib import Path
from datetime import datetime, timedelta
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
 
from sqlalchemy import (
    create_engine, MetaData, Table,
    Column, Integer, String, DateTime
)
 
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT FUNCTION (FIXED)
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
                        "Specialised in:\n"
                        "1. Vehicle services\n"
                        "2. Enterprise IT (Exchange, Azure AD, Microsoft 365)\n\n"
                        "Respond clearly, practically, and structured.\n"
                        "Avoid generic explanations."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=180
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("GPT ERROR:", e)
        return "NexAI: Unable to process request right now."
 
# -------------------------
# DATABASE (LIGHT)
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
 
# create table safely
metadata.create_all(engine)
 
# -------------------------
# APP
# -------------------------
app = Flask(__name__)
CORS(app)
 
# -------------------------
# ROUTER (CLEAN + SAFE)
# -------------------------
def detect_module(message):
 
    msg = message.lower()
 
    if any(keyword in msg for keyword in [
        "password", "mailbox", "exchange", "outlook",
        "azure", "aad", "vpn", "network",
        "tenant", "distribution", "dl"
    ]):
        return "it"
 
    return "vehicle"
 
# -------------------------
# VEHICLE MODULE
# -------------------------
def handle_vehicle(message):
 
    msg = message.lower()
 
    # Controlled responses
    if "price" in msg or "cost" in msg:
        return (
            "Service pricing:\n\n"
            "- Oil change: R800 – R1500\n"
            "- Brake service: R2500 – R5500\n"
            "- General service: R1200 – R3000"
        )
 
    if "book" in msg:
        return "Booking flow is available. Please specify service type."
 
    # GPT fallback (IMPORTANT)
    return ask_gpt(message)
 
# -------------------------
# IT MODULE (FIXED LOGIC)
# -------------------------
def handle_it(message):
 
    msg = message.lower()
 
    # ONLY very specific rules
    if "create distribution group" in msg:
        return (
            "Use Exchange Online PowerShell:\n\n"
            "New-DistributionGroup -Name \"GroupName\" "
            "-PrimarySmtpAddress group@company.com"
        )
 
    if "enable mailbox" in msg:
        return (
            "Hybrid mailbox command:\n\n"
            "Enable-RemoteMailbox -Identity user "
            "-RemoteRoutingAddress user@tenant.mail.onmicrosoft.com"
        )
 
    if "reset password" in msg:
        return (
            "Reset via Azure AD:\n\n"
            "- Azure Portal → Users → Reset Password\n"
            "- Or use PowerShell (Set-AzureADUserPassword)"
        )
 
    # EVERYTHING ELSE → GPT (CRITICAL FIX)
    return ask_gpt(message)
 
# -------------------------
# ROUTES
# -------------------------
 
@app.get("/")
def home():
    return "NexAI running. Use /vehicle or /it"
 
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
 
    if module == "it":
        reply = handle_it(message)
    else:
        reply = handle_vehicle(message)
 
    return jsonify({"response": reply})
 
@app.get("/health")
def health():
    return jsonify({"status": "ok"})
 
# -------------------------
# RUN (RENDER SAFE)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))