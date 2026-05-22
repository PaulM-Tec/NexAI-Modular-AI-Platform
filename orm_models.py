"""
SQLAlchemy ORM for AI Core project (FINAL – DB CONSISTENT + BOOKING)
"""
 
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
 
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    JSON,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
 
# SAME DATABASE AS app.py (CRITICAL)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
 
DATABASE_URL = f"sqlite:///{DB_PATH}"
 
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
 
 
# ---------- Base ----------
class Base(DeclarativeBase):
    pass
 
 
# ---------- Mixins ----------
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
 
 
class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
 
 
# ---------- Core Tables ----------
 
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
 
 
class Session(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sessions"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
 
 
class InteractionLog(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "interaction_logs"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
 
 
class Recommendation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "recommendations"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
 
 
# NEW TABLE (BOOKING FEATURE)
class Booking(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bookings"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    service_type: Mapped[str] = mapped_column(String(255), nullable=False)
    booking_date: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_time: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="confirmed", nullable=False)
 
 
# ---------- Helpers ----------
def get_engine():
    return engine
 
 
def get_session():
    return SessionLocal()
 
 
def create_all():
    Base.metadata.create_all(engine)
 
 
# ---------- Optional Seed ----------
def seed_demo_data():
    db = get_session()
    try:
        session = Session(user_id=1)
        db.add(session)
        db.commit()
    finally:
        db.close()
 
 
# ---------- Run directly ----------
if __name__ == "__main__":
    create_all()
    seed_demo_data()
    print("DB initialized with Booking table")