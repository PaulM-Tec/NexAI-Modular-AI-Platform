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
# VEHICLE MODULE (UNCHANGED BEHAVIOUR)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    if "book" in text or "service" in text:
        current = datetime.now()
        days = []
 
        while len(days) < 5:
            current += timedelta(days=1)
            days.append(current.strftime("%A"))
 
        session["days"] = days
        session["state"] = "day"
 
        return {
            "text": "Select a service day:\n" + "\n".join(
                f"{i+1}. {d}" for i,d in enumerate(days)
            )
        }
 
    if session.get("state") == "day" and msg.isdigit():
        idx = int(msg) - 1
        if 0 <= idx < len(session["days"]):
 
            day = session["days"][idx]
            session["selected_day"] = day
 
            times = ["08:00","10:00","13:00","15:00"]
            session["times"] = times
            session["state"] = "time"
 
            return {
                "text": f"{day} selected\nChoose time:\n" + "\n".join(
                    f"{i+1}. {t}" for i,t in enumerate(times)
                )
            }
 
    if session.get("state") == "time" and msg.isdigit():
        idx = int(msg) - 1
        if 0 <= idx < len(session["times"]):
 
            time = session["times"][idx]
            day = session.get("selected_day","")
            session.clear()
 
            return {
                "text": f"Booking Confirmed\n{day} at {time}",
                "type": "booking",
                "data": {
                    "day": day,
                    "time": time
                }
            }
 
    # GPT fallback
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":
                (
                    "Automotive assistant.\n"
                    "Give clear structured answers.\n"
                    "Use bullets where helpful."
                )
            },
            {"role":"user","content":msg}
        ],
        max_tokens=120
    )
 
    return {"text": response.choices[0].message.content}
 
 
# -------------------------
# IT MODULE (FIXED QUALITY)
# -------------------------
def it_ai(msg):
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
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
            {"role":"user","content":msg}
        ],
        max_tokens=140
    )
 
    return {"text": response.choices[0].message.content}
 
 
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
    sid = data.get("session_id", "default")
 
    if sid not in sessions:
        sessions[sid] = {}
 
    session = sessions[sid]
 
    if module == "vehicle":
        result = vehicle_ai(msg, session)
    else:
        result = it_ai(msg)
 
    return jsonify(result)
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))