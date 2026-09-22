import argparse
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.retrieval.service import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    embedding_service = EmbeddingService()
    retrieval_service = RetrievalService(embedding_service)

    with SessionLocal() as session:
        results = retrieval_service.search(
            session=session,
            tenant_id=UUID(args.tenant_id),
            query=args.query,
            limit=args.limit,
        )

    if not results:
        print("No results.")
        return

    for rank, result in enumerate(results, start=1):
        similarity = result.similarity

        print()
        print("=" * 70)
        print(f"Rank: {rank}")
        print(f"Document: {result.document_title}")
        print(f"Page: {result.page_number}")
        print(f"Similarity: {similarity:.4f}")
        print(f"Chunk ID: {result.chunk_id}")
        print("-" * 70)
        print(result.content[:800])


if __name__ == "__main__":
    main()
