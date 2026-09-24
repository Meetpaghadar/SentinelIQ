from sentineliq.contracts.query import (
    QueryAnalysis,
    QueryComplexity,
    QueryIntent,
    QueryPath,
    RetrievalStrategy,
)
from sentineliq.querying import (
    QueryPlanner,
)


def test_factual_simple_query_uses_normal_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query="What is MFA?",
            normalized_query="What is MFA?",
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.SIMPLE,
        )
    )

    assert plan.path is QueryPath.NORMAL

    assert RetrievalStrategy.HYBRID in plan.strategies

    assert plan.top_k == 5
    assert plan.candidate_k == 40

    assert plan.rerank is True
    assert plan.parent_expansion is True
    assert plan.rewrite is False
    assert plan.path is not QueryPath.FAST


def test_conversational_simple_query_uses_fast_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query="Thanks for the help",
            normalized_query="Thanks for the help",
            intent=QueryIntent.CONVERSATIONAL,
            complexity=QueryComplexity.SIMPLE,
        )
    )

    assert plan.path is QueryPath.FAST

    assert RetrievalStrategy.HYBRID in plan.strategies

    assert plan.top_k == 5
    assert plan.candidate_k == 20

    assert plan.rerank is False
    assert plan.parent_expansion is False
    assert plan.rewrite is False


def test_normal_query_uses_normal_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Explain the MFA policy."),
            normalized_query=("Explain the MFA policy."),
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.NORMAL,
        )
    )

    assert plan.path is QueryPath.NORMAL

    assert plan.strategies == (RetrievalStrategy.HYBRID,)

    assert plan.top_k == 5
    assert plan.candidate_k == 40

    assert plan.rerank is True
    assert plan.parent_expansion is True
    assert plan.rewrite is False


def test_deep_query_uses_deep_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Investigate whether MFA controls are actually implemented."),
            normalized_query=("Investigate whether MFA controls are actually implemented."),
            intent=(QueryIntent.INVESTIGATION),
            complexity=(QueryComplexity.DEEP),
        )
    )

    assert plan.path is QueryPath.DEEP

    assert plan.strategies == (RetrievalStrategy.HYBRID,)

    assert plan.top_k == 8
    assert plan.candidate_k == 60

    assert plan.rerank is True
    assert plan.parent_expansion is True
    assert plan.rewrite is False


def test_temporal_query_requests_temporal_strategy() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("What changed between the 2025 and 2026 policy?"),
            normalized_query=("What changed between the 2025 and 2026 policy?"),
            intent=QueryIntent.TEMPORAL,
            complexity=QueryComplexity.NORMAL,
            temporal_intent=True,
        )
    )

    assert plan.path is QueryPath.DEEP

    assert plan.strategies == (
        RetrievalStrategy.TEMPORAL,
        RetrievalStrategy.HYBRID,
    )

    assert plan.top_k == 8
    assert plan.candidate_k == 60

    assert plan.rerank is True
    assert plan.parent_expansion is True


def test_relationship_query_requests_graph_strategy() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Which systems are affected by this policy?"),
            normalized_query=("Which systems are affected by this policy?"),
            intent=(QueryIntent.RELATIONSHIP),
            complexity=QueryComplexity.NORMAL,
            relationship_intent=True,
        )
    )

    assert plan.path is QueryPath.DEEP

    assert plan.strategies == (
        RetrievalStrategy.GRAPH,
        RetrievalStrategy.HYBRID,
    )

    assert plan.top_k == 8
    assert plan.candidate_k == 60

    assert plan.rerank is True
    assert plan.parent_expansion is True


def test_structured_query_requests_sql_strategy() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("How many departments have overdue compliance findings?"),
            normalized_query=("How many departments have overdue compliance findings?"),
            intent=QueryIntent.STRUCTURED,
            complexity=QueryComplexity.NORMAL,
            structured_data_intent=True,
        )
    )

    assert plan.path is QueryPath.NORMAL

    assert plan.strategies == (
        RetrievalStrategy.SQL,
        RetrievalStrategy.HYBRID,
    )

    assert plan.top_k == 5
    assert plan.candidate_k == 40

    assert plan.rerank is True
    assert plan.parent_expansion is True


def test_comparison_query_uses_normal_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Compare policy A and policy B."),
            normalized_query=("Compare policy A and policy B."),
            intent=QueryIntent.COMPARISON,
            complexity=QueryComplexity.NORMAL,
        )
    )

    assert plan.path is QueryPath.NORMAL

    assert plan.strategies == (RetrievalStrategy.HYBRID,)

    assert plan.rerank is True


def test_factual_deep_complexity_still_uses_deep_path() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Provide a comprehensive analysis of the MFA requirements."),
            normalized_query=("Provide a comprehensive analysis of the MFA requirements."),
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.DEEP,
        )
    )

    assert plan.path is QueryPath.DEEP

    assert plan.top_k == 8
    assert plan.candidate_k == 60
    assert plan.rerank is True


def test_future_rag_features_are_not_enabled_yet() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        QueryAnalysis(
            original_query=("Explain the password policy."),
            normalized_query=("Explain the password policy."),
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.NORMAL,
        )
    )

    assert plan.rewrite is False
    assert plan.multi_query is False
    assert plan.hyde is False
    assert plan.rag_fusion is False
    assert plan.corrective_retrieval is False


def test_every_plan_has_valid_candidate_budget() -> None:
    planner = QueryPlanner()

    analyses = [
        QueryAnalysis(
            original_query="Thanks for the help",
            normalized_query="Thanks for the help",
            intent=QueryIntent.CONVERSATIONAL,
            complexity=QueryComplexity.SIMPLE,
        ),
        QueryAnalysis(
            original_query=("Explain the MFA policy."),
            normalized_query=("Explain the MFA policy."),
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.NORMAL,
        ),
        QueryAnalysis(
            original_query=("Investigate MFA implementation."),
            normalized_query=("Investigate MFA implementation."),
            intent=QueryIntent.INVESTIGATION,
            complexity=QueryComplexity.DEEP,
        ),
    ]

    for analysis in analyses:
        plan = planner.plan(analysis)

        assert plan.candidate_k >= plan.top_k

        assert plan.top_k > 0


def test_planner_can_enable_rewrite_for_normal_and_deep() -> None:
    planner = QueryPlanner(enable_rewrite=True)

    normal = planner.plan(
        QueryAnalysis(
            original_query=("Explain the MFA policy."),
            normalized_query=("Explain the MFA policy."),
            intent=QueryIntent.FACTUAL,
            complexity=QueryComplexity.NORMAL,
        )
    )

    deep = planner.plan(
        QueryAnalysis(
            original_query=("Investigate MFA implementation."),
            normalized_query=("Investigate MFA implementation."),
            intent=QueryIntent.INVESTIGATION,
            complexity=QueryComplexity.DEEP,
        )
    )

    conversational = planner.plan(
        QueryAnalysis(
            original_query="Thanks for the help",
            normalized_query="Thanks for the help",
            intent=QueryIntent.CONVERSATIONAL,
            complexity=QueryComplexity.SIMPLE,
        )
    )

    assert normal.rewrite is True
    assert deep.rewrite is True
    assert conversational.rewrite is False
