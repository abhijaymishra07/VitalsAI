from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.schemas.health import TrendPoint, TrendResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/trends/{metric_name}", response_model=TrendResponse)
def metric_trend(metric_name: str, session: Session = Depends(get_session)):
    rows, slope, signal = AnalyticsService.metric_trend(session, metric_name.lower())
    if not rows:
        raise HTTPException(status_code=404, detail="No metric history found")
    return TrendResponse(
        metric_name=metric_name,
        points=[TrendPoint(timestamp=r.observed_at, value=r.metric_value) for r in rows],
        slope=slope,
        signal=signal,
    )


@router.get("/correlations")
def correlations(session: Session = Depends(get_session)):
    return AnalyticsService.correlation_summary(session)


@router.get("/health-score")
def health_score(session: Session = Depends(get_session)):
    rows, _, _ = AnalyticsService.metric_trend(session, "glucose")
    if not rows:
        return {"score": 75, "reason": "Baseline score used due to limited data"}
    abnormal_count = sum(1 for r in rows if r.is_abnormal)
    score = max(20, 100 - abnormal_count * 8)
    return {"score": score, "reason": "Score decreases with repeated abnormal trends"}
