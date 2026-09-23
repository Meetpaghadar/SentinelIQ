from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from sentineliq.contracts import (
    EmbeddingProvider,
)
from sentineliq.ingestion.chunking import (
    CHUNKER_VERSION,
    build_hierarchical_chunks,
)
from sentineliq.ingestion.parsers import (
    parse_source,
)
from sentineliq.ingestion.structure import (
    extract_sections,
)
from sentineliq.models import (
    Chunk,
    DocumentVersion,
    ParentChunk,
    Section,
)

EMBEDDING_VERSION = (
    "text-embedding-3-small-v1"
)

EMBEDDING_BATCH_SIZE = 64


@dataclass(frozen=True, slots=True)
class ReprocessingResult:
    document_version_id: UUID

    section_count: int
    parent_chunk_count: int
    child_chunk_count: int

    embedding_count: int
    reused_embedding_count: int
    generated_embedding_count: int

    changed_section_count: int
    unchanged_section_count: int

    parser_version: str
    chunker_version: str
    embedding_version: str


def _contextual_summary(
    *,
    document_title: str,
    section_path: str,
) -> str:
    return (
        f"Document: {document_title}. "
        f"Section: {section_path}."
    )


def _embedding_text(
    *,
    contextual_summary: str,
    content: str,
) -> str:
    return (
        f"{contextual_summary}\n\n"
        f"{content}"
    )


def _embed_in_batches(
    embedding_provider: EmbeddingProvider,
    texts: list[str],
) -> list[list[float]]:
    embeddings: list[
        list[float]
    ] = []

    for start in range(
        0,
        len(texts),
        EMBEDDING_BATCH_SIZE,
    ):
        batch = texts[
            start
            : start
            + EMBEDDING_BATCH_SIZE
        ]

        embeddings.extend(
            embedding_provider.embed_documents(
                batch
            )
        )

    if len(embeddings) != len(
        texts
    ):
        raise RuntimeError(
            "Embedding provider returned an "
            "unexpected number of embeddings"
        )

    return embeddings


def reprocess_document_version(
    session: Session,
    *,
    document_version_id: UUID,
    embedding_provider: EmbeddingProvider,
) -> ReprocessingResult:
    version = session.get(
        DocumentVersion,
        document_version_id,
    )

    if version is None:
        raise ValueError(
            f"Document version not found: "
            f"{document_version_id}"
        )

    document = version.document

    file_path = Path(
        version.storage_path
    )

    if not file_path.is_file():
        raise FileNotFoundError(
            file_path
        )

    parsed = parse_source(
        file_path
    )

    if (
        parsed.content_hash
        != version.content_hash
    ):
        raise ValueError(
            "Source content changed. "
            "A changed source requires a new "
            "DocumentVersion."
        )

    parsed_sections = (
        extract_sections(
            list(parsed.pages)
        )
    )

    if not parsed_sections:
        raise ValueError(
            "Document produced no sections"
        )

    hierarchy = (
        build_hierarchical_chunks(
            parsed_sections
        )
    )

    if not hierarchy.parents:
        raise ValueError(
            "Document produced no parent chunks"
        )

    if not hierarchy.children:
        raise ValueError(
            "Document produced no child chunks"
        )

    existing_sections = list(
        session.scalars(
            select(Section).where(
                Section.document_version_id
                == version.id
            )
        )
    )

    old_section_hashes = {
        (
            section.section_path,
            section.content_hash,
        )
        for section in existing_sections
    }

    new_section_hashes = {
        (
            section.section_path,
            section.content_hash,
        )
        for section in parsed_sections
    }

    unchanged_sections = (
        old_section_hashes
        & new_section_hashes
    )

    changed_section_count = len(
        new_section_hashes
        - unchanged_sections
    )

    unchanged_section_count = len(
        unchanged_sections
    )

    existing_chunks = list(
        session.scalars(
            select(Chunk).where(
                Chunk.document_version_id
                == version.id,
                Chunk.embedding.is_not(
                    None
                ),
            )
        )
    )

    reusable_embeddings: dict[
        str,
        list[float],
    ] = {}

    for chunk in existing_chunks:
        if (
            chunk.content_hash
            and chunk.embedding
            is not None
            and chunk.embedding_version
            == EMBEDDING_VERSION
        ):
            reusable_embeddings[
                chunk.content_hash
            ] = list(
                chunk.embedding
            )

    session.execute(
        delete(Chunk).where(
            Chunk.document_version_id
            == version.id
        )
    )

    session.execute(
        delete(ParentChunk).where(
            ParentChunk.document_version_id
            == version.id
        )
    )

    session.execute(
        delete(Section).where(
            Section.document_version_id
            == version.id
        )
    )

    session.flush()

    section_models: dict[
        int,
        Section,
    ] = {}

    section_stack: dict[
        int,
        Section,
    ] = {}

    for parsed_section in (
        parsed_sections
    ):
        parent_section: (
            Section | None
        ) = None

        parent_levels = [
            level
            for level in section_stack
            if level
            < parsed_section.level
        ]

        if parent_levels:
            parent_section = (
                section_stack[
                    max(
                        parent_levels
                    )
                ]
            )

        section = Section(
            document_version_id=(
                version.id
            ),
            parent_section_id=(
                parent_section.id
                if parent_section
                else None
            ),
            section_index=(
                parsed_section.section_index
            ),
            level=(
                parsed_section.level
            ),
            title=(
                parsed_section.title
            ),
            section_path=(
                parsed_section.section_path
            ),
            content=(
                parsed_section.content
            ),
            content_hash=(
                parsed_section.content_hash
            ),
            page_start=(
                parsed_section.page_start
            ),
            page_end=(
                parsed_section.page_end
            ),
            start_char=(
                parsed_section.start_char
            ),
            end_char=(
                parsed_section.end_char
            ),
        )

        session.add(
            section
        )
        session.flush()

        section_models[
            parsed_section.section_index
        ] = section

        section_stack[
            parsed_section.level
        ] = section

        stale_levels = [
            level
            for level in section_stack
            if level
            > parsed_section.level
        ]

        for level in stale_levels:
            del section_stack[
                level
            ]

    parent_models: dict[
        int,
        ParentChunk,
    ] = {}

    for item in (
        hierarchy.parents
    ):
        section = (
            section_models[
                item.section_index
            ]
        )

        contextual_summary = (
            _contextual_summary(
                document_title=(
                    document.title
                ),
                section_path=(
                    section.section_path
                    or "Unknown section"
                ),
            )
        )

        parent = ParentChunk(
            document_version_id=(
                version.id
            ),
            section_id=(
                section.id
            ),
            parent_index=(
                item.parent_index
            ),
            content=item.content,
            content_hash=(
                item.content_hash
            ),
            contextual_summary=(
                contextual_summary
            ),
            source_location=(
                item.source_location
            ),
            page_number=(
                item.page_number
            ),
            start_char=(
                item.start_char
            ),
            end_char=(
                item.end_char
            ),
        )

        session.add(
            parent
        )
        session.flush()

        parent_models[
            item.parent_index
        ] = parent

    chunk_models: list[
        Chunk
    ] = []

    pending_embedding_chunks: list[
        Chunk
    ] = []

    pending_embedding_inputs: list[
        str
    ] = []

    reused_count = 0

    for item in (
        hierarchy.children
    ):
        section = (
            section_models[
                item.section_index
            ]
        )

        parent = (
            parent_models[
                item.parent_index
            ]
        )

        contextual_summary = (
            _contextual_summary(
                document_title=(
                    document.title
                ),
                section_path=(
                    section.section_path
                    or "Unknown section"
                ),
            )
        )

        reusable = (
            reusable_embeddings.get(
                item.content_hash
            )
        )

        chunk = Chunk(
            document_version_id=(
                version.id
            ),
            section_id=(
                section.id
            ),
            parent_chunk_id=(
                parent.id
            ),
            chunk_index=(
                item.chunk_index
            ),
            content=item.content,
            content_hash=(
                item.content_hash
            ),
            contextual_summary=(
                contextual_summary
            ),
            source_location=(
                item.source_location
            ),
            embedding=(
                reusable
            ),
            embedding_version=(
                EMBEDDING_VERSION
                if reusable is not None
                else None
            ),
            page_number=(
                item.page_number
            ),
            start_char=(
                item.start_char
            ),
            end_char=(
                item.end_char
            ),
        )

        chunk_models.append(
            chunk
        )

        if reusable is not None:
            reused_count += 1

        else:
            pending_embedding_chunks.append(
                chunk
            )

            pending_embedding_inputs.append(
                _embedding_text(
                    contextual_summary=(
                        contextual_summary
                    ),
                    content=(
                        item.content
                    ),
                )
            )

    generated_embeddings = (
        _embed_in_batches(
            embedding_provider,
            pending_embedding_inputs,
        )
        if pending_embedding_inputs
        else []
    )

    for chunk, embedding in zip(
        pending_embedding_chunks,
        generated_embeddings,
        strict=True,
    ):
        chunk.embedding = (
            embedding
        )

        chunk.embedding_version = (
            EMBEDDING_VERSION
        )

    session.add_all(
        chunk_models
    )

    version.parser_version = (
        parsed.parser_version
    )

    version.embedding_version = (
        EMBEDDING_VERSION
    )

    session.commit()

    total_embeddings = len(
        chunk_models
    )

    return ReprocessingResult(
        document_version_id=(
            version.id
        ),
        section_count=len(
            parsed_sections
        ),
        parent_chunk_count=len(
            hierarchy.parents
        ),
        child_chunk_count=len(
            hierarchy.children
        ),
        embedding_count=(
            total_embeddings
        ),
        reused_embedding_count=(
            reused_count
        ),
        generated_embedding_count=len(
            generated_embeddings
        ),
        changed_section_count=(
            changed_section_count
        ),
        unchanged_section_count=(
            unchanged_section_count
        ),
        parser_version=(
            parsed.parser_version
        ),
        chunker_version=(
            CHUNKER_VERSION
        ),
        embedding_version=(
            EMBEDDING_VERSION
        ),
    )