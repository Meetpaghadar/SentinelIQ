from dataclasses import dataclass, field

from sentineliq.contracts.knowledge import (
    DataClassification,
)
from sentineliq.contracts.query import RetrievalStrategy


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    policy_id: str
    version: str

    allowed_strategies: frozenset[RetrievalStrategy] = field(
        default_factory=lambda: frozenset(
            {
                RetrievalStrategy.DENSE,
            }
        )
    )

    max_candidates: int = 100
    max_final_results: int = 20
    max_context_tokens: int = 12000

    allow_query_rewrite: bool = True
    allow_multi_query: bool = True
    allow_hyde: bool = True
    allow_corrective_retrieval: bool = True

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id cannot be empty")

        if not self.version.strip():
            raise ValueError("policy version cannot be empty")

        if not self.allowed_strategies:
            raise ValueError("at least one retrieval strategy must be allowed")

        if self.max_candidates <= 0:
            raise ValueError("max_candidates must be greater than zero")

        if self.max_final_results <= 0:
            raise ValueError("max_final_results must be greater than zero")

        if self.max_final_results > self.max_candidates:
            raise ValueError("max_final_results cannot exceed max_candidates")

        if self.max_context_tokens <= 0:
            raise ValueError("max_context_tokens must be greater than zero")


@dataclass(frozen=True, slots=True)
class ModelExecutionPolicy:
    policy_id: str
    version: str

    data_classification: DataClassification

    allowed_providers: frozenset[str] = field(default_factory=frozenset)

    allowed_models: frozenset[str] = field(default_factory=frozenset)

    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_cost_usd: float | None = None

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id cannot be empty")

        if not self.version.strip():
            raise ValueError("policy version cannot be empty")

        if self.max_input_tokens is not None and self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be greater than zero")

        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero")

        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ValueError("max_cost_usd cannot be negative")
