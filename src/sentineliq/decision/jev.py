import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentineliq.decision.contracts import (
    ChoiceDecision,
    DecisionProvider,
    ProbabilityDecision,
    ScoreDecision,
)

DEFAULT_JEV_BASE_URL = "https://api.typesafe.ai"

DEFAULT_JEV_MODEL = "jev-latest"


class JevDecisionError(RuntimeError):
    pass


class JevDecisionProvider(DecisionProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_JEV_MODEL,
        base_url: str = DEFAULT_JEV_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Jev API key cannot be empty")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def choose(
        self,
        *,
        state: object,
        instructions: str,
        choices: dict[str, str],
    ) -> ChoiceDecision:
        if not choices:
            raise ValueError("choices cannot be empty")

        payload = self._request(
            state=state,
            questions={
                "decision": {
                    "type": "choice",
                    "instructions": (instructions),
                    "criteria": choices,
                }
            },
        )

        answer = self._answer(
            payload,
            name="decision",
            expected_type="choice",
        )

        choice = answer.get("choice")

        confidence = answer.get("confidence")

        probabilities = answer.get("probabilities")

        if not isinstance(
            choice,
            str,
        ):
            raise JevDecisionError("Jev returned invalid choice")

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise JevDecisionError("Jev returned invalid confidence")

        if not isinstance(
            probabilities,
            dict,
        ):
            raise JevDecisionError("Jev returned invalid probabilities")

        parsed_probabilities = {
            str(key): float(value)
            for key, value in (probabilities.items())
            if isinstance(
                value,
                (int, float),
            )
        }

        return ChoiceDecision(
            choice=choice,
            confidence=float(confidence),
            probabilities=(parsed_probabilities),
        )

    def score(
        self,
        *,
        state: object,
        instructions: str,
        levels: list[str],
    ) -> ScoreDecision:
        if not levels:
            raise ValueError("levels cannot be empty")

        payload = self._request(
            state=state,
            questions={
                "decision": {
                    "type": "score",
                    "instructions": (instructions),
                    "criteria": levels,
                }
            },
        )

        answer = self._answer(
            payload,
            name="decision",
            expected_type="score",
        )

        score = answer.get("score")

        confidence = answer.get("confidence")

        probabilities = answer.get("probabilities")

        if not isinstance(
            score,
            (int, float),
        ):
            raise JevDecisionError("Jev returned invalid score")

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise JevDecisionError("Jev returned invalid confidence")

        if not isinstance(
            probabilities,
            dict,
        ):
            raise JevDecisionError("Jev returned invalid probabilities")

        parsed_probabilities = {
            str(key): float(value)
            for key, value in (probabilities.items())
            if isinstance(
                value,
                (int, float),
            )
        }

        return ScoreDecision(
            score=float(score),
            confidence=float(confidence),
            probabilities=(parsed_probabilities),
        )

    def probability(
        self,
        *,
        state: object,
        instructions: str,
        true_description: str | None = None,
        false_description: str | None = None,
    ) -> ProbabilityDecision:
        criteria: dict[
            str,
            str,
        ] = {}

        if true_description is not None:
            criteria["true"] = true_description

        if false_description is not None:
            criteria["false"] = false_description

        question: dict[
            str,
            object,
        ] = {
            "type": "noul",
            "instructions": instructions,
        }

        if criteria:
            question["criteria"] = criteria

        payload = self._request(
            state=state,
            questions={"decision": question},
        )

        answer = self._answer(
            payload,
            name="decision",
            expected_type="noul",
        )

        probability = answer.get("noul")

        if not isinstance(
            probability,
            (int, float),
        ):
            raise JevDecisionError("Jev returned invalid probability")

        return ProbabilityDecision(probability=float(probability))

    def _request(
        self,
        *,
        state: object,
        questions: dict[
            str,
            object,
        ],
    ) -> dict[str, Any]:
        body = json.dumps(
            {
                "state": state,
                "model": self._model,
                "questions": questions,
            }
        ).encode("utf-8")

        request = Request(
            (f"{self._base_url}/v1/systemone"),
            data=body,
            headers={
                "Authorization": (f"Bearer {self._api_key}"),
                "Content-Type": ("application/json"),
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=(self._timeout_seconds),
            ) as response:
                raw = response.read()

        except HTTPError as exc:
            raise JevDecisionError(f"Jev request failed with HTTP {exc.code}") from exc

        except URLError as exc:
            raise JevDecisionError("Jev request failed") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise JevDecisionError("Jev returned invalid JSON") from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise JevDecisionError("Jev returned invalid response")

        return payload

    @staticmethod
    def _answer(
        payload: dict[str, Any],
        *,
        name: str,
        expected_type: str,
    ) -> dict[str, Any]:
        answers = payload.get("answers")

        if not isinstance(
            answers,
            dict,
        ):
            raise JevDecisionError("Jev response has no answers")

        answer = answers.get(name)

        if not isinstance(
            answer,
            dict,
        ):
            raise JevDecisionError("Jev response is missing decision")

        if answer.get("type") != expected_type:
            raise JevDecisionError("Jev returned unexpected decision type")

        return answer
