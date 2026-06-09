from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.entities import HealthJournal
from app.schemas.health import JournalRequest

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("")
def create_journal_entry(payload: JournalRequest, session: Session = Depends(get_session)):
    entry = HealthJournal(
        mood=payload.mood,
        sleep_hours=payload.sleep_hours,
        exercise_minutes=payload.exercise_minutes,
        medication_taken=payload.medication_taken,
        notes=payload.notes,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return {"id": entry.id, "message": "Journal entry recorded"}


@router.get("")
def list_journal_entries(session: Session = Depends(get_session)):
    rows = session.exec(select(HealthJournal).order_by(HealthJournal.created_at.desc()).limit(50)).all()
    return rows
