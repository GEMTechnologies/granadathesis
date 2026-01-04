"""
Session Service - Session-based workspace allocation with SQLite persistence

Manages user sessions and workspace associations.
Each new chat session automatically gets its own isolated workspace.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional
from services.session_workspace_db import session_workspace_db


class SessionService:
    """Manage user sessions and workspace allocation with database persistence."""
    
    def __init__(self):
        self.db = session_workspace_db
    
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: str = "default") -> Dict:
        """
        Get or create a session with auto-allocated workspace.
        
        Args:
            session_id: Optional existing session ID
            user_id: User ID (default: "default")
            
        Returns:
            Session data with session_id and workspace_id
        """
        # Check if session exists in database
        if session_id:
            session = self.db.get_session(session_id)
            if session:
                # Update last accessed timestamp
                self.db.update_last_accessed(session_id)
                print(f"📂 Loaded existing session: {session_id} → workspace: {session['workspace_id']}")
                return session
        
        # Create new session with auto-generated workspace
        # Force a unique ID for every conversation to prevent leakage
        if not session_id or session_id in ["default", "new"]:
            new_session_id = str(uuid.uuid4())
        else:
            new_session_id = session_id
            
        workspace_id = f"ws_{new_session_id[:12]}"  # Use 12 chars
        
        # Create workspace using workspace service
        from services.workspace_service import workspace_service
        try:
            workspace_service.create_workspace(
                topic="",
                context="",
                workspace_id=workspace_id
            )
            print(f"✅ Created new workspace: {workspace_id}")
        except Exception as e:
            print(f"⚠️ Workspace creation error (may already exist): {e}")
        
        # Store session in database
        session_data = self.db.create_session(
            session_id=new_session_id,
            workspace_id=workspace_id,
            user_id=user_id,
            metadata={
                "created_at": datetime.now().isoformat(),
                "auto_created": True
            }
        )
        
        print(f"🆕 Created new session: {new_session_id} → workspace: {workspace_id}")
        return session_data
    
    def set_workspace(self, session_id: str, workspace_id: str) -> bool:
        """
        Associate workspace with session (for manual workspace changes).
        
        Args:
            session_id: Session ID
            workspace_id: Workspace ID to associate
            
        Returns:
            True if successful, False otherwise
        """
        session = self.db.get_session(session_id)
        if session:
            # Update the session's workspace_id
            # Note: This requires adding an update method to the DB
            # For now, we'll just update metadata
            metadata = session.get('metadata', {})
            metadata['workspace_changed'] = True
            metadata['previous_workspace'] = session.get('workspace_id')
            self.db.update_metadata(session_id, metadata)
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data from database."""
        return self.db.get_session(session_id)
    
    def get_session_by_workspace(self, workspace_id: str) -> Optional[Dict]:
        """Get session by workspace ID."""
        return self.db.get_session_by_workspace(workspace_id)
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear/delete session data and associated workspace files."""
        session = self.db.get_session(session_id)
        if not session:
            return False
            
        workspace_id = session.get("workspace_id")
        
        # 1. Delete from database
        deleted = self.db.delete_session(session_id)
        
        # 2. Delete workspace files on disk if it's a specific workspace
        if deleted and workspace_id and workspace_id != "default":
            from services.workspace_service import WORKSPACES_DIR
            import shutil
            workspace_path = WORKSPACES_DIR / workspace_id
            if workspace_path.exists():
                try:
                    shutil.rmtree(workspace_path)
                    print(f"🗑️ Deleted workspace directory: {workspace_path}")
                except Exception as e:
                    print(f"⚠️ Error deleting workspace directory {workspace_path}: {e}")
                    
        return deleted
    
    async def clear_all_sessions(self, user_id: str = "default") -> bool:
        """Delete all chat sessions and workspaces for a user."""
        sessions = self.db.list_user_sessions(user_id, limit=1000)
        success = True
        for session in sessions:
            res = await self.clear_session(session["session_id"])
            if not res:
                success = False
        return success
    
    def get_all_sessions(self, user_id: str = "default") -> list:
        """Get all sessions for a user (for admin/history use)."""
        return self.db.list_user_sessions(user_id)
    
    
    def list_user_sessions(self, user_id: str = "default", limit: int = 50) -> list:
        """List user sessions ordered by last accessed."""
        return self.db.list_user_sessions(user_id, limit)

    def update_session_metadata(self, session_id: str, metadata: Dict) -> bool:
        """Update session metadata in database."""
        try:
            return self.db.update_metadata(session_id, metadata)
        except Exception as e:
            print(f"⚠️ Error updating session metadata: {e}")
            return False


# Singleton instance
session_service = SessionService()
