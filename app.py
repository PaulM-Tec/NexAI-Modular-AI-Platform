import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
 
# GOOGLE CALENDAR IMPORTS
from google.oauth2 import service_account
from googleapiclient.discovery import build
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# SLACK FUNCTION
# -------------------------
def send_to_slack(message):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print("Slack webhook not set")
        return
 
    try:
        requests.post(webhook, json={"text": message})
    except Exception as e:
        print("Slack error:", e)
 
 
# -------------------------
# GOOGLE CALENDAR FUNCTION (FIXED FULLY)
# -------------------------
def create_calendar_event(day, time):
    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
 
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=SCOPES
        )
 
        service = build('calendar', 'v3', credentials=creds)
 
        # STEP 1: calculate correct date from selected day
        today = datetime.now()
 
        days_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4
        }
 
        target_day = days_map[day.lower()]
        days_ahead = (target_day - today.weekday()) % 7
 
        if days_ahead == 0:
            days_ahead = 7  # always next occurrence
 
        booking_date = today + timedelta(days=days_ahead)
 
        # STEP 2: build correct datetime
        start_datetime = datetime.strptime(
            f"{booking_date.strftime('%Y-%m-%d')} {time}",
            "%Y-%m-%d %H:%M"
        )
 
        end_datetime = start_datetime + timedelta(hours=1)
 
        event = {
            'summary': 'Vehicle Service Booking',
            'description': f'Booking via NexAI\nDay: {day}\nTime: {time}',
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Africa/Johannesburg',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Africa/Johannesburg',
            }
        }
 
        service.events().insert(
            calendarId='170013714c22b8ae82dd253ea8480175e8ad8708ec57997dddd64a411be8ad41@group.calendar.google.com',
            body=event
        ).execute()
 
        print("Event created:", booking_date, time)
 
        return booking_date
 
    except Exception as e:
        print("Calendar error:", e)
        return datetime.now()
 
 
# -------------------------
# VEHICLE MODULE
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    if "book" in text or "service" in text:
        current = datetime.now()
        days = []
 
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
 
    if session.get("state") == "time" and msg.isdigit():
 
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["times"]):
 
            time = session["times"][idx]
            day = session.get("selected_day", "")
 
            # CREATE CALENDAR EVENT + GET DATE
            booking_date = create_calendar_event(day, time)
 
            session.clear()
 
            return {
                "text": (
                    "NEW LOGIC RUNNING\n\nBooking Confirmed\n\n"
                    f"Date: {booking_date.strftime('%d/%m/%Y')}\n"
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
# IT MODULE (SLACK)
# -------------------------
def it_ai(msg):
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
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
 
    reply = response.choices[0].message.content
 
    send_to_slack(f"""
🖥️ NexAI IT Alert
 
Query:
{msg}
 
Response:
{reply}
""")
 
    return {
        "text": reply
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)