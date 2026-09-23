from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from sentineliq.contracts.retrieval import RetrievalCandidate


class EmbeddingProvider(Protocol):
    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]: ...

    def embed_query(
        self,
        text: str,
    ) -> list[float]: ...


class RerankerProvider(Protocol):
    def rerank(
        self,
        *,
        query: str,
        candidates: Sequence[RetrievalCandidate],
        limit: int,
    ) -> list[RetrievalCandidate]: ...


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    instructions: str
    input_text: str

    max_output_tokens: int | None = None

    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str

    provider: str
    model: str

    input_tokens: int | None = None
    output_tokens: int | None = None

    latency_ms: float | None = None
    cost_usd: float | None = None

    metadata: Mapping[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult: ...
