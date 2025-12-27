"""
Redis Cache Layer with Automatic Serialization

Provides ultra-fast caching for:
- Database queries
- API responses
- Generated content
"""
import os
import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
import redis.asyncio as redis


class CacheLayer:
    """
    High-performance Redis cache layer.
    
    Features:
    - Automatic JSON serialization
    - Decorator for easy caching
    - TTL support
    - Cache invalidation
    """
    
    _client: Optional[redis.Redis] = None
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client."""
        if cls._client is None:
            # Try to get from config first, then env var, then default to localhost
            try:
                from core.config import settings
                redis_url = settings.REDIS_URL
            except:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            
            # If it's a Docker hostname but we're not in Docker, use localhost
            if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
                redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
            
            print(f"🔌 Connecting to Redis: {redis_url.replace('://', '://***')}", flush=True)
            cls._client = await redis.from_url(
                redis_url,
                decode_responses=True,
                max_connections=20,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            try:
                await cls._client.ping()
                print(f"✓ Redis cache connected to {redis_url.split('@')[-1] if '@' in redis_url else redis_url}", flush=True)
            except Exception as e:
                print(f"❌ Redis connection failed: {e}", flush=True)
                raise
        
        return cls._client
    
    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get value from cache."""
        client = await cls.get_client()
        value = await client.get(key)
        
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        return None
    
    @classmethod
    async def set(cls, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (default 1 hour)."""
        client = await cls.get_client()
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        await client.setex(key, ttl, value)
    
    @classmethod
    async def delete(cls, key: str):
        """Delete key from cache."""
        client = await cls.get_client()
        await client.delete(key)
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists."""
        client = await cls.get_client()
        return await client.exists(key) > 0
    
    @classmethod
    def cache_key(cls, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = f"{args}:{kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Usage:
        @cached(ttl=1800, key_prefix="objectives")
        async def get_objectives(thesis_id: str):
            return await db.fetch(...)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{CacheLayer.cache_key(*args, **kwargs)}"
            
            # Check cache
            cached_result = await CacheLayer.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await CacheLayer.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator


# Convenience alias
cache = CacheLayer
