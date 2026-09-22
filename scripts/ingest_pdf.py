import argparse
from pathlib import Path
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.ingestion.service import ingest_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--title")

    args = parser.parse_args()

    with SessionLocal() as session:
        result = ingest_pdf(
            session=session,
            tenant_id=UUID(args.tenant_id),
            file_path=Path(args.file),
            title=args.title,
        )

    print(f"Document: {result.document_id}")
    print(f"Version: {result.document_version_id}")
    print(f"Version number: {result.version_number}")
    print(f"Chunks: {result.chunk_count}")
    print(f"SHA-256: {result.content_hash}")


if __name__ == "__main__":
    main()
