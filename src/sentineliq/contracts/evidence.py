from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from sentineliq.contracts.query import RetrievalStrategy


class TrustState(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_EVIDENCE = "no_evidence"
    UNAUTHORIZED = "unauthorized"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    tenant_id: UUID

    excerpt: str
    retrieval_method: RetrievalStrategy

    source_id: UUID | None = None
    document_id: UUID | None = None
    version_id: UUID | None = None
    section_id: UUID | None = None
    parent_id: UUID | None = None
    chunk_id: UUID | None = None

    page_number: int | None = None
    source_location: str | None = None

    relevance: float | None = None
    authority: float | None = None
    freshness: float | None = None
    applicability: float | None = None

    authorization_verified: bool = False

    supporting_claims: tuple[str, ...] = ()

    provenance: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        scores = (
            self.relevance,
            self.authority,
            self.freshness,
            self.applicability,
        )

        for score in scores:
            if score is not None and not 0 <= score <= 1:
                raise ValueError("evidence scores must be between 0 and 1")
