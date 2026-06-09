from collections import defaultdict
from datetime import datetime

import numpy as np
from sqlmodel import Session, select

from app.models.entities import HealthJournal, HealthMetric

METRIC_QUERY_GROUPS: dict[str, list[str]] = {
    "glucose": ["glucose", "fbs", "fasting glucose", "fasting blood sugar", "blood sugar", "eag", "ppbs"],
    "vitamin c": ["vitamin c", "ascorbic"],
    "vitamin d": ["vitamin d", "25-oh", "25 - oh"],
    "vitamin b12": ["vitamin b12", "b12", "cobalamin"],
    "hemoglobin": ["hemoglobin", "haemoglobin", "hb", "hgb"],
    "creatinine": ["creatinine", "creat"],
    "cholesterol": ["cholesterol", "total cholesterol"],
    "ldl": ["ldl"],
    "hdl": ["hdl"],
    "triglycerides": ["triglyceride", "tg"],
    "tsh": ["tsh", "thyroid stimulating"],
    "rdw": ["rdw"],
    "pcv": ["pcv", "hematocrit", "hct"],
    "urea": ["urea", "bun", "blood urea nitrogen"],
    "iron": ["iron", "ferritin"],
}


class AnalyticsService:
    @staticmethod
    def _metric_name_matches(metric_name: str, query: str) -> bool:
        name = metric_name.lower()
        needle = query.strip().lower()
        if not needle:
            return False
        if needle == name or needle in name or name in needle:
            return True
        for group, keywords in METRIC_QUERY_GROUPS.items():
            query_in_group = needle == group or needle in group or group in needle
            query_matches_keyword = any(needle in kw or kw in needle for kw in keywords)
            if query_in_group or query_matches_keyword:
                return any(kw in name for kw in keywords)
        return False

    @staticmethod
    def metric_trend(session: Session, metric_name: str):
        all_rows = session.exec(select(HealthMetric).order_by(HealthMetric.observed_at.asc())).all()
        rows = [r for r in all_rows if AnalyticsService._metric_name_matches(r.metric_name, metric_name)]
        if len(rows) < 2:
            return rows, 0.0, "insufficient_data"

        y = np.array([r.metric_value for r in rows], dtype=float)
        x = np.arange(len(y))
        slope = float(np.polyfit(x, y, 1)[0])
        signal = "stable"
        if slope > 0.2:
            signal = "rising"
        elif slope < -0.2:
            signal = "falling"
        return rows, slope, signal

    @staticmethod
    def list_matching_metrics(session: Session, query: str) -> list[str]:
        rows = session.exec(select(HealthMetric)).all()
        names = sorted({r.metric_name for r in rows if AnalyticsService._metric_name_matches(r.metric_name, query)})
        return names

    @staticmethod
    def correlation_summary(session: Session) -> dict[str, float]:
        journals = session.exec(select(HealthJournal)).all()
        metrics = session.exec(select(HealthMetric)).all()
        if not journals or not metrics:
            return {}

        latest_metric_by_day = defaultdict(list)
        for m in metrics:
            latest_metric_by_day[m.observed_at.date()].append(m.metric_value)

        sleep_values = []
        metric_values = []
        for entry in journals:
            day_metrics = latest_metric_by_day.get(entry.created_at.date())
            if day_metrics and entry.sleep_hours is not None:
                sleep_values.append(entry.sleep_hours)
                metric_values.append(float(np.mean(day_metrics)))

        if len(sleep_values) < 2:
            return {}

        corr = float(np.corrcoef(np.array(sleep_values), np.array(metric_values))[0, 1])
        return {"sleep_to_metric_correlation": round(corr, 3)}

    @staticmethod
    def format_trend_label(observed_at: datetime | None, index: int) -> str:
        if observed_at is None:
            return f"Reading {index + 1}"
        if hasattr(observed_at, "strftime"):
            return observed_at.strftime("%Y-%m-%d")
        return str(observed_at)[:10]
