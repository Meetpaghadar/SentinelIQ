from sentineliq.retrieval.reranker import (
    LLMReranker,
)


def test_parse_reranker_scores() -> None:
    text = """
    [
        {"index": 1, "score": 0.9},
        {"index": 2, "score": 0.2}
    ]
    """

    scores = LLMReranker._parse_scores(
        text,
        candidate_count=2,
    )

    assert scores[1] == 0.9
    assert scores[2] == 0.2


def test_parse_scores_clamps_values() -> None:
    text = """
    [
        {"index": 1, "score": 1.5},
        {"index": 2, "score": -0.2}
    ]
    """

    scores = LLMReranker._parse_scores(
        text,
        candidate_count=2,
    )

    assert scores[1] == 1.0
    assert scores[2] == 0.0


def test_invalid_json_returns_empty_scores() -> None:
    scores = LLMReranker._parse_scores(
        "not-json",
        candidate_count=3,
    )

    assert scores == {}
