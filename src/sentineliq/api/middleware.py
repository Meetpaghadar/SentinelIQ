from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from sentineliq.logging import CORRELATION_ID_HEADER, correlation_id_var, new_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(CORRELATION_ID_HEADER)
        correlation_id = incoming.strip() if incoming and incoming.strip() else new_correlation_id()
        token = correlation_id_var.set(correlation_id)
        try:
            logger.info(
                "http_request",
                extra={"method": request.method, "path": request.url.path},
            )
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)
