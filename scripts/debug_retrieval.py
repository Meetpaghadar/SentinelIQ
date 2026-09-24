import argparse
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.retrieval.service import RetrievalService


def _print_results(
    title: str,
    results,
) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    for index, result in enumerate(
        results,
        start=1,
    ):
        print()
        print(f"RANK: {index}")
        print(f"Document: {result.document_title}")
        print(f"Page: {result.page_number}")
        print(f"Method: {result.retrieval_method}")
        print(f"Dense score: {result.dense_score}")
        print(f"Dense rank: {result.dense_rank}")
        print(f"Sparse score: {result.sparse_score}")
        print(f"Sparse rank: {result.sparse_rank}")
        print(f"Fusion score: {result.fusion_score}")

        content = " ".join(result.content.split())

        print("Content:")
        print(content[:800])


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tenant-id",
        required=True,
        type=UUID,
    )

    parser.add_argument(
        "--query",
        default=("What advice is given about upskilling?"),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    embedding_service = EmbeddingService()

    retrieval_service = RetrievalService(embedding_service)

    with SessionLocal() as session:
        dense = retrieval_service.search_dense(
            session=session,
            tenant_id=args.tenant_id,
            query=args.query,
            limit=args.limit,
        )

        sparse = retrieval_service.search_sparse(
            session=session,
            tenant_id=args.tenant_id,
            query=args.query,
            limit=args.limit,
        )

        hybrid = retrieval_service.search(
            session=session,
            tenant_id=args.tenant_id,
            query=args.query,
            limit=args.limit,
        )

    _print_results(
        "DENSE",
        dense,
    )

    _print_results(
        "BM25",
        sparse,
    )

    _print_results(
        "HYBRID / RRF",
        hybrid,
    )


if __name__ == "__main__":
    main()
