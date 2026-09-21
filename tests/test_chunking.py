import pytest

from sentineliq.ingestion.chunking import chunk_pages
from sentineliq.ingestion.pdf import ExtractedPage


def test_short_page_creates_one_chunk() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="SentinelIQ understands enterprise knowledge.",
        )
    ]

    chunks = chunk_pages(pages, chunk_size=100, overlap=20)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert chunks[0].content == pages[0].text


def test_long_page_creates_overlapping_chunks() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="A" * 250,
        )
    ]

    chunks = chunk_pages(pages, chunk_size=100, overlap=20)

    assert len(chunks) == 3
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == 100

    assert chunks[1].start_char == 80
    assert chunks[1].end_char == 180

    assert chunks[2].start_char == 160
    assert chunks[2].end_char == 250


def test_chunk_indexes_continue_across_pages() -> None:
    pages = [
        ExtractedPage(page_number=1, text="First page"),
        ExtractedPage(page_number=2, text="Second page"),
    ]

    chunks = chunk_pages(pages, chunk_size=100, overlap=20)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert [chunk.page_number for chunk in chunks] == [1, 2]


def test_invalid_overlap_is_rejected() -> None:
    pages = [ExtractedPage(page_number=1, text="text")]

    with pytest.raises(ValueError):
        chunk_pages(pages, chunk_size=100, overlap=100)
