from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sentineliq.ingestion.chunking import chunk_pages
from sentineliq.ingestion.pdf import extract_pdf
from sentineliq.models import Chunk, Document, DocumentVersion, Tenant


@dataclass(frozen=True)
class IngestionResult:
    document_id: UUID
    document_version_id: UUID
    version_number: int
    chunk_count: int
    content_hash: str


def ingest_pdf(
    session: Session,
    tenant_id: UUID,
    file_path: Path,
    title: str | None = None,
) -> IngestionResult:
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    tenant = session.get(Tenant, tenant_id)

    if tenant is None:
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    extracted = extract_pdf(file_path)
    text_chunks = chunk_pages(extracted.pages)

    if not text_chunks:
        raise ValueError("PDF produced no chunks")

    document = Document(
        tenant_id=tenant_id,
        title=title or file_path.stem,
        source_type="pdf",
        source_uri=str(file_path),
    )

    session.add(document)
    session.flush()

    latest_version = session.scalar(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document.id
        )
    )

    version_number = (latest_version or 0) + 1

    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        content_hash=extracted.content_hash,
        storage_path=str(file_path),
        mime_type="application/pdf",
    )

    session.add(version)
    session.flush()

    chunks = [
        Chunk(
            document_version_id=version.id,
            chunk_index=text_chunk.chunk_index,
            content=text_chunk.content,
            page_number=text_chunk.page_number,
            start_char=text_chunk.start_char,
            end_char=text_chunk.end_char,
        )
        for text_chunk in text_chunks
    ]

    session.add_all(chunks)
    session.commit()

    return IngestionResult(
        document_id=document.id,
        document_version_id=version.id,
        version_number=version_number,
        chunk_count=len(chunks),
        content_hash=extracted.content_hash,
    )