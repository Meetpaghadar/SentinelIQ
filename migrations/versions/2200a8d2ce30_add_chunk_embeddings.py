"""add chunk embeddings

Revision ID: 2200a8d2ce30
Revises: 0a4efff5754e
Create Date: 2026-09-21 17:13:19.278479
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "2200a8d2ce30"
down_revision: str | Sequence[str] | None = "0a4efff5754e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chunks", "embedding")
