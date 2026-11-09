import argparse
from uuid import UUID

from sentineliq.auth.dependencies import resolve_authenticated_user
from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.rag.service import RAGService
from sentineliq.retrieval.service import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    embedding_service = EmbeddingService()
    retrieval_service = RetrievalService(embedding_service)
    rag_service = RAGService(retrieval_service)

    with SessionLocal() as session:
        authenticated_user = resolve_authenticated_user(
            session,
            user_id=UUID(args.user_id),
            tenant_id=UUID(args.tenant_id),
        )
        if "knowledge:query" not in authenticated_user.permissions:
            raise PermissionError("knowledge:query permission is required")

        result = rag_service.answer(
            session=session,
            tenant_id=authenticated_user.tenant_id,
            question=args.question,
            authorization=authenticated_user.authorization_context(),
            limit=args.limit,
        )

    print()
    print("ANSWER")
    print("=" * 70)
    print(result.answer)

    print()
    print("SOURCES")
    print("=" * 70)

    for citation in result.citations:
        print(
            f"[{citation.number}] "
            f"{citation.document_title} | "
            f"Page {citation.page_number} | "
            f"Version {citation.version_number} | "
            f"Chunk {citation.chunk_id}"
        )


if __name__ == "__main__":
    main()
