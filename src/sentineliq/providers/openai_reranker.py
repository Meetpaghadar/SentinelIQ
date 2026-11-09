import json
from collections.abc import Sequence

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
        documents: Sequence[str],
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

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Reranker provider returned malformed JSON") from exc

        if not isinstance(data, list) or len(data) != count:
            raise RuntimeError("Reranker provider returned incomplete scores")

        scores: dict[int, float] = {}
        for item in data:
            if not isinstance(item, dict):
                raise RuntimeError("Reranker provider returned an invalid score item")

            index = item.get("index")

            score = item.get("score")

            if not isinstance(index, int) or isinstance(index, bool):
                raise RuntimeError("Reranker provider returned an invalid index")

            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise RuntimeError("Reranker provider returned an invalid score")

            if not (1 <= index <= count) or index in scores:
                raise RuntimeError("Reranker provider returned an invalid index set")

            scores[index] = max(
                0.0,
                min(
                    1.0,
                    float(score),
                ),
            )

        if len(scores) != count:
            raise RuntimeError("Reranker provider returned incomplete scores")
        return [scores[index] for index in range(1, count + 1)]
