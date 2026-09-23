from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sentineliq.ingestion.chunking import chunk_pages
from sentineliq.ingestion.pdf import extract_pdf
from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    Tenant,
)


@dataclass(frozen=True)
class IngestionResult:
    document_id: UUID
    document_version_id: UUID
    version_number: int
    chunk_count: int
    content_hash: str
    status: str


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
        raise ValueError(f"Tenant not found: {tenant_id}")

    extracted = extract_pdf(file_path)

    source_uri = str(file_path)

    document = session.scalar(
        select(Document).where(
            Document.tenant_id == tenant_id,
            Document.source_uri == source_uri,
        )
    )

    if document is None:
        document = Document(
            tenant_id=tenant_id,
            title=title or file_path.stem,
            source_type="pdf",
            source_uri=source_uri,
        )

        session.add(document)
        session.flush()

    latest_version = session.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )

    if latest_version is not None and latest_version.content_hash == extracted.content_hash:
        return IngestionResult(
            document_id=document.id,
            document_version_id=latest_version.id,
            version_number=latest_version.version_number,
            chunk_count=len(latest_version.chunks),
            content_hash=latest_version.content_hash,
            status="skipped",
        )

    text_chunks = chunk_pages(extracted.pages)

    if not text_chunks:
        raise ValueError("PDF produced no chunks")

    latest_number = session.scalar(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document.id
        )
    )

    version_number = (latest_number or 0) + 1

    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        content_hash=extracted.content_hash,
        storage_path=source_uri,
        mime_type="application/pdf",
    )

    session.add(version)
    session.flush()

    chunks = [
        Chunk(
            document_version_id=version.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
        )
        for chunk in text_chunks
    ]

    session.add_all(chunks)
    session.commit()

    return IngestionResult(
        document_id=document.id,
        document_version_id=version.id,
        version_number=version_number,
        chunk_count=len(chunks),
        content_hash=extracted.content_hash,
        status="ingested",
    )
