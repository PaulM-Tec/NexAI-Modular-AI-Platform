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
# VEHICLE AI (CLEAN FORMAT)
# -------------------------
def vehicle_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an automotive assistant.\n\n"
 
                    "FORMAT STRICTLY:\n"
                    "## Title\n"
                    "Short explanation\n"
                    "- Bullet point\n"
                    "- Bullet point\n\n"
 
                    "Keep spacing tight.\n"
                    "No extra blank lines.\n"
                    "No IT topics."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=150
    )
 
    return response.choices[0].message.content
 
 
# -------------------------
# IT AI (ADMIN + FORMATTED)
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
                    "  • Entra (Azure AD)\n"
                    "  • App Registrations\n\n"
 
                    "Rules:\n"
                    "- Backend/admin ONLY\n"
                    "- Use PowerShell or Admin Center\n"
                    "- NO Outlook instructions\n\n"
 
                    "FORMAT STRICTLY:\n"
                    "## Title\n"
                    "One-line explanation\n"
                    "### Steps\n"
                    "- Step 1\n"
                    "- Step 2\n"
                    "### Command (if needed)\n"
                    "```powershell\ncommand\n```\n"
 
                    "No empty lines between sections.\n"
                    "Keep output compact."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=180
    )
 
    return response.choices[0].message.content
 
 
# -------------------------
# ROUTER (FIXED PROPERLY)
# -------------------------
def detect(msg):
 
    msg = msg.lower()
 
    # IT FIRST (IMPORTANT FIX)
    if any(word in msg for word in [
        "api", "app", "permissions", "graph",
        "azure", "entra", "tenant",
        "exchange", "mailbox",
        "group", "distribution",
        "password", "login"
    ]):
        return "it"
 
    # VEHICLE
    if any(word in msg for word in [
        "car", "engine", "oil",
        "leak", "vehicle", "brake"
    ]):
        return "vehicle"
 
    # SAFE DEFAULT
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
    msg = data.get("message", "").strip()
 
    module = detect(msg)
 
    if module == "vehicle":
        reply = vehicle_ai(msg)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))