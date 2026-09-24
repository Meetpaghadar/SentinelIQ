import math
from collections.abc import Sequence


def _unique_in_order(
    values: Sequence[str],
) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        unique.append(value)

    return unique


def recall_at_k(
    *,
    retrieved: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")

    if not relevant:
        return 1.0

    unique_retrieved = _unique_in_order(retrieved)

    retrieved_at_k = set(unique_retrieved[:k])

    relevant_found = retrieved_at_k & relevant

    return len(relevant_found) / len(relevant)


def reciprocal_rank(
    *,
    retrieved: Sequence[str],
    relevant: set[str],
) -> float:
    if not relevant:
        return 1.0

    unique_retrieved = _unique_in_order(retrieved)

    for rank, item in enumerate(
        unique_retrieved,
        start=1,
    ):
        if item in relevant:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    *,
    retrieved: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")

    if not relevant:
        return 1.0

    unique_retrieved = _unique_in_order(retrieved)

    dcg = 0.0

    for rank, item in enumerate(
        unique_retrieved[:k],
        start=1,
    ):
        if item not in relevant:
            continue

        dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(
        len(relevant),
        k,
    )

    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            ideal_hits + 1,
        )
    )

    if idcg == 0:
        return 0.0

    return dcg / idcg
