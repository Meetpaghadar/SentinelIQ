from dataclasses import dataclass
from pathlib import Path
from typing import cast

import fitz

from sentineliq.ingestion.pdf import ExtractedPage

MIN_NATIVE_TEXT_CHARACTERS = 20


class OCRUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OCRResult:
    pages: tuple[ExtractedPage, ...]
    used_ocr: bool


def needs_ocr(
    pages: list[ExtractedPage] | tuple[ExtractedPage, ...],
) -> bool:
    total_text = sum(len(page.text.strip()) for page in pages)

    return total_text < MIN_NATIVE_TEXT_CHARACTERS


def _get_text(
    page: fitz.Page,
    *,
    textpage: fitz.TextPage | None = None,
) -> str:
    result = page.get_text(
        "text",
        textpage=textpage,
    )

    return cast(
        str,
        result,
    ).strip()


def extract_pdf_with_ocr(
    file_path: Path,
) -> OCRResult:
    pages: list[ExtractedPage] = []

    document: fitz.Document | None = None

    try:
        document = fitz.open(file_path)

        for index in range(len(document)):
            page = document.load_page(index)

            native_text = _get_text(page)

            if len(native_text) >= MIN_NATIVE_TEXT_CHARACTERS:
                text = native_text

            else:
                try:
                    text_page = page.get_textpage_ocr(
                        language="eng",
                        dpi=150,
                        full=True,
                    )

                    text = _get_text(
                        page,
                        textpage=text_page,
                    )

                except Exception as exc:
                    raise OCRUnavailableError(
                        "PDF appears to require OCR, "
                        "but OCR could not run. "
                        "Ensure Tesseract OCR is "
                        "installed and available "
                        "to PyMuPDF."
                    ) from exc

            pages.append(
                ExtractedPage(
                    page_number=index + 1,
                    text=text,
                )
            )

    except OCRUnavailableError:
        raise

    except Exception as exc:
        raise ValueError(f"Unable to OCR PDF: {file_path}") from exc

    finally:
        if document is not None:
            document.close()

    if not any(page.text.strip() for page in pages):
        raise ValueError("OCR produced no text")

    return OCRResult(
        pages=tuple(pages),
        used_ocr=True,
    )
