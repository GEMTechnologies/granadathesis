"""
Session Service - User and Session Management

Manages user sessions, workspace associations, and URL generation.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import os

# In-memory session store (replace with database in production)
_sessions: Dict[str, Dict] = {}
_users: Dict[str, Dict] = {}
_workspace_urls: Dict[str, Dict] = {}  # Maps workspace_id to URL info


class SessionService:
    """Manage user sessions and workspace allocation with URLs."""
    
    @staticmethod
    def get_or_create_user(user_id: Optional[str] = None, username: Optional[str] = None) -> Dict:
        """
        Get or create a user.
        
        Args:
            user_id: Optional existing user ID (defaults to 'user-1' for dummy user)
            username: Optional username
            
        Returns:
            User data with user_id, username, created_at
        """
        # Default to dummy user if not provided
        if not user_id:
            user_id = 'user-1'
        
        if user_id not in _users:
            _users[user_id] = {
                "user_id": user_id,
                "username": username or f"user-{user_id}",
                "created_at": datetime.now().isoformat(),
                "workspace_ids": []
            }
        
        return _users[user_id]
    
    @staticmethod
    def get_or_create_session(
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Get or create a session with user association.
        
        Args:
            session_id: Optional existing session ID
            user_id: Optional user ID (defaults to 'user-1')
            
        Returns:
            Session data with session_id, user_id, workspace_id, url
        """
        if not user_id:
            user_id = 'user-1'  # Default dummy user
        
        # Ensure user exists
        SessionService.get_or_create_user(user_id)
        
        # Check if session exists
        if session_id and session_id in _sessions:
            session = _sessions[session_id]
            # Ensure user association
            if not session.get('user_id'):
                session['user_id'] = user_id
            return session
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        
        # Generate session URL
        session_url = f"/session/{new_session_id}"
        
        session_data = {
            "session_id": new_session_id,
            "user_id": user_id,
            "workspace_id": None,
            "workspace_url": None,
            "session_url": session_url,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        _sessions[new_session_id] = session_data
        return session_data
    
    @staticmethod
    def set_workspace(
        session_id: str,
        workspace_id: str,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Associate workspace with session and generate URL.
        
        Args:
            session_id: Session ID
            workspace_id: Workspace ID
            user_id: Optional user ID
            
        Returns:
            Updated session data with workspace URL
        """
        if session_id not in _sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = _sessions[session_id]
        session["workspace_id"] = workspace_id
        
        # Generate workspace URL
        workspace_url = f"/workspace/{workspace_id}"
        session["workspace_url"] = workspace_url
        
        # Store workspace URL mapping
        if workspace_id not in _workspace_urls:
            _workspace_urls[workspace_id] = {
                "workspace_id": workspace_id,
                "url": workspace_url,
                "user_id": user_id or session.get('user_id'),
                "session_id": session_id,
                "shareable_url": f"/shared/workspace/{workspace_id}",  # Public shareable URL
                "created_at": datetime.now().isoformat()
            }
        
        # Add workspace to user's list
        user_id = user_id or session.get('user_id', 'user-1')
        if user_id in _users:
            if workspace_id not in _users[user_id].get('workspace_ids', []):
                _users[user_id].setdefault('workspace_ids', []).append(workspace_id)
        
        return session
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict]:
        """Get session data."""
        return _sessions.get(session_id)
    
    @staticmethod
    def get_user_sessions(user_id: str) -> list:
        """Get all sessions for a user."""
        return [
            session for session in _sessions.values()
            if session.get('user_id') == user_id
        ]
    
    @staticmethod
    def get_workspace_url(workspace_id: str) -> Optional[Dict]:
        """Get workspace URL information."""
        return _workspace_urls.get(workspace_id)
    
    @staticmethod
    def get_user_workspaces(user_id: str) -> list:
        """Get all workspaces for a user with their URLs."""
        user = _users.get(user_id, {})
        workspace_ids = user.get('workspace_ids', [])
        
        workspaces = []
        for workspace_id in workspace_ids:
            url_info = _workspace_urls.get(workspace_id)
            if url_info:
                workspaces.append({
                    "workspace_id": workspace_id,
                    "url": url_info["url"],
                    "shareable_url": url_info.get("shareable_url"),
                    "created_at": url_info.get("created_at")
                })
        
        return workspaces
    
    @staticmethod
    def clear_session(session_id: str) -> bool:
        """Clear session data."""
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False


# Singleton instance
session_service = SessionService()

















