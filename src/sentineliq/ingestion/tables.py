from pathlib import Path

import fitz


def _cell_text(
    value: object,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def _markdown_table(
    rows: list[list[object]],
) -> str:
    if not rows:
        return ""

    normalized = [
        [
            _cell_text(cell)
            for cell in row
        ]
        for row in rows
    ]

    width = max(
        len(row)
        for row in normalized
    )

    if width == 0:
        return ""

    padded = [
        row
        + [""] * (
            width - len(row)
        )
        for row in normalized
    ]

    header = padded[0]

    lines = [
        "| "
        + " | ".join(header)
        + " |",
        "| "
        + " | ".join(
            ["---"] * width
        )
        + " |",
    ]

    for row in padded[1:]:
        lines.append(
            "| "
            + " | ".join(row)
            + " |"
        )

    return "\n".join(lines)


def extract_pdf_tables(
    file_path: Path,
) -> dict[int, list[str]]:
    results: dict[
        int,
        list[str],
    ] = {}

    document = fitz.open(file_path)

    try:
        for page_index in range(
            len(document)
        ):
            page = document.load_page(
                page_index
            )

            find_tables = getattr(
                page,
                "find_tables",
                None,
            )

            if find_tables is None:
                continue

            try:
                finder = find_tables()
            except Exception:
                continue

            extracted_tables: list[str] = []

            for table in finder.tables:
                try:
                    rows = table.extract()
                except Exception:
                    continue

                markdown = _markdown_table(
                    rows
                )

                if markdown:
                    extracted_tables.append(
                        markdown
                    )

            if extracted_tables:
                results[
                    page_index + 1
                ] = extracted_tables

    finally:
        document.close()

    return results


def append_tables_to_text(
    *,
    page_number: int,
    text: str,
    tables: dict[int, list[str]],
) -> str:
    page_tables = tables.get(
        page_number,
        [],
    )

    if not page_tables:
        return text

    table_blocks: list[str] = []

    for index, table in enumerate(
        page_tables,
        start=1,
    ):
        table_blocks.append(
            "\n".join(
                [
                    f"[TABLE {index}]",
                    table,
                    f"[/TABLE {index}]",
                ]
            )
        )

    return (
        text.rstrip()
        + "\n\n"
        + "\n\n".join(
            table_blocks
        )
    )