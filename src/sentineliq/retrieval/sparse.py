import math
import re
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeStatus,
)
from sentineliq.retrieval.access import (
    RetrievalAccessScope,
    build_access_predicates,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")

BM25_K1 = 1.5
BM25_B = 0.75


@dataclass(frozen=True, slots=True)
class SparseDocument:
    result: RetrievalResult
    tokens: tuple[str, ...]


def _tokenize(
    text: str,
) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text)]


def _bm25_scores(
    *,
    query: str,
    documents: list[SparseDocument],
) -> list[float]:
    if not documents:
        return []

    query_terms = list(dict.fromkeys(_tokenize(query)))

    if not query_terms:
        return [0.0 for _ in documents]

    document_lengths = [len(document.tokens) for document in documents]

    average_length = sum(document_lengths) / len(document_lengths)

    if average_length == 0:
        return [0.0 for _ in documents]

    document_frequency: Counter[str] = Counter()

    for document in documents:
        unique_terms = set(document.tokens)

        for term in query_terms:
            if term in unique_terms:
                document_frequency[term] += 1

    total_documents = len(documents)

    scores: list[float] = []

    for document in documents:
        frequencies = Counter(document.tokens)

        document_length = len(document.tokens)

        score = 0.0

        for term in query_terms:
            frequency = frequencies[term]

            if frequency == 0:
                continue

            df = document_frequency[term]

            inverse_document_frequency = math.log(1.0 + (total_documents - df + 0.5) / (df + 0.5))

            numerator = frequency * (BM25_K1 + 1.0)

            denominator = frequency + BM25_K1 * (
                1.0 - BM25_B + BM25_B * document_length / average_length
            )

            score += inverse_document_frequency * numerator / denominator

        scores.append(score)

    return scores


class BM25Retriever:
    def search(
        self,
        session: Session,
        *,
        tenant_id: UUID,
        query: str,
        candidate_k: int,
        access_scope: (RetrievalAccessScope | None) = None,
    ) -> list[RetrievalResult]:
        if candidate_k <= 0:
            raise ValueError("candidate_k must be greater than zero")

        scope = access_scope or RetrievalAccessScope(tenant_id=tenant_id)

        if scope.tenant_id != tenant_id:
            raise ValueError("Retrieval access scope tenant does not match requested tenant")

        statement = (
            select(
                Chunk.id,
                Document.id.label("document_id"),
                Document.title,
                DocumentVersion.id.label("document_version_id"),
                DocumentVersion.version_number,
                Chunk.page_number,
                Chunk.content,
                Chunk.contextual_summary,
            )
            .join(
                DocumentVersion,
                Chunk.document_version_id == DocumentVersion.id,
            )
            .join(
                Document,
                DocumentVersion.document_id == Document.id,
            )
            .where(
                *build_access_predicates(scope),
                DocumentVersion.status == KnowledgeStatus.ACTIVE.value,
                or_(
                    DocumentVersion.effective_from.is_(None),
                    DocumentVersion.effective_from <= func.now(),
                ),
                or_(
                    DocumentVersion.effective_until.is_(None),
                    DocumentVersion.effective_until > func.now(),
                ),
            )
        )

        rows = session.execute(statement).all()

        documents: list[SparseDocument] = []

        for row in rows:
            contextual_summary = row.contextual_summary or ""

            searchable_text = contextual_summary + "\n" + row.content

            result = RetrievalResult(
                chunk_id=row.id,
                document_id=(row.document_id),
                document_title=(row.title),
                document_version_id=(row.document_version_id),
                version_number=(row.version_number),
                page_number=(row.page_number),
                content=(row.content),
                similarity=0.0,
                retrieval_method=("bm25"),
            )

            documents.append(
                SparseDocument(
                    result=result,
                    tokens=tuple(_tokenize(searchable_text)),
                )
            )

        scores = _bm25_scores(
            query=query,
            documents=documents,
        )

        ranked = sorted(
            zip(
                documents,
                scores,
                strict=True,
            ),
            key=lambda item: item[1],
            reverse=True,
        )

        results: list[RetrievalResult] = []

        for rank, (
            document,
            score,
        ) in enumerate(
            ranked,
            start=1,
        ):
            if score <= 0:
                continue

            results.append(
                document.result.with_updates(
                    sparse_score=score,
                    sparse_rank=rank,
                    retrieval_method=("bm25"),
                )
            )

            if len(results) >= candidate_k:
                break

        return results
