import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
# -------------------------
# VEHICLE AI
# -------------------------
def vehicle_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an automotive assistant.\n"
                    "Give short, structured answers.\n\n"
                    "Format:\n"
                    "Title\n"
                    "Short explanation\n"
                    "Bullet points or steps\n\n"
                    "No IT topics."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content
 
 
# -------------------------
# IT AI (ADMIN LEVEL)
# -------------------------
def it_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NexAI Enterprise IT Assistant.\n\n"
 
                    "User:\n"
                    "- Global Admin\n"
                    "- Works in:\n"
                    "  • Microsoft 365 Admin Center\n"
                    "  • Exchange Admin Center\n"
                    "  • Entra / Azure Portal\n"
                    "  • App Registrations\n\n"
 
                    "Rules:\n"
                    "- Backend/admin ONLY\n"
                    "- Use PowerShell or Admin Center\n"
                    "- NO Outlook instructions\n\n"
 
                    "FORMAT STRICT:\n"
                    "**Title**\n"
                    "One-line explanation\n\n"
                    "**Steps**:\n"
                    "- Step 1\n"
                    "- Step 2\n\n"
                    "**Command (if needed)**:\n"
                    "```powershell\ncommand\n```\n\n"
                    "Keep it SHORT."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=180
    )
 
    return response.choices[0].message.content
 
 
# -------------------------
# ROUTER (CORRECTED)
# -------------------------
def detect(msg):
 
    msg = msg.lower()
 
    # IT FIRST
    if any(w in msg for w in [
        "api", "app", "permission", "azure",
        "entra", "exchange", "mailbox",
        "tenant", "group", "password"
    ]):
        return "it"
 
    # VEHICLE
    if any(w in msg for w in [
        "car","engine","oil","leak","vehicle","brake"
    ]):
        return "vehicle"
 
    return "it"
 
 
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
    msg = data.get("message", "")
 
    if detect(msg) == "vehicle":
        reply = vehicle_ai(msg)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))