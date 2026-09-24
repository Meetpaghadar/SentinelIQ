from sentineliq.contracts import (
    GenerationResult,
    QueryVariantOrigin,
)
from sentineliq.querying import (
    QueryRewriter,
)


class SuccessfulGenerator:
    def generate(self, request):
        del request

        return GenerationResult(
            text="What is multi-factor authentication?",
            provider="test",
            model="test",
        )


class EmptyGenerator:
    def generate(self, request):
        del request

        return GenerationResult(
            text="   ",
            provider="test",
            model="test",
        )


class FailingGenerator:
    def generate(self, request):
        del request

        raise RuntimeError("rewrite provider failed")


def test_successful_rewrite_returns_rewrite_variant() -> None:
    rewriter = QueryRewriter(SuccessfulGenerator())

    variant = rewriter.rewrite("What is MFA?")

    assert variant.origin is QueryVariantOrigin.REWRITE
    assert variant.text == "What is multi-factor authentication?"


def test_failed_rewrite_falls_back_to_original() -> None:
    rewriter = QueryRewriter(FailingGenerator())

    variant = rewriter.rewrite("What is MFA?")

    assert variant.origin is QueryVariantOrigin.ORIGINAL
    assert variant.text == "What is MFA?"


def test_empty_rewrite_falls_back_to_original() -> None:
    rewriter = QueryRewriter(EmptyGenerator())

    variant = rewriter.rewrite("What is MFA?")

    assert variant.origin is QueryVariantOrigin.ORIGINAL
    assert variant.text == "What is MFA?"
