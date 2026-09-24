import pytest

from sentineliq.evaluation.retrieval_metrics import (
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k() -> None:
    score = recall_at_k(
        retrieved=[
            "A",
            "B",
            "C",
        ],
        relevant={
            "B",
            "D",
        },
        k=3,
    )

    assert score == 0.5


def test_reciprocal_rank() -> None:
    score = reciprocal_rank(
        retrieved=[
            "A",
            "B",
            "C",
        ],
        relevant={
            "B",
        },
    )

    assert score == 0.5


def test_reciprocal_rank_missing_result() -> None:
    score = reciprocal_rank(
        retrieved=[
            "A",
            "B",
        ],
        relevant={
            "Z",
        },
    )

    assert score == 0.0


def test_ndcg_perfect_rank() -> None:
    score = ndcg_at_k(
        retrieved=[
            "B",
            "A",
        ],
        relevant={
            "B",
        },
        k=2,
    )

    assert score == pytest.approx(1.0)


def test_ndcg_penalizes_lower_rank() -> None:
    score = ndcg_at_k(
        retrieved=[
            "A",
            "B",
        ],
        relevant={
            "B",
        },
        k=2,
    )

    assert 0.0 < score < 1.0


def test_ndcg_does_not_reward_duplicate_documents() -> None:
    score = ndcg_at_k(
        retrieved=[
            "B",
            "B",
            "B",
        ],
        relevant={
            "B",
        },
        k=5,
    )

    assert score == pytest.approx(1.0)


def test_recall_ignores_duplicate_documents() -> None:
    score = recall_at_k(
        retrieved=[
            "A",
            "A",
            "B",
        ],
        relevant={
            "A",
            "B",
        },
        k=5,
    )

    assert score == 1.0
