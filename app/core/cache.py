import redis.asyncio as redis
from app.core.config import settings

redis_pool = redis.ConnectionPool(host=settings.REDIS_HOST, port=settings.REDIS_PORT, max_connections=10, decode_responses=True)

async def get_redis():
    async with redis.Redis(connection_pool=redis_pool) as client:
        yield client

async def close_redis():
    await redis_pool.aclose()