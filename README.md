# SentinelIQ

Enterprise knowledge intelligence platform with an authorization-aware knowledge registry and
baseline hybrid RAG foundation. Advanced retrieval experiments remain disabled by default.

## Layout

```
src/sentineliq/   Python package
tests/            Pytest suite
config/           File defaults (environment variables override these)
docker/           Container build files
docs/adr/         Architecture decision records
```

## Setup

Python 3.10 is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
copy .env.example .env
```

## Development commands

```powershell
python -m sentineliq.cli config
python -m sentineliq.cli serve
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pyright
```

## API

```powershell
python -m sentineliq.cli serve
```

- `GET /health` → `{"status":"healthy","service":"SentinelIQ"}`
- `GET /ready` → `{"status":"ready"}`

Responses include `X-Correlation-ID`. Send that header to preserve a caller-supplied ID.

Readiness means the process loaded configuration. Postgres and Redis are not part of M0.

## Docker

```powershell
copy .env.example .env
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Compose starts the API and PostgreSQL/pgvector. The API waits for PostgreSQL and runs
`alembic upgrade head` before serving. Configuration is supplied by `SENTINELIQ_*` variables;
replace the example JWT secret before use. An OpenAI key is required only for embedding,
reranking, and generation calls.

## Retrieval authorization

The query API requires `knowledge:query`. Retrieval applies tenant, active-version,
effective-date, classification, document allowlist, and document access-policy constraints
before loading chunk content. The current access-policy format is a JSON object with optional
`roles` (any match), `permissions` (all required), and `attributes` (all exact string matches).
Malformed or unsupported policies fail closed. User attributes are currently empty because the
identity schema does not yet persist attributes.

For a fresh, non-destructive migration check, use a separate Compose project and volume:

```powershell
docker compose -p sentineliq-migration-check up -d --build
docker compose -p sentineliq-migration-check down -v
```
