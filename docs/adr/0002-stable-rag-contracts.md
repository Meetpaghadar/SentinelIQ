# ADR 0002: Stable RAG Contracts

## Status

Accepted

## Context

SentinelIQ will progressively support multiple retrieval and reasoning
strategies including dense retrieval, sparse retrieval, hybrid retrieval,
RRF, reranking, temporal retrieval, GraphRAG, SQL retrieval, corrective
retrieval, semantic caching, model routing, and bounded agentic workflows.

Building separate pipelines for each capability would cause duplicated
models, inconsistent authorization logic, incompatible retrieval results,
and repeated rewrites.

SentinelIQ also requires evidence provenance, knowledge version awareness,
provider replaceability, auditability, and observability.

## Decision

SentinelIQ will use stable internal contracts for:

- authorization
- query analysis
- query planning
- retrieval candidates
- evidence
- knowledge snapshots
- retrieval policies
- model execution policies
- provider abstractions
- audit context
- telemetry

All retrieval strategies will eventually emit a common
RetrievalCandidate representation.

The Knowledge Registry remains the canonical source of truth.

Vector, sparse, graph, cache, and other indexes remain derived state.

External model providers will be accessed through provider interfaces
rather than referenced directly by domain logic.

## Consequences

Benefits:

- retrieval strategies remain interchangeable
- authorization can remain consistent across retrieval paths
- future GraphRAG and SQL retrieval can join the same orchestration
- providers can be changed without rewriting domain logic
- evidence provenance is preserved
- evaluation can compare techniques consistently
- telemetry can observe every strategy consistently

Tradeoffs:

- adapters are required around existing services
- contracts must remain intentionally small
- contracts may evolve when real requirements prove necessary

## Evaluation Requirement

Every new retrieval, ranking, routing, caching, or reasoning technique
must be measured against the existing SentinelIQ baseline.

A technique remains enabled only when it provides measurable value or
supports a required capability that the baseline cannot provide.