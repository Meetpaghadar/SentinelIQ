from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol
from uuid import UUID

from sentineliq.contracts.auth import AuthorizationContext
from sentineliq.contracts.knowledge import KnowledgeSnapshot
from sentineliq.contracts.query import (
    QueryPlan,
    RetrievalStrategy,
)


class CandidateKind(str, Enum):
    CHUNK = "chunk"
    GRAPH = "graph"
    STRUCTURED = "structured"
    TEMPORAL = "temporal"


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    candidate_id: str
    tenant_id: UUID

    kind: CandidateKind
    retrieval_method: RetrievalStrategy
    content: str

    source_id: UUID | None = None
    document_id: UUID | None = None
    version_id: UUID | None = None
    section_id: UUID | None = None
    parent_id: UUID | None = None
    chunk_id: UUID | None = None

    query_variant_id: str | None = None

    raw_score: float | None = None
    normalized_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None

    rank: int | None = None

    metadata: Mapping[str, object] = field(default_factory=dict)

    provenance: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResultSet:
    strategy: RetrievalStrategy
    candidates: tuple[RetrievalCandidate, ...]

    total_considered: int
    latency_ms: float | None = None


class Retriever(Protocol):
    def retrieve(
        self,
        *,
        query: str,
        plan: QueryPlan,
        authorization: AuthorizationContext,
        snapshot: KnowledgeSnapshot,
    ) -> RetrievalResultSet: ...
