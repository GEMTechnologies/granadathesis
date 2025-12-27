from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import active_connections, WebSocketLogHandler
import logging
import asyncio
import redis.asyncio as redis

router = APIRouter()
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(WebSocketLogHandler())

@router.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)
    try:
        while True:
            # Keep connection alive; client may send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(ws)

# Redis subscriber coroutine to forward messages to WebSocket clients
async def redis_subscriber():
    try:
        redis_client = redis.from_url("redis://localhost", decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("backend_events")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                msg = message["data"]
                for ws in list(active_connections):
                    try:
                        await ws.send_text(f"REDIS: {msg}")
                    except Exception:
                        active_connections.discard(ws)
    except Exception as e:
        logger.warning(f"Redis subscriber error (Redis may not be running): {e}")
        # Continue without Redis - the app should work without it
