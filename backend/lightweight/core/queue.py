"""
Job Queue System for On-Demand Agent Awakening

Agents sleep until work appears in Redis queue, then wake up and process.
"""
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from core.cache import cache


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobQueue:
    """
    Redis-based job queue for agent awakening.
    
    Flow:
    1. API pushes job to queue
    2. Worker polls queue (blocking)
    3. Agent awakens, processes job
    4. Result stored, job marked complete
    5. Agent goes back to sleep
    """
    
    @classmethod
    async def push(
        cls,
        queue_name: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None,
        priority: str = "normal"
    ) -> str:
        """
        Push job to queue.
        
        Args:
            queue_name: Queue name (e.g., "objectives", "content")
            data: Job data
            job_id: Optional job ID
            
        Returns:
            Job ID
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "data": data,
            "status": JobStatus.QUEUED,
            "created_at": datetime.now().isoformat(),
            "queue": queue_name,
            "priority": priority
        }
        
        # Store job metadata
        await cache.set(f"job:{job_id}", job, ttl=86400)  # 24 hours
        
        # Push to queue with priority handling
        try:
            client = await cache.get_client()
            
            # Priority queues: high priority jobs go to separate queue or use sorted set
            if priority == "urgent" or priority == "high":
                # Push to high priority queue
                await client.lpush(f"queue:{queue_name}:priority", json.dumps(job))
                print(f"📤 Pushed HIGH PRIORITY job {job_id} to queue:{queue_name}", flush=True)
            else:
                # Normal queue
                await client.lpush(f"queue:{queue_name}", json.dumps(job))
                print(f"📤 Pushed job {job_id} to queue:{queue_name}", flush=True)
        except Exception as e:
            print(f"❌ Error pushing to queue: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        return job_id
    
    @classmethod
    async def pop(cls, queue_name: str, timeout: int = 0) -> Optional[Dict]:
        """
        Pop job from queue (blocking).
        
        Agent sleeps here until work appears.
        
        Args:
            queue_name: Queue name
            timeout: Timeout in seconds (0 = infinite)
            
        Returns:
            Job data or None
        """
        try:
            client = await cache.get_client()
            
            # Try priority queue first (non-blocking)
            priority_result = await client.rpop(f"queue:{queue_name}:priority")
            if priority_result:
                job = json.loads(priority_result)
                job["status"] = JobStatus.PROCESSING
                job["started_at"] = datetime.now().isoformat()
                await cache.set(f"job:{job['job_id']}", job)
                return job
            
            # Blocking pop from normal queue (agent sleeps here)
            result = await client.brpop(f"queue:{queue_name}", timeout=timeout)
            
            with open("queue_debug.log", "a") as f:
                f.write(f"BRPOP returned: {result}\n")
            
            if result:
                _, job_json = result
                job = json.loads(job_json)
                
                # Mark as processing
                job["status"] = JobStatus.PROCESSING
                job["started_at"] = datetime.now().isoformat()
                await cache.set(f"job:{job['job_id']}", job)
                
                return job
            
            return None
        except Exception as e:
            with open("queue_debug.log", "a") as f:
                f.write(f"Queue error: {e}\n")
            raise
    
    @classmethod
    async def complete(cls, job_id: str, result: Any):
        """Mark job as completed with result."""
        job = await cache.get(f"job:{job_id}")
        
        if job:
            job["status"] = JobStatus.COMPLETED
            job["completed_at"] = datetime.now().isoformat()
            job["result"] = result
            await cache.set(f"job:{job_id}", job, ttl=86400)
    
    @classmethod
    async def fail(cls, job_id: str, error: str):
        """Mark job as failed with error."""
        job = await cache.get(f"job:{job_id}")
        
        if job:
            job["status"] = JobStatus.FAILED
            job["failed_at"] = datetime.now().isoformat()
            job["error"] = error
            await cache.set(f"job:{job_id}", job, ttl=86400)
    
    @classmethod
    async def get_status(cls, job_id: str) -> Optional[Dict]:
        """Get job status and result."""
        return await cache.get(f"job:{job_id}")


# Worker decorator
def worker(queue_name: str):
    """
    Decorator to create a worker that processes jobs from queue.
    
    Usage:
        @worker("objectives")
        async def process_objective(data: Dict) -> Any:
            # Agent work here
            return result
    """
    def decorator(func: Callable):
        async def run_worker():
            print(f"🔄 Worker started: {queue_name}", flush=True)
            print(f"   Waiting for jobs (sleeping)...", flush=True)
            
            while True:
                try:
                    # Agent sleeps here until work appears
                    job = await JobQueue.pop(queue_name)
                    
                    if job:
                        job_id = job["job_id"]
                        data = job["data"]
                        
                        print(f"⚡ Agent awakened! Processing job {job_id}", flush=True)
                        
                        try:
                            # Agent does work
                            result = await func(data)
                            
                            # Mark complete
                            await JobQueue.complete(job_id, result)
                            
                            print(f"✓ Job {job_id} completed", flush=True)
                        
                        except Exception as e:
                            # Mark failed
                            await JobQueue.fail(job_id, str(e))
                            print(f"✗ Job {job_id} failed: {str(e)}", flush=True)
                            import traceback
                            traceback.print_exc()
                        
                        print(f"💤 Agent sleeping...", flush=True)
                
                except Exception as e:
                    print(f"Worker error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(5)  # Brief pause on error
        
        return run_worker
    
    return decorator
