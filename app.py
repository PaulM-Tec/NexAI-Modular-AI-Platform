import os
import threading
import sqlite3
import requests  # ADDED FOR SLACK
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
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4
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
# SLACK (RESTORED ONLY)
# -------------------------
def send_to_slack(message):
    try:
        webhook = os.getenv("SLACK_WEBHOOK_URL")
 
        if not webhook:
            print("Slack webhook missing")
            return
 
        response = requests.post(
            webhook,
            json={"text": message},
            timeout=5
        )
 
        if response.status_code == 200:
            print("Sent to Slack")
        else:
            print("Slack error:", response.text)
 
    except Exception as e:
        print("Slack exception:", str(e))
 
# -------------------------
# EMAIL (UNCHANGED)
# -------------------------
def send_email(email, name, vehicle, date, time):
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        message = Mail(
            from_email=os.getenv("EMAIL_USER"),
            to_emails=email,
            subject="Vehicle Booking Confirmed",
            html_content=f"""
<h3>Hello {name}</h3>
<p>Your booking has been confirmed</p>
<p><b>Vehicle:</b> {vehicle}</p>
<p><b>Date:</b> {date}</p>
<p><b>Time:</b> {time}</p>
<p>Thank you for using NexAI</p>
            """
        )
        sg.send(message)
    except Exception as e:
        print("Email error:", e)
 
# -------------------------
# CALENDAR (UNCHANGED)
# -------------------------
def create_calendar_event(day, time, details):
    try:
        print("Starting calendar creation")
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
            'summary': 'Vehicle Booking',
            'description': f"""
NexAI Booking
Booking ID: {details['booking_id']}
Name: {details['name']}
Vehicle: {details['vehicle']}
Email: {details['email']}
Phone: {details['phone']}
Day: {details['day']}
Time: {details['time']}
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
 
        calendar_id = os.getenv("CALENDAR_ID")
        print("Using calendar:", calendar_id)
 
        service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
 
        print("Calendar event CREATED SUCCESSFULLY")
 
    except Exception as e:
        print("Calendar error FULL:", str(e))
 
# -------------------------
# VEHICLE MODULE (UNCHANGED)
# -------------------------
def vehicle_ai(msg, session):
    text = msg.lower()
 
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
 
        return {
            "text": "Select a day:\n" + "\n".join(
                f"{i+1}. {d}" for i, d in enumerate(days)
            )
        }
 
    if session.get("state") == "day" and msg.isdigit():
        idx = int(msg) - 1
        if 0 <= idx < len(session["days"]):
            session["selected_day"] = session["days"][idx]
            session["state"] = "time"
            session["times"] = ["08:00", "10:00", "13:00", "15:00"]
 
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
            session.clear()
            return {"text": "Slot already booked. Please start a new booking or ask a question."}
 
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
 
        return {"text": f"""Booking Confirmed
Booking ID: {booking_id}
Name: {data['name']}
Vehicle: {data['vehicle']}
Email: {data['email']}
Phone: {data['phone']}
Date: {formatted_date}
Time: {time}
"""}
 
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg}],
            max_tokens=150
        )
        return {"text": r.choices[0].message.content}
    except:
        return {"text": "AI unavailable"}
 
# -------------------------
# IT MODULE (SLACK ADDED)
# -------------------------
def it_ai(msg):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg}],
            max_tokens=200
        )
 
        reply = r.choices[0].message.content
 
        # SEND TO SLACK
        send_to_slack(f"""
🖥️ NexAI IT Assistant
 
Query:
{msg}
 
Response:
{reply}
""")
 
        return {"text": reply}
 
    except:
        return {"text": "IT assistant unavailable"}
 
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
 
    msg = data.get("message", "")
    module = data.get("module", "vehicle")
    sid = data.get("session_id", "default")
 
    if sid not in sessions:
        sessions[sid] = {}
 
    if module == "vehicle":
        result = vehicle_ai(msg, sessions[sid])
    else:
        result = it_ai(msg)
 
    return jsonify(result)

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico', mimetype='image/vnd.microsoft.icon')
 
# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)