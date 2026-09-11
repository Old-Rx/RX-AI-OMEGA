import hashlib
import math
import re
from abc import ABC, abstractmethod

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Document
from .schemas import SearchHit

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
VECTOR_SIZE = 128


def tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN_RE.finditer(text)}


def embed(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for token in tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_SIZE
        vector[index] += 1.0 if digest[2] % 2 else -1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


class MemoryStore(ABC):
    @abstractmethod
    def index(self, document: Document) -> None: ...

    @abstractmethod
    def search(self, db: Session, query: str, limit: int) -> list[SearchHit]: ...


class LocalMemoryStore(MemoryStore):
    def index(self, document: Document) -> None:
        return None

    def search(self, db: Session, query: str, limit: int) -> list[SearchHit]:
        query_tokens = tokens(query)
        hits: list[SearchHit] = []
        for document in db.scalars(select(Document)).all():
            document_tokens = tokens(document.title + " " + document.content)
            union = query_tokens | document_tokens
            score = len(query_tokens & document_tokens) / len(union) if union else 0.0
            if score > 0:
                hits.append(
                    SearchHit(
                        document_id=document.id,
                        title=document.title,
                        score=score,
                        excerpt=document.content[:300],
                    )
                )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]


class QdrantMemoryStore(MemoryStore):
    collection = "rx_ai_omega_documents"

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        headers = {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else {}
        self.client = client or httpx.Client(base_url=settings.qdrant_url, headers=headers, timeout=30)
        self.client.put(
            f"/collections/{self.collection}",
            json={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}},
        ).raise_for_status()

    def index(self, document: Document) -> None:
        response = self.client.put(
            f"/collections/{self.collection}/points?wait=true",
            json={
                "points": [{
                    "id": document.id,
                    "vector": embed(document.title + " " + document.content),
                    "payload": {"title": document.title, "content": document.content[:2_000]},
                }]
            },
        )
        response.raise_for_status()

    def search(self, db: Session, query: str, limit: int) -> list[SearchHit]:
        response = self.client.post(
            f"/collections/{self.collection}/points/query",
            json={"query": embed(query), "limit": limit, "with_payload": True},
        )
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        return [
            SearchHit(
                document_id=str(point["id"]),
                title=str(point.get("payload", {}).get("title", "Untitled")),
                score=float(point.get("score", 0)),
                excerpt=str(point.get("payload", {}).get("content", ""))[:300],
            )
            for point in points
        ]


def build_memory(settings: Settings) -> MemoryStore:
    if settings.memory_backend == "qdrant":
        return QdrantMemoryStore(settings)
    return LocalMemoryStore()
