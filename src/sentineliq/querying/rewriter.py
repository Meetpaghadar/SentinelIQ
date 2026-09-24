from sentineliq.contracts import (
    GenerationRequest,
    LLMProvider,
    QueryVariant,
    QueryVariantOrigin,
)

REWRITE_INSTRUCTIONS = (
    "Rewrite the user's enterprise knowledge query to improve document retrieval. "
    "Preserve the original meaning. "
    "Increase retrieval specificity by expanding abbreviations and using clearer search terms. "
    "Do not answer the question. "
    "Do not add facts that are not present in the original query. "
    "Return only the rewritten query text."
)


class QueryRewriter:
    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        self._llm_provider = llm_provider

    def rewrite(
        self,
        query: str,
    ) -> QueryVariant:
        original = " ".join(query.split())

        if not original:
            return QueryVariant(
                variant_id="original",
                text=query,
                origin=QueryVariantOrigin.ORIGINAL,
            )

        try:
            generation = self._llm_provider.generate(
                GenerationRequest(
                    instructions=REWRITE_INSTRUCTIONS,
                    input_text=original,
                )
            )
            rewritten = " ".join(generation.text.split())
        except (
            RuntimeError,
            ValueError,
            OSError,
        ):
            rewritten = ""

        if not rewritten:
            return QueryVariant(
                variant_id="original",
                text=original,
                origin=QueryVariantOrigin.ORIGINAL,
            )

        return QueryVariant(
            variant_id="rewrite",
            text=rewritten,
            origin=QueryVariantOrigin.REWRITE,
        )
