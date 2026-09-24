from sentineliq.evaluation.cases import (
    FROZEN_CASES,
    HARDER_CASES,
)


def test_frozen_benchmark_has_six_cases() -> None:
    assert len(FROZEN_CASES) == 6
    assert sum(case.answerable for case in FROZEN_CASES) == 5
    assert all(case.question for case in FROZEN_CASES)


def test_harder_benchmark_is_separate_and_sized() -> None:
    frozen_questions = {case.question for case in FROZEN_CASES}
    harder_questions = {case.question for case in HARDER_CASES}

    assert 12 <= len(HARDER_CASES) <= 20
    assert frozen_questions.isdisjoint(harder_questions)
    assert any(len(case.expected_documents) > 1 for case in HARDER_CASES)
    assert any(not case.answerable for case in HARDER_CASES)
