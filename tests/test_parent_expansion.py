from uuid import uuid4

from sentineliq.retrieval.models import (
    RetrievalResult,
)


def test_retrieval_result_supports_parent_method() -> None:
    result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Policy",
        document_version_id=uuid4(),
        version_number=1,
        page_number=1,
        content="child",
        similarity=0.8,
        retrieval_method=("dense+bm25+parent"),
    )

    assert result.retrieval_method == "dense+bm25+parent"
