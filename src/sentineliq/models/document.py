import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentineliq.db.base import Base

if TYPE_CHECKING:
    from sentineliq.models.tenant import Tenant


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ARCHIVED = "archived"


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_uri: Mapped[str | None] = mapped_column(
        String(2000),
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

    documents: Mapped[list["Document"]] = relationship(
        back_populates="source",
    )


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_documents_tenant_id_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_uri: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(
        String(50),
        default=DataClassification.INTERNAL.value,
        nullable=False,
        index=True,
    )

    access_policy: Mapped[str | None] = mapped_column(
        Text,
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

    tenant: Mapped["Tenant"] = relationship(
        back_populates="documents",
    )

    source: Mapped[KnowledgeSource | None] = relationship(
        back_populates="documents",
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=KnowledgeStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parser_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    embedding_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
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

    document: Mapped[Document] = relationship(
        back_populates="versions",
    )

    parent_version: Mapped["DocumentVersion | None"] = relationship(
        remote_side="DocumentVersion.id",
    )

    sections: Mapped[list["Section"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )

    parent_chunks: Mapped[list["ParentChunk"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )


class Section(Base):
    __tablename__ = "sections"

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "section_index",
            name="uq_sections_version_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    section_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    level: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    section_path: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    page_start: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    page_end: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    start_char: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    end_char: Mapped[int | None] = mapped_column(
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

    document_version: Mapped[DocumentVersion] = relationship(
        back_populates="sections",
    )

    parent_section: Mapped["Section | None"] = relationship(
        remote_side="Section.id",
        back_populates="child_sections",
    )

    child_sections: Mapped[list["Section"]] = relationship(
        back_populates="parent_section",
    )

    parent_chunks: Mapped[list["ParentChunk"]] = relationship(
        back_populates="section",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="section",
    )


class ParentChunk(Base):
    __tablename__ = "parent_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "parent_index",
            name="uq_parent_chunks_version_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    contextual_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_location: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    start_char: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    end_char: Mapped[int | None] = mapped_column(
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

    document_version: Mapped[DocumentVersion] = relationship(
        back_populates="parent_chunks",
    )

    section: Mapped[Section | None] = relationship(
        back_populates="parent_chunks",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="parent_chunk",
    )


class Chunk(Base):
    __tablename__ = "chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_chunks_version_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parent_chunks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    contextual_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_location: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    embedding_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    start_char: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    end_char: Mapped[int | None] = mapped_column(
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

    document_version: Mapped[DocumentVersion] = relationship(
        back_populates="chunks",
    )

    section: Mapped[Section | None] = relationship(
        back_populates="chunks",
    )

    parent_chunk: Mapped[ParentChunk | None] = relationship(
        back_populates="chunks",
    )
