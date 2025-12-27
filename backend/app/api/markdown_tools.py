"""
Markdown File Creation and Mapping Tools

Tools for creating and managing markdown files, documentation mapping, etc.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import time
from app.api.stream import streamer

router = APIRouter(prefix="/api/markdown", tags=["Markdown Tools"])


class CreateMarkdownRequest(BaseModel):
    """Request to create a markdown file."""
    title: str
    content: str
    file_path: Optional[str] = None
    workspace_id: str = "default"
    session_id: str = "default"
    metadata: Optional[Dict[str, Any]] = None


class MapDocumentationRequest(BaseModel):
    """Request to map/create documentation structure."""
    workspace_id: str = "default"
    project_name: str
    structure: Optional[Dict[str, Any]] = None
    session_id: str = "default"


class MarkdownResponse(BaseModel):
    """Response for markdown operations."""
    success: bool
    file_path: Optional[str] = None
    message: str


def create_markdown_content(title: str, content: str, metadata: Optional[Dict] = None) -> str:
    """Create formatted markdown content."""
    md_content = f"# {title}\n\n"
    
    if metadata:
        md_content += "---\n"
        for key, value in metadata.items():
            md_content += f"{key}: {value}\n"
        md_content += "---\n\n"
    
    md_content += content
    
    return md_content


@router.post("/create", response_model=MarkdownResponse)
async def create_markdown_file(request: CreateMarkdownRequest):
    """
    Create a new markdown file.
    
    Creates a markdown file with the specified content and publishes
    the action to the stream.
    """
    try:
        # Determine file path
        if not request.file_path:
            # Auto-generate path based on title
            safe_title = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in request.title)
            request.file_path = f"{safe_title.lower()}.md"
        
        # Ensure .md extension
        if not request.file_path.endswith('.md'):
            request.file_path += '.md'
        
        # Create markdown content
        md_content = create_markdown_content(
            request.title,
            request.content,
            request.metadata
        )
        
        # Publish file creation action
        action_id = f"md-create-{int(time.time() * 1000)}"
        await streamer.publish_action(request.session_id, {
            "id": action_id,
            "type": "file_write",
            "title": f"Created markdown: {request.title}",
            "status": "completed",
            "content": md_content,
            "metadata": {
                "file_path": request.file_path,
                "file_name": request.title,
                "file_type": "markdown",
                "workspace_id": request.workspace_id,
                **({"metadata": request.metadata} if request.metadata else {})
            }
        })
        
        # Trigger auto-call agent if markdown created
        try:
            from app.api.agent_auto_call import should_trigger_agent
            agent_info = should_trigger_agent("file_created", {
                "file_type": "markdown",
                "file_path": request.file_path,
                "workspace_id": request.workspace_id
            })
            if agent_info:
                # Auto-call documentation agent
                await streamer.publish_action(request.session_id, {
                    "id": f"agent-trigger-{int(time.time() * 1000)}",
                    "type": "tool_call",
                    "title": f"Auto-invoking documentation agent for {request.title}",
                    "status": "pending",
                    "metadata": {
                        "agent_type": agent_info["agent"],
                        "action": agent_info["action"],
                        "file_path": request.file_path
                    }
                })
        except:
            pass  # Auto-call is optional
        
        return MarkdownResponse(
            success=True,
            file_path=request.file_path,
            message=f"Markdown file '{request.title}' created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create markdown file: {str(e)}"
        )


@router.post("/map-documentation", response_model=MarkdownResponse)
async def map_documentation(request: MapDocumentationRequest):
    """
    Create a documentation mapping/structure.
    
    Creates a README.md and documentation structure for a project.
    """
    try:
        # Create README.md structure
        readme_content = f"""# {request.project_name}

## Overview

Project documentation and structure.

## Structure

"""
        
        if request.structure:
            readme_content += "```\n"
            readme_content += json.dumps(request.structure, indent=2)
            readme_content += "\n```\n\n"
        
        # Publish documentation mapping action
        action_id = f"md-map-{int(time.time() * 1000)}"
        await streamer.publish_action(request.session_id, {
            "id": action_id,
            "type": "file_write",
            "title": f"Documentation mapping for {request.project_name}",
            "status": "completed",
            "content": readme_content,
            "metadata": {
                "file_path": "README.md",
                "file_name": "README",
                "file_type": "markdown",
                "workspace_id": request.workspace_id,
                "project_name": request.project_name,
                "is_mapping": True
            }
        })
        
        return MarkdownResponse(
            success=True,
            file_path="README.md",
            message=f"Documentation mapping created for {request.project_name}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to map documentation: {str(e)}"
        )


@router.get("/health")
async def markdown_tools_health():
    """Health check for markdown tools endpoint."""
    return {"status": "ok", "tools": ["create", "map-documentation"]}














