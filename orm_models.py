
"""
SQLAlchemy ORM for AI Core project: users, projects, sessions, logs, recommendations, model runs, feedback, audit.

- Default DB: PostgreSQL or SQLite (configurable via DATABASE_URL env var).
- SQLAlchemy 2.0 style (Declarative Base) with typing.
- JSON fields stored as JSON.
- Includes helper: get_engine(), get_session(), create_all(), seed_demo_data().
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

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

    projects: Mapped[List[Project]] = relationship("Project", back_populates="owner")
    sessions: Mapped[List[Session]] = relationship("Session", back_populates="user")

class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    owner: Mapped[User] = relationship("User", back_populates="projects")
    sessions: Mapped[List[Session]] = relationship("Session", back_populates="project")

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_project_owner_name"),)

class Session(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    user: Mapped[User] = relationship("User", back_populates="sessions")
    project: Mapped[Optional[Project]] = relationship("Project", back_populates="sessions")
    logs: Mapped[List[InteractionLog]] = relationship("InteractionLog", back_populates="session", cascade="all, delete-orphan")
    recommendations: Mapped[List[Recommendation]] = relationship("Recommendation", back_populates="session", cascade="all, delete-orphan")

class InteractionLog(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "interaction_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(100))
    entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    sentiment: Mapped[Optional[str]] = mapped_column(String(30))
    language: Mapped[Optional[str]] = mapped_column(String(10))
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    model_name: Mapped[Optional[str]] = mapped_column(String(100))

    session: Mapped[Session] = relationship("Session", back_populates="logs")
    __table_args__ = (Index("ix_logs_session_created", "session_id", "created_at"),)

class Recommendation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    score: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped[Session] = relationship("Session", back_populates="recommendations")
    __table_args__ = (Index("ix_reco_session_kind", "session_id", "kind"),)

class ModelRun(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "model_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sessions.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[str] = mapped_column(String(50), nullable=False)
    input_ref: Mapped[Optional[int]] = mapped_column(ForeignKey("interaction_logs.id"))
    params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    session: Mapped[Optional[Session]] = relationship("Session")
    input_log: Mapped[Optional[InteractionLog]] = relationship("InteractionLog")
    __table_args__ = (Index("ix_modelrun_task", "task", "created_at"),)

class Feedback(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    recommendation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recommendations.id"))
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    session: Mapped[Session] = relationship("Session")
    recommendation: Mapped[Optional[Recommendation]] = relationship("Recommendation")

class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    actor: Mapped[Optional[User]] = relationship("User")
    __table_args__ = (Index("ix_audit_action_time", "action", "created_at"),)

# ---------- Helpers ----------
def get_engine(echo: bool = False):
    db_url = os.getenv("DATABASE_URL", "sqlite:///ai_core.db")
    return create_engine(db_url, echo=echo, future=True)

def get_session(echo: bool = False):
    engine = get_engine(echo=echo)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return SessionLocal()

def create_all(echo: bool = False):
    engine = get_engine(echo=echo)
    Base.metadata.create_all(engine)
    return engine

def seed_demo_data():
    from sqlalchemy.exc import IntegrityError
    sess = get_session()
    try:
        user = User(email="demo@example.com", display_name="Demo User", role="engineer")
        sess.add(user)
        sess.flush()
        proj = Project(name="AI Core", description="NLP + Recommender", owner_id=user.id)
        sess.add(proj)
        sess.flush()
        s = Session(user_id=user.id, project_id=proj.id)
        sess.add(s)
        sess.flush()
        log = InteractionLog(session_id=s.id, direction="user", message="Find best next step", intent="ask_next_step", entities={"topic": "NLP"})
        sess.add(log)
        reco = Recommendation(session_id=s.id, kind="next_step", title="Implement intent classifier", detail="Use spaCy/transformer", score=0.92, source="nlp")
        sess.add(reco)
        run = ModelRun(session_id=s.id, model_name="intent-bert", task="intent", input_ref=log.id, params={"threshold": 0.6}, output={"intent": "ask_next_step", "score": 0.92}, duration_ms=45.7)
        sess.add(run)
        fb = Feedback(session_id=s.id, recommendation_id=reco.id, rating=5, comment="Useful")
        sess.add(fb)
        audit = AuditEvent(actor_user_id=user.id, action="seed", entity_type="project", entity_id=proj.id)
        sess.add(audit)
        sess.commit()
    except IntegrityError:
        sess.rollback()
    finally:
        sess.close()

if __name__ == "__main__":
    create_all()
    seed_demo_data()
    print("DB initialized and demo data seeded.")
