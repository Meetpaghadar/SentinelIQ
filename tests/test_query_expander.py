from sentineliq.contracts import (
    GenerationResult,
    QueryVariantOrigin,
)
from sentineliq.querying import (
    QueryExpander,
)


class SuccessfulGenerator:
    def generate(self, request):
        del request

        return GenerationResult(
            text="What is multi-factor authentication?\nHow does MFA protect accounts?",
            provider="test",
            model="test",
        )


class FailingGenerator:
    def generate(self, request):
        del request

        raise RuntimeError("expander failed")


def test_expander_returns_multi_query_variants() -> None:
    expander = QueryExpander(SuccessfulGenerator())

    variants = expander.expand("What is MFA?")

    assert len(variants) == 2
    assert all(item.origin is QueryVariantOrigin.MULTI_QUERY for item in variants)
    assert variants[0].text == "What is multi-factor authentication?"


def test_expander_failure_returns_empty_fallback() -> None:
    expander = QueryExpander(FailingGenerator())

    assert expander.expand("What is MFA?") == ()
