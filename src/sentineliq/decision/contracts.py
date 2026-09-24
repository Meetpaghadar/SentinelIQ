from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChoiceDecision:
    choice: str
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True, slots=True)
class ScoreDecision:
    score: float
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True, slots=True)
class ProbabilityDecision:
    probability: float


class DecisionProvider(Protocol):
    def choose(
        self,
        *,
        state: object,
        instructions: str,
        choices: dict[str, str],
    ) -> ChoiceDecision: ...

    def score(
        self,
        *,
        state: object,
        instructions: str,
        levels: list[str],
    ) -> ScoreDecision: ...

    def probability(
        self,
        *,
        state: object,
        instructions: str,
        true_description: str | None = None,
        false_description: str | None = None,
    ) -> ProbabilityDecision: ...
