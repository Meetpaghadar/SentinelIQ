import pytest

from sentineliq.decision.jev import (
    JevDecisionError,
    JevDecisionProvider,
)


def _provider() -> JevDecisionProvider:
    return JevDecisionProvider(api_key="test-key")


def test_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError):
        JevDecisionProvider(api_key="")


def test_extracts_choice_answer() -> None:
    payload = {
        "answers": {
            "decision": {
                "type": "choice",
                "choice": "normal",
                "confidence": 0.91,
                "probabilities": {
                    "fast": 0.05,
                    "normal": 0.91,
                    "deep": 0.04,
                },
            }
        }
    }

    answer = _provider()._answer(
        payload,
        name="decision",
        expected_type="choice",
    )

    assert answer["choice"] == "normal"


def test_rejects_wrong_answer_type() -> None:
    payload = {
        "answers": {
            "decision": {
                "type": "score",
                "score": 1.0,
            }
        }
    }

    with pytest.raises(JevDecisionError):
        _provider()._answer(
            payload,
            name="decision",
            expected_type="choice",
        )


def test_rejects_missing_answers() -> None:
    with pytest.raises(JevDecisionError):
        _provider()._answer(
            {},
            name="decision",
            expected_type="choice",
        )
