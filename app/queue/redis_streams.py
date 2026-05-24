import json
import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config.settings import Settings


@dataclass(frozen=True)
class QueueMessage:
    stream: str
    message_id: str
    job_id: str
    priority: int


class RedisJobQueue:
    def __init__(self, redis: Redis, settings: Settings):
        self.redis = redis
        self.settings = settings

    def stream_for_priority(self, priority: int) -> str:
        band = "high" if priority <= 3 else "normal" if priority <= 7 else "low"
        return f"{self.settings.redis_stream_prefix}:{band}"

    @property
    def streams(self) -> list[str]:
        return [f"{self.settings.redis_stream_prefix}:{band}" for band in ("high", "normal", "low")]

    @property
    def retry_zset(self) -> str:
        return f"{self.settings.redis_stream_prefix}:retry_schedule"

    @property
    def dlq_stream(self) -> str:
        return f"{self.settings.redis_stream_prefix}:dlq"

    async def ensure_groups(self) -> None:
        for stream in self.streams:
            try:
                await self.redis.xgroup_create(stream, self.settings.consumer_group, id="0", mkstream=True)
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise

    async def enqueue(self, job_id: str, priority: int) -> str:
        stream = self.stream_for_priority(priority)
        return await self.redis.xadd(stream, {"job_id": job_id, "priority": str(priority)})

    async def schedule_retry(self, job_id: str, priority: int, delay_seconds: float) -> None:
        due_at = time.time() + delay_seconds
        await self.redis.zadd(self.retry_zset, {json.dumps({"job_id": job_id, "priority": priority}): due_at})

    async def promote_due_retries(self, limit: int = 100) -> int:
        now = time.time()
        items = await self.redis.zrangebyscore(self.retry_zset, min=0, max=now, start=0, num=limit)
        promoted = 0
        for raw in items:
            payload = json.loads(raw)
            removed = await self.redis.zrem(self.retry_zset, raw)
            if removed:
                await self.enqueue(payload["job_id"], int(payload["priority"]))
                promoted += 1
        return promoted

    async def read_next(self, consumer_name: str, block_ms: int = 5000) -> QueueMessage | None:
        stream_offsets = {stream: ">" for stream in self.streams}
        messages = await self.redis.xreadgroup(
            groupname=self.settings.consumer_group,
            consumername=consumer_name,
            streams=stream_offsets,
            count=1,
            block=block_ms,
        )
        if not messages:
            return None
        stream, entries = messages[0]
        message_id, fields = entries[0]
        return QueueMessage(
            stream=stream,
            message_id=message_id,
            job_id=fields["job_id"],
            priority=int(fields.get("priority", "5")),
        )

    async def ack(self, message: QueueMessage) -> None:
        await self.redis.xack(message.stream, self.settings.consumer_group, message.message_id)

    async def move_to_dlq(self, job_id: str, error: str) -> None:
        await self.redis.xadd(self.dlq_stream, {"job_id": job_id, "error": error[:4000]})

    async def queue_lengths(self) -> dict[str, int]:
        return {stream.rsplit(":", 1)[-1]: await self.redis.xlen(stream) for stream in self.streams}
