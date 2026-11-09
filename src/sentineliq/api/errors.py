from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sentineliq.logging import CORRELATION_ID_HEADER, get_correlation_id
from sentineliq.querying.executor import RetrievalExecutionUnavailable

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RetrievalExecutionUnavailable)
    async def retrieval_unavailable(
        _request: Request, exc: RetrievalExecutionUnavailable
    ) -> JSONResponse:
        logger.warning("retrieval_strategy_unavailable", extra={"reason": str(exc)})
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc)},
            headers={CORRELATION_ID_HEADER: get_correlation_id()},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"error_type": type(exc).__name__})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={CORRELATION_ID_HEADER: get_correlation_id()},
        )
