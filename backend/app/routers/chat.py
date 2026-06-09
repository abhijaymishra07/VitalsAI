from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.entities import ChatMessage
from app.schemas.health import ChatRequest, ChatResponse
from app.services.ai_service import AIService
from app.services.memory_service import HealthMemoryService
from app.services.vector_service import SemanticSearchService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, session: Session = Depends(get_session)):
    snapshot = HealthMemoryService.build_health_snapshot(session)
    memory_lines = HealthMemoryService.snapshot_to_prompt_lines(snapshot)
    citations = SemanticSearchService.search_citations(session, payload.message, top_k=4)
    recent_messages = session.exec(select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(12)).all()
    chat_history = [(item.role, item.message) for item in reversed(recent_messages)]

    ai = AIService()
    answer = ai.health_chat(
        payload.message,
        snapshot=snapshot,
        extra_context=memory_lines,
        citations=citations,
        chat_history=chat_history,
    )

    session.add(ChatMessage(role="user", message=payload.message))
    session.add(ChatMessage(role="assistant", message=answer))
    session.commit()

    used_context = memory_lines + citations
    return ChatResponse(
        answer=answer,
        used_context=used_context[:20],
        health_snapshot=snapshot,
        citations=citations,
    )


@router.get("/doctor-summary")
def doctor_summary(session: Session = Depends(get_session)):
    context = HealthMemoryService.build_personal_context(session)
    return {"summary": AIService().doctor_summary(context)}
