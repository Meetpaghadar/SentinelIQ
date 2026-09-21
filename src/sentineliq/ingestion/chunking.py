from dataclasses import dataclass

from sentineliq.ingestion.pdf import ExtractedPage


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int
    content: str
    start_char: int
    end_char: int


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            content = text[start:end].strip()

            if content:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        page_number=page.page_number,
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
