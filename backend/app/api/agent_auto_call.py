"""
Agent Auto-Call API

Automatically invokes agents based on user actions and context.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import time
from app.api.stream import streamer

router = APIRouter(prefix="/api/agent", tags=["Agent Auto-Call"])


class AgentAutoCallRequest(BaseModel):
    """Agent auto-call request."""
    action: str  # e.g., "file_created", "code_written", "research_query"
    context: Dict[str, Any]  # Context about the action
    session_id: str = "default"


class AgentAutoCallResponse(BaseModel):
    """Agent auto-call response."""
    triggered: bool
    agent_type: Optional[str] = None
    message: str


# Agent auto-call rules
AGENT_RULES = {
    "file_created": {
        "conditions": [
            lambda ctx: ctx.get("file_type") == "markdown",
            lambda ctx: ctx.get("file_path", "").endswith(".md")
        ],
        "agent": "documentation_agent",
        "action": "analyze_and_enhance_markdown"
    },
    "code_written": {
        "conditions": [
            lambda ctx: ctx.get("language") in ["python", "javascript", "typescript"]
        ],
        "agent": "code_review_agent",
        "action": "review_code"
    },
    "research_query": {
        "conditions": [
            lambda ctx: "?" in ctx.get("query", "")
        ],
        "agent": "research_agent",
        "action": "search_and_analyze"
    },
    "file_edited": {
        "conditions": [
            lambda ctx: ctx.get("file_type") == "markdown"
        ],
        "agent": "documentation_agent",
        "action": "update_documentation"
    }
}


def should_trigger_agent(action: str, context: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Determine if an agent should be triggered based on action and context."""
    rule = AGENT_RULES.get(action)
    if not rule:
        return None
    
    # Check conditions
    for condition in rule["conditions"]:
        if not condition(context):
            return None
    
    return {
        "agent": rule["agent"],
        "action": rule["action"]
    }


@router.post("/auto-call", response_model=AgentAutoCallResponse)
async def auto_call_agent(request: AgentAutoCallRequest):
    """
    Automatically invoke an agent based on user action.
    
    This endpoint analyzes the action and context to determine
    if an agent should be automatically called.
    """
    try:
        # Check if agent should be triggered
        agent_info = should_trigger_agent(request.action, request.context)
        
        if not agent_info:
            return AgentAutoCallResponse(
                triggered=False,
                message=f"No agent auto-call rules matched for action: {request.action}"
            )
        
        # Publish agent invocation action
        action_id = f"agent-auto-{int(time.time() * 1000)}"
        await streamer.publish_action(request.session_id, {
            "id": action_id,
            "type": "tool_call",
            "title": f"Auto-calling {agent_info['agent']}",
            "status": "running",
            "content": f"Triggered by: {request.action}\nContext: {json.dumps(request.context, indent=2)}",
            "metadata": {
                "agent_type": agent_info["agent"],
                "action": agent_info["action"],
                "trigger": request.action,
                "context": request.context
            }
        })
        
        # Here you would actually invoke the agent
        # For now, we'll just publish the action
        
        return AgentAutoCallResponse(
            triggered=True,
            agent_type=agent_info["agent"],
            message=f"Agent {agent_info['agent']} triggered for action: {request.action}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent auto-call failed: {str(e)}"
        )


@router.get("/health")
async def agent_health():
    """Health check for agent auto-call endpoint."""
    return {
        "status": "ok",
        "supported_actions": list(AGENT_RULES.keys()),
        "available_agents": ["documentation_agent", "code_review_agent", "research_agent"]
    }














