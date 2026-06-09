from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_cors_origins, settings
from app.core.db import init_db
from app.routers.analytics import router as analytics_router
from app.routers.chat import router as chat_router
from app.routers.glossary import router as glossary_router
from app.routers.journal import router as journal_router
from app.routers.copilot import router as copilot_router
from app.routers.reports import router as reports_router
from app.services.rag_service import RAGService

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    RAGService.ensure_collection()


@app.get("/health")
def health():
    rag_ready = RAGService.ensure_collection()
    return {
        "status": "ok",
        "service": settings.app_name,
        "rag_enabled": settings.rag_enabled,
        "rag_ready": rag_ready,
        "rag_mode": RAGService.get_mode(),
        "ai_configured": bool(settings.openai_api_key),
    }


app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(journal_router, prefix=settings.api_prefix)
app.include_router(glossary_router, prefix=settings.api_prefix)
app.include_router(copilot_router, prefix=settings.api_prefix)
