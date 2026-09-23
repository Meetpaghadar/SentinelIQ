from sentineliq.ingestion.reprocessing import (
    _contextual_summary,
    _embedding_text,
)


def test_contextual_summary_contains_document() -> None:
    summary = _contextual_summary(
        document_title="Security Policy",
        section_path=("Authentication > Passwords"),
    )

    assert "Security Policy" in summary

    assert "Authentication > Passwords" in summary


def test_embedding_text_preserves_source_content() -> None:
    contextual_summary = "Document: Security Policy. Section: Authentication."

    content = "Employees must use MFA."

    text = _embedding_text(
        contextual_summary=(contextual_summary),
        content=content,
    )

    assert contextual_summary in text
    assert content in text
