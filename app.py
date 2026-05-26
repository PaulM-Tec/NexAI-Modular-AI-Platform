import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
 
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# VEHICLE AI + BOOKING FLOW
# -------------------------
def vehicle_ai(msg, session):
 
    m = msg.lower()
 
    # Booking trigger
    if "book" in m or "service" in m:
        days = [(datetime.now() + timedelta(days=i)).strftime("%A") for i in range(1,6)]
        session["days"] = days
        session["state"] = "date"
 
        return "Select a service day:\n" + "\n".join([f"{i+1}. {d}" for i,d in enumerate(days)])
 
    # Date selection
    if session.get("state") == "date" and msg.isdigit():
        idx = int(msg) - 1
        if 0 <= idx < len(session["days"]):
            day = session["days"][idx]
            session["state"] = None
            return f"Booking confirmed for {day}"
 
    # Normal GPT
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"Automotive assistant. Keep answers short."},
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# IT AI
# -------------------------
def it_ai(msg):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"Enterprise IT admin assistant. Use backend/admin perspective."},
            {"role":"user","content":msg}
        ]
    )
    return response.choices[0].message.content
 
 
# -------------------------
# ROUTES
# -------------------------
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
    module = data.get("module","default")
    sid = data.get("session_id","default")
 
    if sid not in sessions:
        sessions[sid] = {}
 
    session = sessions[sid]
 
    if module == "vehicle":
        reply = vehicle_ai(msg, session)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))