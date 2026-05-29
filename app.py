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
 
# GOOGLE CALENDAR
from google.oauth2 import service_account
from googleapiclient.discovery import build
 
# -------------------------
# ENV
# -------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
 
DB_PATH = os.path.join(os.getcwd(), "bookings.db")
 
app = Flask(__name__)
CORS(app)
 
sessions = {}
 
# -------------------------
# DATABASE INIT
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
 
def is_slot_taken(day, time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
 
    cursor.execute(
        "SELECT 1 FROM bookings WHERE day = ? AND time = ?",
        (day, time)
    )
 
    result = cursor.fetchone()
    conn.close()
    return result is not None
 
def save_booking(data):
    conn = sqlite3.connect(DB_PATH)
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
 
# -------------------------
# EMAIL
# -------------------------
def send_email(to_email, name, vehicle, date, time):
    try:
        message = Mail(
            from_email=EMAIL_USER,
            to_emails=to_email,
            subject='Vehicle Service Booking Confirmed',
            html_content=f"""
            <h3>Hello {name}</h3>
            <p>Your booking is confirmed</p>
            <p><b>Vehicle:</b> {vehicle}</p>
            <p><b>Date:</b> {date}</p>
            <p><b>Time:</b> {time}</p>
            """
        )
 
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
 
    except Exception as e:
        print("Email error:", e)
 
# -------------------------
# CALENDAR
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
        days_map = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4}
 
        target_day = days_map.get(day.lower())
        days_ahead = (target_day - today.weekday()) % 7 or 7
 
        booking_date = today + timedelta(days=days_ahead)
 
        start_time = datetime.strptime(
            f"{booking_date.date()} {time}",
            "%Y-%m-%d %H:%M"
        )
 
        end_time = start_time + timedelta(hours=1)
 
        event = {
            'summary': 'Vehicle Booking',
            'description': f"{details}",
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Africa/Johannesburg'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Africa/Johannesburg'}
        }
 
        service.events().insert(
            calendarId=os.getenv("CALENDAR_ID"),
            body=event
        ).execute()
 
    except Exception as e:
        print("Calendar error:", e)
 
# -------------------------
# VEHICLE MODULE (FIXED)
# -------------------------
def vehicle_ai(msg, session):
 
    text = msg.lower()
 
    # START BOOKING FLOW
    if "book" in text or "service" in text:
        session.clear()
 
        days = []
        now = datetime.now()
 
        while len(days) < 5:
            now += timedelta(days=1)
            if now.weekday() < 5:
                days.append(now.strftime("%A"))
 
        session["state"] = "day"
        session["days"] = days
 
        return {"text": "Select a day:\n" + "\n".join(f"{i+1}. {d}" for i,d in enumerate(days))}
 
    # FLOW HANDLING
    if session.get("state") == "day" and msg.isdigit():
        i = int(msg)-1
        if i < len(session["days"]):
            session["selected_day"] = session["days"][i]
            session["times"] = ["08:00","10:00","13:00","15:00"]
            session["state"] = "time"
 
            return {"text": "Select time:\n" + "\n".join(f"{i+1}. {t}" for i,t in enumerate(session["times"]))}
 
    if session.get("state") == "time" and msg.isdigit():
        i = int(msg)-1
        if i < len(session["times"]):
            session["selected_time"] = session["times"][i]
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
 
        date = datetime.now() + timedelta(days=1)
        formatted_date = date.strftime("%d/%m/%Y")
 
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
 
        return {"text": f"""
Booking Confirmed
 
ID: {booking_id}
Date: {formatted_date}
Time: {time}
"""}
 
    # FALLBACK AI (IMPORTANT FIX)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":msg}],
            max_tokens=150
        )
        return {"text": response.choices[0].message.content}
    except Exception as e:
        print("AI error:", e)
        return {"text": "Unable to process request right now."}
 
 
# -------------------------
# IT MODULE (FIXED)
# -------------------------
def it_ai(msg):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":msg}],
            max_tokens=200
        )
        return {"text": response.choices[0].message.content}
    except Exception as e:
        print("IT error:", e)
        return {"text": "IT assistant unavailable."}
 
 
# -------------------------
# ROUTES
# -------------------------
@app.get("/vehicle")
def vehicle():
    return send_from_directory(".", "index_vehicle.html")
 
@app.get("/it")
def it():
    return send_from_directory(".", "index_it.html")
 
@app.post("/chat")
def chat():
    data = request.get_json()
    msg = data.get("message","")
    module = data.get("module","vehicle")
    sid = data.get("session_id","default")
 
    if sid not in sessions:
        sessions[sid] = {}
 
    if module == "vehicle":
        result = vehicle_ai(msg, sessions[sid])
    else:
        result = it_ai(msg)
 
    return jsonify(result)
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)