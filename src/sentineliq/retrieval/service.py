from uuid import UUID

from sqlalchemy.orm import Session

from sentineliq.embeddings.service import (
    EmbeddingService,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
)
from sentineliq.retrieval.dense import (
    DenseRetriever,
)
from sentineliq.retrieval.fusion import (
    reciprocal_rank_fuse_lists,
    reciprocal_rank_fusion,
    unique_merge,
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
        access_scope: RetrievalAccessScope | None = None,
        candidate_k: int | None = None,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        resolved_candidate_k = max(
            candidate_k or DEFAULT_CANDIDATE_K,
            limit * 2,
        )

        dense_results = self._dense_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=resolved_candidate_k,
            access_scope=access_scope,
        )

        sparse_results = self._sparse_retriever.search(
            session,
            tenant_id=tenant_id,
            query=query,
            candidate_k=resolved_candidate_k,
            access_scope=access_scope,
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
        access_scope: RetrievalAccessScope | None = None,
        candidate_k: int | None = None,
        rerank: bool = True,
        parent_expansion: bool = True,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        fused_limit = max(DEFAULT_FUSION_K, limit) if rerank else limit

        fused = self.search_hybrid(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=fused_limit,
            access_scope=access_scope,
            candidate_k=candidate_k,
        )

        children = fused[:limit]

        if rerank:
            children = self._reranker.rerank(
                query=query,
                candidates=fused,
                limit=limit,
            )

        if not parent_expansion:
            return children[:limit]

        expanded = self._parent_expander.expand(
            session,
            children=children,
        )

        return expanded[:limit]

    def search_multi(
        self,
        session: Session,
        tenant_id: UUID,
        queries: list[str],
        *,
        original_query: str,
        limit: int = 5,
        access_scope: RetrievalAccessScope | None = None,
        candidate_k: int | None = None,
        fusion: str = "rrf",
        rerank: bool = True,
        parent_expansion: bool = True,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        if not queries:
            raise ValueError("at least one query is required")

        fused_limit = max(DEFAULT_FUSION_K, limit) if rerank else limit

        ranked_lists = [
            self.search_hybrid(
                session=session,
                tenant_id=tenant_id,
                query=query,
                limit=fused_limit,
                access_scope=access_scope,
                candidate_k=candidate_k,
            )
            for query in queries
        ]

        if fusion == "rrf":
            fused = reciprocal_rank_fuse_lists(
                ranked_lists,
                limit=fused_limit,
            )
        else:
            fused = unique_merge(
                ranked_lists,
                limit=fused_limit,
            )

        children = fused[:limit]

        if rerank:
            children = self._reranker.rerank(
                query=original_query,
                candidates=fused,
                limit=limit,
            )

        if not parent_expansion:
            return children[:limit]

        expanded = self._parent_expander.expand(
            session,
            children=children,
        )

        return expanded[:limit]
