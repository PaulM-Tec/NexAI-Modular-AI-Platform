"""
SQLAlchemy ORM for AI Core project (FIXED DB CONSISTENCY)
"""
 
from __future__ import annotations
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
 
from pathlib import Path
 
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    Float,
    Boolean,
    Text,
    JSON,
    create_engine,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
 
# FORCE SAME DATABASE AS app.py (CRITICAL FIX)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
 
 
class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
 
 
# ---------- Core Entities ----------
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
 
 
class Session(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sessions"
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
 
 
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
 
 
# ---------- Helpers ----------
def get_engine():
    return engine
 
 
def get_session():
    return SessionLocal()
 
 
def create_all():
    Base.metadata.create_all(engine)
 
 
# Optional demo data
def seed_demo_data():
    db = get_session()
    try:
        demo_session = Session(user_id=1)
        db.add(demo_session)
        db.commit()
    finally:
        db.close()
 
 
# Run directly
if __name__ == "__main__":
    create_all()
    seed_demo_data()
    print("DB initialized correctly")