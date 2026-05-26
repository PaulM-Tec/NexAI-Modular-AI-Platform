import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
# Session storage (for booking flow)
sessions = {}
 
# -------------------------
# VEHICLE MODULE (FULL FLOW)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    # START BOOKING
    if "book" in text or "service" in text:
        days = []
        current = datetime.now()
 
        # next 5 working days
        while len(days) < 5:
            current += timedelta(days=1)
            if current.weekday() < 6:
                days.append(current.strftime("%A"))
 
        session["days"] = days
        session["state"] = "day"
 
        return "Select a service day:\n" + "\n".join(
            [f"{i+1}. {d}" for i, d in enumerate(days)]
        )
 
    # DAY SELECTION
    if session.get("state") == "day" and msg.isdigit():
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["days"]):
            selected_day = session["days"][idx]
            session["selected_day"] = selected_day
 
            times = ["08:00", "10:00", "13:00", "15:00"]
            session["times"] = times
            session["state"] = "time"
 
            return f"{selected_day} selected.\n\nChoose a time:\n" + "\n".join(
                [f"{i+1}. {t}" for i, t in enumerate(times)]
            )
 
    # TIME SELECTION
    if session.get("state") == "time" and msg.isdigit():
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["times"]):
            selected_time = session["times"][idx]
            selected_day = session.get("selected_day", "")
 
            session.clear()
 
            return f"Booking Confirmed\n{selected_day} at {selected_time}"
 
    # NORMAL VEHICLE GPT
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an automotive assistant.\n"
                        "Respond concisely.\n"
                        "Use bullet points when helpful.\n"
                        "No IT topics."
                    )
                },
                {"role": "user", "content": msg}
            ],
            max_tokens=120
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("Vehicle GPT Error:", e)
        return "Unable to process vehicle query right now."
 
 
# -------------------------
# IT MODULE (SHORT + ADMIN FOCUSED)
# -------------------------
def it_ai(msg):
 
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are NexAI Enterprise IT Assistant.\n\n"
 
                        "User:\n"
                        "- Global Admin (Exchange, Entra, M365)\n\n"
 
                        "RULES:\n"
                        "- SHORT answers only\n"
                        "- NO explanations beyond 1 line\n"
                        "- NO Outlook or end-user instructions\n"
                        "- Backend/admin perspective ONLY\n\n"
 
                        "FORMAT:\n"
                        "Title\n"
                        "Steps:\n"
                        "- step\n"
                        "- step\n"
 
                        "Optional:\n"
                        "PowerShell command\n\n"
 
                        "Max 6–8 lines."
                    )
                },
                {"role": "user", "content": msg}
            ],
            max_tokens=120
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("IT GPT Error:", e)
        return "Unable to process IT query right now."
 
 
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
 
 
# CORE CHAT ROUTE
@app.post("/chat")
def chat():
 
    data = request.get_json()
 
    msg = data.get("message", "").strip()
    module = data.get("module", "")
    session_id = data.get("session_id", "default")
 
    if session_id not in sessions:
        sessions[session_id] = {}
 
    session = sessions[session_id]
 
    if module == "vehicle":
        reply = vehicle_ai(msg, session)
 
    elif module == "it":
        reply = it_ai(msg)
 
    else:
        reply = "Invalid module."
 
    return jsonify({"response": reply})
 
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))