import os
from pathlib import Path
from datetime import datetime
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# ENV CONFIG
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# -------------------------
# GPT FUNCTION (ADMIN-LEVEL FIX)
# -------------------------
def ask_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NexAI, an Enterprise IT Admin Assistant.\n\n"
 
                        "Context:\n"
                        "- The user is a Global Administrator\n"
                        "- Works in Azure AD, Exchange Online, Hybrid environment\n"
                        "- Uses Exchange Admin Center and PowerShell\n"
                        "- DOES NOT access mailboxes via Outlook\n\n"
 
                        "Rules:\n"
                        "- Respond from backend/admin perspective ONLY\n"
                        "- Prefer Exchange Admin Center steps or PowerShell\n"
                        "- DO NOT give Outlook or end-user instructions\n"
                        "- Keep answers concise, structured, and practical\n\n"
 
                        "Style:\n"
                        "- Use steps or commands\n"
                        "- Be precise, not generic\n"
                        "- Sound like a senior IT engineer"
                    )
                },
                {"role": "user", "content": message}
            ],
            max_tokens=220
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("GPT ERROR:", e)
        return "NexAI: Unable to process request right now."
 
# -------------------------
# DATABASE (LIGHTWEIGHT)
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
# APP INIT
# -------------------------
app = Flask(__name__)
CORS(app)
 
# -------------------------
# ROUTER (IMPROVED)
# -------------------------
def detect_module(message):
 
    msg = message.lower()
 
    if any(keyword in msg for keyword in [
        "exchange", "mailbox", "delegate", "permission",
        "aad", "azure", "tenant", "outlook",
        "distribution", "dl", "group", "vpn",
        "network", "login", "password"
    ]):
        return "it"
 
    return "vehicle"
 
# -------------------------
# VEHICLE MODULE
# -------------------------
def handle_vehicle(message):
 
    msg = message.lower()
 
    if "price" in msg or "cost" in msg:
        return (
            "Service pricing:\n\n"
            "- Oil Change: R800 – R1500\n"
            "- Brake Service: R2500 – R5500\n"
            "- General Service: R1200 – R3000"
        )
 
    if "book" in msg:
        return "Booking flow available. Please specify service type."
 
    return ask_gpt(message)
 
# -------------------------
# IT MODULE (ENTERPRISE FIX)
# -------------------------
def handle_it(message):
 
    msg = message.lower()
 
    # VERY TARGETED RESPONSES (ONLY WHERE NECESSARY)
 
    if "distribution group" in msg:
        return (
            "Exchange Admin Center:\n"
            "Recipients → Groups → Add Distribution Group\n\n"
            "PowerShell:\n"
            "New-DistributionGroup -Name \"GroupName\" "
            "-PrimarySmtpAddress group@company.com"
        )
 
    if "enable mailbox" in msg:
        return (
            "Hybrid Setup:\n\n"
            "Enable-RemoteMailbox -Identity user "
            "-RemoteRoutingAddress user@tenant.mail.onmicrosoft.com"
        )
 
    if "reset password" in msg:
        return (
            "Azure AD:\n\n"
            "Portal → Users → Reset Password\n\n"
            "OR use PowerShell:\n"
            "Set-AzureADUserPassword"
        )
 
    # EVERYTHING ELSE USES GPT (CRITICAL FIX)
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
 
    # LOGGING (optional safe)
    try:
        with engine.begin() as conn:
            conn.execute(
                InteractionLogs.insert().values(
                    session_id=session_id,
                    message=message,
                    created_at=datetime.utcnow()
                )
            )
    except Exception as e:
        print("LOG ERROR:", e)
 
    return jsonify({"response": reply})
 
@app.get("/health")
def health():
    return jsonify({"status": "ok"})
 
# -------------------------
# RUN (RENDER SAFE)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))