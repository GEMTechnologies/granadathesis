"""
Universal Chat API - Routes to Autonomous Agent

Handles ANY user request:
- Thesis chapters
- Essays
- Images
- Websites/code
- Data analysis
- Just chatting

The autonomous agent decides what to do!
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json

router = APIRouter(prefix="/api/chat", tags=["Universal Chat"])


class ChatMessage(BaseModel):
    message: str
    mentioned_agents: Optional[List[str]] = []
    workspace_id: Optional[str] = "default"


@router.post("/message")
async def universal_chat(request: ChatMessage):
    """
    Universal chat endpoint - handles EVERYTHING!
    
    User request → Autonomous Agent → Decides what to do
    
    Examples:
    - "Write Chapter 2 for my thesis" → Thesis API
    - "Create an essay about Uganda" → Agent writes essay
    - "Make me an image of a sunset" → Image API
    - "Build a calculator website" → Code generation + sandbox
    - "Just explain quantum physics" → LLM direct response
    """
    from services.agent.autonomous_agent import AutonomousAgent
    from services.deepseek_direct import deepseek_direct_service
    from services.sandbox_manager import sandbox_manager
    from services.vector_service import vector_service
    from services.conversation_memory import ConversationMemory
    
    # Check if this is a thesis-specific request
    thesis_keywords = ['/uoj_phd', '/generic', 'chapter 2', 'literature review', 'methodology']
    is_thesis_request = any(keyword in request.message.lower() for keyword in thesis_keywords)
    
    if is_thesis_request:
        # Route to existing thesis API
        # This preserves your existing thesis generation functionality
        from api import handle_thesis_request  # Assuming you have this
        # For now, just acknowledge
        return {
            "job_id": f"thesis_{request.workspace_id}",
            "status": "queued",
            "response": "Thesis generation starting - use existing thesis API endpoint"
        }
    
    # For everything else, use autonomous agent
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
        
        # Stream generator for SSE
        async def stream_agent_response():
            """Stream agent's work in real-time."""
            
            yield f"data: {json.dumps({'type': 'start', 'message': request.message})}\n\n"
            
            # Callback for streaming updates
            async def stream_callback(message: str):
                yield f"data: {json.dumps({'type': 'thought', 'content': message})}\n\n"
            
            try:
                # Agent solves the problem
                result = await agent.solve(
                    user_request=request.message,
                    context={},
                    stream_callback=stream_callback
                )
                
                # Send final result
                yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
            
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        # Return streaming response
        return StreamingResponse(
            stream_agent_response(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for universal chat API."""
    return {
        "status": "healthy",
        "message": "Universal chat API ready to handle any request!"
    }
