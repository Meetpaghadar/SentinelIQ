from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from sentineliq.contracts import (
    AuthorizationContext,
    GenerationResult,
)
from sentineliq.contracts.query import (
    QueryPath,
)
from sentineliq.querying import (
    QueryAnalyzer,
    QueryPlanner,
)
from sentineliq.rag.service import (
    RAGService,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


class RecordingRetrievalService:
    def __init__(self) -> None:
        self.hybrid_calls = 0
        self.full_calls = 0
        self.last_access_scope = None

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
        del session, tenant_id, query, limit, candidate_k

        self.hybrid_calls += 1
        self.last_access_scope = access_scope

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
        del session, tenant_id, query, limit, candidate_k, rerank, parent_expansion

        self.full_calls += 1
        self.last_access_scope = access_scope

        return [
            RetrievalResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                document_title="Policy",
                document_version_id=uuid4(),
                version_number=1,
                page_number=1,
                content="Employees must use MFA.",
                similarity=0.9,
                retrieval_method="dense+bm25+parent",
            )
        ]


class FakeGenerator:
    def generate(self, request) -> GenerationResult:
        del request

        return GenerationResult(
            text="Employees must use MFA. [1]",
            provider="test",
            model="test",
        )


def _session() -> Session:
    return cast(Session, MagicMock())


def test_rag_factual_simple_question_uses_full_retrieval_path() -> None:
    retrieval = RecordingRetrievalService()

    service = RAGService(
        retrieval,
        generation_provider=FakeGenerator(),
        query_planner=QueryPlanner(enable_rewrite=False),
    )

    analysis = QueryAnalyzer().analyze("What is MFA?")
    plan = QueryPlanner().plan(analysis)

    assert plan.path is QueryPath.NORMAL
    assert plan.rerank is True
    assert plan.parent_expansion is True

    result = service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question="What is MFA?",
    )

    assert retrieval.hybrid_calls == 0
    assert retrieval.full_calls == 1
    assert result.citations


def test_rag_conversational_question_uses_fast_hybrid_path() -> None:
    retrieval = RecordingRetrievalService()

    service = RAGService(
        retrieval,
        generation_provider=FakeGenerator(),
        query_planner=QueryPlanner(enable_rewrite=False),
    )

    analysis = QueryAnalyzer().analyze("Thanks for the help")
    plan = QueryPlanner().plan(analysis)

    assert plan.path is QueryPath.FAST
    assert plan.rerank is False
    assert plan.parent_expansion is False

    service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question="Thanks for the help",
    )

    assert retrieval.hybrid_calls == 1
    assert retrieval.full_calls == 0


def test_rag_normal_question_uses_full_retrieval_path() -> None:
    retrieval = RecordingRetrievalService()

    service = RAGService(
        retrieval,
        generation_provider=FakeGenerator(),
        query_planner=QueryPlanner(enable_rewrite=False),
    )

    question = (
        "Explain the company password policy for remote contractors "
        "and vendors in production systems."
    )

    analysis = QueryAnalyzer().analyze(question)
    plan = QueryPlanner().plan(analysis)

    assert plan.path is QueryPath.NORMAL
    assert plan.rerank is True
    assert plan.parent_expansion is True

    result = service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question=question,
    )

    assert retrieval.hybrid_calls == 0
    assert retrieval.full_calls == 1
    assert result.citations


def test_rag_passes_authorization_scope_to_retrieval() -> None:
    retrieval = RecordingRetrievalService()

    service = RAGService(
        retrieval,
        generation_provider=FakeGenerator(),
        query_planner=QueryPlanner(enable_rewrite=False),
    )

    tenant_id = uuid4()

    authorization = AuthorizationContext(
        tenant_id=tenant_id,
        user_id=uuid4(),
    )

    service.answer(
        session=_session(),
        tenant_id=tenant_id,
        question="What is MFA?",
        authorization=authorization,
    )

    assert retrieval.last_access_scope is not None
    assert retrieval.last_access_scope.tenant_id == tenant_id
