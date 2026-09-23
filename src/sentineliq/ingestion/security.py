from dataclasses import dataclass
from pathlib import Path

MAX_INGESTION_FILE_SIZE_BYTES = 50 * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".md",
    ".markdown",
    ".docx",
}


class IngestionSecurityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SecurityScanResult:
    extension: str
    size_bytes: int
    mime_type: str


def _detect_mime_type(
    file_path: Path,
    header: bytes,
) -> str:
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        if not header.startswith(b"%PDF"):
            raise IngestionSecurityError(
                "File extension is PDF but the file signature is not a valid PDF signature"
            )

        return "application/pdf"

    if extension == ".docx":
        if not header.startswith(b"PK"):
            raise IngestionSecurityError(
                "File extension is DOCX but the file is not a valid ZIP-based Office document"
            )

        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if extension in {".md", ".markdown"}:
        return "text/markdown"

    raise IngestionSecurityError(f"Unsupported file extension: {extension}")


def scan_ingestion_file(
    file_path: Path,
    *,
    max_size_bytes: int = MAX_INGESTION_FILE_SIZE_BYTES,
) -> SecurityScanResult:
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise IngestionSecurityError(f"Unsupported file type: {extension or '<none>'}")

    size_bytes = file_path.stat().st_size

    if size_bytes <= 0:
        raise IngestionSecurityError("File is empty")

    if size_bytes > max_size_bytes:
        raise IngestionSecurityError(f"File exceeds ingestion size limit of {max_size_bytes} bytes")

    with file_path.open("rb") as handle:
        header = handle.read(8)

    mime_type = _detect_mime_type(
        file_path,
        header,
    )

    if extension in {".md", ".markdown"}:
        try:
            file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise IngestionSecurityError("Markdown file is not valid UTF-8") from exc

    return SecurityScanResult(
        extension=extension,
        size_bytes=size_bytes,
        mime_type=mime_type,
    )
