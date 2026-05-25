from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.handlers import admin, auth, health, jobs
from app.api.middleware.rate_limit import rate_limit_middleware
from app.api.middleware.request_logging import request_logging_middleware
from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.queue.redis_streams import RedisJobQueue
from app.utils.redis import get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    redis = get_redis()
    await RedisJobQueue(redis, settings).ensure_groups()
    await redis.aclose()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Real-time AI, media, and document processing platform with Redis Streams workers.",
    lifespan=lifespan,
)
app.middleware("http")(request_logging_middleware)
app.middleware("http")(rate_limit_middleware)
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse("app/static/index.html")


FastAPIInstrumentor.instrument_app(app)
