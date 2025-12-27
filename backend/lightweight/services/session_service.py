"""
Session Service - Session-based workspace allocation

Manages user sessions and workspace associations.
In production, this should use Redis for persistence.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional

# In-memory session store
# TODO: Replace with Redis in production
_sessions: Dict[str, Dict] = {}


class SessionService:
    """Manage user sessions and workspace allocation."""
    
    @staticmethod
    def get_or_create_session(session_id: Optional[str] = None) -> Dict:
        """
        Get or create a session with allocated workspace.
        
        Args:
            session_id: Optional existing session ID
            
        Returns:
            Session data with session_id and workspace_id (if set)
        """
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        
        session_data = {
            "session_id": new_session_id,
            "workspace_id": None,  # Will be set when user creates workspace
            "created_at": datetime.now().isoformat()
        }
        
        _sessions[new_session_id] = session_data
        return session_data
    
    @staticmethod
    def set_workspace(session_id: str, workspace_id: str) -> bool:
        """
        Associate workspace with session.
        
        Args:
            session_id: Session ID
            workspace_id: Workspace ID to associate
            
        Returns:
            True if successful, False otherwise
        """
        if session_id in _sessions:
            _sessions[session_id]["workspace_id"] = workspace_id
            _sessions[session_id]["workspace_set_at"] = datetime.now().isoformat()
            return True
        return False
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict]:
        """Get session data."""
        return _sessions.get(session_id)
    
    @staticmethod
    def clear_session(session_id: str) -> bool:
        """Clear session data."""
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False
    
    @staticmethod
    def get_all_sessions() -> Dict:
        """Get all sessions (admin use)."""
        return _sessions


# Singleton instance
session_service = SessionService()
