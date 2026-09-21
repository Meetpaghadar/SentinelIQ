from fastapi import FastAPI

from sentineliq import __version__
from sentineliq.config import get_settings


def create_app() -> FastAPI:
    application = FastAPI(title="SentinelIQ", version=__version__)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready")
    def ready() -> dict[str, str]:
        get_settings()
        return {"status": "ready"}

    return application


app = create_app()
