from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    COMPARISON = "comparison"
    TEMPORAL = "temporal"
    RELATIONSHIP = "relationship"
    STRUCTURED = "structured"
    INVESTIGATION = "investigation"
    CONVERSATIONAL = "conversational"
    UNKNOWN = "unknown"


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    NORMAL = "normal"
    DEEP = "deep"


class QueryPath(str, Enum):
    FAST = "fast"
    NORMAL = "normal"
    DEEP = "deep"
    FALLBACK = "fallback"


class RetrievalStrategy(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    TEMPORAL = "temporal"
    GRAPH = "graph"
    SQL = "sql"


class QueryVariantOrigin(str, Enum):
    ORIGINAL = "original"
    REWRITE = "rewrite"
    MULTI_QUERY = "multi_query"
    HYDE = "hyde"
    DECOMPOSITION = "decomposition"


@dataclass(frozen=True, slots=True)
class QueryVariant:
    variant_id: str
    text: str
    origin: QueryVariantOrigin


@dataclass(frozen=True, slots=True)
class QueryAnalysis:
    original_query: str
    normalized_query: str

    intent: QueryIntent = QueryIntent.UNKNOWN
    complexity: QueryComplexity = QueryComplexity.NORMAL

    entities: tuple[str, ...] = ()
    document_references: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    systems: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()

    temporal_start: datetime | None = None
    temporal_end: datetime | None = None

    structured_data_intent: bool = False
    relationship_intent: bool = False
    temporal_intent: bool = False

    security_signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QueryPlan:
    path: QueryPath = QueryPath.NORMAL

    strategies: tuple[RetrievalStrategy, ...] = (RetrievalStrategy.DENSE,)

    top_k: int = 8
    candidate_k: int = 40
    max_context_tokens: int = 8000

    rewrite: bool = False
    multi_query: bool = False
    hyde: bool = False
    rag_fusion: bool = False

    rerank: bool = False
    parent_expansion: bool = False
    corrective_retrieval: bool = False

    metadata_filters: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        if self.candidate_k < self.top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")

        if self.max_context_tokens <= 0:
            raise ValueError("max_context_tokens must be greater than zero")

        if not self.strategies:
            raise ValueError("at least one retrieval strategy is required")
