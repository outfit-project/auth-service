from typing import Annotated, AsyncIterator

from fastapi import Depends
from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True,
    health_check_interval=30,
)


def get_redis_pool() -> ConnectionPool:
    return _pool


async def get_redis() -> AsyncIterator[Redis]:
    client = Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        await client.aclose()


RedisDep = Annotated[Redis, Depends(get_redis)]


async def close_redis() -> None:
    await _pool.aclose()
