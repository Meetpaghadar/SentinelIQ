from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from sentineliq.contracts import (
    AuthorizationContext,
    GenerationRequest,
    GenerationResult,
)
from sentineliq.querying import (
    QueryPlanner,
)
from sentineliq.querying.rewriter import (
    REWRITE_INSTRUCTIONS,
)
from sentineliq.rag.service import (
    RAGService,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


class RecordingRetrievalService:
    def __init__(self) -> None:
        self.last_query: str | None = None
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
        del session, tenant_id, limit, candidate_k

        self.last_query = query
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
        del session, tenant_id, limit, candidate_k, rerank, parent_expansion

        self.last_query = query
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


class RecordingGenerator:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)

        if request.instructions == REWRITE_INSTRUCTIONS:
            return GenerationResult(
                text="What is multi-factor authentication?",
                provider="test",
                model="test",
            )

        return GenerationResult(
            text="Employees must use MFA. [1]",
            provider="test",
            model="test",
        )


def _session() -> Session:
    return cast(Session, MagicMock())


def test_rewritten_retrieval_keeps_authorization_scope() -> None:
    retrieval = RecordingRetrievalService()
    generator = RecordingGenerator()
    tenant_id = uuid4()

    service = RAGService(
        retrieval,
        generation_provider=generator,
        query_planner=QueryPlanner(enable_rewrite=True),
    )

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

    assert retrieval.last_query == "What is multi-factor authentication?"
    assert retrieval.last_access_scope is not None
    assert retrieval.last_access_scope.tenant_id == tenant_id


def test_generation_receives_original_question() -> None:
    retrieval = RecordingRetrievalService()
    generator = RecordingGenerator()

    service = RAGService(
        retrieval,
        generation_provider=generator,
        query_planner=QueryPlanner(enable_rewrite=True),
    )

    original = "What is MFA?"

    result = service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question=original,
    )

    assert result.rewrite_used is True
    assert result.retrieval_query == "What is multi-factor authentication?"

    generation_requests = [
        request
        for request in generator.requests
        if request.instructions != REWRITE_INSTRUCTIONS
    ]

    assert generation_requests
    assert f"Question:\n{original}\n" in generation_requests[0].input_text
