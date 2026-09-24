from sentineliq.contracts.query import (
    QueryAnalysis,
    QueryComplexity,
    QueryIntent,
    QueryPath,
)
from sentineliq.decision import (
    ChoiceDecision,
    ProbabilityDecision,
    ScoreDecision,
)
from sentineliq.querying import (
    QueryPlanner,
)


class FixedDecisionProvider:
    def __init__(
        self,
        *,
        choice: str,
        confidence: float,
    ) -> None:
        self.choice = choice
        self.confidence = confidence

    def choose(self, **kwargs):
        del kwargs

        return ChoiceDecision(
            choice=self.choice,
            confidence=self.confidence,
            probabilities={self.choice: self.confidence},
        )

    def score(self, **kwargs):
        del kwargs

        return ScoreDecision(
            score=0.0,
            confidence=1.0,
            probabilities={},
        )

    def probability(self, **kwargs):
        del kwargs

        return ProbabilityDecision(probability=0.0)


class FailingDecisionProvider(FixedDecisionProvider):
    def choose(self, **kwargs):
        del kwargs

        raise RuntimeError("jev unavailable")


def _factual_simple() -> QueryAnalysis:
    return QueryAnalysis(
        original_query="What is MFA?",
        normalized_query="What is MFA?",
        intent=QueryIntent.FACTUAL,
        complexity=QueryComplexity.SIMPLE,
    )


def test_jev_failure_uses_deterministic_plan() -> None:
    planner = QueryPlanner(
        decision_provider=FailingDecisionProvider(
            choice="fast",
            confidence=0.99,
        )
    )

    plan = planner.plan(_factual_simple())

    assert plan.path is QueryPath.NORMAL
    assert plan.rerank is True


def test_low_confidence_uses_normal_path() -> None:
    planner = QueryPlanner(
        decision_provider=FixedDecisionProvider(
            choice="deep",
            confidence=0.2,
        )
    )

    plan = planner.plan(_factual_simple())

    assert plan.path is QueryPath.NORMAL
    assert plan.rerank is True


def test_jev_cannot_force_fast_for_factual_query() -> None:
    planner = QueryPlanner(
        decision_provider=FixedDecisionProvider(
            choice="fast",
            confidence=0.99,
        )
    )

    plan = planner.plan(_factual_simple())

    assert plan.path is QueryPath.NORMAL
