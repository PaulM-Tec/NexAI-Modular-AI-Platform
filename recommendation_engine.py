# recommendation_engine.py
"""
Recommendation Engine for AI Core Project
- Consumes latest InteractionLog per Session
- Generates data-driven suggestions based on intent + entities
- Persists rows in Recommendation and logs a ModelRun for traceability

Intents supported (from zero-shot classifier):
    - ASK_NEXT_STEP
    - BOOK_SERVICE
    - GENERAL_QUERY

Usage:
    from recommendation_engine import generate_recommendations
    recos = generate_recommendations(session_id=1)

"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from orm_models import (
    get_session,
    Session as OrmSession,
    InteractionLog,
    Recommendation,
    ModelRun,
)

# ------------------------- Helpers -------------------------

def _extract_entity(entities: Optional[Dict[str, Any]], label: str) -> Optional[str]:
    """Find first entity text by spaCy label (e.g., 'GPE', 'DATE').
    entities expected format: {"extracted": [(text, label), ...]}
    """
    if not entities or "extracted" not in entities:
        return None
    for text, lab in entities["extracted"]:
        if lab == label:
            return text
    return None


def _score(base: float, bonuses: List[float]) -> float:
    s = base + sum(bonuses)
    return max(0.0, min(1.0, round(s, 4)))


# ------------------------- Core Recommendation Logic -------------------------

def _recommend_for_intent(intent: str, message: str, entities: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a list of recommendation dicts (kind, title, detail, payload, score, source)."""
    recos: List[Dict[str, Any]] = []

    # Common extracted entities
    location = _extract_entity(entities, "GPE")  # Geo-political entity (e.g., 'Cape Town')
    date_text = _extract_entity(entities, "DATE")

    if intent == "BOOK_SERVICE":
        # Primary next step: create a booking
        bonuses = [0.15 if location else 0.0, 0.15 if date_text else 0.0]
        recos.append({
            "kind": "next_step",
            "title": "Create a service booking",
            "detail": (
                "Proceed to create a booking. If available, prefill location and date from the message."
            ),
            "payload": {
                "action": "create_booking",
                "prefill": {"location": location, "date": date_text},
            },
            "score": _score(0.7, bonuses),
            "source": "rules",
        })
        # Secondary: confirm details
        recos.append({
            "kind": "prompt",
            "title": "Confirm booking details",
            "detail": "Ask user to confirm service type, preferred time, and contact info.",
            "payload": {"checklist": ["service_type", "time", "contact"]},
            "score": _score(0.55, bonuses),
            "source": "rules",
        })

    elif intent == "ASK_NEXT_STEP":
        # Recommend structured next steps in project context
        recos.append({
            "kind": "next_step",
            "title": "Run NLP and store annotations",
            "detail": "Extract intent & entities for the latest message and persist to InteractionLog.",
            "payload": {"action": "nlp_annotate"},
            "score": 0.75,
            "source": "rules",
        })
        recos.append({
            "kind": "resource",
            "title": "View recent session context",
            "detail": "Open the session timeline to review logs and recommendations.",
            "payload": {"action": "open_timeline"},
            "score": 0.6,
            "source": "rules",
        })

    else:  # GENERAL_QUERY or unknown
        recos.append({
            "kind": "prompt",
            "title": "Clarify user goal",
            "detail": "Ask 1-2 questions to understand the desired outcome and constraints.",
            "payload": {"questions": [
                "What outcome are you trying to achieve?",
                "Any constraints on time, budget, or location?"
            ]},
            "score": 0.65,
            "source": "rules",
        })
        if location or date_text:
            recos.append({
                "kind": "next_step",
                "title": "Use extracted entities",
                "detail": "Use location/date from the query to tailor the next action.",
                "payload": {"entities": {"location": location, "date": date_text}},
                "score": _score(0.55, [0.15]),
                "source": "rules",
            })

    return recos


# ------------------------- Public API -------------------------

def generate_recommendations(session_id: int, input_log_id: Optional[int] = None) -> List[Recommendation]:
    """Generate and persist recommendations based on the latest InteractionLog in a session.

    Args:
        session_id: Target session.
        input_log_id: Optional specific InteractionLog id to use. If None, uses latest 'user' log.
    Returns:
        List of Recommendation ORM instances that were persisted.
    """
    db = get_session()

    # Validate session exists
    session_row = db.query(OrmSession).filter(OrmSession.id == session_id).one_or_none()
    if not session_row:
        db.close()
        raise ValueError(f"Session {session_id} not found")

    # Find input log
    q = db.query(InteractionLog).filter(InteractionLog.session_id == session_id)
    if input_log_id:
        q = q.filter(InteractionLog.id == input_log_id)
    else:
        q = q.filter(InteractionLog.direction == "user").order_by(InteractionLog.created_at.desc())
    input_log = q.first()

    if not input_log:
        # Create a placeholder recommendation when there is no user input
        placeholder = Recommendation(
            session_id=session_id,
            kind="prompt",
            title="Start the conversation",
            detail="No user message found. Ask the user what they want to accomplish.",
            payload={"action": "start"},
            score=0.5,
            source="rules",
        )
        db.add(placeholder)
        db.commit()
        db.close()
        return [placeholder]

    # Build recommendations from intent + entities
    rec_dicts = _recommend_for_intent(
        intent=input_log.intent or "GENERAL_QUERY",
        message=input_log.message,
        entities=input_log.entities,
    )

    # Persist recommendations
    reco_rows: List[Recommendation] = []
    for r in rec_dicts:
        reco = Recommendation(
            session_id=session_id,
            kind=r["kind"],
            title=r["title"],
            detail=r.get("detail"),
            payload=r.get("payload"),
            score=r.get("score"),
            source=r.get("source", "rules"),
            acknowledged=False,
        )
        db.add(reco)
        reco_rows.append(reco)

    db.flush()  # obtain IDs for model run output

    # Log model run for traceability
    run_output = {
        "input_log_id": input_log.id,
        "generated": [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "score": r.score,
            } for r in reco_rows
        ]
    }
    model_run = ModelRun(
        session_id=session_id,
        model_name="rule-engine-v1",
        task="recommendation",
        input_ref=input_log.id,
        params={"ruleset": "v1"},
        output=run_output,
        duration_ms=None,
        success=True,
    )
    db.add(model_run)
    db.commit()
    db.close()

    return reco_rows


def get_recommendations(session_id: int, limit: int = 10) -> List[Recommendation]:
    """Fetch recent recommendations for a session."""
    db = get_session()
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.session_id == session_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return rows


def acknowledge_recommendation(recommendation_id: int) -> bool:
    """Mark a recommendation as acknowledged."""
    db = get_session()
    row = db.query(Recommendation).filter(Recommendation.id == recommendation_id).one_or_none()
    if not row:
        db.close()
        return False
    row.acknowledged = True
    db.commit()
    db.close()
    return True


if __name__ == "__main__":
    # Quick smoke test: generate for session 1 using latest user log
    recos = generate_recommendations(session_id=1)
    print([{"id": r.id, "title": r.title, "score": r.score} for r in recos])
