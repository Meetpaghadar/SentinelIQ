import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sentineliq.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestionStatus(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    ENRICHING = "enriching"
    CHUNKING = "chunking"
    INDEXING = "indexing"
    GRAPH_PROCESSING = "graph_processing"
    VALIDATED = "validated"
    ACTIVE = "active"

    FAILED = "failed"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_uri: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=IngestionStatus.RECEIVED.value,
        nullable=False,
        index=True,
    )

    parser_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    chunker_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    embedding_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
