from typing import Annotated

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import redis_dependency
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(redis_dependency)],
) -> dict[str, str]:
    await db.execute(text("select 1"))
    await redis.ping()
    return {"status": "ready"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
