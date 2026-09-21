# ADR 0002: M0 HTTP runtime

## Status

Accepted

## Context

M0 requires a process that starts, serves `/health` and `/ready`, and can be tested, linted, and type-checked. The current CLI only prints text. Postgres and Redis were present in Compose and application settings without any M0 consumer.

## Problem

We need an HTTP runtime for liveness and readiness without introducing later-milestone infrastructure or RAG/LLM stacks.

## Requirements

- Typed HTTP handlers
- `/health` and `/ready`
- No Postgres, Redis, vector, embedding, agent, or LLM client libraries
- One process (modular monolith)
- Tests that exercise HTTP behavior

## Alternatives

1. **FastAPI + Uvicorn** — typed routes, Starlette test client, OpenAPI available when API specs are required later.
2. **Starlette only** — smaller, no first-class request/response models.
3. **Flask** — WSGI, weaker native typing for this codebase.
4. **stdlib `http.server`** — insufficient for typed handlers and later auth middleware.

## Decision

Use FastAPI with Uvicorn as the M0 HTTP runtime.

- `GET /health` — process liveness (`status: ok`).
- `GET /ready` — process has loaded configuration (`status: ready`). Readiness does not probe datastores in M0.
- Application settings do not include Postgres or Redis until a milestone requires them.
- Compose runs the API process only. Datastores are not M0 application dependencies.
- Type checking uses MyPy on application and test code.
- Structured logging is deferred to a later M0 increment.

## Trade-offs

FastAPI is a larger dependency than Starlette. It avoids a later rewrite for typed routes and OpenAPI. Uvicorn is an extra process dependency compared with a WSGI server.

## Consequences

The CLI starts Uvicorn against `sentineliq.app:app`. Quality gates include Pytest, Ruff, and MyPy. Identity, knowledge, and retrieval remain out of scope.

## Operational implications

Local run: `sentineliq` or `uvicorn sentineliq.app:app --host 0.0.0.0 --port 8000`. Docker image must run the same ASGI app, not a print-only CLI.
