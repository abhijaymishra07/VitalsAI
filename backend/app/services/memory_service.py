from sqlmodel import Session, select

from app.models.entities import ChatMessage, HealthMetric, MedicalReport
from app.schemas.health import HealthSnapshot, MetricSnapshot


class HealthMemoryService:
    @staticmethod
    def build_health_snapshot(session: Session, metric_limit: int = 80) -> HealthSnapshot:
        reports = session.exec(select(MedicalReport).order_by(MedicalReport.created_at.desc()).limit(5)).all()
        report_by_id = {r.id: r for r in reports if r.id is not None}
        if reports and reports[0].id is not None:
            for report in reports:
                if report.id is not None:
                    report_by_id[report.id] = report

        rows = session.exec(select(HealthMetric).order_by(HealthMetric.observed_at.desc())).all()
        snapshots: list[MetricSnapshot] = []
        seen_names: set[str] = set()
        for m in rows:
            key = m.metric_name.strip().lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            report = report_by_id.get(m.report_id)
            snapshots.append(
                MetricSnapshot(
                    metric_name=m.metric_name,
                    metric_value=m.metric_value,
                    unit=m.unit or "",
                    is_abnormal=m.is_abnormal,
                    reference_min=m.reference_min,
                    reference_max=m.reference_max,
                    observed_at=m.observed_at,
                    report_title=report.title if report else None,
                )
            )
            if len(snapshots) >= metric_limit:
                break

        abnormal = [s for s in snapshots if s.is_abnormal]
        latest_title = reports[0].title if reports else None
        latest_abnormal = [s for s in snapshots if s.is_abnormal and s.report_title == latest_title]
        display_abnormal = latest_abnormal or abnormal
        deduped_abnormal: list[MetricSnapshot] = []
        seen_abnormal: set[str] = set()
        for item in display_abnormal:
            key = item.metric_name.strip().lower()
            if key in seen_abnormal:
                continue
            seen_abnormal.add(key)
            deduped_abnormal.append(item)
        return HealthSnapshot(
            metrics=snapshots,
            abnormal_metrics=deduped_abnormal,
            recent_report_titles=[r.title for r in reports],
        )

    @staticmethod
    def snapshot_to_prompt_lines(snapshot: HealthSnapshot) -> list[str]:
        lines: list[str] = []
        if snapshot.recent_report_titles:
            lines.append("Recent reports: " + ", ".join(snapshot.recent_report_titles))
        for m in snapshot.metrics[:12]:
            ref = ""
            if m.reference_min is not None and m.reference_max is not None:
                ref = f" (ref {m.reference_min}-{m.reference_max})"
            flag = "ABNORMAL" if m.is_abnormal else "normal"
            title = f" from '{m.report_title}'" if m.report_title else ""
            lines.append(
                f"Lab: {m.metric_name} = {m.metric_value} {m.unit}{ref} [{flag}]{title}"
            )
        if snapshot.abnormal_metrics:
            names = ", ".join(m.metric_name for m in snapshot.abnormal_metrics[:8])
            lines.append(f"Priority abnormal markers: {names}")
        return lines

    @staticmethod
    def build_personal_context(session: Session) -> list[str]:
        snapshot = HealthMemoryService.build_health_snapshot(session)
        return HealthMemoryService.snapshot_to_prompt_lines(snapshot)
