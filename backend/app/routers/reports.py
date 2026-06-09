from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.entities import HealthMetric, MedicalReport
from app.schemas.health import ReportResponse
from app.services.ai_service import AIService
from app.services.extraction_service import MedicalExtractionService
from app.services.ingestion_service import ReportIngestionService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/upload", response_model=ReportResponse)
async def upload_report(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    report, metrics, extraction_method = await ReportIngestionService.process_report(
        session, title, file, background_tasks=background_tasks
    )
    text_chars = len(report.raw_text or "")
    return ReportResponse(
        report_id=report.id or 0,
        title=report.title,
        language=report.language,
        raw_text_preview=MedicalExtractionService.lab_text_preview(report.raw_text or ""),
        extracted_metrics=metrics,
        text_chars=text_chars,
        extraction_method=extraction_method,
        parse_hint=MedicalExtractionService.build_parse_hint(len(metrics), text_chars, extraction_method),
    )


@router.post("/reindex-rag")
def reindex_rag(session: Session = Depends(get_session)):
    reports = session.exec(select(MedicalReport)).all()
    indexed = 0
    chunks = 0
    for report in reports:
        if report.id is None:
            continue
        count = RAGService.index_report(report.id, report.title, report.raw_text)
        if count > 0:
            indexed += 1
            chunks += count
    return {"reports_indexed": indexed, "chunks_indexed": chunks, "rag_ready": RAGService.ensure_collection()}


@router.get("/{report_id}/explanations")
def metric_explanations(report_id: int, session: Session = Depends(get_session)):
    ai = AIService()
    metrics = session.exec(select(HealthMetric).where(HealthMetric.report_id == report_id)).all()
    # Prioritize abnormal values; cap count so the UI does not hang.
    abnormal = [m for m in metrics if m.is_abnormal]
    normal = [m for m in metrics if not m.is_abnormal]
    ordered = (abnormal + normal)[:5]
    return {
        "report_id": report_id,
        "explanations": [
            {
                "metric_name": m.metric_name,
                "explanation": ai.explain_metric(m.metric_name, m.metric_value, m.unit, m.is_abnormal, fast=True),
            }
            for m in ordered
        ],
    }
