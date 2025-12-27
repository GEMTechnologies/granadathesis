"""
Unified API Hub - Central Manager for All External API Communications

This module provides:
1. Centralized API client management
2. Rate limiting and circuit breakers
3. Fallback chains for LLMs
4. Unified error handling
5. Request/response logging to Redis
"""

import asyncio
import os
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator, List
from dataclasses import dataclass
from enum import Enum


class APIProvider(Enum):
    """Available API providers."""
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    OPENAI = "openai"
    TAVILY = "tavily"
    UNSPLASH = "unsplash"
    PEXELS = "pexels"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    concurrent_requests: int = 10


class CircuitBreaker:
    """Simple circuit breaker for API resilience."""
    
    def __init__(self, failure_threshold: int = 5, recovery_time: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures: Dict[str, int] = {}
        self.last_failure_time: Dict[str, float] = {}
        self.open_circuits: Dict[str, bool] = {}
    
    def is_open(self, provider: str) -> bool:
        """Check if circuit is open (blocking requests)."""
        if provider not in self.open_circuits:
            return False
        
        if self.open_circuits[provider]:
            # Check if recovery time has passed
            if time.time() - self.last_failure_time.get(provider, 0) > self.recovery_time:
                self.open_circuits[provider] = False
                self.failures[provider] = 0
                return False
            return True
        return False
    
    def record_failure(self, provider: str):
        """Record a failure for a provider."""
        self.failures[provider] = self.failures.get(provider, 0) + 1
        self.last_failure_time[provider] = time.time()
        
        if self.failures[provider] >= self.failure_threshold:
            self.open_circuits[provider] = True
            print(f"⚡ Circuit breaker OPEN for {provider}", flush=True)
    
    def record_success(self, provider: str):
        """Record a success, resetting failure count."""
        self.failures[provider] = 0
        self.open_circuits[provider] = False


class APIHub:
    """
    Central hub for all external API communications.
    
    Features:
    - Unified interface for LLM calls
    - Automatic fallback between providers
    - Rate limiting
    - Circuit breaker pattern
    - Request logging to Redis
    """
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.redis = None
        self._request_counts: Dict[str, int] = {}
        self._last_minute: Dict[str, float] = {}
        
        # LLM fallback order
        self.llm_fallback_order = [
            APIProvider.DEEPSEEK,
            APIProvider.OPENROUTER,
            APIProvider.GEMINI,
        ]
    
    async def _ensure_redis(self):
        """Connect to Redis for logging."""
        if self.redis is None:
            try:
                import redis.asyncio as aioredis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
                    redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
                self.redis = aioredis.from_url(redis_url, decode_responses=True)
                await self.redis.ping()
            except Exception as e:
                print(f"⚠️ API Hub Redis unavailable: {e}", flush=True)
                self.redis = None
    
    async def _log_request(self, provider: str, request_type: str, success: bool, duration: float):
        """Log API request to Redis for monitoring."""
        await self._ensure_redis()
        if self.redis:
            try:
                log_entry = {
                    "provider": provider,
                    "type": request_type,
                    "success": success,
                    "duration_ms": int(duration * 1000),
                    "timestamp": time.time()
                }
                await self.redis.rpush("api_hub:logs", json.dumps(log_entry))
                await self.redis.ltrim("api_hub:logs", -1000, -1)  # Keep last 1000
            except:
                pass
    
    def _check_rate_limit(self, provider: str, limit: int = 60) -> bool:
        """Check if rate limit is exceeded."""
        current_minute = time.time() // 60
        
        if self._last_minute.get(provider) != current_minute:
            self._request_counts[provider] = 0
            self._last_minute[provider] = current_minute
        
        if self._request_counts.get(provider, 0) >= limit:
            return False
        
        self._request_counts[provider] = self._request_counts.get(provider, 0) + 1
        return True
    
    async def generate_llm_response(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        provider: Optional[APIProvider] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate LLM response with automatic fallback.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            provider: Specific provider to use (or auto-fallback)
            stream: Whether to stream response
        
        Yields:
            Response chunks
        """
        providers_to_try = [provider] if provider else self.llm_fallback_order
        
        for prov in providers_to_try:
            if self.circuit_breaker.is_open(prov.value):
                print(f"⚡ Skipping {prov.value} - circuit open", flush=True)
                continue
            
            if not self._check_rate_limit(prov.value):
                print(f"⚠️ Rate limit hit for {prov.value}", flush=True)
                continue
            
            start_time = time.time()
            try:
                async for chunk in self._call_llm_provider(prov, prompt, system_prompt, stream, **kwargs):
                    yield chunk
                
                self.circuit_breaker.record_success(prov.value)
                await self._log_request(prov.value, "llm", True, time.time() - start_time)
                return
                
            except Exception as e:
                print(f"❌ {prov.value} failed: {e}", flush=True)
                self.circuit_breaker.record_failure(prov.value)
                await self._log_request(prov.value, "llm", False, time.time() - start_time)
                continue
        
        # All providers failed
        yield "I apologize, but I'm having trouble connecting to AI services right now. Please try again in a moment."
    
    async def _call_llm_provider(
        self,
        provider: APIProvider,
        prompt: str,
        system_prompt: str,
        stream: bool,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Call specific LLM provider."""
        
        if provider == APIProvider.DEEPSEEK:
            from services.deepseek_direct import deepseek_direct
            async for chunk in deepseek_direct.generate_stream(prompt, system_prompt=system_prompt):
                yield chunk
        
        elif provider == APIProvider.OPENROUTER:
            from services.openrouter import openrouter_client
            async for chunk in openrouter_client.generate_stream(prompt, system_prompt=system_prompt):
                yield chunk
        
        elif provider == APIProvider.GEMINI:
            from services.gemini_direct import gemini_direct
            async for chunk in gemini_direct.generate_stream(prompt, system_prompt=system_prompt):
                yield chunk
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def search_images(self, query: str, limit: int = 6) -> List[Dict]:
        """Search images with fallback between providers."""
        try:
            from services.image_search import image_search_service
            return await image_search_service.search(query, limit=limit)
        except Exception as e:
            print(f"Image search error: {e}")
            return []
    
    async def search_web(self, query: str, limit: int = 5) -> List[Dict]:
        """Search web with Tavily or fallback."""
        try:
            from services.web_search import web_search_service
            return await web_search_service.search(query, limit=limit)
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    async def search_papers(self, query: str, limit: int = 10) -> List[Dict]:
        """Search academic papers."""
        try:
            from services.academic_search import academic_search_service
            return await academic_search_service.search(query, limit=limit)
        except Exception as e:
            print(f"Paper search error: {e}")
            return []
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all API providers."""
        return {
            "circuit_breakers": {
                p.value: {
                    "open": self.circuit_breaker.is_open(p.value),
                    "failures": self.circuit_breaker.failures.get(p.value, 0)
                }
                for p in APIProvider
            },
            "rate_limits": self._request_counts.copy()
        }


# Global instance
api_hub = APIHub()
