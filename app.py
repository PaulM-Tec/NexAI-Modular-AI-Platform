import os
import requests
import smtplib
import threading
from email.mime.text import MIMEText
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
 
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
 
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# EMAIL FUNCTION FIXED
# -------------------------
def send_email(to_email, name, vehicle, date, time):
    try:
        print("Attempting email send...")
 
        subject = "Vehicle Service Booking Confirmed"
 
        body = f"""
Hello {name},
 
Your booking has been confirmed
 
Vehicle: {vehicle}
Date: {date}
Time: {time}
 
Thank you for using NexAI
"""
 
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
 
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
 
        print("LOGIN SUCCESS")
 
        result = server.send_message(msg)
 
        print("MESSAGE SENT RESULT:", result)
 
        server.quit()
 
        print("Email sent successfully to:", to_email)
 
    except Exception as e:
        import traceback
        print("EMAIL ERROR:", e)
        traceback.print_exc()
 
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
# GOOGLE CALENDAR FUNCTION
# -------------------------
def create_calendar_event(day, time, details):
    try:
        print("FUNCTION CALLED:", day, time)
 
        SCOPES = ['https://www.googleapis.com/auth/calendar']
 
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=SCOPES
        )
 
        service = build('calendar', 'v3', credentials=creds)
 
        today = datetime.now()
 
        days_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4
        }
 
        target_day = days_map.get(day.lower())
 
        if target_day is None:
            print("Invalid day received:", day)
            return datetime.now()
 
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
 
        booking_date = today + timedelta(days=days_ahead)
 
        print("CALCULATED DATE:", booking_date)
 
        start_datetime = datetime.strptime(
            f"{booking_date.strftime('%Y-%m-%d')} {time}",
            "%Y-%m-%d %H:%M"
        )
 
        end_datetime = start_datetime + timedelta(hours=1)
 
        event = {
            'summary': 'Vehicle Service Booking',
            'description': (
                f"NexAI Booking\n\n"
                f"Name: {details.get('name')}\n"
                f"Vehicle: {details.get('vehicle')}\n"
                f"Contact: {details.get('contact')}\n\n"
                f"Day: {day}\n"
                f"Time: {time}"
            ),
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Africa/Johannesburg',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Africa/Johannesburg',
            }
        }
 
        print("SENDING EVENT TO CALENDAR...")
 
        service.events().insert(
            calendarId='170013714c22b8ae82dd253ea8480175e8ad8708ec57997dddd64a411be8ad41@group.calendar.google.com',
            body=event
        ).execute()
 
        print("EVENT CREATED SUCCESSFULLY")
 
        return booking_date
 
    except Exception as e:
        import traceback
        print("CALENDAR ERROR:", e)
        traceback.print_exc()
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
 
        if 0 <= idx < len(session.get("days", [])):
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
 
        if 0 <= idx < len(session.get("times", [])):
            session["selected_time"] = session["times"][idx]
            session["state"] = "name"
 
            return {"text": "Enter your name:"}
 
    if session.get("state") == "name":
        session["name"] = msg
        session["state"] = "vehicle"
 
        return {"text": "Enter vehicle type (e.g. Toyota Corolla):"}
 
    if session.get("state") == "vehicle":
        session["vehicle"] = msg
        session["state"] = "contact"
 
        return {"text": "Enter contact email:"}
 
    if session.get("state") == "contact":
 
        session["contact"] = msg
 
        day = session["selected_day"]
        time = session["selected_time"]
 
        print("ABOUT TO CREATE EVENT:", day, time)
 
        booking_date = create_calendar_event(day, time, session)
 
        name = session["name"]
        vehicle = session["vehicle"]
        contact = session["contact"]
 
        # NON-BLOCKING EMAIL (FIX)
        threading.Thread(
            target=send_email,
            args=(
                contact,
                name,
                vehicle,
                booking_date.strftime('%d/%m/%Y'),
                time
            )
        ).start()
 
        session.clear()
 
        return {
            "text": (
                "Booking Confirmed\n\n"
                f"Name: {name}\n"
                f"Vehicle: {vehicle}\n"
                f"Contact: {contact}\n\n"
                f"Date: {booking_date.strftime('%d/%m/%Y')}\n"
                f"Day: {day}\n"
                f"Time: {time}\n"
                "Confirmation email is being sent"
            )
        }
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Automotive assistant."},
            {"role": "user", "content": msg}
        ],
        max_tokens=120
    )
 
    return {"text": response.choices[0].message.content}
 
 
# -------------------------
# IT MODULE
# -------------------------
def it_ai(msg):
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Enterprise IT Admin Assistant."},
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
 
    return {"text": reply}
 
 
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