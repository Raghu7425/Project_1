import asyncio
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_user, queue_dependency, redis_dependency, settings_dependency
from app.api.schemas import JobCreateRequest, JobResponse
from app.config.settings import Settings
from app.db.session import get_db
from app.models.user import User
from app.queue.redis_streams import RedisJobQueue
from app.repositories.jobs import JobRepository
from app.services.jobs import JobService
from app.utils.security import decode_access_token

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=202)
async def create_job(
    body: JobCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    redis: Annotated[Redis, Depends(redis_dependency)],
    queue: Annotated[RedisJobQueue, Depends(queue_dependency)],
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> JobResponse:
    job = await JobService(JobRepository(db), queue, redis, settings).submit(
        user_id=user.id,
        job_type=body.job_type.value,
        payload=body.payload,
        priority=body.priority,
        max_retries=body.max_retries,
        idempotency_key=body.idempotency_key,
    )
    return JobResponse.model_validate(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    redis: Annotated[Redis, Depends(redis_dependency)],
    queue: Annotated[RedisJobQueue, Depends(queue_dependency)],
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> JobResponse:
    job = await JobService(JobRepository(db), queue, redis, settings).get_for_user(job_id, user.id)
    return JobResponse.model_validate(job)


@router.websocket("/ws/{job_id}")
async def job_status_ws(
    websocket: WebSocket,
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(redis_dependency)],
    queue: Annotated[RedisJobQueue, Depends(queue_dependency)],
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    service = JobService(JobRepository(db), queue, redis, settings)
    last_status = None
    try:
        while True:
            job = await service.get_for_user(job_id, user_id)
            if job.status != last_status:
                await websocket.send_json(JobResponse.model_validate(job).model_dump(mode="json"))
                last_status = job.status
            if job.status in {"completed", "failed"}:
                return
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
