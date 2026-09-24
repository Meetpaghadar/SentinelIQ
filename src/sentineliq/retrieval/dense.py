from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sentineliq.config import get_settings
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeStatus,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
    build_access_predicates,
)
from sentineliq.retrieval.models import RetrievalResult


class DenseRetriever:
    def __init__(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        self._embedding_service = embedding_service

    def search(
        self,
        session: Session,
        *,
        tenant_id: UUID,
        query: str,
        candidate_k: int,
        access_scope: RetrievalAccessScope | None = None,
    ) -> list[RetrievalResult]:
        if candidate_k <= 0:
            raise ValueError(
                "candidate_k must be greater than zero"
            )

        scope = (
            access_scope
            or RetrievalAccessScope(
                tenant_id=tenant_id
            )
        )

        if scope.tenant_id != tenant_id:
            raise ValueError(
                "Retrieval access scope tenant "
                "does not match requested tenant"
            )

        query_embedding = (
            self._embedding_service.embed_query(
                query
            )
        )

        distance = (
            Chunk.embedding.cosine_distance(
                query_embedding
            )
        )

        statement = (
            select(
                Chunk.id,
                Document.id.label(
                    "document_id"
                ),
                Document.title,
                DocumentVersion.id.label(
                    "document_version_id"
                ),
                DocumentVersion.version_number,
                Chunk.page_number,
                Chunk.content,
                distance.label(
                    "distance"
                ),
            )
            .join(
                DocumentVersion,
                Chunk.document_version_id
                == DocumentVersion.id,
            )
            .join(
                Document,
                DocumentVersion.document_id
                == Document.id,
            )
            .where(
                *build_access_predicates(
                    scope
                ),
                DocumentVersion.status
                == KnowledgeStatus.ACTIVE.value,
                or_(
                    DocumentVersion.effective_from.is_(
                        None
                    ),
                    DocumentVersion.effective_from
                    <= func.now(),
                ),
                or_(
                    DocumentVersion.effective_until.is_(
                        None
                    ),
                    DocumentVersion.effective_until
                    > func.now(),
                ),
                Chunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(candidate_k)
        )

        rows = (
            session.execute(
                statement
            ).all()
        )

        settings = get_settings()

        results: list[
            RetrievalResult
        ] = []

        for rank, row in enumerate(
            rows,
            start=1,
        ):
            similarity = (
                1.0
                - float(
                    row.distance
                )
            )

            if (
                similarity
                < settings.retrieval_min_similarity
            ):
                continue

            results.append(
                RetrievalResult(
                    chunk_id=row.id,
                    document_id=(
                        row.document_id
                    ),
                    document_title=(
                        row.title
                    ),
                    document_version_id=(
                        row.document_version_id
                    ),
                    version_number=(
                        row.version_number
                    ),
                    page_number=(
                        row.page_number
                    ),
                    content=row.content,
                    similarity=similarity,
                    dense_score=similarity,
                    dense_rank=rank,
                    retrieval_method="dense",
                )
            )

        return results