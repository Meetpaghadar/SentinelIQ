from uuid import uuid4

from sentineliq.retrieval.fusion import (
    reciprocal_rank_fusion,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


def _result(
    name: str,
    *,
    similarity: float = 0.0,
    sparse_score: float | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=name,
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content=name,
        similarity=similarity,
        sparse_score=sparse_score,
    )


def test_rrf_rewards_result_found_by_both() -> None:
    shared = _result(
        "shared",
        similarity=0.9,
        sparse_score=4.0,
    )

    dense_only = _result(
        "dense",
        similarity=0.95,
    )

    sparse_only = _result(
        "sparse",
        sparse_score=5.0,
    )

    results = reciprocal_rank_fusion(
        dense_results=[
            dense_only,
            shared,
        ],
        sparse_results=[
            sparse_only,
            shared,
        ],
        limit=3,
    )

    assert results[0].chunk_id == shared.chunk_id

    assert results[0].retrieval_method == "dense+bm25"


def test_rrf_respects_limit() -> None:
    dense = [
        _result(
            f"dense-{index}",
            similarity=0.8,
        )
        for index in range(5)
    ]

    results = reciprocal_rank_fusion(
        dense_results=dense,
        sparse_results=[],
        limit=2,
    )

    assert len(results) == 2
