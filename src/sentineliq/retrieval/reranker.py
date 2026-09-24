import json
from dataclasses import dataclass

from sentineliq.contracts import (
    RerankerProvider,
)
from sentineliq.providers.openai_reranker import (
    OpenAIRerankerProvider,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


@dataclass(frozen=True, slots=True)
class RerankedResult:
    result: RetrievalResult
    score: float


class LLMReranker:
    def __init__(
        self,
        provider: RerankerProvider | None = None,
    ) -> None:
        self._provider = (
            provider
            or OpenAIRerankerProvider()
        )

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RetrievalResult],
        limit: int,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        if not candidates:
            return []

        documents = [
            "\n".join(
                [
                    (
                        "Document: "
                        f"{candidate.document_title}"
                    ),
                    (
                        "Page: "
                        f"{candidate.page_number}"
                    ),
                    "Content:",
                    candidate.content[:1600],
                ]
            )
            for candidate in candidates
        ]

        scores = self._provider.rerank(
            query=query,
            documents=documents,
        )

        if len(scores) != len(
            candidates
        ):
            raise ValueError(
                "Reranker provider returned "
                "incorrect number of scores"
            )

        ranked = [
            RerankedResult(
                result=candidate,
                score=score,
            )
            for candidate, score in zip(
                candidates,
                scores,
                strict=True,
            )
        ]

        ranked.sort(
            key=lambda item: (
                item.score,
                item.result.fusion_score
                or 0.0,
            ),
            reverse=True,
        )

        return [
            item.result
            for item in ranked[:limit]
        ]

    @staticmethod
    def _parse_scores(
        text: str,
        *,
        candidate_count: int,
    ) -> dict[int, float]:
        cleaned = (
            text.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        try:
            data = json.loads(
                cleaned
            )
        except json.JSONDecodeError:
            return {}

        if not isinstance(
            data,
            list,
        ):
            return {}

        scores: dict[
            int,
            float,
        ] = {}

        for item in data:
            if not isinstance(
                item,
                dict,
            ):
                continue

            index = item.get(
                "index"
            )

            score = item.get(
                "score"
            )

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

            if not (
                1
                <= index
                <= candidate_count
            ):
                continue

            scores[index] = max(
                0.0,
                min(
                    1.0,
                    float(score),
                ),
            )

        return scores