import hashlib
import re
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

from app.core.config import settings, get_qdrant_url

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels

    QDRANT_AVAILABLE = True
except ImportError:
    QdrantClient = None  # type: ignore[misc, assignment]
    qmodels = None  # type: ignore[assignment]
    QDRANT_AVAILABLE = False

COLLECTION = "health_report_chunks"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
MAX_CHUNKS_PER_REPORT = 20

QdrantMode = Literal["server", "local", "none"]


def _chunk_text(text: str) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def _point_id(report_id: int, chunk_index: int) -> int:
    raw = f"{report_id}:{chunk_index}".encode()
    return int(hashlib.md5(raw).hexdigest()[:15], 16)


class RAGService:
    _client: Any = None
    _mode: QdrantMode = "none"
    _collection_ready = False

    @classmethod
    def get_mode(cls) -> QdrantMode:
        cls._qdrant()
        return cls._mode

    @classmethod
    def _qdrant(cls) -> Any:
        if not settings.rag_enabled or not QDRANT_AVAILABLE:
            cls._mode = "none"
            return None
        if cls._client is not None:
            return cls._client

        if not settings.qdrant_prefer_local:
            client = cls._try_server_client()
            if client:
                return client

        client = cls._try_local_client()
        if client:
            return client

        if settings.qdrant_prefer_local:
            client = cls._try_server_client()
            if client:
                return client

        cls._mode = "none"
        return None

    @classmethod
    def _try_server_client(cls) -> Any:
        try:
            client = QdrantClient(url=get_qdrant_url(), timeout=5)
            client.get_collections()
            cls._client = client
            cls._mode = "server"
            return client
        except Exception:
            return None

    @classmethod
    def _try_local_client(cls) -> Any:
        try:
            path = Path(settings.qdrant_local_path)
            path.mkdir(parents=True, exist_ok=True)
            client = QdrantClient(path=str(path.resolve()))
            client.get_collections()
            cls._client = client
            cls._mode = "local"
            return client
        except Exception:
            return None

    @classmethod
    def _openai(cls) -> OpenAI | None:
        if not settings.openai_api_key:
            return None
        return OpenAI(api_key=settings.openai_api_key, timeout=15)

    @classmethod
    def ensure_collection(cls) -> bool:
        if not QDRANT_AVAILABLE:
            return False
        client = cls._qdrant()
        oai = cls._openai()
        if not client or not oai:
            return False
        if cls._collection_ready:
            return True
        try:
            names = {c.name for c in client.get_collections().collections}
            if COLLECTION not in names:
                client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=qmodels.VectorParams(
                        size=settings.embedding_dimensions,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            cls._collection_ready = True
            return True
        except Exception:
            return False

    @classmethod
    def _embed(cls, texts: list[str]) -> list[list[float]] | None:
        oai = cls._openai()
        if not oai or not texts:
            return None
        try:
            res = oai.embeddings.create(model=settings.embedding_model, input=texts)
            return [item.embedding for item in res.data]
        except Exception:
            return None

    @classmethod
    def index_report(cls, report_id: int, title: str, raw_text: str) -> int:
        if not cls.ensure_collection():
            return 0
        client = cls._qdrant()
        if not client:
            return 0

        chunks = _chunk_text(raw_text)[:MAX_CHUNKS_PER_REPORT]
        if not chunks:
            return 0

        vectors = cls._embed(chunks)
        if not vectors:
            return 0

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                qmodels.PointStruct(
                    id=_point_id(report_id, idx),
                    vector=vector,
                    payload={
                        "report_id": report_id,
                        "title": title,
                        "chunk_index": idx,
                        "text": chunk,
                    },
                )
            )

        try:
            client.upsert(collection_name=COLLECTION, points=points)
            return len(points)
        except Exception:
            return 0

    @classmethod
    def search(cls, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if not cls.ensure_collection():
            return []
        client = cls._qdrant()
        if not client:
            return []

        vectors = cls._embed([query])
        if not vectors:
            return []

        try:
            hits = client.search(
                collection_name=COLLECTION,
                query_vector=vectors[0],
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []

        results: list[dict[str, Any]] = []
        for hit in hits:
            payload = hit.payload or {}
            text = str(payload.get("text", ""))
            title = str(payload.get("title", "Report"))
            snippet = text[:280].replace("\n", " ")
            results.append(
                {
                    "report_id": payload.get("report_id"),
                    "title": title,
                    "snippet": snippet,
                    "score": hit.score,
                    "citation": f"[{title}] {snippet}",
                }
            )
        return results

    @classmethod
    def search_citations(cls, query: str, top_k: int = 4) -> list[str]:
        return [r["citation"] for r in cls.search(query, top_k=top_k)]
