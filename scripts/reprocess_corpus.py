import argparse
from uuid import UUID

from sqlalchemy import select

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.ingestion.reprocessing import (
    reprocess_document_version,
)
from sentineliq.models import (
    Document,
    DocumentVersion,
    KnowledgeStatus,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Rebuild SentinelIQ derived knowledge representation for existing versions.")
    )

    parser.add_argument(
        "--tenant-id",
        required=True,
        type=UUID,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    embedding_service = EmbeddingService()

    with SessionLocal() as session:
        versions = list(
            session.scalars(
                select(DocumentVersion)
                .join(
                    Document,
                    Document.id == DocumentVersion.document_id,
                )
                .where(
                    Document.tenant_id == args.tenant_id,
                    DocumentVersion.status == KnowledgeStatus.ACTIVE.value,
                )
                .order_by(DocumentVersion.created_at)
            )
        )

        if not versions:
            print("No active document versions found.")
            return

        print(f"Reprocessing {len(versions)} active versions...")

        for version in versions:
            document = version.document

            print()
            print(f"Document: {document.title}")
            print(f"Version: {version.version_number}")
            print(f"Version ID: {version.id}")

            result = reprocess_document_version(
                session,
                document_version_id=(version.id),
                embedding_provider=(embedding_service),
            )

            print(f"Sections: {result.section_count}")
            print(f"Parents: {result.parent_chunk_count}")
            print(f"Children: {result.child_chunk_count}")
            print(f"Embeddings: {result.embedding_count}")
            print(f"Reused embeddings: {result.reused_embedding_count}")
            print(f"Generated embeddings: {result.generated_embedding_count}")
            print(f"Changed sections: {result.changed_section_count}")
            print(f"Unchanged sections: {result.unchanged_section_count}")

        print()
        print("Corpus reprocessing complete.")


if __name__ == "__main__":
    main()
