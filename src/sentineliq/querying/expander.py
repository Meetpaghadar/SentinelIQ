from sentineliq.contracts import (
    GenerationRequest,
    LLMProvider,
    QueryVariant,
    QueryVariantOrigin,
)

EXPAND_INSTRUCTIONS = (
    "Generate 2 alternative search queries for enterprise document retrieval. "
    "Preserve the original meaning. "
    "Do not answer the question. "
    "Do not add facts that are not present in the original query. "
    "Return one query per line and nothing else."
)


class QueryExpander:
    def __init__(
        self,
        llm_provider: LLMProvider,
    ) -> None:
        self._llm_provider = llm_provider

    def expand(
        self,
        query: str,
    ) -> tuple[QueryVariant, ...]:
        original = " ".join(query.split())

        if not original:
            return ()

        try:
            generation = self._llm_provider.generate(
                GenerationRequest(
                    instructions=EXPAND_INSTRUCTIONS,
                    input_text=original,
                )
            )
            lines = [
                line.lstrip("0123456789.-) ").strip()
                for line in generation.text.splitlines()
                if line.strip()
            ]
        except (
            RuntimeError,
            ValueError,
            OSError,
        ):
            return ()

        variants: list[QueryVariant] = []

        for index, line in enumerate(lines[:3], start=1):
            if not line:
                continue

            if line.casefold() == original.casefold():
                continue

            variants.append(
                QueryVariant(
                    variant_id=f"multi-{index}",
                    text=line,
                    origin=QueryVariantOrigin.MULTI_QUERY,
                )
            )

        return tuple(variants[:3])
