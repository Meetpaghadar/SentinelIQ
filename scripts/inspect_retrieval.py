import argparse
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.retrieval.service import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect SentinelIQ retrieval results.")
    parser.add_argument("question")
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    embedding_service = EmbeddingService()
    retrieval_service = RetrievalService(embedding_service)

    with SessionLocal() as session:
        results = retrieval_service.search(
            session=session,
            tenant_id=args.tenant_id,
            query=args.question,
            limit=args.limit,
        )

    print(f"\nQuestion: {args.question}")
    print(f"Retrieved: {len(results)} chunks\n")

    if not results:
        print("No relevant chunks found.")
        return

    for rank, result in enumerate(results, start=1):
        print("=" * 80)
        print(f"RANK:       {rank}")
        print(f"SIMILARITY: {result.similarity:.4f}")
        print(f"DOCUMENT:   {result.document_title}")
        print(f"VERSION:    {result.version_number}")
        print(f"PAGE:       {result.page_number}")
        print(f"CHUNK ID:   {result.chunk_id}")
        print("-" * 80)
        print(result.content)
        print()


if __name__ == "__main__":
    main()
