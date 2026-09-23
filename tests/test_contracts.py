from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sentineliq.contracts import (
    AuthorizationContext,
    CandidateKind,
    DataClassification,
    Evidence,
    ExecutionStage,
    KnowledgeSnapshot,
    KnowledgeStatus,
    ModelExecutionPolicy,
    QueryPath,
    QueryPlan,
    RetrievalCandidate,
    RetrievalPolicy,
    RetrievalStrategy,
    TelemetryEvent,
)


def test_authorization_context_checks_permissions() -> None:
    context = AuthorizationContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset(
            {
                "knowledge:query",
            }
        ),
    )

    assert context.has_permission("knowledge:query")
    assert not context.has_permission("knowledge:delete")


def test_query_plan_rejects_invalid_candidate_count() -> None:
    with pytest.raises(ValueError):
        QueryPlan(
            path=QueryPath.NORMAL,
            top_k=10,
            candidate_k=5,
        )


def test_query_plan_requires_strategy() -> None:
    with pytest.raises(ValueError):
        QueryPlan(
            strategies=(),
        )


def test_retrieval_candidate_preserves_scores() -> None:
    candidate = RetrievalCandidate(
        candidate_id="candidate-1",
        tenant_id=uuid4(),
        kind=CandidateKind.CHUNK,
        retrieval_method=RetrievalStrategy.DENSE,
        content="Example evidence",
        raw_score=0.82,
        fused_score=0.79,
        rerank_score=0.91,
        rank=1,
    )

    assert candidate.raw_score == 0.82
    assert candidate.rerank_score == 0.91


def test_evidence_rejects_invalid_score() -> None:
    with pytest.raises(ValueError):
        Evidence(
            evidence_id="evidence-1",
            tenant_id=uuid4(),
            excerpt="Evidence text",
            retrieval_method=RetrievalStrategy.DENSE,
            relevance=1.2,
        )


def test_snapshot_defaults_to_active_knowledge() -> None:
    snapshot = KnowledgeSnapshot()

    assert snapshot.statuses == frozenset(
        {
            KnowledgeStatus.ACTIVE,
        }
    )


def test_snapshot_requires_status() -> None:
    with pytest.raises(ValueError):
        KnowledgeSnapshot(
            statuses=frozenset(),
        )


def test_retrieval_policy_validates_result_limits() -> None:
    with pytest.raises(ValueError):
        RetrievalPolicy(
            policy_id="default",
            version="1",
            max_candidates=10,
            max_final_results=20,
        )


def test_model_execution_policy_rejects_negative_cost() -> None:
    with pytest.raises(ValueError):
        ModelExecutionPolicy(
            policy_id="default",
            version="1",
            data_classification=(DataClassification.INTERNAL),
            max_cost_usd=-1,
        )


def test_telemetry_rejects_invalid_time_order() -> None:
    started = datetime(
        2026,
        9,
        23,
        12,
        0,
        tzinfo=timezone.utc,
    )

    completed = datetime(
        2026,
        9,
        23,
        11,
        59,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValueError):
        TelemetryEvent(
            request_id="request-1",
            stage=ExecutionStage.RETRIEVAL,
            started_at=started,
            completed_at=completed,
        )
