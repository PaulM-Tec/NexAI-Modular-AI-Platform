import os
import requests
import threading
import sqlite3
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
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
 
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
 
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# DATABASE INIT NEW
# -------------------------
def init_db():
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT,
        name TEXT,
        vehicle TEXT,
        email TEXT,
        phone TEXT,
        day TEXT,
        time TEXT,
        date TEXT
    )
    """)
 
    conn.commit()
    conn.close()
 
init_db()
 
 
# -------------------------
# BOOKING ID GENERATOR NEW
# -------------------------
def generate_booking_id():
    return f"NX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
 
 
# -------------------------
# SAVE BOOKING NEW
# -------------------------
def save_booking(data):
 
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
 
    cursor.execute("""
    INSERT INTO bookings (
        booking_id, name, vehicle, email, phone, day, time, date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["booking_id"],
        data["name"],
        data["vehicle"],
        data["email"],
        data["phone"],
        data["day"],
        data["time"],
        data["date"]
    ))
 
    conn.commit()
    conn.close()
 
    print("Booking saved:", data["booking_id"])
 
 
# -------------------------
# SENDGRID EMAIL FUNCTION
# -------------------------
def send_email(to_email, name, vehicle, date, time):
    try:
        print("Sending email via SendGrid...")
 
        message = Mail(
            from_email=EMAIL_USER,
            to_emails=to_email,
            subject='Vehicle Service Booking Confirmed',
            html_content=f"""
            <h3>Hello {name},</h3>
            <p>Your booking has been confirmed</p>
            <p><b>Vehicle:</b> {vehicle}</p>
            <p><b>Date:</b> {date}</p>
            <p><b>Time:</b> {time}</p>
            <br>
            <p>Thank you for using NexAI</p>
            """
        )
 
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
 
        print("SendGrid response:", response.status_code)
 
    except Exception as e:
        import traceback
        print("SendGrid error:", e)
        traceback.print_exc()
 
 
# -------------------------
# SLACK FUNCTION
# -------------------------
def send_to_slack(message):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
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
            return datetime.now()
 
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
 
        booking_date = today + timedelta(days=days_ahead)
 
        start_datetime = datetime.strptime(
            f"{booking_date.strftime('%Y-%m-%d')} {time}",
            "%Y-%m-%d %H:%M"
        )
 
        end_datetime = start_datetime + timedelta(hours=1)
 
        event = {
            'summary': 'Vehicle Service Booking',
            'description': (
                f"NexAI Booking\n\n"
                f"Booking ID: {details.get('booking_id', 'N/A')}\n"
                f"Name: {details.get('name')}\n"
                f"Vehicle: {details.get('vehicle')}\n"
                f"Email: {details.get('email')}\n"
                f"Phone: {details.get('phone')}\n\n"
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
 
        service.events().insert(
            calendarId='170013714c22b8ae82dd253ea8480175e8ad8708ec57997dddd64a411be8ad41@group.calendar.google.com',
            body=event
        ).execute()
 
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
        session["state"] = "email"
        return {"text": "Enter your email:"}
 
    if session.get("state") == "email":
        session["email"] = msg
        session["state"] = "phone"
        return {"text": "Enter phone number:"}
 
    if session.get("state") == "phone":
 
        session["phone"] = msg
 
        day = session["selected_day"]
        time = session["selected_time"]
 
        booking_id = generate_booking_id()
        session["booking_id"] = booking_id
 
        booking_date = create_calendar_event(day, time, session)
 
        booking_data = {
            "booking_id": booking_id,
            "name": session["name"],
            "vehicle": session["vehicle"],
            "email": session["email"],
            "phone": session["phone"],
            "day": day,
            "time": time,
            "date": booking_date.strftime('%d/%m/%Y')
        }
 
        save_booking(booking_data)
 
        threading.Thread(
            target=send_email,
            args=(
                booking_data["email"],
                booking_data["name"],
                booking_data["vehicle"],
                booking_data["date"],
                booking_data["time"]
            )
        ).start()
 
        session.clear()
 
        return {
            "text": (
                "Booking Confirmed\n\n"
                f"Booking ID: {booking_id}\n"
                f"Name: {booking_data['name']}\n"
                f"Vehicle: {booking_data['vehicle']}\n"
                f"Email: {booking_data['email']}\n"
                f"Phone: {booking_data['phone']}\n\n"
                f"Date: {booking_data['date']}\n"
                f"Time: {booking_data['time']}\n"
                "Confirmation email sent"
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
 
@app.get("/bookings")
def view_bookings():
    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
 
    cursor.execute("SELECT * FROM bookings")
    rows = cursor.fetchall()
 
    conn.close()
 
    return jsonify(rows)
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)