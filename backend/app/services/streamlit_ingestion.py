from sqlmodel import Session

from app.models.entities import HealthMetric, MedicalReport
from app.schemas.health import MetricPayload
from app.services.extraction_service import MedicalExtractionService
from app.services.ocr_service import OCRService
from app.services.rag_service import RAGService


class StreamlitIngestionService:
    @staticmethod
    def process_report(
        session: Session,
        title: str,
        filename: str,
        content: bytes,
    ) -> tuple[MedicalReport, list[MetricPayload], str]:
        raw_text, extraction_method = OCRService.extract_text_from_bytes(filename, content)
        language = MedicalExtractionService.detect_language(raw_text)
        metrics = MedicalExtractionService.extract_metrics(raw_text)

        report = MedicalReport(
            title=title,
            source_file_name=filename or "unknown",
            raw_text=raw_text,
            language=language,
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        for metric in metrics:
            session.add(
                HealthMetric(
                    report_id=report.id,
                    metric_name=metric.metric_name,
                    metric_value=metric.metric_value,
                    unit=metric.unit,
                    reference_min=metric.reference_min,
                    reference_max=metric.reference_max,
                    is_abnormal=metric.is_abnormal,
                    observed_at=metric.observed_at,
                )
            )

        session.commit()

        if report.id is not None:
            RAGService.index_report(report.id, report.title, report.raw_text)

        return report, metrics, extraction_method
