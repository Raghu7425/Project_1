import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

from app.utils.metrics import HTTP_REQUESTS

logger = structlog.get_logger()


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    path = request.url.path
    HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    logger.info(
        "http_request",
        method=request.method,
        path=path,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
    )
    return response
