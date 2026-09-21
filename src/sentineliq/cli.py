from __future__ import annotations

import sys
from collections.abc import Sequence

import uvicorn
from pydantic import ValidationError

from sentineliq.config import Settings, get_settings
from sentineliq.logging import configure_logging


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _usage()
        raise SystemExit(2)

    command = args[0]
    if command == "config":
        _print_config()
        return
    if command == "serve":
        _serve()
        return

    print(f"unknown command: {command}", file=sys.stderr)
    _usage()
    raise SystemExit(2)


def _usage() -> None:
    print("usage: python -m sentineliq.cli {config|serve}", file=sys.stderr)


def _print_config() -> None:
    settings = _load_settings()
    for key, value in settings.safe_display().items():
        print(f"{key} = {value}")


def _serve() -> None:
    settings = _load_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "sentineliq.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        log_config=None,
    )


def _load_settings() -> Settings:
    get_settings.cache_clear()
    try:
        return get_settings()
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
