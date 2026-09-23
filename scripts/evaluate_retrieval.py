import argparse
import json
from pathlib import Path
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.retrieval.service import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SentinelIQ retrieval.")
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument(
        "--eval-file",
        type=Path,
        default=Path("evals/retrieval_questions.json"),
    )
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    cases = json.loads(args.eval_file.read_text(encoding="utf-8"))

    retrieval_service = RetrievalService(EmbeddingService())

    passed = 0

    with SessionLocal() as session:
        for index, case in enumerate(cases, start=1):
            question = case["question"]
            expected_pages = set(case["expected_pages"])

            results = retrieval_service.search(
                session=session,
                tenant_id=args.tenant_id,
                query=question,
                limit=args.limit,
            )

            retrieved_pages = {
                result.page_number for result in results if result.page_number is not None
            }

            if expected_pages:
                success = bool(expected_pages & retrieved_pages)
            else:
                success = len(results) == 0

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"

            print("=" * 80)
            print(f"{index}. {status}")
            print(f"Question: {question}")
            print(f"Expected pages: {sorted(expected_pages)}")
            print(f"Retrieved pages: {sorted(retrieved_pages)}")

            if results:
                print(
                    "Scores:",
                    [round(result.similarity, 4) for result in results],
                )

    total = len(cases)

    print("\n" + "=" * 80)
    print("RETRIEVAL EVALUATION")
    print("=" * 80)
    print(f"Passed: {passed}/{total}")
    print(f"Accuracy: {(passed / total) * 100:.1f}%")


if __name__ == "__main__":
    main()
