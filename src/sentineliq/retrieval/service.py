from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sentineliq.config import get_settings
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.models import Chunk, Document, DocumentVersion


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version_id: UUID
    version_number: int
    page_number: int | None
    content: str
    similarity: float


class RetrievalService:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def search(
        self,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        query_embedding = self._embedding_service.embed_query(query)
        distance = Chunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(
                Chunk.id,
                Document.id.label("document_id"),
                Document.title,
                DocumentVersion.id.label("document_version_id"),
                DocumentVersion.version_number,
                Chunk.page_number,
                Chunk.content,
                distance.label("distance"),
            )
            .join(
                DocumentVersion,
                Chunk.document_version_id == DocumentVersion.id,
            )
            .join(
                Document,
                DocumentVersion.document_id == Document.id,
            )
            .where(
                Document.tenant_id == tenant_id,
                Chunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        )

        rows = session.execute(statement).all()
        settings = get_settings()

        results: list[RetrievalResult] = []

        for row in rows:
            similarity = 1.0 - float(row.distance)

            if similarity < settings.retrieval_min_similarity:
                continue

            results.append(
                RetrievalResult(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    document_title=row.title,
                    document_version_id=row.document_version_id,
                    version_number=row.version_number,
                    page_number=row.page_number,
                    content=row.content,
                    similarity=similarity,
                )
            )

        return results
