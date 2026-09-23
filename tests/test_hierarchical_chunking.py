from sentineliq.ingestion.chunking import (
    build_hierarchical_chunks,
)
from sentineliq.ingestion.pdf import (
    ExtractedPage,
)
from sentineliq.ingestion.structure import (
    extract_sections,
)


def test_extracts_numbered_sections() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "1 Authentication\n"
                "Employees must use MFA.\n"
                "\n"
                "1.1 Password Policy\n"
                "Passwords must be strong."
            ),
        )
    ]

    sections = extract_sections(pages)

    assert len(sections) == 2

    assert sections[0].title == ("1 Authentication")

    assert sections[0].level == 1

    assert sections[1].level == 2

    assert "Authentication" in sections[1].section_path


def test_section_has_content_hash() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=("Security Policy\nEmployees must use MFA."),
        )
    ]

    sections = extract_sections(pages)

    assert sections
    assert len(sections[0].content_hash) == 64


def test_builds_parent_child_hierarchy() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "Authentication\n" + ("Employees must use secure authentication methods. " * 100)
            ),
        )
    ]

    sections = extract_sections(pages)

    hierarchy = build_hierarchical_chunks(sections)

    assert hierarchy.parents
    assert hierarchy.children

    parent_ids = {parent.parent_index for parent in hierarchy.parents}

    assert all(child.parent_index in parent_ids for child in hierarchy.children)


def test_child_chunk_is_smaller_than_parent() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=("Authentication\n" + ("security policy " * 300)),
        )
    ]

    hierarchy = build_hierarchical_chunks(extract_sections(pages))

    assert hierarchy.parents
    assert hierarchy.children

    assert max(len(child.content) for child in hierarchy.children) <= 900


def test_source_location_contains_section() -> None:
    pages = [
        ExtractedPage(
            page_number=3,
            text=("Password Policy\nPasswords must be rotated."),
        )
    ]

    hierarchy = build_hierarchical_chunks(extract_sections(pages))

    child = hierarchy.children[0]

    assert "page=3" in child.source_location
    assert "section=" in child.source_location
