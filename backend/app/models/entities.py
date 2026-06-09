from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class MedicalReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    source_file_name: str
    raw_text: str
    language: str = "unknown"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(index=True)
    metric_name: str = Field(index=True)
    metric_value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    is_abnormal: bool = False
    observed_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class HealthJournal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mood: Optional[str] = None
    sleep_hours: Optional[float] = None
    exercise_minutes: Optional[int] = None
    medication_taken: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class MedicalTerm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    term: str = Field(index=True, unique=True)
    explanation: str
    category: str = "general"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
