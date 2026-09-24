from uuid import uuid4

from sentineliq.rag.context import (
    ContextAssembler,
)
from sentineliq.retrieval.models import (
    RetrievalResult,
)


def _result(
    content: str,
    *,
    title: str,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content=content,
        similarity=0.9,
        retrieval_method="dense+bm25+parent",
    )


def test_all_results_are_preserved() -> None:
    assembler = ContextAssembler()

    context = assembler.assemble(
        [
            _result(
                "Employees must use MFA.",
                title="Policy A",
            ),
            _result(
                "Employees must use MFA.",
                title="Policy B",
            ),
        ]
    )

    assert len(context.items) == 2

    assert (
        context.items[0].result.document_title
        == "Policy A"
    )

    assert (
        context.items[1].result.document_title
        == "Policy B"
    )


def test_context_numbers_are_stable() -> None:
    assembler = ContextAssembler()

    context = assembler.assemble(
        [
            _result(
                "First evidence.",
                title="A",
            ),
            _result(
                "Second evidence.",
                title="B",
            ),
        ]
    )

    assert context.items[0].number == 1
    assert context.items[1].number == 2

    assert "[1]" in context.text
    assert "[2]" in context.text


def test_empty_results_produce_empty_context() -> None:
    assembler = ContextAssembler()

    context = assembler.assemble([])

    assert context.text == ""
    assert context.items == ()