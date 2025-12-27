"""
Chat API Endpoint for AI Assistant

Handles chat messages and generates responses using the LLM service.
Supports streaming responses and chat history per workspace.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
import sys
from pathlib import Path
import json
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.chat_history_service import chat_history_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = None


async def stream_response(response_text: str) -> AsyncGenerator[str, None]:
    """Stream response in chunks."""
    # Split response into sentences or chunks
    chunk_size = 50
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i + chunk_size]
        yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        await asyncio.sleep(0.01)  # Small delay for streaming effect
    yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"


@router.post("/message")
async def chat_message(request: ChatMessage):
    """
    Send a chat message and get AI response.
    
    This endpoint handles:
    - General chat and conversation
    - Research questions
    - Planning and structure
    - Writing assistance
    
    Supports streaming responses and maintains chat history per workspace.
    """
    try:
        import asyncio
        
        workspace_id = request.workspace_id or "default"
        conversation_id = request.conversation_id or str(__import__('uuid').uuid4())
        
        # Store message in chat history
        await chat_history_service.add_message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        
        response_text = None
        error_details = []
        
        # Try to use DeepSeek service first
        try:
            from app.services.deepseek import DeepSeekService
            service = DeepSeekService()
            
            # Check if API key is configured
            if not service.api_key:
                error_details.append("DeepSeek API key not configured")
                raise ValueError("DeepSeek API Key is not configured")
            
            system_prompt = """You are Manus, an intelligent AI assistant specialized in academic writing and research.
            
Your role is to help users with:
- Academic research and paper search
- Thesis planning and structure
- Content generation and writing assistance
- Citation and bibliography management
- Research gap analysis
- Academic editing and proofreading

Be helpful, professional, and academic in tone. Provide clear, well-structured responses.
Always be specific and actionable in your advice."""

            response_text = await service.generate_content(
                prompt=request.message,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            # If we got a response, store it in history
            if response_text:
                await chat_history_service.add_message(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response_text
                )
                
                # Return based on streaming preference
                if request.stream:
                    return StreamingResponse(
                        stream_response(response_text),
                        media_type="text/event-stream"
                    )
                else:
                    return ChatResponse(
                        response=response_text,
                        conversation_id=conversation_id,
                        workspace_id=workspace_id
                    )
            
        except Exception as e:
            error_msg = f"DeepSeek service error: {str(e)}"
            error_details.append(error_msg)
            logger.error(f"Chat API - DeepSeek failed: {error_msg}", exc_info=True)
            
            # Fallback to mdap_llm_client if available
            try:
                from app.services.mdap_llm_client import mdap_llm_client
                
                response_text = await mdap_llm_client.call(
                    system_prompt="You are a helpful academic assistant. Be concise and helpful.",
                    user_prompt=request.message,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                if response_text:
                    await chat_history_service.add_message(
                        workspace_id=workspace_id,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=response_text
                    )
                    
                    if request.stream:
                        return StreamingResponse(
                            stream_response(response_text),
                            media_type="text/event-stream"
                        )
                    else:
                        return ChatResponse(
                            response=response_text,
                            conversation_id=conversation_id,
                            workspace_id=workspace_id
                        )
                
            except Exception as e2:
                error_details.append(f"MDAP LLM client error: {str(e2)}")
                logger.error(f"MDAP fallback failed: {str(e2)}", exc_info=True)
        
        # If no response was generated, return error message
        if not response_text:
            error_msg = "\n".join(error_details) if error_details else "Unknown error occurred"
            logger.error(f"Chat API error: {error_msg}")
            
            response_text = f"""I received your message: '{request.message}'.

Unfortunately, I couldn't generate a response due to:
{error_msg}

To fix this:
1. Ensure `DEEPSEEK_API_KEY` is set in your `.env` file
2. Check network connectivity to the LLM API
3. Verify your API key is valid
4. Check backend logs for detailed error information"""

            await chat_history_service.add_message(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                role="assistant",
                content=response_text
            )

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            workspace_id=workspace_id
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating chat response: {str(e)}"
        )


@router.get("/health")
async def chat_health():
    """Health check for chat endpoint."""
    return {"status": "ok", "service": "chat"}


@router.get("/history/{workspace_id}")
async def get_chat_history(
    workspace_id: str = "default",
    conversation_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Get chat history for a workspace or specific conversation."""
    try:
        if conversation_id:
            messages = await chat_history_service.get_conversation(
                workspace_id=workspace_id,
                conversation_id=conversation_id
            )
        else:
            messages = await chat_history_service.get_workspace_history(
                workspace_id=workspace_id,
                limit=limit
            )
        
        return {
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat history: {str(e)}"
        )

