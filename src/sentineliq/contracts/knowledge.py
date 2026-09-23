from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class KnowledgeStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ARCHIVED = "archived"


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    snapshot_id: str | None = None
    as_of: datetime | None = None

    statuses: frozenset[KnowledgeStatus] = field(
        default_factory=lambda: frozenset(
            {
                KnowledgeStatus.ACTIVE,
            }
        )
    )

    parser_version: str | None = None
    embedding_version: str | None = None

    def __post_init__(self) -> None:
        if not self.statuses:
            raise ValueError("knowledge snapshot requires at least one status")
