import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pymupdf


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedPdf:
    content_hash: str
    pages: list[ExtractedPage]


def extract_pdf(file_path: Path) -> ExtractedPdf:
    file_bytes = file_path.read_bytes()
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    pages: list[ExtractedPage] = []

    with pymupdf.open(file_path) as pdf:
        for index in range(pdf.page_count):
            page = pdf.load_page(index)
            text = cast(str, page.get_text("text"))
            text = text.replace("\x00", "").strip()

            if not text:
                continue

            pages.append(
                ExtractedPage(
                    page_number=index + 1,
                    text=text,
                )
            )

    if not pages:
        raise ValueError("PDF contains no extractable text")

    return ExtractedPdf(
        content_hash=content_hash,
        pages=pages,
    )
