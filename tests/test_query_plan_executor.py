from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from sentineliq.contracts.query import (
    QueryPath,
    QueryPlan,
    RetrievalStrategy,
)
from sentineliq.querying import (
    QueryPlanExecutor,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
)


class FakeRetrievalService:
    def __init__(self) -> None:
        self.hybrid_calls = 0
        self.full_calls = 0
        self.last_access_scope = None
        self.last_candidate_k = None

    def search_hybrid(
        self,
        *,
        session: Session,
        tenant_id,
        query: str,
        limit: int,
        access_scope=None,
        candidate_k=None,
    ):
        del (
            session,
            tenant_id,
            query,
            limit,
        )

        self.hybrid_calls += 1
        self.last_access_scope = access_scope
        self.last_candidate_k = candidate_k

        return []

    def search(
        self,
        *,
        session: Session,
        tenant_id,
        query: str,
        limit: int,
        access_scope=None,
        candidate_k=None,
        rerank=True,
        parent_expansion=True,
    ):
        del (
            session,
            tenant_id,
            query,
            limit,
            rerank,
            parent_expansion,
        )

        self.full_calls += 1
        self.last_access_scope = access_scope
        self.last_candidate_k = candidate_k

        return []


def _session() -> Session:
    return cast(
        Session,
        MagicMock(),
    )


def test_fast_path_uses_hybrid_without_full_pipeline() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.FAST,
        strategies=(RetrievalStrategy.HYBRID,),
        top_k=5,
        candidate_k=20,
        rerank=False,
        parent_expansion=False,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query="What is MFA?",
        plan=plan,
    )

    assert retrieval.hybrid_calls == 1
    assert retrieval.full_calls == 0

    assert execution.executed_path is QueryPath.FAST

    assert execution.degraded is False

    assert retrieval.last_candidate_k == 20


def test_fast_path_with_parent_expansion_uses_configured_search() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.FAST,
        strategies=(RetrievalStrategy.HYBRID,),
        top_k=5,
        candidate_k=20,
        rerank=False,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query="What is MFA?",
        plan=plan,
    )

    assert retrieval.hybrid_calls == 0
    assert retrieval.full_calls == 1
    assert execution.executed_path is QueryPath.FAST


def test_normal_path_preserves_full_pipeline() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.NORMAL,
        strategies=(RetrievalStrategy.HYBRID,),
        top_k=5,
        candidate_k=40,
        rerank=True,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query="Explain the MFA policy.",
        plan=plan,
    )

    assert retrieval.hybrid_calls == 0
    assert retrieval.full_calls == 1

    assert execution.executed_path is QueryPath.NORMAL

    assert execution.degraded is False

    assert retrieval.last_candidate_k == 40


def test_executor_forwards_access_scope() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    tenant_id = uuid4()

    access_scope = RetrievalAccessScope(tenant_id=tenant_id)

    plan = QueryPlan(
        path=QueryPath.FAST,
        strategies=(RetrievalStrategy.HYBRID,),
        top_k=5,
        candidate_k=20,
        rerank=False,
        parent_expansion=False,
    )

    executor.execute(
        session=_session(),
        tenant_id=tenant_id,
        query="What is MFA?",
        plan=plan,
        access_scope=access_scope,
    )

    assert retrieval.last_access_scope is access_scope


def test_deep_path_currently_uses_full_pipeline() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.DEEP,
        strategies=(RetrievalStrategy.HYBRID,),
        top_k=8,
        candidate_k=60,
        rerank=True,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query="Investigate MFA controls.",
        plan=plan,
    )

    assert retrieval.full_calls == 1

    assert execution.executed_path is QueryPath.DEEP


def test_graph_strategy_degrades_to_document_retrieval() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.DEEP,
        strategies=(
            RetrievalStrategy.GRAPH,
            RetrievalStrategy.HYBRID,
        ),
        top_k=8,
        candidate_k=60,
        rerank=True,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query=("Which systems are affected by this policy?"),
        plan=plan,
    )

    assert retrieval.full_calls == 1

    assert execution.degraded is True

    assert execution.executed_path is QueryPath.NORMAL

    assert execution.degradation_reason is not None


def test_sql_strategy_degrades_to_document_retrieval() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.NORMAL,
        strategies=(
            RetrievalStrategy.SQL,
            RetrievalStrategy.HYBRID,
        ),
        top_k=5,
        candidate_k=40,
        rerank=True,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query=("How many findings are overdue?"),
        plan=plan,
    )

    assert retrieval.full_calls == 1
    assert execution.degraded is True
    assert execution.executed_path is QueryPath.NORMAL
    assert execution.degradation_reason is not None


def test_temporal_strategy_degrades_to_document_retrieval() -> None:
    retrieval = FakeRetrievalService()

    executor = QueryPlanExecutor(retrieval)

    plan = QueryPlan(
        path=QueryPath.DEEP,
        strategies=(
            RetrievalStrategy.TEMPORAL,
            RetrievalStrategy.HYBRID,
        ),
        top_k=8,
        candidate_k=60,
        rerank=True,
        parent_expansion=True,
    )

    execution = executor.execute(
        session=_session(),
        tenant_id=uuid4(),
        query=("What was the policy in 2025?"),
        plan=plan,
    )

    assert retrieval.full_calls == 1
    assert execution.degraded is True
    assert execution.executed_path is QueryPath.NORMAL
    assert execution.degradation_reason is not None
