import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
# -------------------------
# VEHICLE GPT
# -------------------------
def ask_vehicle_gpt(message):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content":
             "Automotive assistant only. Focus on vehicle issues."},
            {"role": "user", "content": message}
        ],
        max_tokens=150
    ).choices[0].message.content
 
# -------------------------
# IT GPT (ADMIN CONTEXT)
# -------------------------
def ask_it_gpt(message):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content":
             "Enterprise IT admin assistant. Use Exchange Admin Center or PowerShell. No Outlook steps."},
            {"role": "user", "content": message}
        ],
        max_tokens=200
    ).choices[0].message.content
 
# -------------------------
# ROUTER (FIXED)
# -------------------------
def detect_module(msg):
    msg = msg.lower()
 
    if any(w in msg for w in ["car","engine","oil","brake","vehicle","leak","smoke"]):
        return "vehicle"
 
    if any(w in msg for w in ["exchange","mailbox","azure","aad","tenant","group","password"]):
        return "it"
 
    return "vehicle"
 
# -------------------------
# HANDLERS
# -------------------------
def handle_vehicle(msg):
    if "price" in msg.lower():
        return "Oil Change: R800–1500\nBrake Service: R2500–5500"
    return ask_vehicle_gpt(msg)
 
def handle_it(msg):
    if "distribution group" in msg.lower():
        return "New-DistributionGroup -Name \"GroupName\""
    return ask_it_gpt(msg)
 
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
    message = data.get("message", "")
 
    module = detect_module(message)
 
    if module == "vehicle":
        reply = handle_vehicle(message)
    else:
        reply = handle_it(message)
 
    return jsonify({"response": reply})
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))