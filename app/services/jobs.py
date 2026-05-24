import json

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config.settings import Settings
from app.models.job import Job
from app.queue.redis_streams import RedisJobQueue
from app.repositories.jobs import JobRepository
from app.utils.metrics import JOBS_SUBMITTED


class JobService:
    def __init__(self, jobs: JobRepository, queue: RedisJobQueue, redis: Redis, settings: Settings):
        self.jobs = jobs
        self.queue = queue
        self.redis = redis
        self.settings = settings

    async def submit(
        self,
        *,
        user_id: str,
        job_type: str,
        payload: dict,
        priority: int,
        max_retries: int,
        idempotency_key: str | None,
    ) -> Job:
        if idempotency_key:
            existing = await self.jobs.get_by_idempotency_key(user_id, idempotency_key)
            if existing:
                return existing
        job = await self.jobs.create(
            user_id=user_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            idempotency_key=idempotency_key,
        )
        await self.queue.enqueue(job.id, priority)
        await self.cache_status(job)
        JOBS_SUBMITTED.labels(job_type=job_type).inc()
        return job

    async def get_for_user(self, job_id: str, user_id: str) -> Job:
        cached = await self.redis.get(f"job_status:{user_id}:{job_id}")
        job = await self.jobs.get_for_user(job_id, user_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        if not cached:
            await self.cache_status(job)
        return job

    async def cache_status(self, job: Job) -> None:
        await self.redis.setex(
            f"job_status:{job.user_id}:{job.id}",
            60,
            json.dumps({"id": job.id, "status": job.status, "updated_at": job.updated_at.isoformat()}),
        )
