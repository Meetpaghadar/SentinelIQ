from fastapi import FastAPI

from sentineliq import __version__
from sentineliq.api.errors import register_exception_handlers
from sentineliq.api.middleware import CorrelationIdMiddleware
from sentineliq.api.router import api_router
from sentineliq.config import get_settings
from sentineliq.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(title="SentinelIQ", version=__version__)
    application.add_middleware(CorrelationIdMiddleware)
    application.include_router(api_router)
    register_exception_handlers(application)
    return application


app = create_app()
