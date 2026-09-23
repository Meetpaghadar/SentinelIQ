from pathlib import Path

import pytest

from sentineliq.ingestion.retry import (
    RetryExhaustedError,
    retry_call,
)
from sentineliq.ingestion.security import (
    IngestionSecurityError,
    scan_ingestion_file,
)


def test_rejects_unsupported_extension(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "test.exe"

    file_path.write_bytes(b"not allowed")

    with pytest.raises(IngestionSecurityError):
        scan_ingestion_file(file_path)


def test_rejects_fake_pdf(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "fake.pdf"

    file_path.write_bytes(b"not really a pdf")

    with pytest.raises(IngestionSecurityError):
        scan_ingestion_file(file_path)


def test_accepts_markdown(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "test.md"

    file_path.write_text(
        "# Policy\nUse MFA.",
        encoding="utf-8",
    )

    result = scan_ingestion_file(file_path)

    assert result.mime_type == "text/markdown"


def test_retry_succeeds_after_transient_failures() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts

        attempts += 1

        if attempts < 3:
            raise OSError("temporary")

        return "ok"

    result, failures = retry_call(
        operation,
        attempts=3,
        initial_delay_seconds=0,
    )

    assert result == "ok"
    assert failures == 2


def test_retry_exhaustion() -> None:
    def operation() -> str:
        raise OSError("temporary")

    with pytest.raises(RetryExhaustedError):
        retry_call(
            operation,
            attempts=2,
            initial_delay_seconds=0,
        )
    
from sentineliq.ingestion.ocr import needs_ocr
from sentineliq.ingestion.pdf import ExtractedPage
from sentineliq.ingestion.tables import (
    _markdown_table,
)


def test_detects_pdf_that_needs_ocr() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="",
        ),
        ExtractedPage(
            page_number=2,
            text=" ",
        ),
    ]

    assert needs_ocr(pages)


def test_text_pdf_does_not_need_ocr() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "This PDF already contains "
                "extractable document text."
            ),
        )
    ]

    assert not needs_ocr(pages)


def test_table_is_preserved_as_markdown() -> None:
    table = _markdown_table(
        [
            [
                "Control",
                "Status",
            ],
            [
                "MFA",
                "Required",
            ],
            [
                "Encryption",
                "Enabled",
            ],
        ]
    )

    assert "| Control | Status |" in table
    assert "| MFA | Required |" in table
    assert (
        "| Encryption | Enabled |"
        in table
    )
