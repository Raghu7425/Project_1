from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobStatus
from app.models.job import Job


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: str,
        job_type: str,
        payload: dict,
        priority: int,
        max_retries: int,
        idempotency_key: str | None,
    ) -> Job:
        job = Job(
            user_id=user_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            status=JobStatus.QUEUED.value,
            idempotency_key=idempotency_key,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_for_user(self, job_id: str, user_id: str) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, user_id: str, key: str) -> Job | None:
        result = await self.db.execute(
            select(Job).where(Job.user_id == user_id, Job.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def claim(self, job_id: str, worker_id: str) -> Job | None:
        stmt = (
            update(Job)
            .where(Job.id == job_id, Job.status.in_([JobStatus.QUEUED.value, JobStatus.RETRYING.value]))
            .values(status=JobStatus.PROCESSING.value, locked_by=worker_id, locked_at=datetime.now(UTC))
            .returning(Job)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def complete(self, job_id: str, result: dict) -> None:
        await self.db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                result=result,
                error_message=None,
                locked_by=None,
                locked_at=None,
                completed_at=datetime.now(UTC),
            )
        )
        await self.db.commit()

    async def mark_retrying(self, job: Job, error: str) -> None:
        await self.db.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(
                status=JobStatus.RETRYING.value,
                retry_count=Job.retry_count + 1,
                error_message=error[:4000],
                locked_by=None,
                locked_at=None,
            )
        )
        await self.db.commit()

    async def fail_terminal(self, job_id: str, error: str) -> None:
        await self.db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.FAILED.value,
                error_message=error[:4000],
                locked_by=None,
                locked_at=None,
                completed_at=datetime.now(UTC),
            )
        )
        await self.db.commit()

    async def stuck_jobs(self, timeout_seconds: int) -> list[Job]:
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        result = await self.db.execute(
            select(Job).where(Job.status == JobStatus.PROCESSING.value, Job.locked_at < cutoff)
        )
        return list(result.scalars().all())

    async def counts(self) -> dict[str, int]:
        result = await self.db.execute(select(Job.status, func.count()).group_by(Job.status))
        counts = {status: count for status, count in result.all()}
        return {status.value: counts.get(status.value, 0) for status in JobStatus}
