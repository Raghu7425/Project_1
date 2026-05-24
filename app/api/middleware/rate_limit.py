from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.config.settings import get_settings
from app.utils.redis import get_redis


async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.url.path in {"/health", "/ready", "/metrics"}:
        return await call_next(request)
    settings = get_settings()
    client = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client}:{request.url.path}"
    redis = get_redis()
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    finally:
        await redis.aclose()
    return await call_next(request)
