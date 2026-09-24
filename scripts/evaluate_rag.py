import argparse
from dataclasses import dataclass
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.evaluation.retrieval_metrics import (
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from sentineliq.rag.service import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    RAGService,
)
from sentineliq.retrieval.service import (
    RetrievalService,
)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    question: str
    expected_document: str | None
    answerable: bool


CASES = [
    EvaluationCase(
        question=("What advice is given about writing?"),
        expected_document=("JP Essay Writing"),
        answerable=True,
    ),
    EvaluationCase(
        question=("What advice is given about improving memory while writing?"),
        expected_document=("JP Essay Writing"),
        answerable=True,
    ),
    EvaluationCase(
        question=("What is a large language model?"),
        expected_document=("NLP standford"),
        answerable=True,
    ),
    EvaluationCase(
        question=("What is perplexity in language modeling?"),
        expected_document=("NLP standford"),
        answerable=True,
    ),
    EvaluationCase(
        question=("What advice is given about upskilling?"),
        expected_document=("Advice on Upskilling"),
        answerable=True,
    ),
    EvaluationCase(
        question=("How do I configure an AWS VPC with Terraform?"),
        expected_document=None,
        answerable=False,
    ),
]


def _normalize(
    value: str,
) -> str:
    return " ".join(value.split()).casefold()


def _is_insufficient_evidence(
    answer: str,
) -> bool:
    normalized = _normalize(answer)

    expected = _normalize(INSUFFICIENT_EVIDENCE_ANSWER)

    if normalized == expected:
        return True

    markers = (
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

    return any(marker in normalized for marker in markers)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tenant-id",
        required=True,
        type=UUID,
    )

    args = parser.parse_args()

    embedding_service = EmbeddingService()

    retrieval_service = RetrievalService(embedding_service)

    rag_service = RAGService(retrieval_service)

    passed = 0

    retrieval_recall_scores: list[float] = []

    retrieval_rr_scores: list[float] = []

    retrieval_ndcg_scores: list[float] = []

    with SessionLocal() as session:
        for index, case in enumerate(
            CASES,
            start=1,
        ):
            if case.answerable and case.expected_document is not None:
                retrieval_results = retrieval_service.search(
                    session=session,
                    tenant_id=args.tenant_id,
                    query=case.question,
                    limit=5,
                )

                retrieved_documents = [result.document_title for result in retrieval_results]

                relevant_documents = {case.expected_document}

                retrieval_recall_scores.append(
                    recall_at_k(
                        retrieved=(retrieved_documents),
                        relevant=(relevant_documents),
                        k=5,
                    )
                )

                retrieval_rr_scores.append(
                    reciprocal_rank(
                        retrieved=(retrieved_documents),
                        relevant=(relevant_documents),
                    )
                )

                retrieval_ndcg_scores.append(
                    ndcg_at_k(
                        retrieved=(retrieved_documents),
                        relevant=(relevant_documents),
                        k=5,
                    )
                )

            result = rag_service.answer(
                session=session,
                tenant_id=args.tenant_id,
                question=case.question,
            )

            cited_documents = [citation.document_title for citation in result.citations]

            insufficient = _is_insufficient_evidence(result.answer)

            success = False
            failure_reason = ""

            if case.answerable:
                if insufficient:
                    failure_reason = "Answerable question returned insufficient evidence"

                elif case.expected_document not in cited_documents:
                    failure_reason = "Expected document was not cited"

                elif not result.citations:
                    failure_reason = "Answerable question returned no citations"

                else:
                    success = True

            else:
                if not insufficient:
                    failure_reason = "Unanswerable question did not return insufficient evidence"

                elif result.citations:
                    failure_reason = "Insufficient-evidence answer returned citations"

                else:
                    success = True

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"

            print()
            print(f"[{index}] {status}")

            print(f"Question: {case.question}")

            print(f"Expected: {case.expected_document}")

            print(f"Answerable: {case.answerable}")

            print(f"Insufficient evidence: {insufficient}")

            print(f"Cited: {cited_documents}")

            print(f"Answer: {result.answer}")

            if not success:
                print(f"Failure reason: {failure_reason}")

    total = len(CASES)

    accuracy = passed / total * 100.0

    print()
    print("=" * 30)
    print("SentinelIQ RAG Evaluation")
    print("=" * 30)

    print(f"Passed: {passed}/{total}")

    print(f"Accuracy: {accuracy:.1f}%")

    if retrieval_recall_scores:
        average_recall = sum(retrieval_recall_scores) / len(retrieval_recall_scores)

        average_mrr = sum(retrieval_rr_scores) / len(retrieval_rr_scores)

        average_ndcg = sum(retrieval_ndcg_scores) / len(retrieval_ndcg_scores)

        print()
        print("Retrieval Evaluation")
        print("=" * 30)

        print(f"Recall@5: {average_recall:.3f}")

        print(f"MRR: {average_mrr:.3f}")

        print(f"nDCG@5: {average_ndcg:.3f}")


if __name__ == "__main__":
    main()
