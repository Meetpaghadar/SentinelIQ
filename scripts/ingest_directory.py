import argparse
from pathlib import Path
from uuid import UUID

from sentineliq.db.session import SessionLocal
from sentineliq.ingestion.service import ingest_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest all PDFs from a directory.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--tenant-id", required=True, type=UUID)

    args = parser.parse_args()

    pdf_files = sorted(args.directory.glob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No PDF files found in {args.directory}")

    print(f"\nFound {len(pdf_files)} PDF files.\n")

    with SessionLocal() as session:
        for file_path in pdf_files:
            print(f"Ingesting: {file_path.name}")

            result = ingest_pdf(
                session=session,
                tenant_id=args.tenant_id,
                file_path=file_path,
                title=file_path.stem,
            )

            print(f"  Document ID: {result.document_id}")
            print(f"  Version: {result.version_number}")
            print(f"  Chunks: {result.chunk_count}")
            print()


if __name__ == "__main__":
    main()
