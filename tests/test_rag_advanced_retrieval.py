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
    QueryExpander,
    QueryPlanner,
)
from sentineliq.querying.hyde import (
    HYDE_INSTRUCTIONS,
)
from sentineliq.rag.service import (
    RAGService,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


def _result(title: str, content: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content=content,
        similarity=0.9,
        retrieval_method="hybrid",
    )


class RecordingMultiRetrieval:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.scopes = []
        self.original_query: str | None = None

    def search_hybrid(self, **kwargs):
        del kwargs
        return []

    def search(self, **kwargs):
        query = kwargs["query"]
        self.queries.append(query)
        self.scopes.append(kwargs.get("access_scope"))
        return [_result("Policy", "Employees must use MFA.")]

    def search_multi(self, session, tenant_id, queries, **kwargs):
        del session, tenant_id
        self.queries.extend(queries)
        self.original_query = kwargs.get("original_query")
        self.scopes.append(kwargs.get("access_scope"))
        return [_result("Policy", "Employees must use MFA.")]


class RecordingGenerator:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)

        if request.instructions == HYDE_INSTRUCTIONS:
            return GenerationResult(
                text="Hypothetical MFA policy passage.",
                provider="test",
                model="test",
            )

        return GenerationResult(
            text="Employees must use MFA. [1]",
            provider="test",
            model="test",
        )


class ExpandGenerator:
    def generate(self, request: GenerationRequest) -> GenerationResult:
        del request

        return GenerationResult(
            text="What is multi-factor authentication?",
            provider="test",
            model="test",
        )


class EmptyGenerator:
    def generate(self, request: GenerationRequest) -> GenerationResult:
        del request

        return GenerationResult(
            text="",
            provider="test",
            model="test",
        )


def _session() -> Session:
    return cast(Session, MagicMock())


def test_multi_query_forwards_authorization_scope() -> None:
    retrieval = RecordingMultiRetrieval()
    tenant_id = uuid4()

    service = RAGService(
        retrieval,
        generation_provider=RecordingGenerator(),
        query_planner=QueryPlanner(enable_multi_query=True),
        query_expander=QueryExpander(ExpandGenerator()),
    )

    service.answer(
        session=_session(),
        tenant_id=tenant_id,
        question="What is MFA?",
        authorization=AuthorizationContext(
            tenant_id=tenant_id,
            user_id=uuid4(),
        ),
    )

    assert retrieval.queries == [
        "What is MFA?",
        "What is multi-factor authentication?",
    ]
    assert retrieval.scopes
    assert retrieval.scopes[0] is not None
    assert retrieval.scopes[0].tenant_id == tenant_id


def test_multi_query_fallback_uses_original_query() -> None:
    retrieval = RecordingMultiRetrieval()

    service = RAGService(
        retrieval,
        generation_provider=RecordingGenerator(),
        query_planner=QueryPlanner(enable_multi_query=True),
        query_expander=QueryExpander(EmptyGenerator()),
    )

    service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question="What is MFA?",
    )

    assert retrieval.queries == ["What is MFA?"]


def test_hyde_text_is_not_used_as_evidence_or_citation() -> None:
    retrieval = RecordingMultiRetrieval()
    generator = RecordingGenerator()
    hyde_text = "Hypothetical MFA policy passage."

    service = RAGService(
        retrieval,
        generation_provider=generator,
        query_planner=QueryPlanner(enable_hyde=True),
    )

    original = "What is MFA?"

    result = service.answer(
        session=_session(),
        tenant_id=uuid4(),
        question=original,
    )

    assert result.retrieval_query == hyde_text
    assert "hyde" in result.techniques
    assert all(hyde_text not in citation.excerpt for citation in result.citations)
    assert all(citation.document_title != hyde_text for citation in result.citations)

    answer_requests = [
        request for request in generator.requests if request.instructions != HYDE_INSTRUCTIONS
    ]

    assert answer_requests
    assert f"Question:\n{original}\n" in answer_requests[0].input_text
    assert hyde_text not in answer_requests[0].input_text
