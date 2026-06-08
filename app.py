import os
import threading
import sqlite3
import requests
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
# SLACK / EMAIL / CALENDAR
# -------------------------
def send_to_slack(msg):
    try:
        webhook=os.getenv("SLACK_WEBHOOK_URL")
        if webhook:
            requests.post(webhook,json={"text":msg})
    except:
        pass
 
def send_email(email,name,vehicle,date,time):
    try:
        sg=SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        msg=Mail(
            from_email=os.getenv("EMAIL_USER"),
            to_emails=email,
            subject="Booking Confirmed",
            html_content=f"&lt;h3&gt;Hello {name}&lt;/h3&gt;&lt;p&gt;{vehicle} booked for {date} at {time}&lt;/p&gt;"
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
                'start':{'dateTime':start.isoformat(),'timeZone':'Africa/Johannesburg'},
                'end':{'dateTime':end.isoformat(),'timeZone':'Africa/Johannesburg'}
            }
        ).execute()
    except:
        pass
 
# -------------------------
# IMAGE AI
# -------------------------
def process_it_image(img):
    try:
        r=get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role":"system",
                    "content":(
                        "You are NexAI Assist, an enterprise IT assistant.\n"
                        "ONLY analyze images related to enterprise IT.\n"
                        "If not IT-related, respond:\n"
                        "'This image is not related to enterprise IT systems.'"
                    )
                },
                {
                    "role":"user",
                    "content":[
                        {"type":"text","text":"Explain this image"},
                        {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img}"}}
                    ]
                }
            ]
        )
        return r.choices[0].message.content
    except:
        return "Image analysis failed"
 
# -------------------------
# VEHICLE
# -------------------------
def vehicle_ai(msg,session):
    text=msg.lower()
 
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
        return {"text":"Select time:\n"+"\n".join(
            f"{i+1}. {t}" for i,t in enumerate(session["times"])
        )}
 
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
            return {"text":"⚠️ The selected time slot is already booked.\n\nPlease start again."}
 
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
 
        threading.Thread(
            target=send_email,
            args=(data["email"],data["name"],data["vehicle"],date,time)
        ).start()
 
        session.clear()
 
        return {"text":f"Booking confirmed\nID:{booking_id}"}
 
    # ADDED: DOMAIN CONSTRAINT ONLY
    r=get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":
                "Only respond to vehicle services, bookings, and mechanical issues. "
                "Otherwise respond: 'This module handles vehicle servicing, bookings, and mechanical-related queries only.'"
            },
            {"role":"user","content":msg}
        ]
    )
    return {"text":r.choices[0].message.content}
 
# -------------------------
# ASSIST (IT)
# -------------------------
def it_ai(msg):
    r=get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":
                "Strictly answer enterprise IT queries only including Azure, Entra, RBAC, NSG, Key Vault, Automation, Storage, App Service, Azure SQL, DHCP, DNS, AD Sync, GPO, Clustering, DFS, Exchange, Intune, Purview, Power BI, Security, SharePoint, Teams. "
                "Otherwise respond: 'This request is outside enterprise IT support scope.'"
            },
            {"role":"user","content":msg}
        ]
    )
    return {"text":r.choices[0].message.content}
 
# -------------------------
# ROUTES
# -------------------------
 
@app.get("/vehicle")
def vehicle():
    return send_from_directory(BASE_DIR, "index_vehicle.html")
 
 
@app.get("/it")
def it():
    return send_from_directory(BASE_DIR, "index_it.html")
 
 
@app.post("/chat")
def chat():
    data=request.get_json()
    msg=data.get("message","")
    module=data.get("module","it")
    sid=data.get("session_id","default")
 
    if sid not in sessions:
        sessions[sid]={}
 
    # ADDITION: AUTO IMAGE USE (does not remove your logic)
    if module == "it" and sid in last_images:
        try:
            return jsonify({"text": process_it_image(last_images[sid])})
        except:
            pass
 
    image_keywords = ["image","screenshot","attached","uploaded"]
 
    # ORIGINAL LOGIC PRESERVED
    if any(word in msg.lower() for word in image_keywords):
        if sid in last_images:
            return jsonify({"text": process_it_image(last_images[sid])})
        else:
            return jsonify({
                "text": "No image found in this session. Please upload an image first."
            })
 
    if module=="vehicle":
        return jsonify(vehicle_ai(msg,sessions[sid]))
 
    return jsonify(it_ai(msg))
 
 
@app.post("/analyze-image")
def analyze_image():
    file=request.files.get("image")
    sid=request.form.get("session_id","default")
 
    if not file:
        return {"text":"No image"}
 
    img=base64.b64encode(file.read()).decode()
    last_images[sid]=img
 
    return {"text":process_it_image(img)}
 
 
@app.post("/upload")
def upload():
    file=request.files.get("image")
 
    if not file:
        return {"error":"no file"},400
 
    file.save(os.path.join(UPLOAD_FOLDER,file.filename))
 
    return {"status":"ok"}
 
 
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)
 
 
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(BASE_DIR,'favicon.ico')
 
 
# -------------------------
# RUN
# -------------------------
if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    print(f"Running on {port}")
    app.run(host="0.0.0.0",port=port, debug=False)