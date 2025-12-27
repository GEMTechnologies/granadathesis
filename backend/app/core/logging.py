import logging
from typing import Set
from fastapi import WebSocket

# Global set of active WebSocket connections
active_connections: Set[WebSocket] = set()

class WebSocketLogHandler(logging.Handler):
    """Logging handler that broadcasts log records to all connected WebSocket clients."""
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        # Broadcast to all active websockets (non‑blocking)
        for ws in list(active_connections):
            try:
                # Use send_text without awaiting to avoid blocking logger
                ws.send_text(msg)
            except Exception:
                # Remove dead connections
                active_connections.discard(ws)
