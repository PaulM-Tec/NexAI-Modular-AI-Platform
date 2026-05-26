import os
from pathlib import Path
from datetime import datetime
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT - VEHICLE
# -------------------------
def ask_vehicle_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an automotive assistant.\n"
                        "- Focus ONLY on vehicles\n"
                        "- Diagnostics, faults, causes, maintenance\n"
                        "- Be practical and concise\n"
                        "- No IT or unrelated topics"
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except:
        return "Vehicle assistant unavailable."
 
# -------------------------
# GPT - IT ADMIN
# -------------------------
def ask_it_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Enterprise IT Admin Assistant.\n\n"
                        "Context:\n"
                        "- User is a Global Admin\n"
                        "- Works in Exchange Admin Center, Azure AD, Hybrid\n"
                        "- Uses PowerShell\n\n"
                        "Rules:\n"
                        "- Respond as backend admin ONLY\n"
                        "- Prefer EAC steps or PowerShell\n"
                        "- No Outlook or end-user instructions\n"
                        "- Be structured, direct, practical\n\n"
                        "Sound like a senior M365 engineer."
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content
    except:
        return "IT assistant unavailable."
 
# -------------------------
# DATABASE
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
engine = create_engine(f"sqlite:///{BASE_DIR / 'app.db'}")
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
 
# -------------------------
# ROUTER (FIXED PROPERLY)
# -------------------------
def detect_module(message):
 
    msg = message.lower()
 
    # VEHICLE FIRST (PRIORITY)
    if any(word in msg for word in [
        "car", "vehicle", "engine", "oil",
        "brake", "service", "tyre", "tire",
        "leak", "smoke"
    ]):
        return "vehicle"
 
    # IT SECOND
    if any(word in msg for word in [
        "exchange", "mailbox", "azure", "aad",
        "tenant", "distribution", "group",
        "password", "login"
    ]):
        return "it"
 
    # SAFE DEFAULT
    return "vehicle"
 
# -------------------------
# VEHICLE MODULE
# -------------------------
def handle_vehicle(message):
 
    msg = message.lower()
 
    if "price" in msg:
        return (
            "Service estimates:\n\n"
            "- Oil change: R800 – R1500\n"
            "- Brake service: R2500 – R5500\n"
        )
 
    if "book" in msg:
        return "Booking feature available. Specify service type."
 
    return ask_vehicle_gpt(message)
 
# -------------------------
# IT MODULE
# -------------------------
def handle_it(message):
 
    msg = message.lower()
 
    if "distribution group" in msg:
        return (
            "Exchange Admin Center:\n"
            "Recipients → Groups → New → Distribution List\n\n"
            "PowerShell:\n"
            "New-DistributionGroup -Name \"GroupName\""
        )
 
    if "enable mailbox" in msg:
        return (
            "Hybrid mailbox enablement:\n\n"
            "Enable-RemoteMailbox -Identity user\n"
            "-RemoteRoutingAddress user@tenant.mail.onmicrosoft.com"
        )
 
    return ask_it_gpt(message)
 
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
        reply = handle_vehicle(message)
    else:
        reply = handle_it(message)
 
    return jsonify({"response": reply})
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))