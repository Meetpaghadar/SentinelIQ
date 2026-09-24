from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from sentineliq.contracts.query import (
    QueryPath,
    QueryPlan,
    RetrievalStrategy,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


class RetrievalExecutionUnavailable(RuntimeError):
    pass


class RetrievalBackend(Protocol):
    def search_hybrid(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int,
        access_scope: RetrievalAccessScope | None = None,
        candidate_k: int | None = None,
    ) -> list[RetrievalResult]: ...

    def search(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        limit: int,
        access_scope: RetrievalAccessScope | None = None,
        candidate_k: int | None = None,
        rerank: bool = True,
        parent_expansion: bool = True,
    ) -> list[RetrievalResult]: ...


@dataclass(frozen=True, slots=True)
class PlannedRetrievalExecution:
    results: list[RetrievalResult]

    requested_path: QueryPath
    executed_path: QueryPath

    requested_strategies: tuple[
        RetrievalStrategy,
        ...,
    ]

    degraded: bool = False
    degradation_reason: str | None = None


class QueryPlanExecutor:
    def __init__(
        self,
        retrieval_service: RetrievalBackend,
    ) -> None:
        self._retrieval_service = retrieval_service

    def execute(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None = None,
        variant_queries: tuple[str, ...] = (),
    ) -> PlannedRetrievalExecution:
        self._validate_plan(plan)

        if variant_queries:
            return self._execute_multi(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
                variant_queries=variant_queries,
            )

        if RetrievalStrategy.SQL in plan.strategies:
            return self._execute_sql_fallback(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        if RetrievalStrategy.TEMPORAL in plan.strategies:
            return self._execute_temporal_fallback(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        if RetrievalStrategy.GRAPH in plan.strategies:
            return self._execute_graph_fallback(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        if plan.path is QueryPath.FAST:
            if plan.rerank or plan.parent_expansion:
                return self._execute_full(
                    session=session,
                    tenant_id=tenant_id,
                    query=query,
                    plan=plan,
                    access_scope=access_scope,
                )

            return self._execute_fast(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        if plan.path in {
            QueryPath.NORMAL,
            QueryPath.DEEP,
        }:
            return self._execute_full(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        if plan.path is QueryPath.FALLBACK:
            return self._execute_fallback(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        raise RetrievalExecutionUnavailable("Unsupported query path")

    def _execute_fast(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search_hybrid(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=QueryPath.FAST,
            requested_strategies=(plan.strategies),
        )

    def _execute_full(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=plan.path,
            requested_strategies=(plan.strategies),
        )

    def _execute_sql_fallback(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=QueryPath.NORMAL,
            requested_strategies=(plan.strategies),
            degraded=True,
            degradation_reason=(
                "SQL retrieval is not implemented yet; used the document hybrid retrieval path."
            ),
        )

    def _execute_temporal_fallback(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=QueryPath.NORMAL,
            requested_strategies=(plan.strategies),
            degraded=True,
            degradation_reason=(
                "Temporal/version-aware retrieval is not implemented yet; "
                "used the document hybrid retrieval path."
            ),
        )

    def _execute_graph_fallback(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=QueryPath.NORMAL,
            requested_strategies=(plan.strategies),
            degraded=True,
            degradation_reason=(
                "Graph retrieval is not implemented yet; used the document hybrid retrieval path."
            ),
        )

    def _execute_fallback(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
    ) -> PlannedRetrievalExecution:
        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=QueryPath.NORMAL,
            requested_strategies=(plan.strategies),
            degraded=True,
            degradation_reason=("Fallback path executed using the stable hybrid retrieval path."),
        )

    def _execute_multi(
        self,
        *,
        session: Session,
        tenant_id: UUID,
        query: str,
        plan: QueryPlan,
        access_scope: RetrievalAccessScope | None,
        variant_queries: tuple[str, ...],
    ) -> PlannedRetrievalExecution:
        search_multi = getattr(
            self._retrieval_service,
            "search_multi",
            None,
        )

        if search_multi is None:
            return self._execute_full(
                session=session,
                tenant_id=tenant_id,
                query=query,
                plan=plan,
                access_scope=access_scope,
            )

        fusion = "rrf" if plan.rag_fusion else "merge"

        results = search_multi(
            session,
            tenant_id,
            list(variant_queries),
            original_query=query,
            limit=plan.top_k,
            access_scope=access_scope,
            candidate_k=plan.candidate_k,
            fusion=fusion,
            rerank=plan.rerank,
            parent_expansion=plan.parent_expansion,
        )

        return PlannedRetrievalExecution(
            results=results,
            requested_path=plan.path,
            executed_path=plan.path,
            requested_strategies=(plan.strategies),
        )

    @staticmethod
    def _validate_plan(
        plan: QueryPlan,
    ) -> None:
        implemented = {
            RetrievalStrategy.DENSE,
            RetrievalStrategy.SPARSE,
            RetrievalStrategy.HYBRID,
            RetrievalStrategy.TEMPORAL,
            RetrievalStrategy.GRAPH,
            RetrievalStrategy.SQL,
        }

        unknown = set(plan.strategies) - implemented

        if unknown:
            raise RetrievalExecutionUnavailable(
                f"Query plan contains unsupported strategies: {unknown}"
            )
