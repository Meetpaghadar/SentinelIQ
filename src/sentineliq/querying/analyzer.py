import re

from sentineliq.contracts.query import (
    QueryAnalysis,
    QueryComplexity,
    QueryIntent,
)
from sentineliq.decision import (
    DecisionProvider,
)

YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


class QueryAnalyzer:
    def __init__(
        self,
        decision_provider: DecisionProvider | None = None,
    ) -> None:
        self._decision_provider = decision_provider

    def analyze(
        self,
        query: str,
    ) -> QueryAnalysis:
        normalized = self._normalize(query)

        if not normalized:
            raise ValueError("query cannot be empty")

        deterministic_intent = self._determine_intent(normalized)

        deterministic_complexity = self._determine_complexity(
            normalized,
            deterministic_intent,
        )

        intent = deterministic_intent
        complexity = deterministic_complexity

        if self._decision_provider is not None:
            intent = self._refine_intent(
                query=normalized,
                fallback=deterministic_intent,
            )

            complexity = self._refine_complexity(
                query=normalized,
                fallback=(deterministic_complexity),
            )

        temporal_intent = intent is QueryIntent.TEMPORAL or self._has_temporal_signal(normalized)

        relationship_intent = intent is QueryIntent.RELATIONSHIP or self._has_relationship_signal(
            normalized
        )

        structured_data_intent = intent is QueryIntent.STRUCTURED or self._has_structured_signal(
            normalized
        )

        security_signals = self._detect_security_signals(normalized)

        return QueryAnalysis(
            original_query=query,
            normalized_query=normalized,
            intent=intent,
            complexity=complexity,
            temporal_intent=temporal_intent,
            relationship_intent=(relationship_intent),
            structured_data_intent=(structured_data_intent),
            security_signals=security_signals,
        )

    @staticmethod
    def _normalize(
        query: str,
    ) -> str:
        return " ".join(query.strip().split())

    @staticmethod
    def _determine_intent(
        query: str,
    ) -> QueryIntent:
        lowered = query.casefold()

        if QueryAnalyzer._has_temporal_signal(lowered):
            return QueryIntent.TEMPORAL

        if QueryAnalyzer._has_relationship_signal(lowered):
            return QueryIntent.RELATIONSHIP

        if QueryAnalyzer._has_structured_signal(lowered):
            return QueryIntent.STRUCTURED

        comparison_terms = (
            "compare ",
            "difference between",
            "differences between",
            " versus ",
            " vs ",
        )

        if any(term in lowered for term in comparison_terms):
            return QueryIntent.COMPARISON

        investigation_terms = (
            "investigate",
            "determine whether",
            "verify whether",
            "verify if",
            "find evidence",
            "what evidence",
            "why did",
            "why does",
            "root cause",
        )

        if any(term in lowered for term in investigation_terms):
            return QueryIntent.INVESTIGATION

        conversational_terms = (
            "hello",
            "hi ",
            "hey ",
            "thanks",
            "thank you",
        )

        if any(lowered.startswith(term) for term in conversational_terms):
            return QueryIntent.CONVERSATIONAL

        return QueryIntent.FACTUAL

    @staticmethod
    def _determine_complexity(
        query: str,
        intent: QueryIntent,
    ) -> QueryComplexity:
        lowered = query.casefold()

        deep_intents = {
            QueryIntent.INVESTIGATION,
        }

        if intent in deep_intents:
            return QueryComplexity.DEEP

        deep_terms = (
            "across multiple",
            "investigate",
            "root cause",
            "determine whether",
            "all evidence",
            "comprehensive",
            "in depth",
            "deep analysis",
        )

        if any(term in lowered for term in deep_terms):
            return QueryComplexity.DEEP

        normal_intents = {
            QueryIntent.COMPARISON,
            QueryIntent.TEMPORAL,
            QueryIntent.RELATIONSHIP,
            QueryIntent.STRUCTURED,
        }

        if intent in normal_intents:
            return QueryComplexity.NORMAL

        word_count = len(query.split())

        if word_count <= 12:
            return QueryComplexity.SIMPLE

        return QueryComplexity.NORMAL

    @staticmethod
    def _has_temporal_signal(
        query: str,
    ) -> bool:
        lowered = query.casefold()

        terms = (
            "previous version",
            "current version",
            "historical",
            "as of",
            "effective date",
            "expired",
            "superseded",
            "what changed",
            "changed between",
            "before ",
            "after ",
            "last year",
        )

        return any(term in lowered for term in terms) or YEAR_PATTERN.search(lowered) is not None

    @staticmethod
    def _has_relationship_signal(
        query: str,
    ) -> bool:
        lowered = query.casefold()

        terms = (
            "related to",
            "relationship between",
            "depends on",
            "dependency",
            "dependencies",
            "affected by",
            "affects ",
            "impact on",
            "connected to",
            "linked to",
            "which systems",
        )

        return any(term in lowered for term in terms)

    @staticmethod
    def _has_structured_signal(
        query: str,
    ) -> bool:
        lowered = query.casefold()

        terms = (
            "how many",
            "count of",
            "average ",
            "sum of",
            "total ",
            "percentage ",
            "percent ",
            "top 10",
            "top ten",
            "overdue findings",
            "list departments",
            "group by",
        )

        return any(term in lowered for term in terms)

    @staticmethod
    def _detect_security_signals(
        query: str,
    ) -> tuple[str, ...]:
        lowered = query.casefold()

        signals: list[str] = []

        patterns = {
            "prompt_injection": (
                "ignore previous instructions",
                "ignore all previous",
                "ignore system prompt",
                "system prompt",
                "developer message",
            ),
            "authorization_bypass": (
                "bypass authorization",
                "bypass permissions",
                "ignore permissions",
                "show restricted",
                "show confidential",
                "access unauthorized",
            ),
            "secret_extraction": (
                "reveal api key",
                "show api key",
                "reveal password",
                "show password",
                "dump secrets",
                "environment variables",
            ),
        }

        for signal, terms in patterns.items():
            if any(term in lowered for term in terms):
                signals.append(signal)

        return tuple(signals)

    def _refine_intent(
        self,
        *,
        query: str,
        fallback: QueryIntent,
    ) -> QueryIntent:
        assert self._decision_provider is not None

        try:
            decision = self._decision_provider.choose(
                state={
                    "query": query,
                },
                instructions=("Classify the primary intent of this enterprise knowledge query."),
                choices={
                    intent.value: (self._intent_description(intent))
                    for intent in QueryIntent
                    if intent is not QueryIntent.UNKNOWN
                },
            )

            return QueryIntent(decision.choice)

        except (
            ValueError,
            RuntimeError,
        ):
            return fallback

    def _refine_complexity(
        self,
        *,
        query: str,
        fallback: QueryComplexity,
    ) -> QueryComplexity:
        assert self._decision_provider is not None

        try:
            decision = self._decision_provider.choose(
                state={
                    "query": query,
                },
                instructions=(
                    "Classify the retrieval and "
                    "reasoning complexity required "
                    "for this enterprise query."
                ),
                choices={
                    QueryComplexity.SIMPLE.value: ("Single direct fact or straightforward lookup."),
                    QueryComplexity.NORMAL.value: (
                        "Requires moderate retrieval, comparison, filtering, or reasoning."
                    ),
                    QueryComplexity.DEEP.value: (
                        "Requires multi-source "
                        "investigation, complex "
                        "reasoning, or iterative "
                        "retrieval."
                    ),
                },
            )

            return QueryComplexity(decision.choice)

        except (
            ValueError,
            RuntimeError,
        ):
            return fallback

    @staticmethod
    def _intent_description(
        intent: QueryIntent,
    ) -> str:
        descriptions = {
            QueryIntent.FACTUAL: ("Direct factual knowledge lookup."),
            QueryIntent.COMPARISON: (
                "Compare two or more items, documents, versions, or concepts."
            ),
            QueryIntent.TEMPORAL: (
                "Question about time, versions, history, effective dates, or changes."
            ),
            QueryIntent.RELATIONSHIP: (
                "Question about relationships, dependencies, connections, or impact."
            ),
            QueryIntent.STRUCTURED: (
                "Question best answered from structured records, aggregation, or tabular data."
            ),
            QueryIntent.INVESTIGATION: (
                "Deep investigation requiring evidence across multiple sources."
            ),
            QueryIntent.CONVERSATIONAL: (
                "Conversational interaction rather than enterprise knowledge retrieval."
            ),
        }

        return descriptions[intent]
