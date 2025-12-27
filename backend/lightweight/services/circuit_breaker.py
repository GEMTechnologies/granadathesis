"""
Circuit Breaker Pattern

Prevents cascading failures by stopping requests to failing services.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
from core.cache import cache


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for service calls."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: Optional[datetime] = None
    
    async def _get_state(self) -> Dict:
        """Get state from cache."""
        state_key = f"circuit:{self.name}"
        state_data = await cache.get(state_key)
        if state_data:
            self.state = CircuitState(state_data.get("state", "closed"))
            self.failure_count = state_data.get("failure_count", 0)
            self.success_count = state_data.get("success_count", 0)
            if state_data.get("last_failure_time"):
                self.last_failure_time = datetime.fromisoformat(state_data["last_failure_time"])
            if state_data.get("last_state_change"):
                self.last_state_change = datetime.fromisoformat(state_data["last_state_change"])
        return state_data or {}
    
    async def _save_state(self):
        """Save state to cache."""
        state_key = f"circuit:{self.name}"
        state_data = {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None
        }
        await cache.set(state_key, state_data, ttl=3600)
    
    async def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        await self._get_state()
        
        # Check if circuit should transition
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    # Try to recover
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.last_state_change = datetime.now()
                    await self._save_state()
                    print(f"🔄 Circuit {self.name} entering HALF_OPEN state")
                else:
                    # Still in open state, reject immediately
                    raise Exception(f"Circuit breaker {self.name} is OPEN. Service unavailable.")
        
        # Attempt call
        try:
            result = await func(*args, **kwargs)
            
            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    # Recovered
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = datetime.now()
                    await self._save_state()
                    print(f"✅ Circuit {self.name} recovered, entering CLOSED state")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = max(0, self.failure_count - 1)
                    await self._save_state()
            
            return result
            
        except Exception as e:
            # Failure
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                # Failed during recovery, go back to open
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.last_state_change = datetime.now()
                await self._save_state()
                print(f"❌ Circuit {self.name} failed during recovery, entering OPEN state")
            elif self.failure_count >= self.failure_threshold:
                # Too many failures, open circuit
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
                await self._save_state()
                print(f"⚠️ Circuit {self.name} opened after {self.failure_count} failures")
            
            await self._save_state()
            raise
    
    async def get_status(self) -> Dict:
        """Get circuit breaker status."""
        await self._get_state()
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


# Global circuit breakers
circuit_breakers = {
    "planner": CircuitBreaker("planner", failure_threshold=3, recovery_timeout=30),
    "deepseek": CircuitBreaker("deepseek", failure_threshold=5, recovery_timeout=60),
    "image_generation": CircuitBreaker("image_generation", failure_threshold=3, recovery_timeout=30),
    "web_search": CircuitBreaker("web_search", failure_threshold=5, recovery_timeout=60),
    "image_search": CircuitBreaker("image_search", failure_threshold=5, recovery_timeout=60)
}




