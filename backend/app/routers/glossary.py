from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.entities import MedicalTerm
from app.services.ai_service import AIService

router = APIRouter(prefix="/glossary", tags=["glossary"])


@router.get("/{term}")
def explain_term(term: str, session: Session = Depends(get_session)):
    normalized = AIService._canonical_medical_term(term)
    item = session.exec(select(MedicalTerm).where(MedicalTerm.term == normalized)).first()
    if item:
        weak_markers = [
            "i can provide a stronger explanation with an ai model key configured",
            "is a medical term.",
        ]
        if any(marker in item.explanation.lower() for marker in weak_markers):
            item.explanation = AIService().explain_medical_term(normalized)
            item.updated_at = datetime.utcnow()
            session.add(item)
            session.commit()
            session.refresh(item)
        return item
    # Auto-generate and persist explanation on first lookup.
    explanation = AIService().explain_medical_term(normalized)
    item = MedicalTerm(term=normalized, explanation=explanation, category="auto")
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post("/{term}")
def upsert_term(term: str, explanation: str, session: Session = Depends(get_session)):
    normalized = AIService._canonical_medical_term(term)
    item = session.exec(select(MedicalTerm).where(MedicalTerm.term == normalized)).first()
    if item:
        item.explanation = explanation
        item.updated_at = datetime.utcnow()
    else:
        item = MedicalTerm(term=normalized, explanation=explanation)
        session.add(item)
    session.commit()
    session.refresh(item)
    return item
