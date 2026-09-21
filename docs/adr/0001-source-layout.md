# ADR 0001: Source layout

## Status

Accepted

## Context

SentinelIQ needs a Python package layout that supports local development, tests, and container builds without mixing application code with tooling files.

## Decision

Use a `src/` layout (`src/sentineliq`) with `tests/`, `config/`, `docker/`, `docs/adr/`, and `scripts/` as first-class top-level directories. Package metadata lives in `pyproject.toml`.

## Consequences

Installs and tests must include `src` on the Python path (configured in `pyproject.toml`). Application imports start from `sentineliq`.
