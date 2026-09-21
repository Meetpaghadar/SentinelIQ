# SentinelIQ

Enterprise knowledge intelligence platform. Current milestone: **M0 — Engineering Foundation**.

M0 provides a runnable HTTP process, health/readiness endpoints, tests, and quality gates. It does not implement identity, knowledge retrieval, or RAG.

## Layout

```
src/sentineliq/   Python package
tests/            Pytest suite
config/           Non-secret defaults (not yet loaded by the app)
docker/           Container build files
docs/adr/         Architecture decision records
scripts/          Operator and developer scripts
```

## Setup

Python 3.10+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```powershell
sentineliq
```

Then:

- `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
- `GET http://127.0.0.1:8000/ready` → `{"status":"ready"}`

## Quality gates

```powershell
pytest
ruff format --check src tests
ruff check src tests
mypy
```

## Docker

```powershell
docker compose up --build
```

Configuration is environment variables (`SENTINELIQ_*`). See `.env.example`.
