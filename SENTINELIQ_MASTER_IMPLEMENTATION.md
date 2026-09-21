# SentinelIQ — Master Implementation Brief

**Status:** LOCKED ARCHITECTURE / ACTIVE IMPLEMENTATION CONTEXT  
**Project:** SentinelIQ — Enterprise Knowledge Intelligence Platform  
**Current milestone:** M0 — Engineering Foundation  
**Next milestone:** M1 — Identity & Tenant Model

> This file is the source of truth for Cursor agents. Read it before modifying code. The ChatGPT conversation is not required to continue implementation.

---

## 1. Mission

SentinelIQ is an enterprise knowledge intelligence platform, with compliance/policy intelligence as its flagship demonstration domain. It must generalize to HR, legal/contracts, engineering, finance, operations, security, and other enterprise domains.

The goal is **not** to build another PDF chatbot or tutorial RAG. The goal is to demonstrate a production-oriented system that can determine:

- what organizational knowledge exists;
- which version is authoritative and current;
- what a user is authorized to see;
- which retrieval/reasoning strategy a question requires;
- what evidence supports a claim;
- when evidence is insufficient or conflicting;
- how structured and unstructured knowledge relate;
- how knowledge changes propagate through derived indexes;
- what model/provider may receive which data;
- and why the final answer was produced.

### Core problem

> How do we build an enterprise AI knowledge system that can provide trustworthy, current, context-aware answers from fragmented and continuously changing organizational knowledge while respecting authorization, understanding relationships and versions, detecting conflicting or insufficient evidence, and preventing unsupported information from reaching the user?

### Trust principle

The organization controls its data, model/provider choices, retrieval infrastructure, authorization policies, tools, and auditability. External AI providers must never receive unrestricted enterprise information merely because an LLM is being used.

---

# 2. Non-Negotiable Engineering Principles

1. Do not blindly copy tutorials or GitHub repositories.
2. Do not add technologies merely because they are popular.
3. Do not activate every RAG technique for every query.
4. Retrieval must be dynamically planned.
5. Authorization is a security invariant, not a post-processing step.
6. Unauthorized resources must never enter a user's retrieval context.
7. The Knowledge Registry is the canonical source of truth; vector/search/graph indexes are derived state.
8. Knowledge versions must remain traceable.
9. Revocation/deletion must propagate through all derived representations and caches.
10. Evidence is a first-class domain object.
11. Citations must be provenance-backed and programmatically verifiable.
12. The LLM is a component, not the system.
13. Agents are bounded and used only where they provide measurable value.
14. Major architectural choices require ADRs.
15. Features are not complete without relevant tests, observability, failure handling, and documentation.
16. Prefer explicit, typed, modular code over unnecessary abstraction.
17. Avoid premature microservices. Start modular and container-ready.
18. Never claim functionality that is not actually implemented and tested.
19. Never weaken security to make a demo work.
20. Never commit secrets, credentials, private documents, or `.env` files.

---

# 3. Target Users

### General Knowledge Worker
Internal Q&A, citations, current information, conversational follow-up.

### Domain Expert / Analyst
Compliance, security, legal, finance, engineering, operations; deep investigation and evidence analysis.

### Knowledge Administrator
Upload/update/version/revoke/delete/reindex knowledge and monitor ingestion.

### Security / Platform Administrator
Identity, roles, permissions, tenant isolation, audits, security policies, model/provider configuration.

### Organization / AI Governance Administrator
Data classification, model/provider policies, external-provider restrictions, AI access audit, provenance governance.

---

# 4. Core Use Cases

## Tier 1 — Core Intelligence

1. Enterprise Knowledge Q&A
2. Deep Multi-Document Investigation
3. Enterprise Knowledge Discovery

## Tier 2 — Enterprise Reasoning

4. Knowledge Change & Version Intelligence
5. Evidence & Compliance Intelligence
6. Structured Enterprise Intelligence

## Tier 3 — Enterprise Trust

7. Secure / Permission-Aware Intelligence
8. Knowledge Governance & Administration
9. Trust-state answering: supported, partial, conflict, insufficient evidence, no evidence, or authorization-safe response.

Important real-world cases include stale policies, modified documents, conflicting sources, deleted/revoked knowledge, changed permissions, temporal questions, Draft/Active/Superseded/Expired/Revoked/Archived states, evidence sufficiency, and malicious/indirect prompt injection.

---

# 5. Functional Requirements

**FR-01 Identity & Access:** authentication, tenant identification, roles/permissions, authorization before retrieval/generation, resource-level ACL.

**FR-02 Knowledge Ingestion:** PDF, DOCX, HTML, Markdown, CSV, JSON, structured DB; parsing/OCR, cleaning, classification, dedupe, version detection, incremental updates, deletion/revocation.

**FR-03 Knowledge Lifecycle:** Draft → Active → Superseded → Expired/Revoked → Archived; version relationships and stale-answer prevention.

**FR-04 Knowledge Representation:** hierarchical chunks, parent/child, metadata, relationships, structured records, graph where justified.

**FR-05 Intelligent Retrieval:** dense, sparse/BM25, hybrid, metadata filtering, parent-child, reranking, query rewriting, multi-query, RRF/RAG-Fusion, graph, SQL.

**FR-06 Corrective Retrieval:** initial retrieval → evidence check → corrective strategy → re-retrieval → evidence check → generate only if sufficient.

**FR-07 Generation:** grounded, uncertainty-aware, cited, freshness/version-aware, authorization-aware, conflict-aware.

**FR-08 Evidence/Citation Verification:** claim → evidence → source validation.

**FR-09 Conversational Intelligence:** session history and follow-ups; current authorization always wins.

**FR-10 Structured Data Intelligence:** structured intent → schema retrieval → SQL generation → validation → authorization → execution → explanation.

**FR-11 Knowledge Graph:** policies, controls, procedures, systems, teams, evidence, dependencies, versions and related entities.

**FR-12 Semantic Cache:** cannot bypass authorization, tenant, version/freshness, or retrieval policy.

**FR-13 Security:** prompt/indirect injection, unauthorized retrieval, leakage, cross-tenant access, malicious documents, unsafe tools, secrets.

**FR-14 Evaluation:** retrieval, generation, trust, system, security metrics.

**FR-15 Observability:** structured telemetry for requests, auth, queries, strategy, retrieval, reranking, generation, citations, validation; avoid sensitive logging.

**FR-16 Administration:** knowledge, ingestion, versions, reprocessing, failures, access policies, audit, AI/model policies.

**FR-17 AI Execution & Provider Governance:** data classification → AI policy → allowed model/provider → allowed tools → execution; provider abstraction.

---

# 6. Non-Functional Requirements

- Security: zero trust, least privilege, defense in depth.
- Privacy/sovereignty: control storage, embeddings, model exposure, retention, deletion, audit.
- Authorization correctness: security correctness outranks retrieval quality.
- Reliability: retries/backoff/timeouts/fallback/circuit breakers where justified/graceful degradation.
- Freshness: version-aware retrieval, incremental ingestion, invalidation, deletion propagation, reindexing.
- Performance: measure every major pipeline stage and end-to-end latency.
- Scalability: independently scale API, workers, retrieval, model inference, background jobs where useful.
- Maintainability: types, modularity, configuration, errors, tests, linting, formatting, static analysis.
- Observability: logs, metrics, traces, correlation IDs, retrieval traces, model/token/cost metrics, security events.
- Auditability: who → what → when → resource → authorization → knowledge/model version → outcome.
- Explainability: query → interpretation → strategy → evidence → claims → citations → validation. Never expose hidden chain-of-thought.
- Cost efficiency: cost/query, embeddings, tokens, model use, cache savings, retrieval efficiency.
- Extensibility: replace LLM, embeddings, reranker, vector store, graph DB, auth provider without rewriting core logic.
- Testability: independently test ingestion, chunking, retrieval, routing, auth, graph, SQL, generation, citation, cache, security.
- Deployment portability: local → Docker → cloud.
- Data integrity: no orphan chunks, stale embeddings, version mismatch, inconsistent metadata, partial deletion, corrupted indexes.
- Safe degradation: graph failure → document retrieval; reranker failure → hybrid; provider failure → configured fallback/controlled failure; cache failure → bypass.

---

# 7. Knowledge & Dataset Strategy

Four knowledge categories:

1. **Unstructured:** policies, procedures, SOPs, security docs, audit reports, contracts, technical docs, handbooks, compliance frameworks, incidents.
2. **Semi-structured:** CSV, JSON, spreadsheets, exported reports, tables.
3. **Structured:** controls, findings, employees, departments, systems, assets, evidence, audit records, compliance status.
4. **Relationship knowledge:** graph relationships among the above.

Three datasets:

### A. Seed / Engineering Dataset
Public/researched material used to validate early pipelines. It is not the final benchmark.

### B. SentinelIQ Enterprise Corpus
Public enterprise/compliance material plus synthetic organizational policies, procedures, controls, evidence, audit findings and structured compliance records. Must include multiple versions, conflicts, obsolete documents, permission-sensitive content, and adversarial documents.

### C. Independent Evaluation Dataset
Simple factual, multi-document, multi-hop, ambiguous, temporal, version/change, conflict, no-answer, evidence-sufficiency, graph, SQL, permission-sensitive, and adversarial/injection cases.

Evaluation case fields:

```text
case_id
question
gold_answer
relevant_documents
relevant_chunks
expected_citations
category
difficulty
required_authorization_scope
expected_strategy
knowledge_snapshot
```

Never mix the evaluation set into ordinary retrieval knowledge without an explicit reason.

---

# 8. Knowledge Representation

Canonical hierarchy:

```text
Document
  ↓
Section
  ↓
Subsection
  ↓
Parent Chunk
  ↓
Child Chunk
```

Preserve headings, titles, lists, policy/control blocks, tables, page/source location, and relationships.

Parent-child retrieval:

```text
retrieve child → rerank → expand parent → construct context
```

Chunking strategies:

1. structure-aware hierarchical — default
2. table-aware
3. schema-aware CSV/JSON
4. semantic/recursive fallback
5. late chunking — experimental

Contextual enrichment occurs after structural chunking. Contextual retrieval is not synonymous with chunking.

Minimum metadata:

```text
chunk_id
document_id
version_id
parent_id
tenant_id
section_path
page_number
source_location
content_hash
classification
access_policy
created_at
updated_at
effective_from
effective_until
status
embedding_version
parser_version
ingestion_timestamp
```

Optional metadata includes entities, keywords, document type, department, and owner.

Full lineage:

```text
source → document → version → section → parent → child → embedding/index → evidence → citation
```

---

# 9. Canonical Knowledge Registry

The **Knowledge Registry is the source of truth**.

Vector DB, sparse/search index, graph DB, caches, and other derived stores must never become the authoritative state.

Conceptually:

```text
                    Knowledge Registry
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Vector Index   Sparse Index   Graph
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                       Derived State
```

All derived representations must be traceable to canonical IDs/version IDs.

---

# 10. Ingestion Architecture

Production-oriented asynchronous ingestion:

```text
Source
  ↓
Ingestion API/Event
  ↓
Job Queue
  ↓
Validation
  ↓
Security Scan
  ↓
Parse/OCR
  ↓
Normalize/Clean
  ↓
Classify
  ↓
Metadata Extraction
  ↓
Version/Change Detection
  ↓
Structure Extraction
  ↓
Hierarchical Chunking
  ↓
Contextual Enrichment
  ↓
Embeddings
  ↓
Vector/Sparse Index
  ↓
Graph Processing
  ↓
Validation
  ↓
Knowledge Registry / ACTIVE
```

Ingestion modes:

- file
- API/event
- scheduled sync

Security scanning covers malicious files, embedded instructions, prompt injection, metadata, size limits, malformed/unsupported content.

Document/job states:

```text
RECEIVED
VALIDATING
PARSING
NORMALIZING
ENRICHING
CHUNKING
INDEXING
GRAPH_PROCESSING
VALIDATED
ACTIVE
```

Failure/quarantine/rejected/dead-letter states must be observable and retryable.

---

# 11. Query & Retrieval Architecture

Golden path:

```text
User Query
  ↓
Authentication
  ↓
Authorization Context
  ↓
Query Understanding
  ↓
Query Classification
  ↓
Retrieval Planner
  ↓
Hybrid / Graph / SQL retrieval as appropriate
  ↓
Candidate Fusion (RRF/RAG-Fusion where useful)
  ↓
Neural Reranking
  ↓
Parent/Context Expansion
  ↓
Evidence Validation
  ↓
Corrective Retrieval if required
  ↓
Generation
  ↓
Claim Extraction
  ↓
Claim/Evidence Verification
  ↓
Citation Validation
  ↓
Output Security Check
  ↓
Response + Audit + Telemetry
```

### Query understanding

Extract/classify:

- intent
- entities
- dates/time ranges
- document/version references
- departments/systems/policies
- structured-data intent
- relationship intent
- complexity
- security-sensitive/adversarial signals

Use deterministic logic and LLM assistance where appropriate.

### Retrieval planner

Dynamic, not all-on.

Examples:

```text
"What is the password policy?"
→ hybrid

"What changed between the 2025 and 2026 policy?"
→ temporal/version retrieval

"Which systems are affected by this policy?"
→ graph

"Which departments have overdue compliance findings?"
→ SQL

"Investigate whether MFA controls are actually implemented."
→ hybrid + graph + structured evidence + corrective retrieval
```

### Corrective retrieval

```text
Initial retrieval
→ evidence quality check
→ diagnose
→ rewrite / expand / alternate strategy
→ re-retrieve
→ validate again
→ generate or return insufficient evidence
```

---

# 12. Evidence & Trust Architecture

Evidence is a first-class domain object:

```text
Evidence
├── source
├── document
├── version
├── chunk
├── authority
├── freshness
├── applicability
├── authorization
├── relevance
├── provenance
└── supporting_claims
```

Do not confuse:

- a mention of a control
- a policy requirement
- an implementation record
- evidence of implementation
- sufficient evidence for a conclusion

### Conflict resolution

Evaluate, in context:

1. authorization
2. status
3. effective date
4. expiration
5. authority
6. applicability
7. version
8. source reliability
9. evidence relationships

If unresolved, surface the conflict rather than inventing certainty.

### Trust states

Use evidence states rather than arbitrary confidence percentages:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `CONFLICTING`
- `INSUFFICIENT_EVIDENCE`
- `NO_EVIDENCE`
- `UNAUTHORIZED`

Do not reveal information about unauthorized resources.

---

# 13. Temporal & Version Intelligence

Support:

- current policy
- policy at a historical date
- previous versions
- what changed
- when it changed
- active version
- effective dates
- expiration
- supersession

Example:

> "What was our password policy in March 2025?"

must resolve against the relevant historical knowledge snapshot, not simply the newest document.

Version metadata should include content hash, timestamps, effective period, status, parent version, parser version, embedding version, ingestion job, and change summary.

---

# 14. Knowledge Graph

Potential entities:

```text
Organization
Department
Person
Policy
Procedure
Control
System
Asset
Evidence
Finding
Audit
Document
Version
Requirement
Regulation
```

Potential relationships:

```text
POLICY
 ├── governs → PROCEDURE
 ├── implements → CONTROL
 ├── applies_to → SYSTEM
 ├── owned_by → DEPARTMENT
 ├── supported_by → EVIDENCE
 ├── supersedes → VERSION
 └── derived_from → DOCUMENT
```

Graph complements rather than replaces semantic/hybrid retrieval.

---

# 15. Structured / SQL Intelligence

Pipeline:

```text
Question
→ structured intent
→ schema retrieval
→ SQL generation
→ SQL validation
→ authorization
→ read-only execution
→ result validation
→ explanation
```

Security requirements:

- read-only DB credentials
- allowlisted schemas/tables
- row-level authorization
- query timeout
- result-size limits
- SQL injection defenses
- no arbitrary writes
- complete audit trail

---

# 16. Agents

Use **bounded agents + deterministic workflow/state-machine orchestration**.

Possible specialized capabilities:

- retrieval
- graph
- SQL
- evidence verification
- document analysis

Agent requirements:

- explicit tools
- typed schemas
- permissions
- max iterations
- timeouts
- token/cost budgets
- deterministic termination
- auditability
- validation

Simple questions should not invoke an agent unnecessarily.

---

# 17. Memory

Separate:

1. conversation/session memory
2. non-sensitive user preference memory where appropriate
3. retrieval memory
4. temporary agent execution state

Memory can improve context but **never grants authorization**. Current authorization must always be evaluated.

---

# 18. Security & Authorization

Threat model includes:

- direct prompt injection
- indirect prompt injection
- malicious documents
- unauthorized retrieval
- cross-tenant leakage
- stale permissions
- data exfiltration
- unsafe tools
- SQL injection
- secrets leakage
- sensitive logging
- provider/model leakage
- poisoned knowledge
- citation manipulation
- malicious metadata

Security flow:

```text
Identity
 ↓
Authentication
 ↓
Authorization
 ↓
Tenant Isolation
 ↓
Document/Record ACL
 ↓
Retrieval Filtering
 ↓
Tool Authorization
 ↓
Generation Controls
 ↓
Output Validation
 ↓
Audit
```

Authorization model:

**RBAC + ABAC + resource-level ACL**

ABAC may consider tenant, department, classification, resource, project, environment, and relevant user attributes.

### Critical invariant

> If a user cannot access a resource, that resource must not enter their retrieval context.

Filtering after the model has seen the content is not sufficient.

---

# 19. AI Provider / Data Sovereignty Architecture

Use provider abstraction:

```text
LLM Gateway
 ├── OpenAI
 ├── Anthropic
 ├── Azure OpenAI
 ├── Private/self-hosted
 └── Future providers
```

Likewise abstract embedding and reranking providers.

Model routing considers:

- data classification
- task
- latency
- cost
- quality
- organizational policy
- provider availability

Conceptual policy:

```text
Public → external allowed
Internal → approved external/private
Confidential → restricted
Highly Confidential → private/self-hosted only
```

Exact policy must be configurable, not hardcoded.

---

# 20. Citation Architecture

Citations must be provenance-backed, not invented by the LLM.

```text
Evidence
 ↓
Claim
 ↓
Claim ↔ Evidence Mapping
 ↓
Citation Generator
 ↓
Citation Validator
 ↓
Final Answer
```

Citation data may include:

- document
- version
- section
- page/source location
- evidence/chunk
- effective date

---

# 21. Semantic Cache

Cache identity must account for:

```text
tenant
authorization scope
query
normalized query
knowledge snapshot
retrieval policy
model
prompt version
language
```

Every cache hit must revalidate authorization/freshness/policy as required.

Permission changes must invalidate affected cache entries.

---

# 22. Evaluation

Evaluation is continuous, not a final-phase activity.

### Retrieval

- Recall@K
- Precision@K
- MRR
- nDCG
- hit rate
- contextual relevance

### Generation

- faithfulness
- groundedness
- answer relevance
- citation correctness
- citation completeness

### Enterprise trust

- authorization correctness
- stale-answer rate
- conflict detection accuracy
- temporal retrieval accuracy
- evidence sufficiency accuracy
- unsupported-claim rate
- citation provenance accuracy

### System

- latency
- throughput
- token usage
- cost/query
- cache hit rate
- error rate

### Security evaluation

Dedicated adversarial tests for direct/indirect injection, malicious docs, cross-tenant access, unauthorized requests, permission changes, exfiltration, SQL attacks, tool abuse, secret extraction, and citation manipulation.

---

# 23. Observability & Audit

Trace:

```text
Request ID
→ user/auth
→ query classification
→ retrieval strategy
→ retriever calls
→ candidate IDs
→ reranking
→ graph/SQL
→ evidence validation
→ LLM
→ citations
→ output validation
```

Capture latency, token usage, cost, strategies, IDs, scores, graph/SQL activity, cache outcomes, errors, and security events.

Avoid logging raw sensitive document content by default.

Audit is a dedicated trail, separate from ordinary logs, answering:

> Who did what, when, against what resource, under which authorization policy, using which knowledge/model version, with what outcome?

---

# 24. Reliability & Degradation

Expected fallbacks:

```text
Vector unavailable → sparse fallback
Reranker unavailable → hybrid without reranking
Graph unavailable → document retrieval
SQL unavailable → controlled structured-data failure
LLM provider unavailable → configured fallback or controlled failure
Cache unavailable → bypass cache
Malformed document → quarantine
Embedding failure → retry → dead letter
```

Never silently ignore a critical failure.

---

# 25. Deletion & Revocation

When knowledge is revoked/deleted, propagate through:

```text
Source
→ Knowledge Registry
→ Chunks
→ Embeddings
→ Sparse Index
→ Graph
→ Cache
→ Searchability
```

Conceptual state:

```text
ACTIVE
→ REVOKED
→ INDEX INVALIDATION
→ CACHE INVALIDATION
→ GRAPH CLEANUP
→ VERIFIED DELETED
```

Retention/audit requirements may preserve an audit event even when content is deleted.

---

# 26. Infrastructure & Engineering Quality

Container-first and cloud-portable.

Local development uses Docker Compose.

Avoid premature microservices; use clear modules and worker boundaries first. Split services only when scale, isolation, deployment, or reliability requires it.

CI/CD quality gates should eventually include:

```text
Formatting
→ Lint
→ Type check
→ Unit tests
→ Integration tests
→ Security tests
→ Evaluation regression
→ Build
→ Container validation
```

Potential tools include Ruff, MyPy/Pyright, Pytest, pre-commit, GitHub Actions, and dependency/security scanners. Choose through evidence and ADRs.

---

# 27. Architecture Documentation

Required artifacts:

- Product Requirements Document
- Functional Requirements
- Non-Functional Requirements
- Use Cases
- C4 diagrams
- system architecture
- data architecture
- retrieval architecture
- ingestion architecture
- security architecture
- deployment architecture
- API specification
- data schemas
- event schemas
- tool schemas
- evaluation specification
- testing strategy
- threat model
- ADRs
- deployment/runbook documentation

---

# 28. Technology Selection Philosophy

Never select technology merely because it is popular.

For every major component ask:

> What problem does this solve, and why can't an existing component solve it adequately?

Avoid unnecessary stacks such as combining multiple RAG/orchestration frameworks without a concrete need.

Major decisions require ADRs containing:

```text
Context
Problem
Requirements
Alternatives
Decision
Trade-offs
Consequences
Operational implications
```

Specific technology choices remain implementation decisions and must be based on requirements and measured trade-offs.

---

# 29. Implementation Roadmap

```text
M0  Engineering Foundation
M1  Identity & Tenant Model
M2  Knowledge Registry
M3  Ingestion Pipeline
M4  Hierarchical Knowledge Representation
M5  Baseline RAG
M6  Hybrid Retrieval
M7  Query Planning & Advanced Retrieval
M8  Evidence & Citation Engine
M9  Version / Temporal Intelligence
M10 Graph Intelligence
M11 Structured SQL Intelligence
M12 Agentic Investigation
M13 Security Hardening
M14 Evaluation Framework
M15 Observability & Audit
M16 Performance / Cost Optimization
M17 Deployment
M18 Production Hardening
```

Architecture is production-oriented from the start; implementation is incremental.

Do not implement later milestones prematurely.

---

# 30. Current Repository State

The repository currently contains the initial M0 foundation. Before changing anything, inspect the actual repository rather than assuming a file exists.

Expected initial areas include:

```text
config/
docker/
docs/
scripts/
src/
tests/
.env.example
.gitignore
docker-compose.yml
pyproject.toml
README.md
```

The exact structure is allowed to evolve when justified by the architecture.

---

# 31. M0 Definition of Done

M0 is complete when:

- installation is reproducible
- environment configuration works
- API starts
- `/health` works
- `/ready` exists
- Docker infrastructure starts
- tests run
- lint runs
- type checking runs
- structured logging works
- repository documentation exists
- no secrets are committed

Do not begin sophisticated RAG implementation until M0 is validated.

---

# 32. M1 — Identity & Tenant Model

First real domain milestone.

Initial entities:

```text
Tenant
User
Role
Permission
UserRole
RolePermission
```

Potential later entities:

```text
UserAttribute
Department
Group
ResourcePolicy
ResourceACL
```

Required capabilities:

- create tenant
- create user
- assign role
- assign permissions
- resolve authorization context
- determine tenant
- represent resource access policy

Every authenticated request must have a defined authorization context containing, as appropriate:

```text
tenant_id
user_id
roles
permissions
attributes
```

Before implementing knowledge retrieval, establish the tenant/security foundation.

---

# 33. M2 — Knowledge Registry

Canonical entities should evolve toward:

```text
KnowledgeSource
Document
DocumentVersion
Section
ParentChunk
ChildChunk
KnowledgeEntity
KnowledgeRelationship
```

Derived representations must reference canonical IDs and versions.

---

# 34. M3 — Ingestion

Start with a limited, robust subset such as Markdown, PDF, and DOCX. Do not build every parser at once.

The ingestion pipeline must be observable, retryable, idempotent where possible, and version-aware.

---

# 35. M4 — Hierarchical Representation

Implement document → version → section → parent chunk → child chunk with lineage, metadata, hashes, access policy, timestamps, and lifecycle state.

---

# 36. M5 — Baseline RAG

Only after the knowledge foundation exists.

Initial baseline:

```text
query
→ authorization
→ dense retrieval
→ parent expansion
→ grounded generation
→ provenance-backed citations
```

This baseline becomes the benchmark for advanced retrieval.

---

# 37. M6+ — Advanced Retrieval

Add progressively and measure each capability:

- sparse retrieval
- hybrid retrieval
- reranking
- query rewriting
- multi-query
- RRF
- corrective retrieval
- graph retrieval
- SQL retrieval
- bounded agentic investigation

Every advanced capability should have a measurable reason for inclusion.

---

# 38. Coding Rules for Cursor Agents

### Before editing

1. Read this file.
2. Inspect the repository.
3. Determine current milestone and actual implementation state.
4. Inspect relevant ADRs.
5. Identify dependencies and security implications.
6. Do not assume missing files exist.

### While editing

- use type hints
- keep functions focused
- validate inputs
- handle errors deliberately
- use structured logging
- avoid hidden global state
- use configuration for environment-specific values
- write meaningful tests
- preserve tenant/security boundaries
- avoid unnecessary abstractions
- avoid premature distributed architecture

### After editing

Run appropriate tests, linting, formatting, and type checking.

Report:

- files changed
- what changed
- why
- tests executed
- results
- known limitations
- architectural decisions
- next task

---

# 39. Cursor Agent Handoff Prompt

Use this when starting a new Cursor agent:

> Read `SENTINELIQ_MASTER_IMPLEMENTATION.md` completely before modifying code.
>
> You are contributing to SentinelIQ, an enterprise-grade authorization-aware knowledge intelligence platform.
>
> Treat the document as the current architectural source of truth.
>
> First inspect the existing repository and determine the actual current milestone/state.
>
> Do not blindly introduce frameworks or technologies.
>
> Do not implement future milestones prematurely.
>
> Do not weaken security or bypass authorization for convenience.
>
> Make changes only for the requested milestone.
>
> Before coding, identify the relevant requirements and existing implementation.
>
> After coding, run tests, linting, formatting, and type checks appropriate to the changed code.
>
> Report exactly: files changed, implementation completed, tests executed, test results, known limitations, architectural decisions made, and next recommended task.
>
> If an implementation choice conflicts with the master architecture, stop and explain the conflict instead of silently changing the architecture.
>
> **Current milestone: M0 — Engineering Foundation.**
>
> First validate M0. Once M0 passes, proceed to **M1 — Identity & Tenant Model**.

---

# 40. Definition of Production-Grade

For this project, production-grade means professional engineering discipline, not pretending a student project is a globally distributed enterprise SaaS product.

It means demonstrating:

- explicit architecture
- secure boundaries
- typed code
- modular design
- tests
- failure handling
- observability
- auditability
- evaluation
- reproducibility
- configuration
- containerization
- documentation
- measurable performance
- realistic security controls
- clear trade-offs

Claims must remain proportional to what is actually implemented and tested.

---

# 41. North Star

SentinelIQ is not trying to answer:

> Can we make an LLM answer questions over PDFs?

It is trying to answer:

> **Can we build an enterprise AI knowledge system that knows what information exists, which version is authoritative, who is allowed to see it, what evidence supports a claim, when evidence is insufficient or conflicting, which reasoning strategy is appropriate, and how to prove why the system produced its answer?**

Every implementation decision should move toward that goal.
