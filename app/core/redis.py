import redis.asyncio as redis
from typing import Optional
from app.core.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

async def get_redis_client() -> redis.Redis:
    return redis_client
