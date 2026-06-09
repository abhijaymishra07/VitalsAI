import re
from collections import Counter
from math import sqrt

from sqlmodel import Session, select

from app.models.entities import MedicalReport
from app.services.rag_service import RAGService

BOILERPLATE_PATTERN = re.compile(
    r"apollo clinic|phone no:|disclaimer|kothandaram|health report\s*$|patient name",
    flags=re.IGNORECASE,
)

LAB_SNIPPET_MARKERS = (
    "lab panel",
    "vitamin d",
    "vitamin b12",
    "cholesterol",
    "glucose",
    "haemoglobin",
    "creatinine",
    "thyroid",
    "triglyceride",
    "complete blood count",
)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if t.strip()]


def _report_snippet(text: str, query: str, max_len: int = 240) -> str:
    lower_text = text.lower()
    for term in _tokenize(query):
        if len(term) < 3:
            continue
        idx = lower_text.find(term)
        if idx >= 0:
            start = max(0, idx - 60)
            snippet = text[start : start + max_len].replace("\n", " ").strip()
            if not BOILERPLATE_PATTERN.search(snippet[:120]):
                return snippet

    for marker in LAB_SNIPPET_MARKERS:
        idx = lower_text.find(marker)
        if idx >= 0:
            return text[idx : idx + max_len].replace("\n", " ").strip()

    trimmed = text[400 : 400 + max_len] if len(text) > 400 else text[:max_len]
    return trimmed.replace("\n", " ").strip()


def _cosine(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    numerator = sum(a[t] * b[t] for t in common)
    den_a = sqrt(sum(v * v for v in a.values()))
    den_b = sqrt(sum(v * v for v in b.values()))
    if den_a == 0 or den_b == 0:
        return 0.0
    return numerator / (den_a * den_b)


class SemanticSearchService:
    @staticmethod
    def _lexical_search(session: Session, query: str, top_k: int = 5) -> list[str]:
        query_vec = Counter(_tokenize(query))
        rows = session.exec(select(MedicalReport)).all()
        scored = []
        for row in rows:
            score = _cosine(query_vec, Counter(_tokenize(row.raw_text)))
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[str] = []
        for score, row in scored[:top_k]:
            if score <= 0:
                continue
            snippet = _report_snippet(row.raw_text, query)
            if BOILERPLATE_PATTERN.search(snippet[:160]):
                continue
            results.append(f"{row.title}: {snippet}")
        return results

    @staticmethod
    def search_reports(session: Session, query: str, top_k: int = 5) -> list[str]:
        lexical_hits = SemanticSearchService._lexical_search(session, query, top_k=top_k)
        if lexical_hits:
            return lexical_hits
        return RAGService.search_citations(query, top_k=top_k)

    @staticmethod
    def search_citations(session: Session, query: str, top_k: int = 5) -> list[str]:
        return SemanticSearchService.search_reports(session, query, top_k=top_k)
