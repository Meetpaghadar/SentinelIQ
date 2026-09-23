from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from sentineliq.models import (
    Chunk,
    DocumentVersion,
    KnowledgeStatus,
    ParentChunk,
    Section,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def revoke_document_version(
    session: Session,
    *,
    document_version_id: UUID,
) -> None:
    version = session.get(
        DocumentVersion,
        document_version_id,
    )

    if version is None:
        raise ValueError(f"Document version not found: {document_version_id}")

    if version.status == KnowledgeStatus.REVOKED.value:
        return

    version.status = KnowledgeStatus.REVOKED.value

    version.effective_until = utc_now()

    session.execute(delete(Chunk).where(Chunk.document_version_id == version.id))

    session.execute(delete(ParentChunk).where(ParentChunk.document_version_id == version.id))

    session.execute(delete(Section).where(Section.document_version_id == version.id))

    session.commit()
