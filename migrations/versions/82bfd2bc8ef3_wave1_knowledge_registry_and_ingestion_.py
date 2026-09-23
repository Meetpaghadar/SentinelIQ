"""wave1 knowledge registry and ingestion jobs

Revision ID: 82bfd2bc8ef3
Revises: a4ea3f2e45a6
Create Date: 2026-09-23 14:19:15.241828
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "82bfd2bc8ef3"
down_revision: str | Sequence[str] | None = "a4ea3f2e45a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "source_uri",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_knowledge_sources_tenant_id"),
        "knowledge_sources",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "document_version_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "source_uri",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="received",
            nullable=False,
        ),
        sa.Column(
            "parser_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "chunker_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "embedding_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_ingestion_jobs_document_id"),
        "ingestion_jobs",
        ["document_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_ingestion_jobs_document_version_id"),
        "ingestion_jobs",
        ["document_version_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_ingestion_jobs_status"),
        "ingestion_jobs",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_ingestion_jobs_tenant_id"),
        "ingestion_jobs",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "sections",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "document_version_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "parent_section_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "section_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "level",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "section_path",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "page_start",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "page_end",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "start_char",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "end_char",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_section_id"],
            ["sections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "section_index",
            name="uq_sections_version_index",
        ),
    )

    op.create_index(
        op.f("ix_sections_document_version_id"),
        "sections",
        ["document_version_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_sections_parent_section_id"),
        "sections",
        ["parent_section_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # chunks
    # ------------------------------------------------------------------

    op.add_column(
        "chunks",
        sa.Column(
            "section_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "contextual_summary",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "source_location",
            sa.String(length=2000),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "embedding_version",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.add_column(
        "chunks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.alter_column(
        "chunks",
        "content",
        existing_type=sa.VARCHAR(),
        type_=sa.Text(),
        existing_nullable=False,
    )

    op.create_index(
        op.f("ix_chunks_section_id"),
        "chunks",
        ["section_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_chunks_section_id_sections",
        "chunks",
        "sections",
        ["section_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # document_versions
    # ------------------------------------------------------------------

    op.add_column(
        "document_versions",
        sa.Column(
            "parent_version_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="active",
            nullable=False,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "effective_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "change_summary",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "parser_version",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "embedding_version",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "ingestion_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.add_column(
        "document_versions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        op.f("ix_document_versions_parent_version_id"),
        "document_versions",
        ["parent_version_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_document_versions_status"),
        "document_versions",
        ["status"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_document_versions_parent_version_id",
        "document_versions",
        "document_versions",
        ["parent_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------

    op.add_column(
        "documents",
        sa.Column(
            "source_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "classification",
            sa.String(length=50),
            server_default="internal",
            nullable=False,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "access_policy",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        op.f("ix_documents_classification"),
        "documents",
        ["classification"],
        unique=False,
    )

    op.create_index(
        op.f("ix_documents_source_id"),
        "documents",
        ["source_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_documents_source_id_knowledge_sources",
        "documents",
        "knowledge_sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # parent_chunks
    # ------------------------------------------------------------------

    op.add_column(
        "parent_chunks",
        sa.Column(
            "section_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.add_column(
        "parent_chunks",
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "parent_chunks",
        sa.Column(
            "contextual_summary",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "parent_chunks",
        sa.Column(
            "source_location",
            sa.String(length=2000),
            nullable=True,
        ),
    )

    op.add_column(
        "parent_chunks",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.add_column(
        "parent_chunks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.alter_column(
        "parent_chunks",
        "content",
        existing_type=sa.VARCHAR(),
        type_=sa.Text(),
        existing_nullable=False,
    )

    op.create_index(
        op.f("ix_parent_chunks_section_id"),
        "parent_chunks",
        ["section_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_parent_chunks_section_id_sections",
        "parent_chunks",
        "sections",
        ["section_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # parent_chunks
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_parent_chunks_section_id_sections",
        "parent_chunks",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_parent_chunks_section_id"),
        table_name="parent_chunks",
    )

    op.alter_column(
        "parent_chunks",
        "content",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(),
        existing_nullable=False,
    )

    op.drop_column(
        "parent_chunks",
        "updated_at",
    )

    op.drop_column(
        "parent_chunks",
        "created_at",
    )

    op.drop_column(
        "parent_chunks",
        "source_location",
    )

    op.drop_column(
        "parent_chunks",
        "contextual_summary",
    )

    op.drop_column(
        "parent_chunks",
        "content_hash",
    )

    op.drop_column(
        "parent_chunks",
        "section_id",
    )

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_documents_source_id_knowledge_sources",
        "documents",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_documents_source_id"),
        table_name="documents",
    )

    op.drop_index(
        op.f("ix_documents_classification"),
        table_name="documents",
    )

    op.drop_column(
        "documents",
        "updated_at",
    )

    op.drop_column(
        "documents",
        "access_policy",
    )

    op.drop_column(
        "documents",
        "classification",
    )

    op.drop_column(
        "documents",
        "source_id",
    )

    # ------------------------------------------------------------------
    # document_versions
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_document_versions_parent_version_id",
        "document_versions",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_document_versions_status"),
        table_name="document_versions",
    )

    op.drop_index(
        op.f("ix_document_versions_parent_version_id"),
        table_name="document_versions",
    )

    op.drop_column(
        "document_versions",
        "updated_at",
    )

    op.drop_column(
        "document_versions",
        "ingestion_timestamp",
    )

    op.drop_column(
        "document_versions",
        "embedding_version",
    )

    op.drop_column(
        "document_versions",
        "parser_version",
    )

    op.drop_column(
        "document_versions",
        "change_summary",
    )

    op.drop_column(
        "document_versions",
        "effective_until",
    )

    op.drop_column(
        "document_versions",
        "effective_from",
    )

    op.drop_column(
        "document_versions",
        "status",
    )

    op.drop_column(
        "document_versions",
        "parent_version_id",
    )

    # ------------------------------------------------------------------
    # chunks
    # ------------------------------------------------------------------

    op.drop_constraint(
        "fk_chunks_section_id_sections",
        "chunks",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_chunks_section_id"),
        table_name="chunks",
    )

    op.alter_column(
        "chunks",
        "content",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(),
        existing_nullable=False,
    )

    op.drop_column(
        "chunks",
        "updated_at",
    )

    op.drop_column(
        "chunks",
        "created_at",
    )

    op.drop_column(
        "chunks",
        "embedding_version",
    )

    op.drop_column(
        "chunks",
        "source_location",
    )

    op.drop_column(
        "chunks",
        "contextual_summary",
    )

    op.drop_column(
        "chunks",
        "content_hash",
    )

    op.drop_column(
        "chunks",
        "section_id",
    )

    # ------------------------------------------------------------------
    # new tables
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_sections_parent_section_id"),
        table_name="sections",
    )

    op.drop_index(
        op.f("ix_sections_document_version_id"),
        table_name="sections",
    )

    op.drop_table("sections")

    op.drop_index(
        op.f("ix_ingestion_jobs_tenant_id"),
        table_name="ingestion_jobs",
    )

    op.drop_index(
        op.f("ix_ingestion_jobs_status"),
        table_name="ingestion_jobs",
    )

    op.drop_index(
        op.f("ix_ingestion_jobs_document_version_id"),
        table_name="ingestion_jobs",
    )

    op.drop_index(
        op.f("ix_ingestion_jobs_document_id"),
        table_name="ingestion_jobs",
    )

    op.drop_table("ingestion_jobs")

    op.drop_index(
        op.f("ix_knowledge_sources_tenant_id"),
        table_name="knowledge_sources",
    )

    op.drop_table("knowledge_sources")