"""
Event Publisher for Real-Time Updates.

Publishes events to Redis channels that the API subscribes to for SSE.
"""
import json
import time
import redis.asyncio as redis
import os


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'as_posix'):
            return obj.as_posix()
        try:
            from pathlib import Path
            if isinstance(obj, Path):
                return str(obj)
        except ImportError:
            pass
        return super().default(obj)

class EventPublisher:
    def __init__(self):
        # Try to get from config first, then env var, then default
        try:
            from core.config import settings
            redis_url = settings.REDIS_URL
        except:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # If it's a Docker hostname but we're not in Docker, use localhost
        if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
            redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
        
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            try:
                await self.redis.ping()
                print(f"✓ Event publisher connected to Redis", flush=True)
            except Exception as e:
                print(f"❌ Event publisher Redis connection failed: {e}", flush=True)
                raise

    async def publish(self, job_id: str, event_type: str, data: dict, session_id: str = None):
        """
        Publish an event to the job's channel AND session channel.
        
        Args:
            job_id: The ID of the job (used as channel name)
            event_type: 'log', 'graph_node', 'debate_message', 'progress', 'file_created', 'file_updated', 'stage_completed'
            data: The payload
            session_id: Optional session ID for cross-job messaging
        """
        if not self.redis:
            await self.connect()
            
        message = {
            "timestamp": time.time(),
            "type": event_type,
            "data": data,
            "job_id": job_id  # Include job_id in payload for frontend routing
        }
        
        json_message = json.dumps(message, cls=ExtendedJSONEncoder)
        
        # Publish to job-specific channel
        await self.redis.publish(f"job:{job_id}", json_message)
        
        # ALSO publish to session channel for continuous chat
        # This allows frontend to receive ALL events for the session
        if session_id:
            await self.redis.publish(f"session:{session_id}", json_message)
        else:
            # If no session_id provided, try to extract from data or use default
            sess = data.get("session_id", data.get("workspace_id", "default"))
            if sess:
                await self.redis.publish(f"session:{sess}", json_message)
        
        # PERSISTENCE: Store in history list (expire after 24h) - non-blocking
        history_key = f"job:{job_id}:history"
        try:
            await self.redis.rpush(history_key, json_message)
            await self.redis.expire(history_key, 300)
        except:
            pass  # Don't block on history storage
        
        # Also log to console for debugging (only for important events to reduce noise)
        if event_type in ["reasoning_chunk", "response_chunk", "agent_activity", "file_created"]:
            print(f"📡 Event [{event_type}]: {str(data)[:50]}...", flush=True)
    
    # Convenience methods for common events
    # All methods now accept session_id for continuous chat support
    async def log(self, job_id: str, message: str, level: str = "info", session_id: str = None):
        """Publish a log message."""
        await self.publish(job_id, "log", {"message": message, "level": level}, session_id=session_id)
    
    async def file_created(self, job_id: str, file_path: str, file_type: str, session_id: str = None):
        """Publish a file creation event."""
        await self.publish(job_id, "file_created", {
            "path": file_path,
            "type": file_type,
            "timestamp": time.time()
        }, session_id=session_id)
    
    async def file_updated(self, job_id: str, file_path: str, session_id: str = None):
        """Publish a file update event."""
        await self.publish(job_id, "file_updated", {
            "path": file_path,
            "timestamp": time.time()
        }, session_id=session_id)
    
    async def stage_completed(self, job_id: str, stage_name: str, metadata: dict = None, session_id: str = None):
        """Publish a stage completion event."""
        await self.publish(job_id, "stage_completed", {
            "stage": stage_name,
            "metadata": metadata or {},
            "timestamp": time.time()
        }, session_id=session_id)

    async def stage_started(self, job_id: str, stage_name: str, metadata: dict = None, session_id: str = None):
        """Publish a stage start event."""
        payload = {
            "stage": stage_name,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        if metadata and isinstance(metadata, dict) and metadata.get("message"):
            payload["message"] = metadata.get("message")
        await self.publish(job_id, "stage_started", payload, session_id=session_id)
    
    async def debate_message(self, job_id: str, speaker: str, message: str, objectives: list = None, session_id: str = None):
        """Publish a debate message with optional objectives."""
        data = {
            "speaker": speaker,
            "message": message
        }
        if objectives:
            data["objectives"] = objectives
        await self.publish(job_id, "debate_message", data, session_id=session_id)
    
    async def response_chunk(self, job_id: str, chunk: str, accumulated: str, completed: bool = False, session_id: str = None):
        """Publish a response chunk for streaming."""
        await self.publish(job_id, "response_chunk", {
            "chunk": chunk,
            "accumulated": accumulated,
            "completed": completed
        }, session_id=session_id)
    
    async def stream_start(self, job_id: str, session_id: str = None):
        """Publish stream start event."""
        await self.publish(job_id, "stream_start", {"timestamp": time.time()}, session_id=session_id)
    
    async def stream_end(self, job_id: str, session_id: str = None):
        """Publish stream end event."""
        await self.publish(job_id, "stream_end", {"timestamp": time.time()}, session_id=session_id)

# Global instance
events = EventPublisher()
