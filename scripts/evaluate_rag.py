import argparse
import json
from pathlib import Path
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.rag.service import RAGService
from sentineliq.retrieval.service import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SentinelIQ RAG behavior.")
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
        for index, case in enumerate(cases, start=1):
            question = case["question"]
            expected_document = case["expected_document"]
            answerable = case["answerable"]

            result = rag_service.answer(
                session=session,
                tenant_id=args.tenant_id,
                question=question,
                limit=5,
            )

            cited_documents = {citation.document_title for citation in result.citations}

            if answerable:
                success = expected_document in cited_documents and len(result.citations) > 0
            else:
                success = len(result.citations) == 0

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"

            print(f"\n[{index}] {status}")
            print(f"Question: {question}")
            print(f"Expected: {expected_document}")
            print(f"Cited: {sorted(cited_documents)}")
            print(f"Answer: {result.answer[:300]}")

    total = len(cases)

    print("\n==============================")
    print("SentinelIQ RAG Evaluation")
    print("==============================")
    print(f"Passed: {passed}/{total}")
    print(f"Accuracy: {(passed / total) * 100:.1f}%")


if __name__ == "__main__":
    main()
