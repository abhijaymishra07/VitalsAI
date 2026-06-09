from app.schemas.health import HealthSnapshot, MetricSnapshot


def _find_metrics(snapshot: HealthSnapshot, keywords: list[str]) -> list[MetricSnapshot]:
    out: list[MetricSnapshot] = []
    for m in snapshot.metrics:
        name = m.metric_name.lower()
        if any(k in name for k in keywords):
            out.append(m)
    return out


def _risk_score(metrics: list[MetricSnapshot]) -> tuple[int, list[str]]:
    if not metrics:
        return 15, ["Insufficient related lab data in uploaded reports."]
    abnormal = [m for m in metrics if m.is_abnormal]
    if not abnormal:
        return 22, ["Related markers are within provided reference ranges."]
    score = min(92, 35 + len(abnormal) * 12)
    factors = [
        f"{m.metric_name}: {m.metric_value}{m.unit} (flagged abnormal)"
        for m in abnormal[:4]
    ]
    return score, factors


class DiseasePredictionService:
    MODELS = {
        "diabetes": ["glucose", "sugar", "hba1c", "fbs", "ppbs", "eag"],
        "heart": ["ldl", "hdl", "cholesterol", "triglyceride", "tg", "non-hdl", "apob", "lp(a)", "hs-crp", "homocysteine"],
        "liver": ["alt", "ast", "sgot", "sgpt", "bilirubin", "alp", "ggt", "albumin", "protein"],
        "kidney": ["creatinine", "egfr", "urea", "bun", "uric", "acr", "sodium", "potassium"],
        "lungs": ["wbc", "tlc", "neut", "esr", "spo2", "oxygen", "nt-probnp", "trop"],
    }

    @classmethod
    def predict_all(cls, snapshot: HealthSnapshot) -> list[dict]:
        results: list[dict] = []
        for disease, keys in cls.MODELS.items():
            related = _find_metrics(snapshot, keys)
            score, factors = _risk_score(related)
            level = "low"
            if score >= 70:
                level = "high"
            elif score >= 45:
                level = "moderate"
            results.append(
                {
                    "disease": disease,
                    "risk_score": score,
                    "risk_level": level,
                    "factors": factors,
                    "metrics_used": len(related),
                    "disclaimer": "Screening estimate only — not a medical diagnosis.",
                }
            )
        return results
