from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_user, queue_dependency, redis_dependency
from app.api.schemas import AdminStatsResponse
from app.db.session import get_db
from app.models.user import User
from app.queue.redis_streams import RedisJobQueue
from app.repositories.jobs import JobRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(redis_dependency)],
    queue: Annotated[RedisJobQueue, Depends(queue_dependency)],
    _: Annotated[User, Depends(current_user)],
) -> AdminStatsResponse:
    counts = await JobRepository(db).counts()
    dlq_size = await redis.xlen(queue.dlq_stream)
    return AdminStatsResponse(
        queued=counts["queued"],
        processing=counts["processing"],
        retrying=counts["retrying"],
        completed=counts["completed"],
        failed=counts["failed"],
        dlq_size=dlq_size,
    )
