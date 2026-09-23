from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from sentineliq.contracts.auth import (
    AuthorizationContext,
)
from sentineliq.contracts.knowledge import (
    KnowledgeSnapshot,
)


class ExecutionStage(str, Enum):
    AUTHORIZATION = "authorization"

    QUERY_ANALYSIS = "query_analysis"
    QUERY_PLANNING = "query_planning"

    RETRIEVAL = "retrieval"
    FUSION = "fusion"
    RERANKING = "reranking"
    CONTEXT_EXPANSION = "context_expansion"

    GRAPH = "graph"
    SQL = "sql"

    EVIDENCE_VALIDATION = "evidence_validation"
    CORRECTIVE_RETRIEVAL = "corrective_retrieval"

    GENERATION = "generation"

    CITATION_VALIDATION = "citation_validation"
    OUTPUT_VALIDATION = "output_validation"

    CACHE = "cache"
    AGENT = "agent"


@dataclass(frozen=True, slots=True)
class AuditContext:
    request_id: str

    authorization: AuthorizationContext
    knowledge_snapshot: KnowledgeSnapshot

    retrieval_policy_id: str | None = None
    retrieval_policy_version: str | None = None

    model_policy_id: str | None = None
    model_policy_version: str | None = None

    prompt_version: str | None = None


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    request_id: str

    stage: ExecutionStage
    started_at: datetime

    completed_at: datetime | None = None

    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")
