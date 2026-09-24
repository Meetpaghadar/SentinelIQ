from dataclasses import dataclass, replace
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version_id: UUID
    version_number: int
    page_number: int | None
    content: str
    similarity: float

    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None

    dense_rank: int | None = None
    sparse_rank: int | None = None

    retrieval_method: str = "unknown"

    def with_updates(
        self,
        **changes: object,
    ) -> "RetrievalResult":
        return replace(
            self,
            **changes,
        )
