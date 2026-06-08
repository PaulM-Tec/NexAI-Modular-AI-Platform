import os
import threading
import requestsimport sqlite3
import base64
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
client = None
 
def get_client():
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client
 
app = Flask(__name__)
CORS(app)
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bookings.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 
sessions = {}
last_images = {}
 
# -------------------------
# HEALTH
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}
 
# -------------------------
# DB
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
        "monday":0,"tuesday":1,"wednesday":2,
        "thursday":3,"friday":4
    }
    target = days_map[day.lower()]
    diff = (target - today.weekday()) % 7
    return today + timedelta(days=7 if diff == 0 else diff)
 
def is_slot_taken(day,time):
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    cursor.execute("SELECT 1 FROM bookings WHERE day=? AND time=?", (day,time))
    result=cursor.fetchone()
    conn.close()
    return result is not None
 
def save_booking(data):
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    cursor.execute("""
    INSERT INTO bookings VALUES (NULL,?,?,?,?,?,?,?,?)
    """,(
        data["booking_id"],data["name"],data["vehicle"],
        data["email"],data["phone"],data["day"],
        data["time"],data["date"]
    ))
    conn.commit()
    conn.close()
 
# -------------------------
# EMAIL / CALENDAR
# -------------------------
def send_email(email,name,vehicle,date,time):
    try:
        sg=SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        msg=Mail(
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
        sg.send(msg)
    except:
        pass
 
def create_calendar_event(day,time,data):
    try:
        creds=service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        service=build('calendar','v3',credentials=creds)
 
        date_obj=calculate_date(day)
        start=datetime.strptime(
            f"{date_obj.strftime('%Y-%m-%d')} {time}",
            "%Y-%m-%d %H:%M"
        )
        end=start+timedelta(hours=1)
 
        service.events().insert(
            calendarId=os.getenv("CALENDAR_ID"),
            body={
                'summary':'Vehicle Booking',
                'description': f"""
Booking Confirmed
 
Booking ID: {data["booking_id"]}
Name: {data["name"]}
Vehicle: {data["vehicle"]}
Email: {data["email"]}
Phone: {data["phone"]}
 
Day: {data["day"]}
Date: {data["date"]}
Time: {data["time"]}
""",
                'start':{'dateTime':start.isoformat(),'timeZone':'Africa/Johannesburg'},
                'end':{'dateTime':end.isoformat(),'timeZone':'Africa/Johannesburg'}
            }
        ).execute()
    except:
        pass
 
# -------------------------
# VEHICLE AI ✅ FIXED
# -------------------------
def vehicle_ai(msg,session):
    text = msg.lower().strip()
 
    # ✅ Conversational responses
    if text in ["thanks","thank you","ok","okay"]:
        return {"text":"You're welcome 👍 Let me know if you need anything else"}
 
    if text in ["no","no thanks"]:
        return {"text":"No problem 👍 I'm here if you need help with your vehicle"}
 
    # ✅ YES (FIXED)
    if text in ["yes","yeah","sure","ok","okay"]:
        if session.get("last_intent") == "offer_booking" or "state" not in session:
            session["state"] = "day"
 
            days=[]
            now=datetime.now()
            while len(days)<5:
                now+=timedelta(days=1)
                if now.weekday()<5:
                    days.append(now.strftime("%A"))
 
            session["days"]=days
 
            return {"text":"Select day:\n"+"\n".join(f"{i+1}. {d}" for i,d in enumerate(days))}
 
    # ✅ Booking flow unchanged
    if "book" in text or "service" in text:
        session.clear()
 
        days=[]
        now=datetime.now()
        while len(days)<5:
            now+=timedelta(days=1)
            if now.weekday()<5:
                days.append(now.strftime("%A"))
 
        session["state"]="day"
        session["days"]=days
        return {"text":"Select day:\n"+"\n".join(f"{i+1}. {d}" for i,d in enumerate(days))}
 
    if session.get("state")=="day" and msg.isdigit():
        session["selected_day"]=session["days"][int(msg)-1]
        session["state"]="time"
        session["times"]=["08:00","10:00","13:00","15:00"]
        return {"text":"Select time:\n"+"\n".join(f"{i+1}. {t}" for i,t in enumerate(session["times"]))}
 
    if session.get("state")=="time" and msg.isdigit():
        session["selected_time"]=session["times"][int(msg)-1]
        session["state"]="name"
        return {"text":"Enter name:"}
 
    if session.get("state")=="name":
        session["name"]=msg
        session["state"]="vehicle"
        return {"text":"Enter vehicle:"}
 
    if session.get("state")=="vehicle":
        session["vehicle"]=msg
        session["state"]="email"
        return {"text":"Enter email:"}
 
    if session.get("state")=="email":
        session["email"]=msg
        session["state"]="phone"
        return {"text":"Enter phone:"}
 
    if session.get("state")=="phone":
        day=session["selected_day"]
        time=session["selected_time"]
 
        if is_slot_taken(day,time):
            session.clear()
            return {"text":"⚠️ Slot already booked"}
 
        booking_id=generate_booking_id()
        date=calculate_date(day).strftime('%d/%m/%Y')
 
        data={
            "booking_id":booking_id,
            "name":session["name"],
            "vehicle":session["vehicle"],
            "email":session["email"],
            "phone":msg,
            "day":day,
            "time":time,
            "date":date
        }
 
        save_booking(data)
        create_calendar_event(day,time,data)
 
        threading.Thread(target=send_email,args=(data["email"],data["name"],data["vehicle"],date,time)).start()
 
        session.clear()
 
        return {"text":f"""Booking Confirmed
 
ID: {booking_id}
Vehicle: {data["vehicle"]}
Date: {date}
Time: {time}
"""}
 
    # ✅ Structured AI
    r=get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":
                "You are a vehicle assistant. Only answer vehicle issues.\n"
                "Structure responses clearly:\n"
                "Problem\nCauses\nRecommended actions\nThen ask to book service."
            },
            {"role":"user","content":msg}
        ]
    )
 
    session["last_intent"]="offer_booking"
 
    return {"text":r.choices[0].message.content}
 
# -------------------------
# ROUTES
# -------------------------
@app.post("/chat")
def chat():
    data=request.get_json()
    msg=data.get("message","")
    module=data.get("module","vehicle")
    sid=data.get("session_id","default")
 
    if sid not in sessions:
        sessions[sid]={}
 
    return jsonify(vehicle_ai(msg,sessions[sid]))
 
@app.post("/upload")
def upload():
    file=request.files.get("image")
    if not file:
        return {"error":"no file"},400
    file.save(os.path.join(UPLOAD_FOLDER,file.filename))
    return {"status":"ok"}
 
# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)