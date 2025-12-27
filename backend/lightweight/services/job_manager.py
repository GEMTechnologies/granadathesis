"""
Job Manager Service - Persistent Background Job Execution

Features:
- Jobs run independently of frontend connection
- State persisted to disk (survives browser close, server restart)
- Pause/Resume/Cancel controls
- Reconnectable SSE streams
- Progress tracking and step logging
"""

import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, asdict, field

from services.workspace_service import WORKSPACES_DIR


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobStep:
    """A step in the job execution."""
    name: str
    status: str  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class Job:
    """Persistent job state."""
    job_id: str
    workspace_id: str
    message: str
    status: JobStatus
    progress: float = 0.0
    current_step: str = ""
    steps: List[Dict] = field(default_factory=list)
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Execution metadata
    mentioned_agents: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value if isinstance(self.status, JobStatus) else self.status
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Job':
        """Create from dictionary."""
        data['status'] = JobStatus(data.get('status', 'pending'))
        return cls(**data)


class JobManager:
    """
    Manages persistent background jobs.
    
    Jobs are stored as JSON files and run in background asyncio tasks.
    They continue running even if the frontend disconnects.
    """
    
    def __init__(self):
        self._active_jobs: Dict[str, asyncio.Task] = {}
        self._job_events: Dict[str, asyncio.Queue] = {}  # For SSE streaming
        self._pause_flags: Dict[str, asyncio.Event] = {}  # For pause/resume
        self._cancel_flags: Dict[str, bool] = {}
    
    def _get_jobs_dir(self, workspace_id: str) -> Path:
        """Get the jobs directory for a workspace."""
        jobs_dir = WORKSPACES_DIR / workspace_id / "data" / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        return jobs_dir
    
    def _get_job_path(self, workspace_id: str, job_id: str) -> Path:
        """Get the path to a job file."""
        return self._get_jobs_dir(workspace_id) / f"{job_id}.json"
    
    def _save_job(self, job: Job):
        """Save job state to disk."""
        job.updated_at = datetime.now().isoformat()
        job_path = self._get_job_path(job.workspace_id, job.job_id)
        job_path.write_text(json.dumps(job.to_dict(), indent=2, ensure_ascii=False), encoding='utf-8')
    
    def _load_job(self, workspace_id: str, job_id: str) -> Optional[Job]:
        """Load job state from disk."""
        job_path = self._get_job_path(workspace_id, job_id)
        if job_path.exists():
            try:
                data = json.loads(job_path.read_text(encoding='utf-8'))
                return Job.from_dict(data)
            except Exception as e:
                print(f"⚠️ Error loading job {job_id}: {e}")
        return None
    
    async def create_job(
        self,
        workspace_id: str,
        message: str,
        mentioned_agents: Optional[List[str]] = None,
        files: Optional[List[str]] = None
    ) -> Job:
        """
        Create a new persistent job.
        
        Returns the job immediately - execution happens in background.
        """
        job_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        job = Job(
            job_id=job_id,
            workspace_id=workspace_id,
            message=message,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            mentioned_agents=mentioned_agents or [],
            files=files or []
        )
        
        # Save job to disk
        self._save_job(job)
        
        # Create event queue for SSE streaming
        self._job_events[job_id] = asyncio.Queue()
        
        # Create pause flag (set = running, clear = paused)
        self._pause_flags[job_id] = asyncio.Event()
        self._pause_flags[job_id].set()  # Start unpaused
        
        # Cancel flag
        self._cancel_flags[job_id] = False
        
        print(f"📋 Created job {job_id} for workspace {workspace_id}")
        
        return job
    
    async def start_job(
        self,
        job: Job,
        processor: Callable[['Job', 'JobManager'], Awaitable[None]]
    ):
        """
        Start job execution in background.
        
        Args:
            job: The job to execute
            processor: Async function that processes the job
        """
        async def _run_job():
            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now().isoformat()
                self._save_job(job)
                
                await self.emit_event(job.job_id, "status", {"status": "running"})
                
                # Run the processor
                await processor(job, self)
                
                # Mark completed if not cancelled/failed
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now().isoformat()
                    job.progress = 1.0
                    self._save_job(job)
                    await self.emit_event(job.job_id, "completed", {"result": job.result})
                    
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                self._save_job(job)
                await self.emit_event(job.job_id, "cancelled", {})
                
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                self._save_job(job)
                await self.emit_event(job.job_id, "error", {"error": str(e)})
                print(f"❌ Job {job.job_id} failed: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                # Cleanup
                self._active_jobs.pop(job.job_id, None)
                
        # Start the background task
        task = asyncio.create_task(_run_job())
        self._active_jobs[job.job_id] = task
    
    async def update_progress(
        self,
        job: Job,
        progress: float,
        current_step: str,
        data: Optional[Dict] = None
    ):
        """Update job progress and emit event."""
        # Check for pause
        if job.job_id in self._pause_flags:
            await self._pause_flags[job.job_id].wait()
        
        # Check for cancel
        if self._cancel_flags.get(job.job_id, False):
            job.status = JobStatus.CANCELLED
            self._save_job(job)
            raise asyncio.CancelledError("Job cancelled by user")
        
        job.progress = progress
        job.current_step = current_step
        self._save_job(job)
        
        await self.emit_event(job.job_id, "progress", {
            "progress": progress,
            "step": current_step,
            "data": data
        })
    
    async def add_step(self, job: Job, step_name: str, status: str = "running"):
        """Add or update a step in the job."""
        step = {
            "name": step_name,
            "status": status,
            "started_at": datetime.now().isoformat()
        }
        
        # Check if step exists
        existing = next((s for s in job.steps if s.get("name") == step_name), None)
        if existing:
            existing.update(step)
        else:
            job.steps.append(step)
        
        self._save_job(job)
        await self.emit_event(job.job_id, "step", {"step": step})
    
    async def complete_step(self, job: Job, step_name: str, result: Optional[Dict] = None):
        """Mark a step as completed."""
        for step in job.steps:
            if step.get("name") == step_name:
                step["status"] = "completed"
                step["completed_at"] = datetime.now().isoformat()
                if result:
                    step["result"] = result
                break
        
        self._save_job(job)
        await self.emit_event(job.job_id, "step_complete", {"step": step_name, "result": result})
    
    async def emit_event(self, job_id: str, event_type: str, data: Dict):
        """Emit an event for SSE streaming."""
        if job_id in self._job_events:
            await self._job_events[job_id].put({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
    
    async def emit_log(self, job_id: str, message: str, level: str = "info"):
        """Emit a log message."""
        await self.emit_event(job_id, "log", {"message": message, "level": level})
    
    async def emit_content(self, job_id: str, content: str, file_path: Optional[str] = None):
        """Emit generated content (for streaming text)."""
        await self.emit_event(job_id, "content", {"content": content, "file_path": file_path})
    
    def get_job(self, workspace_id: str, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._load_job(workspace_id, job_id)
    
    def list_jobs(
        self,
        workspace_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[Job]:
        """List jobs for a workspace."""
        jobs_dir = self._get_jobs_dir(workspace_id)
        jobs = []
        
        for job_file in sorted(jobs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if len(jobs) >= limit:
                break
            
            try:
                data = json.loads(job_file.read_text(encoding='utf-8'))
                job = Job.from_dict(data)
                
                if status is None or job.status == status:
                    jobs.append(job)
            except Exception as e:
                print(f"⚠️ Error loading job file {job_file}: {e}")
        
        return jobs
    
    def get_active_jobs(self, workspace_id: str) -> List[Job]:
        """Get currently running or paused jobs."""
        return self.list_jobs(workspace_id, status=None)
    
    async def pause_job(self, workspace_id: str, job_id: str) -> bool:
        """Pause a running job."""
        job = self._load_job(workspace_id, job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False
        
        if job_id in self._pause_flags:
            self._pause_flags[job_id].clear()  # Clear = paused
        
        job.status = JobStatus.PAUSED
        self._save_job(job)
        await self.emit_event(job_id, "paused", {})
        print(f"⏸️ Job {job_id} paused")
        return True
    
    async def resume_job(self, workspace_id: str, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._load_job(workspace_id, job_id)
        if not job or job.status != JobStatus.PAUSED:
            return False
        
        if job_id in self._pause_flags:
            self._pause_flags[job_id].set()  # Set = running
        
        job.status = JobStatus.RUNNING
        self._save_job(job)
        await self.emit_event(job_id, "resumed", {})
        print(f"▶️ Job {job_id} resumed")
        return True
    
    async def cancel_job(self, workspace_id: str, job_id: str) -> bool:
        """Cancel a running or paused job."""
        job = self._load_job(workspace_id, job_id)
        if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        # Set cancel flag
        self._cancel_flags[job_id] = True
        
        # If paused, resume to allow cancel check
        if job_id in self._pause_flags:
            self._pause_flags[job_id].set()
        
        # Cancel the task if running
        if job_id in self._active_jobs:
            self._active_jobs[job_id].cancel()
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now().isoformat()
        self._save_job(job)
        await self.emit_event(job_id, "cancelled", {})
        print(f"🛑 Job {job_id} cancelled")
        return True
    
    async def get_event_stream(self, job_id: str):
        """
        Generator for SSE events.
        
        Can be called multiple times (e.g., on reconnect).
        """
        if job_id not in self._job_events:
            self._job_events[job_id] = asyncio.Queue()
        
        queue = self._job_events[job_id]
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {"type": "heartbeat", "data": {}, "timestamp": datetime.now().isoformat()}
        except asyncio.CancelledError:
            pass
    
    def is_job_active(self, job_id: str) -> bool:
        """Check if a job is currently being executed."""
        return job_id in self._active_jobs
    
    async def recover_jobs(self, workspace_id: str):
        """
        Recover interrupted jobs on server restart.
        
        Jobs that were 'running' when server stopped are marked as 'failed'
        with option to retry.
        """
        jobs = self.list_jobs(workspace_id)
        recovered = 0
        
        for job in jobs:
            if job.status == JobStatus.RUNNING:
                # Job was interrupted - mark as failed
                job.status = JobStatus.FAILED
                job.error = "Server restarted - job interrupted"
                self._save_job(job)
                recovered += 1
        
        if recovered > 0:
            print(f"⚠️ Recovered {recovered} interrupted jobs in workspace {workspace_id}")
        
        return recovered


# Singleton instance
job_manager = JobManager()
