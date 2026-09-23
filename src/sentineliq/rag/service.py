import re
from dataclasses import dataclass
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from sentineliq.config import get_settings
from sentineliq.retrieval.service import RetrievalResult, RetrievalService


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
    def __init__(self, retrieval_service: RetrievalService) -> None:
        settings = get_settings()

        if settings.openai_api_key is None:
            raise RuntimeError("SENTINELIQ_OPENAI_API_KEY is required")

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.generation_model
        self._retrieval_service = retrieval_service

    def answer(
        self,
        session: Session,
        tenant_id: UUID,
        question: str,
        limit: int = 5,
    ) -> RAGAnswer:
        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty")

        results = self._retrieval_service.search(
            session=session,
            tenant_id=tenant_id,
            query=question,
            limit=limit,
        )

        if not results:
            return RAGAnswer(
                answer="I could not find relevant information in the available sources.",
                citations=[],
            )

        context = self._build_context(results)

        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "You are SentinelIQ, a grounded enterprise knowledge assistant. "
                "Answer using only the supplied source excerpts. "
                "Do not use outside knowledge. "
                "Every factual claim must be supported by the sources. "
                "Cite sources using [1], [2], and so on. "
                "If the sources do not contain enough information to answer the "
                "question, say that the available sources do not provide enough "
                "information. Do not invent an answer."
            ),
            input=(f"Question:\n{question}\n\nAuthorized source excerpts:\n{context}"),
        )

        used_numbers = self._used_citation_numbers(
            response.output_text,
            len(results),
        )

        citations = [
            Citation(
                number=index,
                document_id=result.document_id,
                document_title=result.document_title,
                document_version_id=result.document_version_id,
                version_number=result.version_number,
                page_number=result.page_number,
                chunk_id=result.chunk_id,
                excerpt=self._build_excerpt(result.content),
            )
            for index, result in enumerate(results, start=1)
            if index in used_numbers
        ]

        return RAGAnswer(
            answer=response.output_text,
            citations=citations,
        )

    @staticmethod
    def _build_context(results: list[RetrievalResult]) -> str:
        sections: list[str] = []

        for index, result in enumerate(results, start=1):
            sections.append(
                "\n".join(
                    [
                        f"[{index}]",
                        f"Document: {result.document_title}",
                        f"Version: {result.version_number}",
                        f"Page: {result.page_number}",
                        result.content,
                    ]
                )
            )

        return "\n\n".join(sections)

    @staticmethod
    def _used_citation_numbers(
        answer: str,
        maximum: int,
    ) -> set[int]:
        numbers = {int(match) for match in re.findall(r"\[(\d+)\]", answer)}

        return {number for number in numbers if 1 <= number <= maximum}

    @staticmethod
    def _build_excerpt(
        content: str,
        maximum_length: int = 300,
    ) -> str:
        cleaned = " ".join(content.split())

        if len(cleaned) <= maximum_length:
            return cleaned

        return cleaned[:maximum_length].rstrip() + "..."
