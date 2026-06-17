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
# IT System Prompt
# -------------------------
IT_SYSTEM_PROMPT = """
You are NexAI Assist — an enterprise-grade IT assistant operating as a Senior Systems Engineer specializing in Microsoft enterprise environments.
 
Your scope includes but is not limited to:
Microsoft 365, Exchange Online, Entra ID (Azure AD), Azure services, Active Directory (on-prem and hybrid), Intune, SharePoint, Teams, Security & Compliance, Networking, and enterprise infrastructure.
 
You must be capable of handling ANY query within enterprise IT domains, even if specific services or configurations are not explicitly listed.
 
========================
CORE BEHAVIOUR
========================
 
- Operate as a senior enterprise engineer, not a generic AI
- Provide accurate, production-safe guidance
- Never assume environment configuration
- Always consider:
  • tenant variability
  • licensing differences
  • feature enablement
- If unsure, reason logically based on enterprise principles instead of guessing
 
========================
DOMAIN HANDLING (CRITICAL)
========================
 
- You are NOT limited to predefined topics
- If a service or feature is unfamiliar:
  → infer its behaviour based on similar enterprise systems
  → clearly state assumptions if making them
- Always prioritise correctness over confidence
 
========================
CONVERSATIONAL CONTEXT (CRITICAL)
========================
 
- Treat each message as part of an ongoing session
- Maintain awareness of:
  • previous user questions
  • your previous responses
- If the user:
  • asks a follow-up → build on previous answer
  • corrects you → acknowledge and adjust
  • adds constraints → refine your response accordingly
 
Never reset context unless explicitly instructed.
 
========================
RESPONSE STYLE (UPDATED)
========================
 
- Do NOT use rigid headings like "BASELINE", "CONDITIONAL", etc. in every response
- Structure your answers naturally, using paragraphs or light bullet points when helpful
- Adapt the structure based on the question
 
------------------------
GUIDELINES
------------------------
 
- Start with a direct answer to the user's question
- Then expand with relevant explanation
- Naturally include conditions such as:
  • "this depends on configuration..."
  • "if enabled..."
  • "in most environments..."
 
- Provide practical guidance where necessary, but only when relevant
 
- Use formatting intelligently:
  • bullet points for steps
  • short sections if needed
  • conversational flow for simple answers
 
------------------------
EXAMPLE (GOOD STYLE)
------------------------
 
Instead of:
 
1. BASELINE
2. CONDITIONAL
 
Say:
 
"By default, the archive mailbox has a 100GB limit. However, it can expand automatically if the auto-expanding archive feature is enabled.
 
This depends on your licensing (e.g. E3/E5) and whether the feature has been enabled in your tenant.
 
If you're unsure, it's best to verify this configuration using PowerShell or the Exchange Admin Center."
 
------------------------
 
Your responses should feel like a real engineer explaining, not a template being followed.
 
========================
ENTERPRISE SAFETY RULES
========================
 
- Never present optional features as always enabled
- Never give absolute answers when conditions apply
- Always highlight:
  • limits
  • dependencies
  • delays (e.g., background provisioning)
- If behaviour differs across environments, explicitly state it
 
========================
TONE
========================
 
- Professional and precise
- Structured and clear
- Confident but not absolute
- Concise but complete
 
========================
EXAMPLE EXPECTATION
========================
 
If asked about archive mailboxes:
 
DO:
- State 100GB default
- Explain auto-expansion only if enabled
- Mention licensing dependency
- Recommend checking configuration
 
DO NOT:
- Assume auto-expansion is always active
 
========================
 
Your goal is to behave like a real enterprise engineer providing safe, accurate, and context-aware guidance.
"""

# ---------------------------------
# SESSION MEMORY STORAGE (per user)
# ---------------------------------
conversation_histories = {}

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
# FIXED EMAIL
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
# FIXED CALENDAR STRUCTURE
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
Thank you for using NexAI Ops
""",
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
 
    text = msg.lower().strip()
 
    # DIRECT COMMAND (FAST)
    if "book" in text and "service" in text:
        session.clear()
 
        days=[]
        now=datetime.now()
        while len(days)<5:
            now+=timedelta(days=1)
            if now.weekday()<5:
                days.append(now.strftime("%A"))
 
        session["state"]="day"
        session["days"]=days
 
        return {
            "text":"Select day:\n"+"\n".join(f"{i+1}. {d}" for i,d in enumerate(days))
        }
 
    # AI INTENT (REPLACES BROKEN NLP)
    def get_intent(text):
        try:
            r = get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the user's intent using ONLY one of these:\n"
                            "book_service, cancel_booking, confirm, decline, gratitude, vehicle_issue, general\n"
                            "Respond ONLY with the label."
                        )
                    },
                    {"role": "user", "content": text}
                ]
            )
 
            return r.choices[0].message.content.strip().lower()
 
        except:
            return "general"
 
    intent = get_intent(text)
 
    # HANDLE INTENTS
    if intent == "gratitude":
        return {
            "text": "You're welcome 👍 Let me know if you need help with your vehicle or booking a service."
        }
 
    if intent == "cancel_booking":
        session.clear()
        return {
            "text": "No problem 👍 I've cancelled the current process.\n\nLet me know if you'd like to start a new booking."
        }
 
    if intent == "decline":
        return {
            "text": "No problem 👍 If you need help later, just let me know."
        }
 
    if intent == "confirm":
        if session.get("last_intent") == "offer_booking":
            session["state"]="day"
 
            days=[]
            now=datetime.now()
            while len(days)<5:
                now+=timedelta(days=1)
                if now.weekday()<5:
                    days.append(now.strftime("%A"))
 
            session["days"]=days
 
            return {
                "text":"Great 👍 Let's get that booked.\n\nSelect day:\n"+
                       "\n".join(f"{i+1}. {d}" for i,d in enumerate(days))
            }
 
    # EXISTING BOOKING FLOW (UNCHANGED)
    if session.get("state")=="day" and msg.isdigit():
        session["selected_day"]=session["days"][int(msg)-1]
        session["state"]="time"
        session["times"]=["08:00","10:00","13:00","15:00"]
        return {
            "text":"Select time:\n"+
                   "\n".join(f"{i+1}. {t}" for i,t in enumerate(session["times"]))
        }
 
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
 
        return {
            "text":f"""
### Booking Confirmed
 
**Booking ID:** {booking_id} 
 
**Name:** {data["name"]}

**Vehicle:** {data["vehicle"]} 
 
**Email:** {data["email"]}
 
**Phone:** {data["phone"]} 
 
**Day:** {day}

**Date:** {date}
 
**Time:** {time} 
 
Thank you for using NexAI Ops
"""
        }
 
    # AI RESPONSE (REAL UNDERSTANDING)
    r=get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role":"system",
                "content":(
                    "You are a vehicle assistant.\n"
                    "If the user has a vehicle issue, respond with:\n"
                    "- What the problem likely is\n"
                    "- Possible causes\n"
                    "- What they should do immediately (especially if urgent)\n\n"
                    "ONLY after that, ask if they want to book.\n"
                )
            },
            {"role":"user","content":msg}
        ]
    )
 
    response_text = r.choices[0].message.content
 
    # SMART INTENT MEMORY
    if "book" in response_text.lower():
        session["last_intent"] = "offer_booking"
    else:
        session.pop("last_intent", None)
 
    return {"text":response_text}

# -------------------------
# ASSIST (IT)
# -------------------------
def it_ai(msg, sid):
 
    # CREATE SESSION MEMORY IF NOT EXISTS
    if sid not in conversation_histories:
        conversation_histories[sid] = []
 
    history = conversation_histories[sid]
 
    # ADD USER MESSAGE
    history.append({"role": "user", "content": msg})
 
    r=get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content": IT_SYSTEM_PROMPT},
            *history
        ]
    )
 
    response = r.choices[0].message.content
 
    # SAVE RESPONSE IN MEMORY
    history.append({"role": "assistant", "content": response})
 
    # LIMIT HISTORY SIZE
    if len(history) > 20:
        conversation_histories[sid] = history[-20:]
 
    # SLACK LOGIC
    send_to_slack(f"""
New IT Query:
{msg}
 
Response:
{response}
""")
 
    return {"text": response}

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
    # AUTO IMAGE USE
    # AUTO IMAGE DETECTION (FIXED + CLEAN)
    if module == "it" and sid in last_images:
   
       # If user message is empty or short → assume image intent
       if not msg.strip() or len(msg.split()) <= 3:
          try:
             return jsonify({"text": process_it_image(last_images[sid])})
          except:
             pass
 
       # If user explicitly refers to image
       image_keywords = ["image", "screenshot", "attached", "upload", "analyze"]
 
       if any(word in msg.lower() for word in image_keywords):
          try:
             return jsonify({"text": process_it_image(last_images[sid])})
          except:
             pass
    
    if module=="vehicle":
        return jsonify(vehicle_ai(msg,sessions[sid]))
    return jsonify(it_ai(msg, sid))

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