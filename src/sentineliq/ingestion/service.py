from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sentineliq.ingestion.chunking import (
    CHUNKER_VERSION,
    build_hierarchical_chunks,
)
from sentineliq.ingestion.parsers import (
    ParsedSource,
    parse_source,
)
from sentineliq.ingestion.retry import (
    RetryExhaustedError,
    retry_call,
)
from sentineliq.ingestion.security import (
    IngestionSecurityError,
    scan_ingestion_file,
)
from sentineliq.ingestion.structure import (
    extract_sections,
)
from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    IngestionJob,
    IngestionStatus,
    KnowledgeSource,
    KnowledgeStatus,
    ParentChunk,
    Section,
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _set_job_status(
    session: Session,
    job: IngestionJob,
    status: IngestionStatus,
) -> None:
    job.status = status.value
    job.updated_at = _utc_now()

    if status != IngestionStatus.RECEIVED and job.started_at is None:
        job.started_at = _utc_now()

    if status in {
        IngestionStatus.ACTIVE,
        IngestionStatus.FAILED,
        IngestionStatus.QUARANTINED,
        IngestionStatus.REJECTED,
        IngestionStatus.DEAD_LETTER,
    }:
        job.completed_at = _utc_now()

    session.flush()


def _persist_failure(
    session: Session,
    *,
    job_id: UUID,
    status: IngestionStatus,
    error: Exception,
    retry_count: int,
) -> None:
    session.rollback()

    job = session.get(
        IngestionJob,
        job_id,
    )

    if job is None:
        raise RuntimeError("Ingestion job disappeared after rollback")

    job.status = status.value
    job.error_message = str(error)
    job.retry_count = retry_count
    job.completed_at = _utc_now()
    job.updated_at = _utc_now()

    session.commit()


def _get_or_create_source(
    session: Session,
    *,
    tenant_id: UUID,
    source_uri: str,
    source_type: str,
    title: str,
) -> KnowledgeSource:
    source = session.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.tenant_id == tenant_id,
            KnowledgeSource.source_type == source_type,
            KnowledgeSource.source_uri == source_uri,
        )
    )

    if source is not None:
        return source

    source = KnowledgeSource(
        tenant_id=tenant_id,
        name=title,
        source_type=source_type,
        source_uri=source_uri,
    )

    session.add(source)
    session.flush()

    return source


def _persist_structure(
    session: Session,
    *,
    version: DocumentVersion,
    parsed: ParsedSource,
) -> int:
    parsed_sections = extract_sections(list(parsed.pages))

    if not parsed_sections:
        raise ValueError("Document produced no sections")

    hierarchy = build_hierarchical_chunks(parsed_sections)

    if not hierarchy.children:
        raise ValueError("Document produced no child chunks")

    section_models: dict[
        int,
        Section,
    ] = {}

    section_stack: dict[
        int,
        Section,
    ] = {}

    for parsed_section in parsed_sections:
        parent_section: Section | None = None

        parent_levels = [level for level in section_stack if level < parsed_section.level]

        if parent_levels:
            parent_section = section_stack[max(parent_levels)]

        section = Section(
            document_version_id=(version.id),
            parent_section_id=(parent_section.id if parent_section else None),
            section_index=(parsed_section.section_index),
            level=(parsed_section.level),
            title=(parsed_section.title),
            section_path=(parsed_section.section_path),
            content=(parsed_section.content),
            content_hash=(parsed_section.content_hash),
            page_start=(parsed_section.page_start),
            page_end=(parsed_section.page_end),
            start_char=(parsed_section.start_char),
            end_char=(parsed_section.end_char),
        )

        session.add(section)
        session.flush()

        section_models[parsed_section.section_index] = section

        section_stack[parsed_section.level] = section

        stale_levels = [level for level in section_stack if level > parsed_section.level]

        for level in stale_levels:
            del section_stack[level]

    parent_models: dict[
        int,
        ParentChunk,
    ] = {}

    for item in hierarchy.parents:
        section = section_models[item.section_index]

        parent = ParentChunk(
            document_version_id=(version.id),
            section_id=(section.id),
            parent_index=(item.parent_index),
            content=item.content,
            content_hash=(item.content_hash),
            source_location=(item.source_location),
            page_number=(item.page_number),
            start_char=(item.start_char),
            end_char=(item.end_char),
        )

        session.add(parent)
        session.flush()

        parent_models[item.parent_index] = parent

    chunks: list[Chunk] = []

    for item in hierarchy.children:
        section = section_models[item.section_index]

        parent = parent_models[item.parent_index]

        chunks.append(
            Chunk(
                document_version_id=(version.id),
                section_id=(section.id),
                parent_chunk_id=(parent.id),
                chunk_index=(item.chunk_index),
                content=(item.content),
                content_hash=(item.content_hash),
                source_location=(item.source_location),
                page_number=(item.page_number),
                start_char=(item.start_char),
                end_char=(item.end_char),
            )
        )

    session.add_all(chunks)
    session.flush()

    return len(chunks)


def ingest_file(
    session: Session,
    tenant_id: UUID,
    file_path: Path,
    title: str | None = None,
) -> IngestionResult:
    tenant = session.get(
        Tenant,
        tenant_id,
    )

    if tenant is None:
        raise ValueError(f"Tenant not found: {tenant_id}")

    source_uri = str(file_path.resolve())

    document_title = title or file_path.stem

    job = IngestionJob(
        tenant_id=tenant_id,
        source_uri=source_uri,
        status=(IngestionStatus.RECEIVED.value),
    )

    session.add(job)

    # Commit the ingestion job first so it
    # survives later ingestion rollback.
    session.commit()

    job_id = job.id

    retry_count = 0

    try:
        _set_job_status(
            session,
            job,
            IngestionStatus.VALIDATING,
        )

        scan = scan_ingestion_file(file_path)

        source_type = scan.extension.lstrip(".")

        source = _get_or_create_source(
            session,
            tenant_id=tenant_id,
            source_uri=source_uri,
            source_type=(source_type),
            title=(document_title),
        )

        document = session.scalar(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.source_uri == source_uri,
            )
        )

        if document is None:
            document = Document(
                tenant_id=tenant_id,
                source_id=source.id,
                title=(document_title),
                source_type=(source_type),
                source_uri=(source_uri),
            )

            session.add(document)
            session.flush()

        elif document.source_id is None:
            document.source_id = source.id

        job.document_id = document.id

        _set_job_status(
            session,
            job,
            IngestionStatus.PARSING,
        )

        parsed, retry_count = retry_call(lambda: parse_source(file_path))

        job.retry_count = retry_count

        job.parser_version = parsed.parser_version

        job.chunker_version = CHUNKER_VERSION

        latest_version = session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )

        if (
            latest_version is not None
            and latest_version.content_hash == parsed.content_hash
            and latest_version.parser_version == parsed.parser_version
            and latest_version.sections
            and latest_version.parent_chunks
        ):
            job.document_version_id = latest_version.id

            _set_job_status(
                session,
                job,
                IngestionStatus.ACTIVE,
            )

            session.commit()

            return IngestionResult(
                document_id=(document.id),
                document_version_id=(latest_version.id),
                version_number=(latest_version.version_number),
                chunk_count=len(latest_version.chunks),
                content_hash=(latest_version.content_hash),
                status="skipped",
            )

        _set_job_status(
            session,
            job,
            IngestionStatus.NORMALIZING,
        )

        _set_job_status(
            session,
            job,
            IngestionStatus.CHUNKING,
        )

        latest_number = session.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )

        version_number = (latest_number or 0) + 1

        if latest_version is not None:
            latest_version.status = KnowledgeStatus.SUPERSEDED.value

            latest_version.effective_until = _utc_now()

        version = DocumentVersion(
            document_id=(document.id),
            parent_version_id=(latest_version.id if latest_version else None),
            version_number=(version_number),
            content_hash=(parsed.content_hash),
            storage_path=(source_uri),
            mime_type=(parsed.mime_type),
            status=(KnowledgeStatus.ACTIVE.value),
            effective_from=(_utc_now()),
            parser_version=(parsed.parser_version),
            ingestion_timestamp=(_utc_now()),
        )

        session.add(version)
        session.flush()

        job.document_version_id = version.id

        chunk_count = _persist_structure(
            session,
            version=version,
            parsed=parsed,
        )

        _set_job_status(
            session,
            job,
            IngestionStatus.INDEXING,
        )

        _set_job_status(
            session,
            job,
            IngestionStatus.VALIDATED,
        )

        _set_job_status(
            session,
            job,
            IngestionStatus.ACTIVE,
        )

        session.commit()

        return IngestionResult(
            document_id=(document.id),
            document_version_id=(version.id),
            version_number=(version.version_number),
            chunk_count=(chunk_count),
            content_hash=(version.content_hash),
            status="ingested",
        )

    except IngestionSecurityError as exc:
        _persist_failure(
            session,
            job_id=(job_id),
            status=(IngestionStatus.REJECTED),
            error=(exc),
            retry_count=(retry_count),
        )

        raise

    except RetryExhaustedError as exc:
        _persist_failure(
            session,
            job_id=(job_id),
            status=(IngestionStatus.DEAD_LETTER),
            error=(exc),
            retry_count=3,
        )

        raise

    except Exception as exc:
        _persist_failure(
            session,
            job_id=(job_id),
            status=(IngestionStatus.FAILED),
            error=(exc),
            retry_count=(retry_count),
        )

        raise


def ingest_pdf(
    session: Session,
    tenant_id: UUID,
    file_path: Path,
    title: str | None = None,
) -> IngestionResult:
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("ingest_pdf requires a PDF file")

    return ingest_file(
        session=session,
        tenant_id=tenant_id,
        file_path=file_path,
        title=title,
    )
