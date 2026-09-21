# SentinelIQ

Enterprise knowledge intelligence platform. Current milestone: **M0 — Engineering Foundation**.

M0 is a runnable API process with health/readiness checks, typed settings, structured logging, and quality gates. It does not implement identity, knowledge retrieval, or RAG.

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
docker compose up --build
```

Only the API container is defined. Configuration is `SENTINELIQ_*` environment variables, which override `config/settings.toml` and `.env`.
