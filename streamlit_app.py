"""VitalsAI — Streamlit health copilot (Streamlit Cloud entry point)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Streamlit Cloud secrets → env (before pydantic settings load)
try:
    for key in ("OPENAI_API_KEY", "LLM_MODEL", "EMBEDDING_MODEL", "DATABASE_URL", "RAG_ENABLED"):
        if key in st.secrets:
            os.environ.setdefault(key, str(st.secrets[key]))
except Exception:
    pass

os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND / 'health_copilot.db'}")
os.environ.setdefault("QDRANT_PREFER_LOCAL", "true")
os.environ.setdefault("RAG_ENABLED", "true")

from sqlmodel import Session, select  # noqa: E402

from app.core.db import engine, init_db  # noqa: E402
from app.models.entities import ChatMessage, MedicalTerm  # noqa: E402
from app.services.ai_service import AIService  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402
from app.services.memory_service import HealthMemoryService  # noqa: E402
from app.services.prediction_service import DiseasePredictionService  # noqa: E402
from app.services.streamlit_ingestion import StreamlitIngestionService  # noqa: E402
from app.services.vector_service import SemanticSearchService  # noqa: E402


@st.cache_resource
def bootstrap() -> None:
    init_db()


def get_snapshot():
    with Session(engine) as session:
        return HealthMemoryService.build_health_snapshot(session)


def run_chat(message: str) -> tuple[str, list[str]]:
    with Session(engine) as session:
        snapshot = HealthMemoryService.build_health_snapshot(session)
        citations = SemanticSearchService.search_citations(session, message, top_k=4)
        recent = session.exec(select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(12)).all()
        history = [(m.role, m.message) for m in reversed(recent)]
        ai = AIService()
        answer = ai.health_chat(message, snapshot=snapshot, citations=citations, chat_history=history)
        session.add(ChatMessage(role="user", message=message))
        session.add(ChatMessage(role="assistant", message=answer))
        session.commit()
        return answer, citations


def page_upload() -> None:
    st.subheader("Medical Report Intake")
    st.caption("Upload `.txt`, digital PDF, or image reports. Best results with text-based PDFs.")

    title = st.text_input("Report title", value="My Lab Report")
    uploaded = st.file_uploader("Choose file", type=["txt", "pdf", "png", "jpg", "jpeg", "webp"])

    if uploaded and st.button("Upload & Extract", type="primary"):
        with st.spinner("Reading report and extracting labs..."):
            with Session(engine) as session:
                report, metrics, method = StreamlitIngestionService.process_report(
                    session,
                    title=title,
                    filename=uploaded.name,
                    content=uploaded.getvalue(),
                )
            st.success(f"Extracted **{len(metrics)}** lab values ({method}).")
            if metrics:
                st.session_state["last_report_id"] = report.id
            else:
                st.warning("No metrics found. Try a `.txt` file or a clearer PDF.")

    snapshot = get_snapshot()
    if not snapshot.metrics:
        st.info("Upload a report to see your labs here.")
        return

    abnormal = snapshot.abnormal_metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total metrics", len(snapshot.metrics))
    c2.metric("Abnormal signals", len(abnormal))
    c3.metric("Reports", len(snapshot.recent_report_titles))

    if abnormal:
        st.markdown("**Flagged values**")
        for m in abnormal[:15]:
            ref = ""
            if m.reference_min is not None and m.reference_max is not None:
                ref = f" (ref {m.reference_min}–{m.reference_max} {m.unit})"
            st.markdown(f"- **{m.metric_name}:** {m.metric_value} {m.unit}{ref}")

    with st.expander("All extracted metrics"):
        for m in snapshot.metrics[:40]:
            flag = " 🔴" if m.is_abnormal else ""
            st.text(f"{m.metric_name}: {m.metric_value} {m.unit}{flag}")


def page_chat() -> None:
    st.subheader("Conversational Health Copilot")
    st.caption("Ask about your labs — e.g. *what are my abnormal values*, *what is RDW*, *what disease is linked to HbA1c*")

    snapshot = get_snapshot()
    if snapshot.abnormal_metrics:
        with st.expander(f"Your flagged values ({len(snapshot.abnormal_metrics)})"):
            for m in snapshot.abnormal_metrics[:10]:
                st.markdown(f"- {m.metric_name}: {m.metric_value} {m.unit}")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hi! I'm your health copilot.\n\n"
                    "Try:\n"
                    "- *what are my abnormal values*\n"
                    "- *what does RDW mean*\n"
                    "- *what disease is linked to vitamin D*"
                ),
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your labs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Reading your labs..."):
                answer, citations = run_chat(prompt)
            st.markdown(answer)
            if citations:
                with st.expander("Sources from your reports"):
                    for c in citations:
                        st.caption(c)
        st.session_state.messages.append({"role": "assistant", "content": answer})


def page_risk() -> None:
    st.subheader("Risk Screen & Guidance")

    snapshot = get_snapshot()
    if not snapshot.metrics:
        st.info("Upload a report first.")
        return

    if st.button("Run multi-disease screen", type="primary"):
        preds = DiseasePredictionService.predict_all(snapshot)
        for p in preds:
            level = p["risk_level"]
            color = {"low": "green", "moderate": "orange", "high": "red"}.get(level, "gray")
            st.markdown(f"#### {p['disease'].title()} — :{color}[{level.upper()}] ({p['risk_score']}%)")
            for f in p["factors"][:3]:
                st.markdown(f"- {f}")

    st.divider()
    st.markdown("**Personal risk reduction plan**")
    if st.button("Generate action plan"):
        abnormal = snapshot.abnormal_metrics
        if not abnormal:
            st.success("No abnormal labs flagged.")
        else:
            ai = AIService()
            for m in abnormal[:6]:
                steps = ai._reduction_steps_for_metric(m.metric_name).replace("Steps: ", "")
                st.markdown(f"- **{m.metric_name}:** {steps}")

    st.divider()
    st.markdown("**Symptom guidance**")
    symptoms = st.text_input("Describe symptoms", placeholder="e.g. chest tightness, skin rash")
    if symptoms and st.button("Check symptoms"):
        text = symptoms.lower()
        specialist, urgency = "General Physician", "routine"
        if any(w in text for w in ("chest", "breath", "faint", "stroke", "palpitation")):
            specialist, urgency = "Emergency / Cardiology", "urgent"
        elif any(w in text for w in ("skin", "rash", "itch")):
            specialist = "Dermatology"
        elif any(w in text for w in ("sugar", "thirst", "diabetes")):
            specialist = "Endocrinology"
        st.markdown(f"**Specialist:** {specialist} · **Urgency:** {urgency}")
        advice = AIService().symptom_guidance(symptoms, snapshot, specialist, urgency)
        st.markdown(advice)


def page_tools() -> None:
    st.subheader("Glossary & Doctor Summary")
    st.caption("Try vitamins (e.g. *vitamin c*), lab markers (*creatinine*), or abbreviations (*RDW*, *HbA1c*).")

    term = st.text_input("Medical term", value="creatinine")
    if st.button("Explain term"):
        snapshot = get_snapshot()
        explanation = AIService().explain_medical_term(term, snapshot=snapshot)
        st.markdown(explanation)
        with Session(engine) as session:
            normalized = AIService._canonical_medical_term(term)
            row = session.exec(select(MedicalTerm).where(MedicalTerm.term == normalized)).first()
            if row is None:
                session.add(MedicalTerm(term=normalized, explanation=explanation))
            else:
                row.explanation = explanation
            session.commit()

    st.divider()
    metric = st.text_input("Trend metric name", value="glucose")
    if st.button("Analyze trend"):
        with Session(engine) as session:
            rows, slope, signal = AnalyticsService.metric_trend(session, metric)
            matches = AnalyticsService.list_matching_metrics(session, metric)
        if not rows:
            st.warning("No matching metric found. Upload a report first, or try a name from your labs.")
            if matches:
                st.info("Did you mean: " + ", ".join(matches[:5]))
        elif len(rows) < 2:
            st.warning(
                f"Only one reading found for **{rows[0].metric_name}**. "
                "Upload another report over time to see a trend."
            )
            st.metric(rows[0].metric_name, f"{rows[0].metric_value} {rows[0].unit}")
        else:
            chart = {
                AnalyticsService.format_trend_label(r.observed_at, i): r.metric_value
                for i, r in enumerate(rows)
            }
            st.line_chart(chart)
            st.caption(f"Metric: **{rows[0].metric_name}** · Signal: **{signal}** · Slope: {slope:.3f}")

    st.divider()
    if st.button("Generate doctor visit summary", type="primary"):
        with Session(engine) as session:
            context = HealthMemoryService.build_personal_context(session)
        summary = AIService().doctor_summary(context)
        st.text_area("Doctor-ready summary", value=summary, height=280)


def render_footer() -> None:
    st.markdown("---")
    st.markdown(
        '<p style="text-align:center;color:#94a3b8;margin-top:1rem;">'
        "Built by <strong style=\"color:#e2e8f0;\">Abhijay Mishra</strong>"
        "</p>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="VitalsAI — Health Copilot",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    bootstrap()

    st.title("VitalsAI")
    st.caption("Your private lab memory · trends · copilot · *Educational only, not a diagnosis.*")

    tab1, tab2, tab3, tab4 = st.tabs(["Upload & Labs", "Chat Copilot", "Risk & Symptoms", "Tools"])

    with tab1:
        page_upload()
    with tab2:
        page_chat()
    with tab3:
        page_risk()
    with tab4:
        page_tools()

    with st.sidebar:
        st.markdown("### Quick tips")
        st.markdown(
            "- Upload a lab report first\n"
            "- Ask about abnormal values in chat\n"
            "- Run disease risk screen\n"
            "- Set `OPENAI_API_KEY` in Streamlit secrets for best AI answers"
        )
        if not os.environ.get("OPENAI_API_KEY"):
            st.warning("No OpenAI key — offline copilot mode active.")

    render_footer()


if __name__ == "__main__":
    main()
