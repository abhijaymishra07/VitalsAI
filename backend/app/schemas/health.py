from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MetricPayload(BaseModel):
    metric_name: str
    metric_value: float
    unit: str = ""
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    is_abnormal: bool = False
    observed_at: Optional[datetime] = None


class MetricSnapshot(BaseModel):
    metric_name: str
    metric_value: float
    unit: str = ""
    is_abnormal: bool = False
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    observed_at: Optional[datetime] = None
    report_title: Optional[str] = None


class HealthSnapshot(BaseModel):
    metrics: list[MetricSnapshot] = []
    abnormal_metrics: list[MetricSnapshot] = []
    recent_report_titles: list[str] = []


class ReportResponse(BaseModel):
    report_id: int
    title: str
    language: str
    raw_text_preview: str
    extracted_metrics: list[MetricPayload]
    text_chars: int = 0
    extraction_method: str = ""
    parse_hint: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)


class ChatResponse(BaseModel):
    answer: str
    used_context: list[str] = []
    health_snapshot: Optional[HealthSnapshot] = None
    citations: list[str] = []


class JournalRequest(BaseModel):
    mood: Optional[str] = None
    sleep_hours: Optional[float] = None
    exercise_minutes: Optional[int] = None
    medication_taken: Optional[str] = None
    notes: Optional[str] = None


class TrendPoint(BaseModel):
    timestamp: datetime
    value: float


class TrendResponse(BaseModel):
    metric_name: str
    points: list[TrendPoint]
    slope: float
    signal: str
