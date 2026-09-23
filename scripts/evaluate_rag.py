import argparse
import json
from pathlib import Path
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.rag.service import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    RAGService,
)
from sentineliq.retrieval.service import RetrievalService


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _is_insufficient_evidence(
    answer: str,
) -> bool:
    return _normalize(answer) == _normalize(INSUFFICIENT_EVIDENCE_ANSWER)


def main() -> None:
    parser = argparse.ArgumentParser(description=("Evaluate SentinelIQ RAG behavior."))

    parser.add_argument(
        "--tenant-id",
        required=True,
        type=UUID,
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/rag_questions.json"),
    )

    args = parser.parse_args()

    cases = json.loads(args.dataset.read_text(encoding="utf-8"))

    embedding_service = EmbeddingService()

    retrieval_service = RetrievalService(embedding_service)

    rag_service = RAGService(retrieval_service)

    passed = 0

    with SessionLocal() as session:
        for index, case in enumerate(
            cases,
            start=1,
        ):
            question = case["question"]

            expected_document = case["expected_document"]

            answerable = case["answerable"]

            result = rag_service.answer(
                session=session,
                tenant_id=(args.tenant_id),
                question=question,
                limit=5,
            )

            cited_documents = {citation.document_title for citation in result.citations}

            insufficient = _is_insufficient_evidence(result.answer)

            if answerable:
                success = (
                    not insufficient
                    and expected_document in cited_documents
                    and len(result.citations) > 0
                )

                failure_reason = None

                if insufficient:
                    failure_reason = "Answerable question returned insufficient evidence"

                elif expected_document not in cited_documents:
                    failure_reason = "Expected document was not cited"

                elif not result.citations:
                    failure_reason = "Answerable question returned no citations"

            else:
                success = insufficient and len(result.citations) == 0

                failure_reason = None

                if not insufficient:
                    failure_reason = (
                        "Unanswerable question "
                        "did not return the canonical "
                        "insufficient-evidence answer"
                    )

                elif result.citations:
                    failure_reason = "Insufficient-evidence answer incorrectly included citations"

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"

            print(f"\n[{index}] {status}")
            print(f"Question: {question}")
            print(f"Expected: {expected_document}")
            print(f"Answerable: {answerable}")
            print(f"Insufficient evidence: {insufficient}")
            print(f"Cited: {sorted(cited_documents)}")
            print(f"Answer: {result.answer[:300]}")

            if not success and failure_reason:
                print(f"Failure reason: {failure_reason}")

    total = len(cases)

    accuracy = passed / total * 100 if total else 0.0

    print()
    print("==============================")
    print("SentinelIQ RAG Evaluation")
    print("==============================")
    print(f"Passed: {passed}/{total}")
    print(f"Accuracy: {accuracy:.1f}%")


if __name__ == "__main__":
    main()
