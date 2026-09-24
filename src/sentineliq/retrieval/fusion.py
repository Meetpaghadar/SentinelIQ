from dataclasses import dataclass
from uuid import UUID

from sentineliq.retrieval.models import (
    RetrievalResult,
)

DEFAULT_RRF_K = 60


@dataclass
class _FusionEntry:
    result: RetrievalResult

    dense_rank: int | None = None
    sparse_rank: int | None = None

    dense_score: float | None = None
    sparse_score: float | None = None

    fusion_score: float = 0.0


def reciprocal_rank_fusion(
    *,
    dense_results: list[RetrievalResult],
    sparse_results: list[RetrievalResult],
    limit: int,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[RetrievalResult]:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    if rrf_k <= 0:
        raise ValueError("rrf_k must be greater than zero")

    entries: dict[
        UUID,
        _FusionEntry,
    ] = {}

    for rank, result in enumerate(
        dense_results,
        start=1,
    ):
        entry = entries.get(result.chunk_id)

        if entry is None:
            entry = _FusionEntry(result=result)

            entries[result.chunk_id] = entry

        entry.dense_rank = rank
        entry.dense_score = (
            result.dense_score if result.dense_score is not None else result.similarity
        )

        entry.fusion_score += 1.0 / (rrf_k + rank)

    for rank, result in enumerate(
        sparse_results,
        start=1,
    ):
        entry = entries.get(result.chunk_id)

        if entry is None:
            entry = _FusionEntry(result=result)

            entries[result.chunk_id] = entry

        entry.sparse_rank = rank
        entry.sparse_score = result.sparse_score

        entry.fusion_score += 1.0 / (rrf_k + rank)

    ranked_entries = sorted(
        entries.values(),
        key=lambda entry: (
            entry.fusion_score,
            entry.dense_score if entry.dense_score is not None else -1.0,
        ),
        reverse=True,
    )

    results: list[RetrievalResult] = []

    for entry in ranked_entries[:limit]:
        if entry.dense_rank is not None and entry.sparse_rank is not None:
            method = "dense+bm25"

        elif entry.dense_rank is not None:
            method = "dense"

        else:
            method = "bm25"

        similarity = entry.dense_score if entry.dense_score is not None else 0.0

        results.append(
            entry.result.with_updates(
                similarity=(similarity),
                dense_score=(entry.dense_score),
                sparse_score=(entry.sparse_score),
                fusion_score=(entry.fusion_score),
                dense_rank=(entry.dense_rank),
                sparse_rank=(entry.sparse_rank),
                retrieval_method=(method),
            )
        )

    return results
