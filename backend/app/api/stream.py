"""
Streaming API Endpoint for Agent Actions

Provides Server-Sent Events (SSE) stream of all agent actions for real-time updates.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import time
from typing import Dict, Any
import redis.asyncio as redis

router = APIRouter(prefix="/api/stream", tags=["Stream"])

# Store active sessions/jobs
_active_streams: Dict[str, asyncio.Queue] = {}


class AgentActionStreamer:
    """Manages streaming of agent actions to clients."""
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
    
    async def connect_redis(self):
        """Connect to Redis for event distribution."""
        try:
            self.redis_client = redis.from_url("redis://localhost", decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("agent_actions")
        except Exception as e:
            print(f"Redis connection failed (optional): {e}")
            self.redis_client = None
    
    async def stream_agent_actions(self, session_id: str = None):
        """
        Stream agent actions via SSE.
        
        This generator yields Server-Sent Events that the frontend can listen to.
        """
        if session_id is None:
            session_id = "default"
        
        # Create a queue for this stream
        action_queue = asyncio.Queue()
        _active_streams[session_id] = action_queue
        
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "message": "Stream connected"
                })
            }
            
            # Connect to Redis if available
            if not self.redis_client:
                await self.connect_redis()
            
            # If Redis is connected, listen to pub/sub
            if self.redis_client and self.pubsub:
                async def redis_listener():
                    async for message in self.pubsub.listen():
                        if message["type"] == "message":
                            try:
                                action_data = json.loads(message["data"])
                                await action_queue.put(action_data)
                            except Exception as e:
                                print(f"Error processing Redis message: {e}")
                
                # Start Redis listener in background
                redis_task = asyncio.create_task(redis_listener())
                
                try:
                    # Process actions from queue
                    while True:
                        try:
                            # Wait for action with timeout to allow periodic checks
                            action = await asyncio.wait_for(action_queue.get(), timeout=1.0)
                            
                            yield {
                                "event": "action",
                                "data": json.dumps(action)
                            }
                        except asyncio.TimeoutError:
                            # Send keepalive
                            yield {
                                "event": "keepalive",
                                "data": json.dumps({"timestamp": time.time()})
                            }
                finally:
                    redis_task.cancel()
            else:
                # Fallback: just send keepalives if Redis not available
                while True:
                    yield {
                        "event": "keepalive",
                        "data": json.dumps({
                            "timestamp": time.time(),
                            "message": "Stream active (Redis not available)"
                        })
                    }
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup
            if session_id in _active_streams:
                del _active_streams[session_id]
    
    async def publish_action(self, session_id: str, action: Dict[str, Any]):
        """
        Publish an agent action to all streams.
        
        This can be called by agents to push actions to the frontend.
        """
        # Add timestamp if not present
        if "timestamp" not in action:
            action["timestamp"] = time.time()
        
        # Send to queue if exists
        if session_id in _active_streams:
            await _active_streams[session_id].put(action)
        
        # Also publish to Redis for multi-server support
        if self.redis_client:
            try:
                await self.redis_client.publish(
                    "agent_actions",
                    json.dumps({"session_id": session_id, **action})
                )
            except Exception as e:
                print(f"Redis publish failed: {e}")


# Singleton instance
streamer = AgentActionStreamer()


@router.get("/agent-actions")
async def stream_agent_actions(request: Request, session_id: str = "default"):
    """
    SSE endpoint for streaming agent actions.
    
    Usage:
        const eventSource = new EventSource('/api/stream/agent-actions?session_id=my-session');
        eventSource.addEventListener('action', (e) => {
            const action = JSON.parse(e.data);
            console.log('Agent action:', action);
        });
    """
    async def event_generator():
        async for event in streamer.stream_agent_actions(session_id):
            yield event
    
    # Create SSE response
    async def event_generator_wrapper():
        async for event in streamer.stream_agent_actions(session_id):
            yield event
    
    # Create SSE response with explicit CORS headers
    response = EventSourceResponse(event_generator_wrapper())
    
    # Set CORS headers for SSE - EventSource is very sensitive to CORS
    # Use wildcard for development (matches browser origin automatically)
    origin = request.headers.get("origin", "*")
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    
    response.headers["Access-Control-Allow-Credentials"] = "false"
    response.headers["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Last-Event-ID"
    response.headers["Access-Control-Expose-Headers"] = "*"
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    
    return response


@router.post("/publish")
async def publish_action(action: Dict[str, Any], session_id: str = "default"):
    """
    Publish an agent action to the stream.
    
    This endpoint can be called by agents or backend services to push actions.
    """
    await streamer.publish_action(session_id, action)
    return {"status": "published", "session_id": session_id}


@router.get("/health")
async def stream_health():
    """Health check for streaming endpoint."""
    return {
        "status": "ok",
        "active_streams": len(_active_streams),
        "redis_connected": streamer.redis_client is not None
    }



