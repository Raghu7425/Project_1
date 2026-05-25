import asyncio
import signal
import socket
import time
from contextlib import suppress

import structlog

from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.models.job import Job
from app.queue.redis_streams import QueueMessage, RedisJobQueue
from app.repositories.jobs import JobRepository
from app.utils.metrics import JOB_LATENCY, JOBS_FAILED, JOBS_PROCESSED, QUEUE_LENGTH
from app.utils.redis import get_redis
from app.worker.processors import PROCESSORS

logger = structlog.get_logger()


class Worker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = get_redis()
        self.queue = RedisJobQueue(self.redis, self.settings)
        self.worker_id = f"{socket.gethostname()}:{id(self)}"
        self.stop_event = asyncio.Event()
        self.active: set[asyncio.Task] = set()

    async def start(self) -> None:
        configure_logging()
        await self.queue.ensure_groups()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.stop_event.set)
        logger.info("worker_started", worker_id=self.worker_id, concurrency=self.settings.worker_concurrency)
        supervisors = [
            asyncio.create_task(self.retry_promoter()),
            asyncio.create_task(self.stuck_job_reclaimer()),
            asyncio.create_task(self.metrics_sampler()),
        ]
        try:
            await self.consume()
        finally:
            self.stop_event.set()
            for task in supervisors:
                task.cancel()
            await self.drain_active()
            await self.redis.aclose()
            logger.info("worker_stopped", worker_id=self.worker_id)

    async def consume(self) -> None:
        while not self.stop_event.is_set():
            self.active = {task for task in self.active if not task.done()}
            if len(self.active) >= self.settings.worker_concurrency:
                await asyncio.sleep(0.1)
                continue
            message = await self.queue.read_next(self.worker_id, block_ms=1000)
            if message:
                task = asyncio.create_task(self.handle_message(message))
                self.active.add(task)

    async def drain_active(self) -> None:
        if not self.active:
            return
        done, pending = await asyncio.wait(
            self.active, timeout=self.settings.worker_shutdown_grace_seconds
        )
        for task in done:
            with suppress(Exception):
                task.result()
        for task in pending:
            task.cancel()

    async def handle_message(self, message: QueueMessage) -> None:
        started = time.perf_counter()
        async with SessionLocal() as db:
            repo = JobRepository(db)
            job = await repo.claim(message.job_id, self.worker_id)
            if not job:
                await self.queue.ack(message)
                return
            logger.info("job_claimed", job_id=job.id, job_type=job.job_type, worker_id=self.worker_id)
            try:
                processor = PROCESSORS.get(job.job_type)
                if not processor:
                    raise ValueError(f"no processor registered for job_type={job.job_type!r}")
                result = await asyncio.wait_for(
                    processor(job.payload),
                    timeout=self.settings.job_timeout_seconds,
                )
                await repo.complete(job.id, result)
                await self.queue.ack(message)
                JOBS_PROCESSED.labels(job_type=job.job_type).inc()
                JOB_LATENCY.labels(job_type=job.job_type).observe(time.perf_counter() - started)
                logger.info("job_completed", job_id=job.id, latency_ms=round((time.perf_counter() - started) * 1000, 2))
            except Exception as exc:
                await self.handle_failure(repo, job, message, exc)

    async def handle_failure(self, repo: JobRepository, job: Job, message: QueueMessage, exc: Exception) -> None:
        error = repr(exc)
        if job.retry_count < job.max_retries:
            next_retry = job.retry_count + 1
            delay = min(2**next_retry, 300)
            await repo.mark_retrying(job, error)
            await self.queue.schedule_retry(job.id, job.priority, delay)
            await self.queue.ack(message)
            JOBS_FAILED.labels(job_type=job.job_type, terminal="false").inc()
            logger.warning("job_retry_scheduled", job_id=job.id, retry_count=next_retry, delay_seconds=delay, error=error)
        else:
            await repo.fail_terminal(job.id, error)
            await self.queue.move_to_dlq(job.id, error)
            await self.queue.ack(message)
            JOBS_FAILED.labels(job_type=job.job_type, terminal="true").inc()
            logger.error("job_moved_to_dlq", job_id=job.id, error=error)

    async def retry_promoter(self) -> None:
        while not self.stop_event.is_set():
            promoted = await self.queue.promote_due_retries()
            if promoted:
                logger.info("retry_jobs_promoted", count=promoted)
            await asyncio.sleep(1)

    async def stuck_job_reclaimer(self) -> None:
        while not self.stop_event.is_set():
            async with SessionLocal() as db:
                repo = JobRepository(db)
                for job in await repo.stuck_jobs(self.settings.stalled_job_grace_seconds):
                    await repo.mark_retrying(job, "job lock expired after worker crash or timeout")
                    await self.queue.enqueue(job.id, job.priority)
                    logger.warning("stuck_job_requeued", job_id=job.id)
            await asyncio.sleep(15)

    async def metrics_sampler(self) -> None:
        while not self.stop_event.is_set():
            for priority, length in (await self.queue.queue_lengths()).items():
                QUEUE_LENGTH.labels(priority=priority).set(length)
            await asyncio.sleep(5)


async def main() -> None:
    await Worker().start()


if __name__ == "__main__":
    asyncio.run(main())
