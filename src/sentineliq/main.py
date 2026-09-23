from fastapi import FastAPI

from sentineliq import __version__
from sentineliq.api.errors import register_exception_handlers
from sentineliq.api.middleware import CorrelationIdMiddleware
from sentineliq.api.router import api_router
from sentineliq.api.v1.auth import router as auth_router
from sentineliq.api.v1.query import router as query_router
from sentineliq.config import get_settings
from sentineliq.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="SentinelIQ",
        version=__version__,
    )

    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(query_router)

    register_exception_handlers(app)

    return app


app = create_app()
