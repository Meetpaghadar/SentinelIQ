from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    ParentChunk,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


class ParentExpander:
    def expand(
        self,
        session: Session,
        *,
        children: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if not children:
            return []

        child_ids = [child.chunk_id for child in children]

        statement = (
            select(
                Chunk.id.label("chunk_id"),
                ParentChunk.id.label("parent_id"),
                ParentChunk.content.label("parent_content"),
                ParentChunk.page_number.label("parent_page_number"),
                Document.id.label("document_id"),
                Document.title.label("document_title"),
                DocumentVersion.id.label("document_version_id"),
                DocumentVersion.version_number.label("version_number"),
            )
            .join(
                ParentChunk,
                Chunk.parent_chunk_id == ParentChunk.id,
            )
            .join(
                DocumentVersion,
                Chunk.document_version_id == DocumentVersion.id,
            )
            .join(
                Document,
                DocumentVersion.document_id == Document.id,
            )
            .where(Chunk.id.in_(child_ids))
        )

        rows = session.execute(statement).mappings().all()

        rows_by_chunk: dict[
            UUID,
            Any,
        ] = {row["chunk_id"]: row for row in rows}

        seen_parent_ids: set[UUID] = set()

        expanded: list[RetrievalResult] = []

        for child in children:
            row = rows_by_chunk.get(child.chunk_id)

            if row is None:
                expanded.append(child)
                continue

            parent_id = row["parent_id"]

            if parent_id is None:
                expanded.append(child)
                continue

            if parent_id in seen_parent_ids:
                continue

            seen_parent_ids.add(parent_id)

            expanded.append(
                RetrievalResult(
                    chunk_id=(child.chunk_id),
                    document_id=(row["document_id"]),
                    document_title=(row["document_title"]),
                    document_version_id=(row["document_version_id"]),
                    version_number=(row["version_number"]),
                    page_number=(row["parent_page_number"]),
                    content=(row["parent_content"]),
                    similarity=(child.similarity),
                    dense_score=(child.dense_score),
                    sparse_score=(child.sparse_score),
                    fusion_score=(child.fusion_score),
                    dense_rank=(child.dense_rank),
                    sparse_rank=(child.sparse_rank),
                    retrieval_method=(f"{child.retrieval_method}+parent"),
                )
            )

        return expanded
