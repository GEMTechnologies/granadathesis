"""
Session API Endpoints
Handles user sessions, workspace associations, and URLs
"""
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from app.services.session_service import session_service
from app.services.chat_history_service import chat_history_service

router = APIRouter(prefix="/api/session", tags=["session"])


# Request Models
class InitSessionRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    workspace_id: Optional[str] = None


class SetWorkspaceRequest(BaseModel):
    workspace_id: str


@router.post("/init")
async def init_session(request: InitSessionRequest):
    """
    Initialize or get existing session for user.
    Returns session with URL and workspace info.
    Also initializes workspace-specific chat history if workspace_id provided.
    """
    try:
        user_id = request.user_id or 'user-1'  # Default dummy user
        user = session_service.get_or_create_user(user_id, request.username)
        session = session_service.get_or_create_session(user_id=user_id)
        
        # Set workspace if provided
        workspace_info = None
        if request.workspace_id:
            session = session_service.set_workspace(
                session["session_id"],
                request.workspace_id,
                user_id=user_id
            )
            workspace_url_info = session_service.get_workspace_url(request.workspace_id)
            if workspace_url_info:
                workspace_info = {
                    "workspace_id": request.workspace_id,
                    "url": workspace_url_info['url'],
                    "shareable_url": workspace_url_info.get('shareable_url')
                }
        elif session.get('workspace_id'):
            workspace_url_info = session_service.get_workspace_url(session['workspace_id'])
            if workspace_url_info:
                workspace_info = {
                    "workspace_id": session['workspace_id'],
                    "url": workspace_url_info['url'],
                    "shareable_url": workspace_url_info.get('shareable_url')
                }
        
        return {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "session_url": session["session_url"],
            "workspace": workspace_info,
            "has_workspace": workspace_info is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing session: {str(e)}")


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    try:
        session = session_service.get_session(session_id)
        if not session:
            # Return a default session structure instead of 404
            # This allows the frontend to work even if session expired
            return {
                "session_id": session_id,
                "user_id": None,
                "workspace": None,
                "session_url": None,
                "expired": True
            }
        
        workspace_info = None
        if session.get('workspace_id'):
            try:
                workspace_url_info = session_service.get_workspace_url(session['workspace_id'])
                if workspace_url_info:
                    workspace_info = {
                        "workspace_id": session['workspace_id'],
                        "url": workspace_url_info['url'],
                        "shareable_url": workspace_url_info.get('shareable_url')
                    }
            except Exception:
                pass  # Workspace might not exist, continue without it
        
        return {
            "session_id": session["session_id"],
            "user_id": session.get("user_id"),
            "workspace": workspace_info,
            "session_url": session.get("session_url")
        }
    except Exception as e:
        # Return a default structure on any error instead of raising
        return {
            "session_id": session_id,
            "user_id": None,
            "workspace": None,
            "session_url": None,
            "error": str(e)
        }


@router.post("/{session_id}/workspace")
async def set_session_workspace(session_id: str, request: SetWorkspaceRequest):
    """Associate workspace with session and generate URLs."""
    try:
        session = session_service.set_workspace(
            session_id,
            request.workspace_id,
            user_id=None  # Will get from session
        )
        
        workspace_url_info = session_service.get_workspace_url(request.workspace_id)
        
        return {
            "session_id": session_id,
            "workspace_id": request.workspace_id,
            "workspace_url": workspace_url_info['url'],
            "shareable_url": workspace_url_info.get('shareable_url')
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting workspace: {str(e)}")


@router.get("/user/{user_id}/workspaces")
async def get_user_workspaces(user_id: str):
    """Get all workspaces for a user with their URLs."""
    try:
        workspaces = session_service.get_user_workspaces(user_id)
        return {
            "user_id": user_id,
            "workspaces": workspaces
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workspaces: {str(e)}")


@router.get("/workspace/{workspace_id}/url")
async def get_workspace_url(workspace_id: str):
    """Get workspace URL information."""
    url_info = session_service.get_workspace_url(workspace_id)
    if not url_info:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return url_info


@router.get("/{session_id}/chat-history")
async def get_session_chat_history(
    session_id: str,
    workspace_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get chat history for a session.
    
    If workspace_id is provided, gets history for that workspace.
    If conversation_id is provided, gets specific conversation.
    Otherwise gets latest messages across all conversations in workspace.
    """
    try:
        # Get session to find workspace
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Use provided workspace or session's workspace
        ws_id = workspace_id or session.get('workspace_id') or 'default'
        
        if conversation_id:
            messages = await chat_history_service.get_conversation(
                workspace_id=ws_id,
                conversation_id=conversation_id
            )
        else:
            messages = await chat_history_service.get_workspace_history(
                workspace_id=ws_id,
                limit=limit
            )
        
        return {
            "session_id": session_id,
            "workspace_id": ws_id,
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat history: {str(e)}"
        )


@router.get("/{session_id}/conversations")
async def get_session_conversations(
    session_id: str,
    workspace_id: Optional[str] = None
):
    """Get list of conversations for a session's workspace."""
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        ws_id = workspace_id or session.get('workspace_id') or 'default'
        
        conversations = await chat_history_service.get_conversations_list(ws_id)
        
        return {
            "session_id": session_id,
            "workspace_id": ws_id,
            "conversations": conversations,
            "count": len(conversations)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversations: {str(e)}"
        )






