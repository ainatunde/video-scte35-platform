import json
import logging
from typing import Any

import redis.asyncio as aioredis

from ..config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish(channel: str, message: dict[str, Any]) -> None:
    r = await get_redis()
    await r.publish(channel, json.dumps(message))


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
