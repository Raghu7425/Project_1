from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.queue.redis_streams import RedisJobQueue
from app.repositories.users import UserRepository
from app.utils.redis import get_redis
from app.utils.security import decode_access_token


async def redis_dependency() -> Redis:
    redis = get_redis()
    try:
        yield redis
    finally:
        await redis.aclose()


def settings_dependency() -> Settings:
    return get_settings()


def queue_dependency(
    redis: Annotated[Redis, Depends(redis_dependency)],
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> RedisJobQueue:
    return RedisJobQueue(redis, settings)


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        user_id = decode_access_token(authorization.removeprefix("Bearer ").strip())
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    user = await UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user
