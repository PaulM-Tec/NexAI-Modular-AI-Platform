import os
import sys
import re
from datetime import datetime
from pathlib import Path
 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
 
# Fix import path
sys.path.append(os.getcwd())
 
# NLP
from nlp_engine import get_response
 
# -------------------------
# CONFIG
# -------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
metadata = MetaData()
 
# Load tables
Users = Table("users", metadata, autoload_with=engine)
InteractionLogs = Table("interaction_logs", metadata, autoload_with=engine)
Recommendations = Table("recommendations", metadata, autoload_with=engine)
Bookings = Table("bookings", metadata, autoload_with=engine)
 
print("Tables loaded:", metadata.tables.keys())
 
# Flask app
app = Flask(__name__)
CORS(app)  # FIX: allow frontend access
 
# -------------------------
# SERVE FRONTEND (CRITICAL FOR MOBILE)
# -------------------------
@app.get("/")
def serve_frontend():
    return send_from_directory(".", "index.html")
 
# -------------------------
# HEALTH
# -------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
 
 
# -------------------------
# CHAT (SMART BOOKING)
# -------------------------
@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
 
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400
 
    session_id = data.get("session_id") or 1
 
    # Default NLP response
    reply = get_response(message)
 
    msg = message.lower()
 
    # -------------------------
    # BOOKING LOGIC
    # -------------------------
    if "book" in msg or "schedule" in msg:
 
        # Service detection
        if "oil" in msg:
            service_type = "oil change"
        elif "brake" in msg:
            service_type = "brake check"
        elif "tire" in msg or "tyre" in msg:
            service_type = "tire rotation"
        else:
            service_type = "general service"
 
        # Date detection
        if "tomorrow" in msg:
            booking_date = "tomorrow"
        elif "today" in msg:
            booking_date = "today"
        else:
            booking_date = "unspecified"
 
        # Time detection
        time_match = re.search(r"\b(\d{1,2})(am|pm)?\b", msg)
 
        if time_match:
            hour = time_match.group(1)
            period = time_match.group(2) or "am"
            booking_time = f"{hour}{period}"
        else:
            booking_time = "unspecified"
 
        try:
            with engine.begin() as conn:
                now = datetime.utcnow()
 
                conn.execute(
                    Bookings.insert().values(
                        session_id=session_id,
                        service_type=service_type,
                        booking_date=booking_date,
                        booking_time=booking_time,
                        status="confirmed",
                        created_at=now,
                        updated_at=now,
                        is_deleted=False
                    )
                )
 
            reply = (
                f"Booking Confirmed!\n"
                f"Service: {service_type.title()}\n"
                f"Date: {booking_date.title()}\n"
                f"Time: {booking_time.upper()}"
            )
 
        except SQLAlchemyError as e:
            print("BOOKING ERROR:", e)
 
    # -------------------------
    # LOGGING
    # -------------------------
    try:
        with engine.begin() as conn:
            now = datetime.utcnow()
 
            # Incoming
            conn.execute(
                InteractionLogs.insert().values(
                    session_id=session_id,
                    direction="incoming",
                    message=message,
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
            )
 
            # Outgoing
            conn.execute(
                InteractionLogs.insert().values(
                    session_id=session_id,
                    direction="outgoing",
                    message=reply,
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
            )
 
    except SQLAlchemyError as e:
        print("LOG ERROR:", e)
 
    return jsonify({"response": reply}), 200
 
 
# -------------------------
# BOOKING HISTORY
# -------------------------
@app.get("/bookings/<int:session_id>")
def get_bookings(session_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                Bookings.select()
                .where(Bookings.c.session_id == session_id)
                .order_by(Bookings.c.created_at.desc())
            )
 
            rows = result.fetchall()
 
            bookings = [
                {
                    "service": r.service_type.title(),
                    "date": r.booking_date.title(),
                    "time": r.booking_time.upper(),
                    "status": r.status.upper()
                }
                for r in rows
            ]
 
            return jsonify({"bookings": bookings}), 200
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
 
# -------------------------
# MAIN (MOBILE ENABLED)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)