"""
Shared Redis cache for all services.
"""
import os
import redis.asyncio as redis
from typing import Optional


class CacheConnection:
    """Singleton Redis connection."""
    
    _instance: redis.Redis = None
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client."""
        if cls._instance is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            cls._instance = await redis.from_url(redis_url, decode_responses=True)
        
        return cls._instance


# Convenience functions
async def get_cache() -> redis.Redis:
    """Get cache client."""
    return await CacheConnection.get_client()


async def cache_get(key: str) -> Optional[str]:
    """Get value from cache."""
    client = await get_cache()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600):
    """Set value in cache with TTL."""
    client = await get_cache()
    await client.setex(key, ttl, value)
