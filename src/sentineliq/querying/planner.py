from dataclasses import replace

from sentineliq.contracts.query import (
    QueryAnalysis,
    QueryComplexity,
    QueryIntent,
    QueryPath,
    QueryPlan,
    RetrievalStrategy,
)
from sentineliq.decision import (
    DecisionProvider,
)

LOW_ROUTE_CONFIDENCE = 0.6


class QueryPlanner:
    def __init__(
        self,
        *,
        enable_rewrite: bool = False,
        enable_multi_query: bool = False,
        enable_hyde: bool = False,
        enable_rag_fusion: bool = False,
        decision_provider: DecisionProvider | None = None,
        min_route_confidence: float = LOW_ROUTE_CONFIDENCE,
    ) -> None:
        self._enable_rewrite = enable_rewrite
        self._enable_multi_query = enable_multi_query
        self._enable_hyde = enable_hyde
        self._enable_rag_fusion = enable_rag_fusion
        self._decision_provider = decision_provider
        self._min_route_confidence = min_route_confidence

    def plan(
        self,
        analysis: QueryAnalysis,
    ) -> QueryPlan:
        deterministic = self._deterministic_plan(analysis)

        if self._decision_provider is None:
            return self._apply_technique_policy(
                analysis,
                deterministic,
            )

        try:
            routed = self._route_with_decision(analysis)
        except (
            ValueError,
            RuntimeError,
        ):
            routed = deterministic

        return self._apply_technique_policy(
            analysis,
            routed,
        )

    def _deterministic_plan(
        self,
        analysis: QueryAnalysis,
    ) -> QueryPlan:
        if analysis.intent is QueryIntent.TEMPORAL:
            return self._temporal_plan()

        if analysis.intent is QueryIntent.RELATIONSHIP:
            return self._relationship_plan()

        if analysis.intent is QueryIntent.STRUCTURED:
            return self._structured_plan()

        if analysis.complexity is QueryComplexity.DEEP:
            return self._deep_plan()

        if (
            analysis.complexity is QueryComplexity.SIMPLE
            and analysis.intent is QueryIntent.CONVERSATIONAL
        ):
            return self._fast_plan()

        return self._normal_plan()

    def _route_with_decision(
        self,
        analysis: QueryAnalysis,
    ) -> QueryPlan:
        assert self._decision_provider is not None

        decision = self._decision_provider.choose(
            state={
                "query": analysis.normalized_query,
                "intent": analysis.intent.value,
                "complexity": analysis.complexity.value,
            },
            instructions=(
                "Choose a retrieval path. "
                "FAST is only for conversational acknowledgements. "
                "Factual knowledge lookup must use NORMAL. "
                "DEEP is for investigation or multi-source reasoning."
            ),
            choices={
                QueryPath.FAST.value: ("Conversational acknowledgement with no knowledge lookup."),
                QueryPath.NORMAL.value: (
                    "Standard hybrid retrieval with reranking and parent expansion."
                ),
                QueryPath.DEEP.value: (
                    "Heavier retrieval budget for investigation or multi-source questions."
                ),
            },
        )

        if decision.confidence < self._min_route_confidence:
            return self._normal_plan()

        if decision.choice == QueryPath.FAST.value:
            if analysis.intent is not QueryIntent.CONVERSATIONAL:
                return self._normal_plan()

            return self._fast_plan()

        if decision.choice == QueryPath.DEEP.value:
            return self._deep_plan()

        if decision.choice == QueryPath.NORMAL.value:
            return self._normal_plan()

        return self._deterministic_plan(analysis)

    def _apply_technique_policy(
        self,
        analysis: QueryAnalysis,
        plan: QueryPlan,
    ) -> QueryPlan:
        if analysis.intent is QueryIntent.CONVERSATIONAL:
            return plan

        if plan.path is QueryPath.FAST:
            return plan

        updates: dict[str, bool] = {}

        if self._enable_rewrite:
            updates["rewrite"] = True

        if self._enable_hyde:
            updates["hyde"] = True

        if self._enable_multi_query:
            updates["multi_query"] = True

            if self._enable_rag_fusion:
                updates["rag_fusion"] = True

        if not updates:
            return plan

        return replace(
            plan,
            rewrite=updates.get("rewrite", plan.rewrite),
            hyde=updates.get("hyde", plan.hyde),
            multi_query=updates.get("multi_query", plan.multi_query),
            rag_fusion=updates.get("rag_fusion", plan.rag_fusion),
        )

    @staticmethod
    def _fast_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.FAST,
            strategies=(RetrievalStrategy.HYBRID,),
            top_k=5,
            candidate_k=20,
            rerank=False,
            parent_expansion=False,
        )

    @staticmethod
    def _normal_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.NORMAL,
            strategies=(RetrievalStrategy.HYBRID,),
            top_k=5,
            candidate_k=40,
            rerank=True,
            parent_expansion=True,
        )

    @staticmethod
    def _deep_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.DEEP,
            strategies=(RetrievalStrategy.HYBRID,),
            top_k=8,
            candidate_k=60,
            rerank=True,
            parent_expansion=True,
        )

    @staticmethod
    def _temporal_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.DEEP,
            strategies=(
                RetrievalStrategy.TEMPORAL,
                RetrievalStrategy.HYBRID,
            ),
            top_k=8,
            candidate_k=60,
            rerank=True,
            parent_expansion=True,
        )

    @staticmethod
    def _relationship_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.DEEP,
            strategies=(
                RetrievalStrategy.GRAPH,
                RetrievalStrategy.HYBRID,
            ),
            top_k=8,
            candidate_k=60,
            rerank=True,
            parent_expansion=True,
        )

    @staticmethod
    def _structured_plan() -> QueryPlan:
        return QueryPlan(
            path=QueryPath.NORMAL,
            strategies=(
                RetrievalStrategy.SQL,
                RetrievalStrategy.HYBRID,
            ),
            top_k=5,
            candidate_k=40,
            rerank=True,
            parent_expansion=True,
        )
