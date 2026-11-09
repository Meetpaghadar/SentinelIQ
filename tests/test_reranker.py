from collections.abc import Sequence
from uuid import uuid4

import pytest

from sentineliq.providers.openai_reranker import OpenAIRerankerProvider
from sentineliq.retrieval.access import RetrievalAccessScope
from sentineliq.retrieval.models import RetrievalResult
from sentineliq.retrieval.reranker import LLMReranker
from sentineliq.retrieval.service import RetrievalService


def test_parse_reranker_scores() -> None:
    text = """
    [
        {"index": 1, "score": 0.9},
        {"index": 2, "score": 0.2}
    ]
    """

    scores = OpenAIRerankerProvider._parse_scores(
        text,
        count=2,
    )

    assert scores == [0.9, 0.2]


def test_parse_scores_clamps_values() -> None:
    text = """
    [
        {"index": 1, "score": 1.5},
        {"index": 2, "score": -0.2}
    ]
    """

    scores = OpenAIRerankerProvider._parse_scores(
        text,
        count=2,
    )

    assert scores == [1.0, 0.0]


def test_invalid_json_raises_controlled_failure() -> None:
    with pytest.raises(RuntimeError, match="malformed JSON"):
        OpenAIRerankerProvider._parse_scores(
            "not-json",
            count=3,
        )


class _Scores:
    def rerank(self, *, query: str, documents: Sequence[str]) -> list[float]:
        del query, documents
        return [0.1, 0.9]


class _Failure:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def rerank(self, *, query: str, documents: Sequence[str]) -> list[float]:
        del query, documents
        raise self.error


def _result(title: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content=title,
        similarity=0.5,
    )


def test_reranker_success_orders_by_provider_score() -> None:
    ordered = LLMReranker(_Scores()).rerank(
        query="policy",
        candidates=[_result("first"), _result("second")],
        limit=2,
    )
    assert [item.document_title for item in ordered] == ["second", "first"]


@pytest.mark.parametrize(
    "error",
    [RuntimeError("malformed provider output"), ValueError("wrong score count")],
)
def test_reranker_failure_falls_back_to_hybrid_order(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    hybrid = [_result("hybrid-first"), _result("hybrid-second")]
    service = RetrievalService.__new__(RetrievalService)
    service._reranker = LLMReranker(_Failure(error))
    monkeypatch.setattr(service, "search_hybrid", lambda **_kwargs: hybrid)

    results = service.search(
        session=None,  # type: ignore[arg-type]
        tenant_id=uuid4(),
        query="policy",
        access_scope=RetrievalAccessScope(tenant_id=uuid4()),
        limit=2,
        rerank=True,
        parent_expansion=False,
    )
    assert results == hybrid
