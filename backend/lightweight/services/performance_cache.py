"""
Performance Cache System

Intelligent caching for API responses, plans, and tool results.
"""
import hashlib
import json
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from core.cache import cache


class PerformanceCache:
    """Intelligent caching system."""
    
    def __init__(self):
        self.default_ttl = 3600  # 1 hour
        self.plan_ttl = 1800  # 30 minutes
        self.search_ttl = 7200  # 2 hours
        self.image_ttl = 86400  # 24 hours
    
    def _make_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)
        
        hash_key = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        return f"cache:{prefix}:{hash_key}"
    
    async def get_plan(self, user_request: str, context: Dict) -> Optional[Dict]:
        """Get cached plan."""
        cache_key = self._make_key("plan", {"request": user_request, "context": context})
        return await cache.get(cache_key)
    
    async def set_plan(self, user_request: str, context: Dict, plan: Dict, ttl: Optional[int] = None):
        """Cache a plan."""
        cache_key = self._make_key("plan", {"request": user_request, "context": context})
        await cache.set(cache_key, plan, ttl=ttl or self.plan_ttl)
    
    async def get_search_results(self, query: str, tool: str) -> Optional[List]:
        """Get cached search results."""
        cache_key = self._make_key("search", {"query": query, "tool": tool})
        return await cache.get(cache_key)
    
    async def set_search_results(self, query: str, tool: str, results: List, ttl: Optional[int] = None):
        """Cache search results."""
        cache_key = self._make_key("search", {"query": query, "tool": tool})
        await cache.set(cache_key, results, ttl=ttl or self.search_ttl)
    
    async def get_image_result(self, prompt: str, model: str) -> Optional[Dict]:
        """Get cached image generation result."""
        cache_key = self._make_key("image", {"prompt": prompt, "model": model})
        return await cache.get(cache_key)
    
    async def set_image_result(self, prompt: str, model: str, result: Dict, ttl: Optional[int] = None):
        """Cache image generation result."""
        cache_key = self._make_key("image", {"prompt": prompt, "model": model})
        await cache.set(cache_key, result, ttl=ttl or self.image_ttl)
    
    async def invalidate(self, prefix: str):
        """Invalidate all cache entries with prefix."""
        # Note: This is a simplified version
        # In production, you'd want to track keys or use Redis pattern matching
        pass


# Global instance
performance_cache = PerformanceCache()

