import hashlib
from dataclasses import dataclass

from sentineliq.ingestion.pdf import ExtractedPage
from sentineliq.ingestion.structure import ParsedSection

PARENT_CHUNK_SIZE = 3000
PARENT_CHUNK_OVERLAP = 300

CHILD_CHUNK_SIZE = 900
CHILD_CHUNK_OVERLAP = 150

CHUNKER_VERSION = "hierarchical-v1"


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    page_number: int
    content: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class ParentTextChunk:
    parent_index: int
    section_index: int
    content: str
    content_hash: str
    page_number: int
    start_char: int | None
    end_char: int | None
    source_location: str


@dataclass(frozen=True, slots=True)
class ChildTextChunk:
    chunk_index: int
    parent_index: int
    section_index: int
    content: str
    content_hash: str
    page_number: int
    start_char: int | None
    end_char: int | None
    source_location: str


@dataclass(frozen=True, slots=True)
class HierarchicalChunks:
    parents: tuple[ParentTextChunk, ...]
    children: tuple[ChildTextChunk, ...]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_chunk_settings(
    chunk_size: int,
    overlap: int,
) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[TextChunk]:
    """
    Legacy baseline chunker.

    Kept temporarily so the existing baseline tests and
    before/after evaluation remain reproducible.
    """

    _validate_chunk_settings(
        chunk_size,
        overlap,
    )

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text
        start = 0

        while start < len(text):
            end = min(
                start + chunk_size,
                len(text),
            )

            content = text[start:end].strip()

            if content:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        page_number=(page.page_number),
                        content=content,
                        start_char=start,
                        end_char=end,
                    )
                )

                chunk_index += 1

            if end == len(text):
                break

            start = end - overlap

    return chunks


def _split_text(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
) -> list[tuple[str, int, int]]:
    _validate_chunk_settings(
        chunk_size,
        overlap,
    )

    if not text.strip():
        return []

    pieces: list[tuple[str, int, int]] = []

    start = 0
    text_length = len(text)

    while start < text_length:
        target_end = min(
            start + chunk_size,
            text_length,
        )

        end = target_end

        if target_end < text_length:
            search_start = max(
                start,
                target_end - 250,
            )

            newline_candidate = text.rfind(
                "\n",
                search_start,
                target_end,
            )

            sentence_candidate = text.rfind(
                ". ",
                search_start,
                target_end,
            )

            if newline_candidate > start:
                end = newline_candidate

            elif sentence_candidate > start:
                end = sentence_candidate + 1

        content = text[start:end].strip()

        if content:
            pieces.append(
                (
                    content,
                    start,
                    end,
                )
            )

        if end >= text_length:
            break

        next_start = end - overlap

        if next_start <= start:
            next_start = end

        start = next_start

    return pieces


def build_hierarchical_chunks(
    sections: list[ParsedSection],
    *,
    parent_size: int = PARENT_CHUNK_SIZE,
    parent_overlap: int = PARENT_CHUNK_OVERLAP,
    child_size: int = CHILD_CHUNK_SIZE,
    child_overlap: int = CHILD_CHUNK_OVERLAP,
) -> HierarchicalChunks:
    parents: list[ParentTextChunk] = []
    children: list[ChildTextChunk] = []

    parent_index = 0
    child_index = 0

    for section in sections:
        parent_pieces = _split_text(
            section.content,
            chunk_size=parent_size,
            overlap=parent_overlap,
        )

        for (
            parent_content,
            parent_start,
            parent_end,
        ) in parent_pieces:
            source_location = f"page={section.page_start};section={section.section_path}"

            parents.append(
                ParentTextChunk(
                    parent_index=parent_index,
                    section_index=(section.section_index),
                    content=parent_content,
                    content_hash=_hash_text(parent_content),
                    page_number=(section.page_start),
                    start_char=parent_start,
                    end_char=parent_end,
                    source_location=(source_location),
                )
            )

            child_pieces = _split_text(
                parent_content,
                chunk_size=child_size,
                overlap=child_overlap,
            )

            for (
                child_content,
                child_start,
                child_end,
            ) in child_pieces:
                children.append(
                    ChildTextChunk(
                        chunk_index=(child_index),
                        parent_index=(parent_index),
                        section_index=(section.section_index),
                        content=(child_content),
                        content_hash=(_hash_text(child_content)),
                        page_number=(section.page_start),
                        start_char=(parent_start + child_start),
                        end_char=(parent_start + child_end),
                        source_location=(source_location),
                    )
                )

                child_index += 1

            parent_index += 1

    return HierarchicalChunks(
        parents=tuple(parents),
        children=tuple(children),
    )
