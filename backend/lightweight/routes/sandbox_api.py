"""
Sandbox API Endpoints

CORS-free API for secure code execution in isolated Docker sandboxes.
All requests go through same origin (no CORS issues!).
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateSandboxRequest(BaseModel):
    workspace_id: str
    template: str = "python"  # python, nodejs, bash
    enable_network: bool = False

class CreateSandboxResponse(BaseModel):
    workspace_id: str
    sandbox_id: str
    template: str
    status: str
    message: str

class ExecuteCodeRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = 30

class ExecuteCodeResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    execution_time: float

class SandboxStatsResponse(BaseModel):
    workspace_id: str
    sandbox_id: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    uptime_seconds: float
    status: str

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create", response_model=CreateSandboxResponse)
async def create_sandbox(
    request: CreateSandboxRequest,
    background_tasks: BackgroundTasks
):
    """
    Create isolated Docker sandbox for code execution.
    
    Security features:
    - Read-only root filesystem
    - No network access (default)
    - Resource limits (512MB RAM, 50% CPU)
    - Runs as non-root user
    - All capabilities dropped
    """
    from services.sandbox_manager import sandbox_manager
    
    try:
        sandbox = await sandbox_manager.create_sandbox(
            workspace_id=request.workspace_id,
            template=request.template,
            enable_network=request.enable_network
        )
        
        return CreateSandboxResponse(
            workspace_id=sandbox.workspace_id,
            sandbox_id=sandbox.id,
            template=sandbox.template,
            status="running",
            message=f"Sandbox created successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sandbox: {str(e)}")


@router.post("/workspace/{workspace_id}/execute", response_model=ExecuteCodeResponse)
async def execute_code(
    workspace_id: str,
    request: ExecuteCodeRequest
):
    """
    Execute code in workspace sandbox.
    
    Code is validated for security before execution:
    - AST analysis for dangerous imports
    - Blocked functions: eval, exec, __import__, open
    - Blocked modules: os, subprocess, socket, urllib
    - Timeout enforcement
    """
    from services.sandbox_manager import sandbox_manager
    
    try:
        result = await sandbox_manager.execute_code(
            workspace_id=workspace_id,
            code=request.code,
            language=request.language,
            timeout=request.timeout
        )
        
        return ExecuteCodeResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/workspace/{workspace_id}/stats", response_model=SandboxStatsResponse)
async def get_sandbox_stats(workspace_id: str):
    """Get sandbox resource usage statistics."""
    from services.sandbox_manager import sandbox_manager
    
    stats = await sandbox_manager.get_sandbox_stats(workspace_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    return SandboxStatsResponse(**stats)


@router.delete("/workspace/{workspace_id}")
async def cleanup_sandbox(workspace_id: str):
    """Stop and remove sandbox container."""
    from services.sandbox_manager import sandbox_manager
    
    success = await sandbox_manager.cleanup_sandbox(workspace_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    return {"status": "cleaned_up", "workspace_id": workspace_id}


@router.get("/list")
async def list_sandboxes():
    """List all active sandboxes."""
    from services.sandbox_manager import sandbox_manager
    
    sandboxes = sandbox_manager.list_sandboxes()
    
    return {"sandboxes": sandboxes, "count": len(sandboxes)}


@router.post("/cleanup-idle")
async def cleanup_idle_sandboxes(background_tasks: BackgroundTasks):
    """Clean up sandboxes that have been idle for more than 1 hour."""
    from services.sandbox_manager import sandbox_manager
    
    background_tasks.add_task(sandbox_manager.cleanup_idle_sandboxes)
    
    return {"status": "cleanup_scheduled", "message": "Idle sandboxes will be cleaned up"}
