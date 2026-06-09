from fastapi import BackgroundTasks, UploadFile
from sqlmodel import Session

from app.models.entities import HealthMetric, MedicalReport
from app.schemas.health import MetricPayload
from app.services.extraction_service import MedicalExtractionService
from app.services.ocr_service import OCRService
from app.services.rag_service import RAGService


def _index_report_background(report_id: int, title: str, raw_text: str) -> None:
    RAGService.index_report(report_id, title, raw_text)


class ReportIngestionService:
    @staticmethod
    async def process_report(
        session: Session,
        title: str,
        file: UploadFile,
        background_tasks: BackgroundTasks | None = None,
    ) -> tuple[MedicalReport, list[MetricPayload], str]:
        raw_text, extraction_method = await OCRService.extract_text(file)
        language = MedicalExtractionService.detect_language(raw_text)
        metrics = MedicalExtractionService.extract_metrics(raw_text)

        report = MedicalReport(
            title=title,
            source_file_name=file.filename or "unknown",
            raw_text=raw_text,
            language=language,
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        for metric in metrics:
            model = HealthMetric(
                report_id=report.id,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                unit=metric.unit,
                reference_min=metric.reference_min,
                reference_max=metric.reference_max,
                is_abnormal=metric.is_abnormal,
                observed_at=metric.observed_at,
            )
            session.add(model)

        session.commit()

        if report.id is not None and background_tasks is not None:
            background_tasks.add_task(_index_report_background, report.id, report.title, report.raw_text)
        elif report.id is not None:
            RAGService.index_report(report.id, report.title, report.raw_text)

        return report, metrics, extraction_method
