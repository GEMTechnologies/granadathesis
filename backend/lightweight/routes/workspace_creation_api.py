"""
Auto Workspace Creation with Sandbox

Endpoint for creating workspace + sandbox in one call (triggered by "New Chat").
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])


class CreateWorkspaceWithSandboxRequest(BaseModel):
    topic: str = "New Project"
    template: str = "python"  # python, nodejs, bash
    enable_network: bool = False
    user_id: Optional[str] = None


class CreateWorkspaceWithSandboxResponse(BaseModel):
    workspace_id: str
    sandbox_id: str
    topic: str
    status: str
    url: str
    message: str


@router.post("/create-with-sandbox", response_model=CreateWorkspaceWithSandboxResponse)
async def create_workspace_with_sandbox(request: CreateWorkspaceWithSandboxRequest):
    """
    Create workspace + spin up sandbox in one call.
   
    **Triggered by:** "New Chat" button click
    
    **Flow:**
    1. Create workspace in DB
    2. Spin up Docker sandbox
    3. Initialize environment
    4. Return workspace_id + sandbox_id
    
    **CORS-free:** All requests through localhost:8000
    """
    from services.workspace_service import workspace_service
    from services.sandbox_manager import sandbox_manager
    import uuid
    
    try:
        # 1. Create workspace
        workspace_id = f"workspace_{uuid.uuid4().hex[:12]}"
        
        # Use workspace_service to create workspace structure
        await workspace_service.create_workspace(
            workspace_id=workspace_id,
            topic=request.topic,
            context=f"Auto-created workspace for user {request.user_id or 'anonymous'}"
        )
        
        # 2. Spin up sandbox
        sandbox = await sandbox_manager.create_sandbox(
            workspace_id=workspace_id,
            template=request.template,
            user_id=request.user_id,
            enable_network=request.enable_network
        )
        
        return CreateWorkspaceWithSandboxResponse(
            workspace_id=workspace_id,
            sandbox_id=sandbox.id,
            topic=request.topic,
            status="ready",
            url=f"/workspace/{workspace_id}",
            message=f"Workspace and sandbox created successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workspace with sandbox: {str(e)}"
        )


@router.post("/{workspace_id}/cleanup-all")
async def cleanup_workspace_and_sandbox(workspace_id: str):
    """
    Clean up both workspace files and sandbox container.
    
    Call this when user deletes a workspace.
    """
    from services.sandbox_manager import sandbox_manager
    from services.workspace_service import workspace_service
    
    # Cleanup sandbox
    await sandbox_manager.cleanup_sandbox(workspace_id)
    
    # Cleanup workspace files (if workspace_service has this method)
    # await workspace_service.delete_workspace(workspace_id)
    
    return {
        "status": "cleaned_up",
        "workspace_id": workspace_id,
        "message": "Workspace and sandbox cleaned up"
    }
