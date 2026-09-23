import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from sentineliq.contracts import (
    GenerationRequest,
    LLMProvider,
)
from sentineliq.providers import (
    OpenAIGenerationProvider,
)
from sentineliq.retrieval.service import (
    RetrievalResult,
    RetrievalService,
)


INSUFFICIENT_EVIDENCE_ANSWER = (
    "The available sources do not provide enough "
    "information to answer this question."
)


@dataclass(frozen=True)
class Citation:
    number: int
    document_id: UUID
    document_title: str
    document_version_id: UUID
    version_number: int
    page_number: int | None
    chunk_id: UUID
    excerpt: str


@dataclass(frozen=True)
class RAGAnswer:
    answer: str
    citations: list[Citation]


class RAGService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        generation_provider: LLMProvider | None = None,
    ) -> None:
        self._retrieval_service = (
            retrieval_service
        )

        self._generation_provider = (
            generation_provider
            or OpenAIGenerationProvider()
        )

    def answer(
        self,
        session: Session,
        tenant_id: UUID,
        question: str,
        limit: int = 5,
    ) -> RAGAnswer:
        question = (
            question.strip()
        )

        if not question:
            raise ValueError(
                "Question cannot be empty"
            )

        results = (
            self._retrieval_service.search(
                session=session,
                tenant_id=tenant_id,
                query=question,
                limit=limit,
            )
        )

        if not results:
            return RAGAnswer(
                answer=(
                    INSUFFICIENT_EVIDENCE_ANSWER
                ),
                citations=[],
            )

        context = self._build_context(
            results
        )

        generation = (
            self._generation_provider.generate(
                GenerationRequest(
                    instructions=(
                        "You are SentinelIQ, a grounded "
                        "enterprise knowledge assistant. "
                        "Answer using only the supplied "
                        "authorized source excerpts. "
                        "Do not use outside knowledge. "
                        "Every factual claim must be "
                        "supported by the supplied sources. "
                        "Cite supporting sources using "
                        "[1], [2], and so on. "
                        "If the supplied excerpts do not "
                        "contain enough evidence to answer "
                        "the question, respond with exactly: "
                        f"{INSUFFICIENT_EVIDENCE_ANSWER} "
                        "When returning that insufficient-"
                        "evidence response, do not include "
                        "citations, explanation, additional "
                        "text, or source numbers. "
                        "Do not invent or infer unsupported "
                        "facts."
                    ),
                    input_text=(
                        f"Question:\n{question}\n\n"
                        "Authorized source excerpts:\n"
                        f"{context}"
                    ),
                )
            )
        )

        answer = (
            generation.text.strip()
        )

        if (
            self._is_insufficient_evidence_answer(
                answer
            )
        ):
            return RAGAnswer(
                answer=(
                    INSUFFICIENT_EVIDENCE_ANSWER
                ),
                citations=[],
            )

        used_numbers = (
            self._used_citation_numbers(
                answer,
                len(results),
            )
        )

        citations = [
            Citation(
                number=index,
                document_id=(
                    result.document_id
                ),
                document_title=(
                    result.document_title
                ),
                document_version_id=(
                    result.document_version_id
                ),
                version_number=(
                    result.version_number
                ),
                page_number=(
                    result.page_number
                ),
                chunk_id=(
                    result.chunk_id
                ),
                excerpt=(
                    self._build_excerpt(
                        result.content
                    )
                ),
            )
            for index, result in enumerate(
                results,
                start=1,
            )
            if index in used_numbers
        ]

        return RAGAnswer(
            answer=answer,
            citations=citations,
        )

    @staticmethod
    def _build_context(
        results: list[RetrievalResult],
    ) -> str:
        sections: list[str] = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            sections.append(
                "\n".join(
                    [
                        f"[{index}]",
                        (
                            "Document: "
                            f"{result.document_title}"
                        ),
                        (
                            "Version: "
                            f"{result.version_number}"
                        ),
                        (
                            "Page: "
                            f"{result.page_number}"
                        ),
                        result.content,
                    ]
                )
            )

        return "\n\n".join(
            sections
        )

    @staticmethod
    def _used_citation_numbers(
        answer: str,
        maximum: int,
    ) -> set[int]:
        numbers = {
            int(match)
            for match in re.findall(
                r"\[(\d+)\]",
                answer,
            )
        }

        return {
            number
            for number in numbers
            if 1
            <= number
            <= maximum
        }

    @staticmethod
    def _build_excerpt(
        content: str,
        maximum_length: int = 300,
    ) -> str:
        cleaned = " ".join(
            content.split()
        )

        if (
            len(cleaned)
            <= maximum_length
        ):
            return cleaned

        return (
            cleaned[
                :maximum_length
            ].rstrip()
            + "..."
        )

    @staticmethod
    def _is_insufficient_evidence_answer(
        answer: str,
    ) -> bool:
        normalized = " ".join(
            answer.split()
        ).casefold()

        expected = " ".join(
            INSUFFICIENT_EVIDENCE_ANSWER.split()
        ).casefold()

        if normalized == expected:
            return True

        refusal_markers = (
            "do not provide enough information",
            "does not provide enough information",
            "not enough information to answer",
            "insufficient information to answer",
            "insufficient evidence",
            (
                "cannot answer based on "
                "the available sources"
            ),
            (
                "cannot answer from "
                "the available sources"
            ),
            (
                "sources do not contain "
                "enough information"
            ),
            (
                "sources don't contain "
                "enough information"
            ),
            (
                "excerpts do not contain "
                "enough information"
            ),
            (
                "excerpts don't contain "
                "enough information"
            ),
        )

        return any(
            marker in normalized
            for marker in refusal_markers
        )