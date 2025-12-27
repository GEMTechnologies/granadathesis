"""
Agent API - Autonomous Problem Solving

Endpoints for the autonomous agent brain.
Streams thoughts and execution in real-time.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
import asyncio
import json

router = APIRouter(prefix="/api/agent", tags=["Autonomous Agent"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentRequest(BaseModel):
    query: str
    workspace_id: str
    context: Optional[dict] = None


class AgentResponse(BaseModel):
    success: bool
    result: Any
    thoughts: str
    plan_steps: list
    tools_created: list
    execution_log: list


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/solve")
async def autonomous_solve(request: AgentRequest):
    """
    Autonomous problem solving with streaming.
    
    The agent:
    1. Reflects on the problem
    2. Plans multi-step solution
    3. Executes (creates tools if needed)
    4. Learns from results
    
    Returns real-time stream of agent's thoughts and actions.
    """
    from services.agent.autonomous_agent import AutonomousAgent
    from services.deepseek_direct import deepseek_direct_service
    from services.sandbox_manager import sandbox_manager
    from services.vector_service import vector_service
    from services.conversation_memory import ConversationMemory
    
    # Stream generator
    async def stream_agent_thoughts():
        """Stream agent's thoughts and actions in real-time."""
        
        # Create agent
        memory = ConversationMemory(request.workspace_id)
        agent = AutonomousAgent(
            workspace_id=request.workspace_id,
            llm_service=deepseek_direct_service,
            sandbox_manager=sandbox_manager,
            vector_service=vector_service,
            conversation_memory=memory
        )
        
        # Callback for streaming
        async def stream_callback(message: str):
            yield f"data: {json.dumps({'type': 'thought', 'content': message})}\n\n"
            await asyncio.sleep(0.1)  # Small delay for readability
        
        # Start solving
        try:
            yield f"data: {json.dumps({'type': 'start', 'query': request.query})}\n\n"
            
            result = await agent.solve(
                user_request=request.query,
                context=request.context or {},
                stream_callback=stream_callback
            )
            
            # Send final result
            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_agent_thoughts(),
        media_type="text/event-stream"
    )


@router.post("/solve-sync", response_model=AgentResponse)
async def autonomous_solve_sync(request: AgentRequest):
    """
    Autonomous problem solving (non-streaming).
    
    Use this for:
    - API integrations
    - Testing
    - When you don't need real-time feedback
    """
    from services.agent.autonomous_agent import AutonomousAgent
    from services.deepseek_direct import deepseek_direct_service
    from services.sandbox_manager import sandbox_manager
    from services.vector_service import vector_service
    from services.conversation_memory import ConversationMemory
    
    try:
        # Create agent
        memory = ConversationMemory(request.workspace_id)
        agent = AutonomousAgent(
            workspace_id=request.workspace_id,
            llm_service=deepseek_direct_service,
            sandbox_manager=sandbox_manager,
            vector_service=vector_service,
            conversation_memory=memory
        )
        
        # Solve
        result = await agent.solve(
            user_request=request.query,
            context=request.context or {}
        )
        
        return AgentResponse(
            success=result['success'],
            result=result.get('result'),
            thoughts=result.get('thoughts', ''),
            plan_steps=[],  # TODO: Extract from plan
            tools_created=[t.name for t in result.get('tools_created', [])],
            execution_log=result.get('execution_log', [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/{workspace_id}/tools")
async def list_created_tools(workspace_id: str):
    """List all tools created by the agent in this workspace."""
    from config import get_tools_dir
    import json
    
    tools_dir = get_tools_dir(workspace_id)
    if not tools_dir.exists():
        return {"tools": []}
    
    tools = []
    for metadata_file in tools_dir.glob("*.json"):
        with open(metadata_file) as f:
            tools.append(json.load(f))
    
    return {"tools": tools, "count": len(tools)}
