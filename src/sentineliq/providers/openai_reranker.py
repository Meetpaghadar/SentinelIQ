import json

from sentineliq.contracts import (
    GenerationRequest,
    LLMProvider,
    RerankerProvider,
)
from sentineliq.providers.openai import (
    OpenAIGenerationProvider,
)


class OpenAIRerankerProvider(RerankerProvider):
    def __init__(
        self,
        generation_provider: (LLMProvider | None) = None,
    ) -> None:
        self._generation_provider = generation_provider or OpenAIGenerationProvider()

    def rerank(
        self,
        *,
        query: str,
        documents: list[str],
    ) -> list[float]:
        if not documents:
            return []

        candidates = "\n\n".join(
            (f"CANDIDATE {index}\n{document}")
            for index, document in enumerate(
                documents,
                start=1,
            )
        )

        result = self._generation_provider.generate(
            GenerationRequest(
                instructions=(
                    "You are a retrieval reranker. "
                    "Score every candidate by how useful "
                    "its actual evidence is for answering "
                    "the query. "
                    "Do not rank based only on titles. "
                    "Return only JSON using: "
                    '[{"index":1,"score":0.95}]. '
                    "Every candidate must appear once. "
                    "Scores must be between 0 and 1."
                ),
                input_text=(f"Query:\n{query}\n\nCandidates:\n{candidates}"),
            )
        )

        return self._parse_scores(
            result.text,
            count=len(documents),
        )

    @staticmethod
    def _parse_scores(
        text: str,
        *,
        count: int,
    ) -> list[float]:
        cleaned = (
            text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        )

        scores = [0.0 for _ in range(count)]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return scores

        if not isinstance(
            data,
            list,
        ):
            return scores

        for item in data:
            if not isinstance(
                item,
                dict,
            ):
                continue

            index = item.get("index")

            score = item.get("score")

            if not isinstance(
                index,
                int,
            ):
                continue

            if not isinstance(
                score,
                (int, float),
            ):
                continue

            if not (1 <= index <= count):
                continue

            scores[index - 1] = max(
                0.0,
                min(
                    1.0,
                    float(score),
                ),
            )

        return scores
