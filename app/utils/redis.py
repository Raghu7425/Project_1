from redis.asyncio import Redis

from app.config.settings import get_settings


def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)
