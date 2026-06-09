from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.db import get_session
from app.services.ai_service import AIService
from app.services.memory_service import HealthMemoryService
from app.services.prediction_service import DiseasePredictionService

router = APIRouter(prefix="/copilot", tags=["copilot"])


class SymptomRequest(BaseModel):
    symptoms: str = Field(min_length=3)


@router.get("/disease-predictions")
def disease_predictions(session: Session = Depends(get_session)):
    snap = HealthMemoryService.build_health_snapshot(session)
    return {
        "predictions": DiseasePredictionService.predict_all(snap),
        "metrics_available": len(snap.metrics),
    }


@router.get("/action-plan")
def action_plan(session: Session = Depends(get_session)):
    snap = HealthMemoryService.build_health_snapshot(session)
    steps: list[str] = []
    if not snap.abnormal_metrics:
        steps.append("No abnormal labs flagged. Keep uploading reports every 3-6 months.")
    else:
        for m in snap.abnormal_metrics[:6]:
            ai = AIService()
            steps.append(
                f"{m.metric_name.upper()} ({m.metric_value} {m.unit}): "
                + ai._reduction_steps_for_metric(m.metric_name).replace("Steps: ", "")
            )
        steps.append("Repeat labs in 8-12 weeks. Log sleep, exercise, and meds in the journal.")
    return {"plan": steps, "abnormal_count": len(snap.abnormal_metrics)}


@router.post("/symptoms")
def analyze_symptoms(payload: SymptomRequest, session: Session = Depends(get_session)):
    text = payload.symptoms.lower()
    specialist = "General Physician"
    urgency = "routine"
    if any(
        w in text
        for w in [
            "chest pain",
            "chest tightness",
            "chest pressure",
            "chest discomfort",
            "breathless",
            "breathlessness",
            "shortness of breath",
            "faint",
            "stroke",
            "severe headache",
            "palpitation",
        ]
    ):
        urgency = "urgent"
        specialist = "Emergency / Cardiology"
    elif any(w in text for w in ["skin", "rash", "lesion"]):
        specialist = "Dermatology"
    elif any(w in text for w in ["anxiety", "depression", "mood", "sleep"]):
        specialist = "Psychiatry / Psychology"
    elif any(w in text for w in ["kidney", "urine", "swelling"]):
        specialist = "Nephrology"
    elif any(w in text for w in ["sugar", "thirst", "diabetes"]):
        specialist = "Endocrinology"
    elif any(w in text for w in ["cough", "fever", "cold"]):
        specialist = "Pulmonology / General Medicine"

    snap = HealthMemoryService.build_health_snapshot(session)
    ai = AIService()
    advice = ai.symptom_guidance(payload.symptoms, snap, specialist, urgency)
    return {"specialist": specialist, "urgency": urgency, "advice": advice}
