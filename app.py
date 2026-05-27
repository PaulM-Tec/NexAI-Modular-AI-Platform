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
# ✅ VEHICLE MODULE (RESTORED STYLE)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    if "book" in text or "service" in text:
        from datetime import datetime, timedelta
 
        current = datetime.now()
        days = []
 
        while len(days) < 5:
            current += timedelta(days=1)
            days.append(current.strftime("%A"))
 
        session["days"] = days
        session["state"] = "day"
 
        return "Select a service day:\n" + "\n".join(
            f"{i+1}. {d}" for i,d in enumerate(days)
        )
 
    if session.get("state") == "day" and msg.isdigit():
        idx = int(msg)-1
        if 0 <= idx < len(session["days"]):
 
            day = session["days"][idx]
            session["selected_day"] = day
 
            times = ["08:00","10:00","13:00","15:00"]
            session["times"] = times
            session["state"] = "time"
 
            return f"{day} selected\nChoose time:\n" + "\n".join(
                f"{i+1}. {t}" for i,t in enumerate(times)
            )
 
    if session.get("state") == "time" and msg.isdigit():
        idx = int(msg)-1
        if 0 <= idx < len(session["times"]):
 
            time = session["times"][idx]
            day = session.get("selected_day","")
            session.clear()
 
            return f"✅ Booking Confirmed\n{day} at {time}"
 
    # ✅ GPT restored nicely structured
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":
                (
                    "Automotive assistant.\n"
                    "Provide structured, short answers.\n"
                    "Use bullet points when needed."
                )
            },
            {"role":"user","content":msg}
        ],
        max_tokens=120
    )
 
    return response.choices[0].message.content
 
 
# -------------------------
# ✅ IT MODULE (FIXED BEHAVIOUR)
# -------------------------
def it_ai(msg):
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content":
                (
                    "You are an Enterprise IT Admin Assistant.\n\n"
 
                    "User is a Global Admin.\n"
                    "Respond using admin tools like:\n"
                    "- Exchange Admin Center\n"
                    "- Entra portal\n"
                    "- PowerShell\n\n"
 
                    "Rules:\n"
                    "- Keep answers short\n"
                    "- Provide steps clearly\n"
                    "- Include PowerShell only when relevant\n"
                    "- DO NOT refuse to answer GUI questions\n\n"
 
                    "FORMAT:\n"
                    "Title\n"
                    "Steps:\n"
                    "- step\n"
                    "- step\n"
                    "Optional: Command\n\n"
 
                    "Keep responses clean and readable."
                )
            },
            {"role": "user", "content": msg}
        ],
        max_tokens=140
    )
 
    return response.choices[0].message.content

# -------------------------
# IT MODULE (STRICT CONTROL + CORRECT FLOW)
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
 
                        "Context:\n"
                        "- User is Global Admin\n"
                        "- Works in Exchange Online, Azure, Entra\n\n"
 
                        "Rules:\n"
                        "- Always include connection step first if PowerShell is used\n"
                        "- No explanations longer than one line\n"
                        "- No Outlook or end-user instructions\n\n"
 
                        "STRICT FORMAT:\n"
                        "Title\n"
                        "Steps:\n"
                        "- step\n"
                        "- step\n"
                        "Command:\n"
                        "- command\n\n"
 
                        "Example:\n"
                        "Connect first before commands.\n"
 
                        "Keep output very short."
                    )
                },
                {"role": "user", "content": msg}
            ],
            max_tokens=120
        )
 
        return response.choices[0].message.content
 
    except Exception as e:
        print("IT ERROR:", e)
        return "Unable to process IT request."
 
 
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
        reply = vehicle_ai(msg, session)
    else:
        reply = it_ai(msg)
 
    return jsonify({"response": reply})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)))