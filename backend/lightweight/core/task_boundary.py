"""
Task Boundary System - Publishes structured task progress events.

This module provides a way to track and communicate agent progress in real-time
through the existing SSE streaming infrastructure.
"""

from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import uuid


class TaskBoundary(BaseModel):
    """Task boundary event model"""
    task_id: str
    task_name: str
    task_status: str = ""
    task_summary: str = ""
    mode: Literal["PLANNING", "EXECUTION", "VERIFICATION"]
    progress: float = 0.0  # 0.0 to 1.0
    parent_task_id: Optional[str] = None
    timestamp: datetime
    content: Optional[str] = None  # Optional markdown content


class TaskProgressPublisher:
    """
    Publishes task progress events through SSE stream.
    
    Usage:
        task_pub = TaskProgressPublisher(agent_run_id, redis_client)
        
        main_task = await task_pub.start_task("Research Papers", "PLANNING")
        await task_pub.update_task(main_task, status="Analyzing 15 sources", progress=0.5)
        await task_pub.complete_task(main_task, "Found 127 relevant papers")
    """
    
    def __init__(self, agent_run_id: str, redis_client):
        self.agent_run_id = agent_run_id
        self.redis = redis_client
        self.current_task_stack = []  # Track task hierarchy
        
    async def start_task(
        self, 
        task_name: str, 
        mode: Literal["PLANNING", "EXECUTION", "VERIFICATION"],
        parent_task_id: Optional[str] = None
    ) -> str:
        """
        Start a new task.
        
        Args:
            task_name: Human-readable task name
            mode: Current agent mode
            parent_task_id: Optional parent task ID for hierarchy
            
        Returns:
            task_id: Unique identifier for this task
        """
        task_id = str(uuid.uuid4())
        
        task = TaskBoundary(
            task_id=task_id,
            task_name=task_name,
            task_status="Initializing...",
            task_summary="",
            mode=mode,
            progress=0.0,
            parent_task_id=parent_task_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        await self._publish_event("task_started", task)
        self.current_task_stack.append(task_id)
        return task_id
    
    async def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        progress: Optional[float] = None,
        content: Optional[str] = None
    ):
        """
        Update task progress.
        
        Args:
            task_id: Task to update
            status: Current status message
            summary: Summary of work done so far
            progress: Progress from 0.0 to 1.0
            content: Optional markdown content
        """
        update_data = {
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if status is not None:
            update_data["task_status"] = status
        if summary is not None:
            update_data["task_summary"] = summary
        if progress is not None:
            update_data["progress"] = progress
        if content is not None:
            update_data["content"] = content
        
        await self._publish_event("task_updated", update_data)
    
    async def complete_task(self, task_id: str, summary: str):
        """
        Mark task as complete.
        
        Args:
            task_id: Task to complete
            summary: Final summary of accomplishments
        """
        await self._publish_event("task_completed", {
            "task_id": task_id,
            "task_summary": summary,
            "progress": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if task_id in self.current_task_stack:
            self.current_task_stack.remove(task_id)
    
    async def error_task(self, task_id: str, error_message: str):
        """
        Mark task as errored.
        
        Args:
            task_id: Task that errored
            error_message: Error description
        """
        await self._publish_event("task_error", {
            "task_id": task_id,
            "task_status": f"Error: {error_message}",
            "progress": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if task_id in self.current_task_stack:
            self.current_task_stack.remove(task_id)
    
    async def _publish_event(self, event_type: str, data):
        """Publish event through existing SSE stream"""
        event = {
            "type": "task_progress",
            "event_type": event_type,
            "data": data.dict() if hasattr(data, 'dict') else data
        }
        
        # Add to response list for SSE streaming
        response_key = f"agent_run:{self.agent_run_id}:responses"
        await self.redis.rpush(response_key, json.dumps(event))
        
        # Notify listeners
        channel = f"agent_run:{self.agent_run_id}:new_response"
        await self.redis.publish(channel, "new")
        
        print(f"📊 Task Event: {event_type} - {data}", flush=True)
