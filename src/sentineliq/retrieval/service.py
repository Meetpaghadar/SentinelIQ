from uuid import UUID

from sqlalchemy.orm import Session

from sentineliq.embeddings.service import (
    EmbeddingService,
)
from sentineliq.retrieval.dense import (
    DenseRetriever,
)
from sentineliq.retrieval.fusion import (
    reciprocal_rank_fusion,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)
from sentineliq.retrieval.parent_expansion import (
    ParentExpander,
)
from sentineliq.retrieval.reranker import (
    LLMReranker,
)
from sentineliq.retrieval.sparse import (
    BM25Retriever,
)

DEFAULT_CANDIDATE_K = 40
DEFAULT_FUSION_K = 20


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
    ) -> None:
        self._dense_retriever = DenseRetriever(embedding_service)

        self._sparse_retriever = BM25Retriever()

        self._reranker = LLMReranker()

        self._parent_expander = ParentExpander()

    def search_dense(
        self,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        candidate_k = max(
            DEFAULT_CANDIDATE_K,
            limit,
        )

        results = self._dense_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=candidate_k,
        )

        return results[:limit]

    def search_sparse(
        self,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        candidate_k = max(
            DEFAULT_CANDIDATE_K,
            limit,
        )

        results = self._sparse_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=candidate_k,
        )

        return results[:limit]

    def search_hybrid(
        self,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        candidate_k = max(
            DEFAULT_CANDIDATE_K,
            limit * 2,
        )

        dense_results = self._dense_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=candidate_k,
        )

        sparse_results = self._sparse_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=candidate_k,
        )

        return reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            limit=limit,
        )

    def search(
        self,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        fused = self.search_hybrid(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=max(
                DEFAULT_FUSION_K,
                limit,
            ),
        )

        reranked_children = self._reranker.rerank(
            query=query,
            candidates=fused,
            limit=limit,
        )

        expanded = self._parent_expander.expand(
            session,
            children=reranked_children,
        )

        return expanded[:limit]
