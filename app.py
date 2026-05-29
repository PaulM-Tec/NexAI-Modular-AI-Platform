import os
import threading
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
 
from google.oauth2 import service_account
from googleapiclient.discovery import build
 
# -------------------------
# INIT
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
app = Flask(__name__)
CORS(app)
 
DB_PATH = os.path.join(os.getcwd(), "bookings.db")
sessions = {}
 
# -------------------------
# DATABASE
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
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
# UTIL
# -------------------------
def generate_booking_id():
    return f"NX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
 
def calculate_date(day):
    today = datetime.now()
 
    days_map = {
        "monday":0,
        "tuesday":1,
        "wednesday":2,
        "thursday":3,
        "friday":4
    }
 
    target = days_map[day.lower()]
    diff = (target - today.weekday()) % 7
    if diff == 0:
        diff = 7
 
    return today + timedelta(days=diff)
 
def is_slot_taken(day, time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
 
    cursor.execute(
        "SELECT 1 FROM bookings WHERE day=? AND time=?",
        (day, time)
    )
 
    result = cursor.fetchone()
    conn.close()
 
    return result is not None
 
def save_booking(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
 
    cursor.execute("""
    INSERT INTO bookings VALUES (NULL,?,?,?,?,?,?,?,?)
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
 
# -------------------------
# EMAIL (FIXED CLEAN FORMAT)
# -------------------------
def send_email(email, name, vehicle, date, time):
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
 
        message = Mail(
            from_email=os.getenv("EMAIL_USER"),
            to_emails=email,
            subject="Vehicle Service Booking Confirmed",
            html_content=f"""
            <div style="font-family:Arial; padding:15px;">
                <h2 style="margin-bottom:10px;">Booking Confirmed</h2>
 
                <p>Hello {name},</p>
 
                <p>Your booking has been confirmed.</p>
 
                <p><b>Vehicle:</b> {vehicle}</p>
                <p><b>Date:</b> {date}</p>
                <p><b>Time:</b> {time}</p>
 
                <br>
 
                <p>Thank you for using NexAI</p>
            </div>
            """
        )
 
        sg.send(message)
 
    except Exception as e:
        print("Email error:", e)
 
# -------------------------
# CALENDAR (FIXED)
# -------------------------
def create_calendar_event(day, time, details):
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=['https://www.googleapis.com/auth/calendar']
        )
 
        service = build('calendar', 'v3', credentials=creds)
 
        date_obj = calculate_date(day)
 
        start = datetime.strptime(
            f"{date_obj.strftime('%Y-%m-%d')} {time}",
            "%Y-%m-%d %H:%M"
        )
 
        end = start + timedelta(hours=1)
 
        event = {
            'summary': 'Vehicle Service Booking',
            'description': f"""
Booking ID: {details['booking_id']}
Name: {details['name']}
Vehicle: {details['vehicle']}
Email: {details['email']}
Phone: {details['phone']}
""",
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'Africa/Johannesburg'
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'Africa/Johannesburg'
            }
        }
 
        service.events().insert(
            calendarId=os.getenv("CALENDAR_ID"),
            body=event
        ).execute()
 
        print("Calendar event created")
 
    except Exception as e:
        print("Calendar error:", e)
 
# -------------------------
# VEHICLE MODULE (ONLY OUTPUT FIXED)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    if "book" in text or "service" in text:
        session.clear()
 
        days = []
        current = datetime.now()
 
        while len(days) < 5:
            current += timedelta(days=1)
            if current.weekday() < 5:
                days.append(current.strftime("%A"))
 
        session["days"] = days
        session["state"] = "day"
 
        return {
            "text": "Select a day:\n" + "\n".join(
                f"{i+1}. {d}" for i, d in enumerate(days)
            )
        }
 
    if session.get("state") == "day" and msg.isdigit():
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["days"]):
            session["selected_day"] = session["days"][idx]
            session["times"] = ["08:00", "10:00", "13:00", "15:00"]
            session["state"] = "time"
 
            return {
                "text": "Select time:\n" + "\n".join(
                    f"{i+1}. {t}" for i, t in enumerate(session["times"])
                )
            }
 
    if session.get("state") == "time" and msg.isdigit():
        idx = int(msg) - 1
 
        if 0 <= idx < len(session["times"]):
            session["selected_time"] = session["times"][idx]
            session["state"] = "name"
            return {"text": "Enter name:"}
 
    if session.get("state") == "name":
        session["name"] = msg
        session["state"] = "vehicle"
        return {"text": "Enter vehicle:"}
 
    if session.get("state") == "vehicle":
        session["vehicle"] = msg
        session["state"] = "email"
        return {"text": "Enter email:"}
 
    if session.get("state") == "email":
        session["email"] = msg
        session["state"] = "phone"
        return {"text": "Enter phone:"}
 
    if session.get("state") == "phone":
 
        day = session["selected_day"]
        time = session["selected_time"]
 
        if is_slot_taken(day, time):
            return {"text": "Slot already booked. Choose another time."}
 
        booking_id = generate_booking_id()
        date_obj = calculate_date(day)
        formatted_date = date_obj.strftime('%d/%m/%Y')
 
        data = {
            "booking_id": booking_id,
            "name": session["name"],
            "vehicle": session["vehicle"],
            "email": session["email"],
            "phone": msg,
            "day": day,
            "time": time,
            "date": formatted_date
        }
 
        save_booking(data)
        create_calendar_event(day, time, data)
 
        threading.Thread(
            target=send_email,
            args=(data["email"], data["name"], data["vehicle"], formatted_date, time)
        ).start()
 
        session.clear()
 
        # CLEAN OUTPUT FIX
        return {
            "text": f"""Booking Confirmed
 
Booking ID: {booking_id}
 
Name: {data['name']}
Vehicle: {data['vehicle']}
Email: {data['email']}
Phone: {data['phone']}
 
Date: {formatted_date}
Time: {time}
"""
        }
 
    # DO NOT TOUCH AI (YOU SAID WORKING)
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":msg}],
            max_tokens=150
        )
        return {"text": r.choices[0].message.content}
    except:
        return {"text": "AI unavailable"}