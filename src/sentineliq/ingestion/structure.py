import hashlib
import re
from dataclasses import dataclass

from sentineliq.ingestion.pdf import ExtractedPage


@dataclass(frozen=True, slots=True)
class ParsedSection:
    section_index: int
    level: int
    title: str | None
    section_path: str
    content: str
    content_hash: str
    page_start: int
    page_end: int
    start_char: int | None
    end_char: int | None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_line(line: str) -> str:
    return " ".join(line.strip().split())


def _heading_level(line: str) -> int | None:
    stripped = line.strip()

    if not stripped:
        return None

    markdown = re.match(
        r"^(#{1,6})\s+(.+)$",
        stripped,
    )

    if markdown:
        return len(markdown.group(1))

    numbered = re.match(
        r"^(\d+(?:\.\d+)*)[\.\)]?\s+(.+)$",
        stripped,
    )

    if numbered:
        return min(
            numbered.group(1).count(".") + 1,
            6,
        )

    if len(stripped) > 120:
        return None

    words = stripped.split()

    if not 1 <= len(words) <= 14:
        return None

    if stripped.endswith((".", ",", ";", "?", "!")):
        return None

    letters = [char for char in stripped if char.isalpha()]

    if letters and stripped.upper() == stripped and len(words) <= 10:
        return 1

    if stripped.istitle():
        return 2

    return None


def _strip_heading_markup(
    line: str,
) -> str:
    line = re.sub(
        r"^#{1,6}\s+",
        "",
        line,
    )

    return line.strip()


def extract_sections(
    pages: list[ExtractedPage],
) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    section_index = 0

    heading_stack: list[str] = []

    for page in pages:
        raw_text = page.text

        if not raw_text.strip():
            continue

        lines = raw_text.splitlines()

        current_title: str | None = None
        current_level = 1
        current_lines: list[str] = []
        current_start: int | None = None

        cursor = 0

        def flush_section(
            end_char: int,
        ) -> None:
            nonlocal section_index
            nonlocal current_lines
            nonlocal current_start

            content = "\n".join(line for line in current_lines if line.strip()).strip()

            if not content:
                current_lines = []
                current_start = None
                return

            if current_title is None:
                path = " > ".join(heading_stack) if heading_stack else f"Page {page.page_number}"
            else:
                path = " > ".join(heading_stack) if heading_stack else current_title

            sections.append(
                ParsedSection(
                    section_index=section_index,
                    level=current_level,
                    title=current_title,
                    section_path=path,
                    content=content,
                    content_hash=_hash_text(content),
                    page_start=page.page_number,
                    page_end=page.page_number,
                    start_char=current_start,
                    end_char=end_char,
                )
            )

            section_index += 1
            current_lines = []
            current_start = None

        for raw_line in lines:
            line_start = cursor
            cursor += len(raw_line) + 1

            cleaned = _clean_line(raw_line)

            if not cleaned:
                continue

            level = _heading_level(cleaned)

            if level is not None:
                flush_section(line_start)

                title = _strip_heading_markup(cleaned)

                current_title = title
                current_level = level
                current_start = line_start

                while len(heading_stack) >= level:
                    heading_stack.pop()

                heading_stack.append(title)

                continue

            if current_start is None:
                current_start = line_start

            current_lines.append(cleaned)

        flush_section(len(raw_text))

    return sections
