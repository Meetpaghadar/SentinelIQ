import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from sentineliq.contracts import (
    AuthorizationContext,
    GenerationRequest,
    LLMProvider,
    QueryVariantOrigin,
)
from sentineliq.providers import (
    OpenAIGenerationProvider,
)
from sentineliq.querying import (
    HypotheticalQuery,
    QueryAnalyzer,
    QueryExpander,
    QueryPlanExecutor,
    QueryPlanner,
    QueryRewriter,
    RetrievalBackend,
)
from sentineliq.rag.context import (
    ContextAssembler,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
    scope_from_authorization,
)

INSUFFICIENT_EVIDENCE_ANSWER = (
    "The available sources do not provide enough information to answer this question."
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
    retrieval_query: str
    rewrite_used: bool = False
    retrieved_titles: tuple[str, ...] = ()
    techniques: tuple[str, ...] = ()


class RAGService:
    def __init__(
        self,
        retrieval_service: RetrievalBackend,
        generation_provider: LLMProvider | None = None,
        context_assembler: ContextAssembler | None = None,
        query_planner: QueryPlanner | None = None,
        query_rewriter: QueryRewriter | None = None,
        query_expander: QueryExpander | None = None,
        hyde_generator: HypotheticalQuery | None = None,
    ) -> None:
        self._generation_provider = generation_provider or OpenAIGenerationProvider()

        self._context_assembler = context_assembler or ContextAssembler()

        self._query_analyzer = QueryAnalyzer()

        self._query_planner = query_planner or QueryPlanner()

        self._query_rewriter = query_rewriter or QueryRewriter(self._generation_provider)

        self._query_expander = query_expander or QueryExpander(self._generation_provider)

        self._hyde_generator = hyde_generator or HypotheticalQuery(self._generation_provider)

        self._query_executor = QueryPlanExecutor(retrieval_service)

    def answer(
        self,
        session: Session,
        tenant_id: UUID,
        question: str,
        limit: int = 5,
        authorization: (AuthorizationContext | None) = None,
    ) -> RAGAnswer:
        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty")

        analysis = self._query_analyzer.analyze(question)

        plan = self._query_planner.plan(analysis)

        access_scope = self._access_scope(
            tenant_id=tenant_id,
            authorization=authorization,
        )

        retrieval_query = question
        rewrite_used = False
        techniques: list[str] = []
        variant_queries: tuple[str, ...] = ()
        executor_query = question

        if plan.rewrite:
            variant = self._query_rewriter.rewrite(question)
            retrieval_query = variant.text
            executor_query = variant.text
            rewrite_used = variant.origin is QueryVariantOrigin.REWRITE

            if rewrite_used:
                techniques.append("rewrite")

        if plan.hyde:
            hypothetical = self._hyde_generator.generate(question)

            if hypothetical is not None:
                retrieval_query = hypothetical.text
                variant_queries = (hypothetical.text,)
                executor_query = question
                techniques.append("hyde")

        elif plan.multi_query:
            alternates = self._query_expander.expand(question)

            if alternates:
                retrieval_query = question
                variant_queries = (
                    question,
                    *[item.text for item in alternates],
                )
                executor_query = question
                techniques.append("multi_query")

                if plan.rag_fusion:
                    techniques.append("rag_fusion")

        if plan.rerank:
            techniques.append("rerank")

        if plan.parent_expansion:
            techniques.append("parent_expansion")

        execution = self._query_executor.execute(
            session=session,
            tenant_id=tenant_id,
            query=executor_query,
            plan=plan,
            access_scope=access_scope,
            variant_queries=variant_queries,
        )

        results = execution.results

        retrieved_titles = tuple(result.document_title for result in results)

        if not results:
            return RAGAnswer(
                answer=(INSUFFICIENT_EVIDENCE_ANSWER),
                citations=[],
                retrieval_query=retrieval_query,
                rewrite_used=rewrite_used,
                retrieved_titles=retrieved_titles,
                techniques=tuple(techniques),
            )

        assembled = self._context_assembler.assemble(results)

        if not assembled.items:
            return RAGAnswer(
                answer=(INSUFFICIENT_EVIDENCE_ANSWER),
                citations=[],
                retrieval_query=retrieval_query,
                rewrite_used=rewrite_used,
                retrieved_titles=retrieved_titles,
                techniques=tuple(techniques),
            )

        generation = self._generation_provider.generate(
            GenerationRequest(
                instructions=(
                    "You are SentinelIQ, a grounded "
                    "enterprise knowledge assistant. "
                    "Answer using only the supplied "
                    "authorized evidence. "
                    "Do not use outside knowledge. "
                    "Every factual claim must be "
                    "supported by the supplied evidence. "
                    "Cite supporting evidence using "
                    "[1], [2], and so on. "
                    "If the supplied evidence does not "
                    "contain enough information to answer "
                    "the question, respond with exactly: "
                    f"{INSUFFICIENT_EVIDENCE_ANSWER} "
                    "When returning that response, do not "
                    "include citations, explanation, "
                    "additional text, or source numbers. "
                    "Do not invent or infer unsupported "
                    "facts."
                ),
                input_text=(f"Question:\n{question}\n\nAuthorized evidence:\n{assembled.text}"),
            )
        )

        answer = generation.text.strip()

        if self._is_insufficient_evidence_answer(answer):
            return RAGAnswer(
                answer=(INSUFFICIENT_EVIDENCE_ANSWER),
                citations=[],
                retrieval_query=retrieval_query,
                rewrite_used=rewrite_used,
                retrieved_titles=retrieved_titles,
                techniques=tuple(techniques),
            )

        used_numbers = self._used_citation_numbers(
            answer,
            len(assembled.items),
        )

        citations: list[Citation] = []

        for item in assembled.items:
            if item.number not in used_numbers:
                continue

            result = item.result

            citations.append(
                Citation(
                    number=(item.number),
                    document_id=(result.document_id),
                    document_title=(result.document_title),
                    document_version_id=(result.document_version_id),
                    version_number=(result.version_number),
                    page_number=(result.page_number),
                    chunk_id=(result.chunk_id),
                    excerpt=(self._build_excerpt(result.content)),
                )
            )

        return RAGAnswer(
            answer=answer,
            citations=citations,
            retrieval_query=retrieval_query,
            rewrite_used=rewrite_used,
            retrieved_titles=retrieved_titles,
            techniques=tuple(techniques),
        )

    @staticmethod
    def _access_scope(
        *,
        tenant_id: UUID,
        authorization: AuthorizationContext | None,
    ) -> RetrievalAccessScope:
        if authorization is None:
            return RetrievalAccessScope(tenant_id=tenant_id)

        if authorization.tenant_id != tenant_id:
            raise ValueError("Authorization tenant does not match requested tenant")

        return scope_from_authorization(authorization)

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

    @staticmethod
    def _is_insufficient_evidence_answer(
        answer: str,
    ) -> bool:
        normalized = " ".join(answer.split()).casefold()

        expected = " ".join(INSUFFICIENT_EVIDENCE_ANSWER.split()).casefold()

        if normalized == expected:
            return True

        refusal_markers = (
            "do not provide enough information",
            "does not provide enough information",
            "not enough information to answer",
            "insufficient information to answer",
            "insufficient evidence",
            ("cannot answer based on the available sources"),
            ("cannot answer from the available sources"),
            ("sources do not contain enough information"),
            ("sources don't contain enough information"),
            ("excerpts do not contain enough information"),
            ("excerpts don't contain enough information"),
            ("evidence does not contain enough information"),
        )

        return any(marker in normalized for marker in refusal_markers)
