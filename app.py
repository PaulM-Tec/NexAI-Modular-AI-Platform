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
 
# Session storage for booking flow
sessions = {}
 
# -------------------------
# VEHICLE MODULE (FIXED)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    # START BOOKING FLOW
    if "book" in text or "service" in text:
 
        current = datetime.now()
        days = []
 
        # ONLY WEEKDAYS (Mon–Fri)
        while len(days) < 5:
            current += timedelta(days=1)
            if current.weekday() < 5:
                days.append(current.strftime("%A"))
 
        session["days"] = days
        session["state"] = "day"
 
        return {
            "text": "Select a service day:\n" + "\n".join(
                f"{i+1}. {d}" for i, d in enumerate(days)
            )
        }
 
    # DAY SELECTION
    if session.get("state") == "day" and msg.isdigit():
 
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["days"]):
 
            day = session["days"][idx]
            session["selected_day"] = day
 
            times = ["08:00", "10:00", "13:00", "15:00"]
            session["times"] = times
            session["state"] = "time"
 
            return {
                "text": f"{day} selected\nChoose time:\n" + "\n".join(
                    f"{i+1}. {t}" for i, t in enumerate(times)
                )
            }
 
    # TIME SELECTION
    if session.get("state") == "time" and msg.isdigit():
 
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["times"]):
 
            time = session["times"][idx]
            day = session.get("selected_day", "")
 
            session.clear()
 
            # FINAL PROFESSIONAL CONFIRMATION
            return {
                "text": (
                    "Booking Confirmed\n\n"
                    f"Date: {datetime.now().strftime('%d/%m/%Y')}\n"
                    f"Day: {day}\n"
                    f"Time: {time}\n"
                    "Service Type: General Service"
                ),
                "type": "booking",
                "data": {
                    "day": day,
                    "time": time,
                    "service_type": "General Service"
                }
            }
 
    # NORMAL VEHICLE GPT RESPONSE
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Automotive assistant.\n"
                    "Provide clear structured answers.\n"
                    "Use bullet points when helpful."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=120
    )
 
    return {
        "text": response.choices[0].message.content
    }
 
 
# -------------------------
# IT MODULE (UNCHANGED)
# -------------------------
def it_ai(msg):
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content":
                (
                    "Enterprise IT Admin Assistant.\n\n"
 
                    "Context:\n"
                    "- Global Admin\n"
                    "- Exchange, Entra, Azure\n\n"
 
                    "Rules:\n"
                    "- Keep answers SHORT\n"
                    "- Provide steps clearly\n"
                    "- Allow GUI and PowerShell\n"
                    "- If PowerShell used → include connect step first\n\n"
 
                    "FORMAT:\n"
                    "Title\n"
                    "Steps:\n"
                    "- step\n"
                    "- step\n"
                    "Command (if needed)\n\n"
 
                    "No long explanations."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=140
    )
 
    return {
        "text": response.choices[0].message.content
    }
 
 
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
 
    msg = data.get("message", "")
    module = data.get("module", "")
    session_id = data.get("session_id", "default")
 
    if session_id not in sessions:
        sessions[session_id] = {}
 
    session = sessions[session_id]
 
    if module == "vehicle":
        result = vehicle_ai(msg, session)
    else:
        result = it_ai(msg)
 
    return jsonify(result)
 
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))