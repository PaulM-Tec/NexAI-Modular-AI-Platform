import os
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
def vehicle_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Automotive assistant only. No IT answers."
            },
            {"role": "user", "content": msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# IT GPT
# -------------------------
def it_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Enterprise IT Admin assistant.\n"
                    "- Use PowerShell or Exchange Admin Center\n"
                    "- No Outlook user steps\n"
                )
            },
            {"role": "user", "content": msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# ROUTER
# -------------------------
def detect(msg):
    msg = msg.lower()
 
    if any(w in msg for w in ["car","engine","oil","leak","vehicle","brake"]):
        return "vehicle"
 
    if any(w in msg for w in ["exchange","mailbox","azure","group","tenant","password"]):
        return "it"
 
    return "vehicle"
 
 
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
    msg = data.get("message","")
 
    if detect(msg) == "vehicle":
        reply = vehicle_ai(msg)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))