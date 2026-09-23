import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from sentineliq.ingestion.ocr import (
    extract_pdf_with_ocr,
    needs_ocr,
)
from sentineliq.ingestion.pdf import (
    ExtractedPage,
    extract_pdf,
)
from sentineliq.ingestion.tables import (
    append_tables_to_text,
    extract_pdf_tables,
)


@dataclass(frozen=True, slots=True)
class ParsedSource:
    pages: tuple[ExtractedPage, ...]
    content_hash: str
    mime_type: str
    parser_version: str
    used_ocr: bool = False


def _sha256_file(
    file_path: Path,
) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _parse_pdf(
    file_path: Path,
) -> ParsedSource:
    extracted = extract_pdf(
        file_path
    )

    pages: tuple[
        ExtractedPage,
        ...,
    ]

    used_ocr = False

    if needs_ocr(
        extracted.pages
    ):
        ocr_result = (
            extract_pdf_with_ocr(
                file_path
            )
        )

        pages = ocr_result.pages
        used_ocr = True

    else:
        pages = tuple(
            extracted.pages
        )

    tables = extract_pdf_tables(
        file_path
    )

    enriched_pages = tuple(
        ExtractedPage(
            page_number=page.page_number,
            text=append_tables_to_text(
                page_number=(
                    page.page_number
                ),
                text=page.text,
                tables=tables,
            ),
        )
        for page in pages
    )

    if not any(
        page.text.strip()
        for page in enriched_pages
    ):
        raise ValueError(
            "PDF produced no extractable text"
        )

    parser_version = (
        "pdf-pymupdf-ocr-v2"
        if used_ocr
        else "pdf-pymupdf-v2"
    )

    return ParsedSource(
        pages=enriched_pages,
        content_hash=(
            extracted.content_hash
        ),
        mime_type="application/pdf",
        parser_version=(
            parser_version
        ),
        used_ocr=used_ocr,
    )


def _parse_markdown(
    file_path: Path,
) -> ParsedSource:
    text = file_path.read_text(
        encoding="utf-8"
    )

    if not text.strip():
        raise ValueError(
            "Markdown file contains no text"
        )

    return ParsedSource(
        pages=(
            ExtractedPage(
                page_number=1,
                text=text,
            ),
        ),
        content_hash=_sha256_file(
            file_path
        ),
        mime_type="text/markdown",
        parser_version="markdown-v1",
    )


def _extract_docx_table(
    table: ElementTree.Element,
    namespace: dict[str, str],
) -> str:
    rows: list[list[str]] = []

    for row in table.findall(
        ".//w:tr",
        namespace,
    ):
        cells: list[str] = []

        for cell in row.findall(
            "./w:tc",
            namespace,
        ):
            text = " ".join(
                node.text or ""
                for node in cell.findall(
                    ".//w:t",
                    namespace,
                )
            ).strip()

            cells.append(text)

        if cells:
            rows.append(cells)

    if not rows:
        return ""

    width = max(
        len(row)
        for row in rows
    )

    rows = [
        row + [""] * (
            width - len(row)
        )
        for row in rows
    ]

    lines = [
        "| "
        + " | ".join(rows[0])
        + " |",
        "| "
        + " | ".join(
            ["---"] * width
        )
        + " |",
    ]

    for row in rows[1:]:
        lines.append(
            "| "
            + " | ".join(row)
            + " |"
        )

    return "\n".join(lines)


def _parse_docx(
    file_path: Path,
) -> ParsedSource:
    try:
        with zipfile.ZipFile(
            file_path
        ) as archive:
            xml = archive.read(
                "word/document.xml"
            )

    except (
        zipfile.BadZipFile,
        KeyError,
    ) as exc:
        raise ValueError(
            "Malformed DOCX document"
        ) from exc

    root = ElementTree.fromstring(
        xml
    )

    namespace = {
        "w": (
            "http://schemas.openxmlformats.org/"
            "wordprocessingml/2006/main"
        )
    }

    blocks: list[str] = []

    body = root.find(
        ".//w:body",
        namespace,
    )

    if body is None:
        raise ValueError(
            "DOCX contains no body"
        )

    paragraph_tag = (
        "{"
        + namespace["w"]
        + "}p"
    )

    table_tag = (
        "{"
        + namespace["w"]
        + "}tbl"
    )

    for child in body:
        if child.tag == paragraph_tag:
            text = "".join(
                node.text or ""
                for node in child.findall(
                    ".//w:t",
                    namespace,
                )
            ).strip()

            if text:
                blocks.append(text)

        elif child.tag == table_tag:
            table_text = (
                _extract_docx_table(
                    child,
                    namespace,
                )
            )

            if table_text:
                blocks.append(
                    "\n".join(
                        [
                            "[TABLE]",
                            table_text,
                            "[/TABLE]",
                        ]
                    )
                )

    document_text = "\n".join(
        blocks
    ).strip()

    if not document_text:
        raise ValueError(
            "DOCX produced no text"
        )

    return ParsedSource(
        pages=(
            ExtractedPage(
                page_number=1,
                text=document_text,
            ),
        ),
        content_hash=_sha256_file(
            file_path
        ),
        mime_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        parser_version="docx-xml-v2",
    )


def parse_source(
    file_path: Path,
) -> ParsedSource:
    extension = (
        file_path.suffix.lower()
    )

    if extension == ".pdf":
        return _parse_pdf(
            file_path
        )

    if extension in {
        ".md",
        ".markdown",
    }:
        return _parse_markdown(
            file_path
        )

    if extension == ".docx":
        return _parse_docx(
            file_path
        )

    raise ValueError(
        f"No parser registered for "
        f"{extension}"
    )