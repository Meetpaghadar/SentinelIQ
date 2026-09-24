from uuid import uuid4

from sentineliq.retrieval.models import (
    RetrievalResult,
)
from sentineliq.retrieval.sparse import (
    SparseDocument,
    _bm25_scores,
    _tokenize,
)


def _document(
    text: str,
) -> SparseDocument:
    result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="test",
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content=text,
        similarity=0.0,
    )

    return SparseDocument(
        result=result,
        tokens=tuple(_tokenize(text)),
    )


def test_bm25_prefers_matching_document() -> None:
    documents = [
        _document("machine learning model training"),
        _document("terraform vpc aws networking"),
    ]

    scores = _bm25_scores(
        query="machine learning",
        documents=documents,
    )

    assert scores[0] > scores[1]


def test_bm25_returns_zero_for_no_match() -> None:
    documents = [_document("machine learning")]

    scores = _bm25_scores(
        query="terraform",
        documents=documents,
    )

    assert scores == [0.0]


def test_tokenizer_is_case_insensitive() -> None:
    assert _tokenize("Machine LEARNING") == [
        "machine",
        "learning",
    ]
