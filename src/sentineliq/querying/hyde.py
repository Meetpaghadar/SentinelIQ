from sentineliq.contracts import (
    GenerationRequest,
    LLMProvider,
    QueryVariant,
    QueryVariantOrigin,
)

HYDE_INSTRUCTIONS = (
    "Write a short hypothetical passage that would answer the user's question "
    "if it appeared in an authorized enterprise knowledge document. "
    "This text is used only as a retrieval query. "
    "Do not include citations, source numbers, or a direct answer to the user."
)


class HypotheticalQuery:
    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        self._llm_provider = llm_provider

    def generate(
        self,
        query: str,
    ) -> QueryVariant | None:
        original = " ".join(query.split())

        if not original:
            return None

        try:
            generation = self._llm_provider.generate(
                GenerationRequest(
                    instructions=HYDE_INSTRUCTIONS,
                    input_text=original,
                )
            )
            text = " ".join(generation.text.split())
        except (
            RuntimeError,
            ValueError,
            OSError,
        ):
            return None

        if not text:
            return None

        return QueryVariant(
            variant_id="hyde",
            text=text,
            origin=QueryVariantOrigin.HYDE,
        )
