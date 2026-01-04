"""
Session-Workspace Database Service

SQLite database for persistent session-to-workspace mapping.
Each chat session gets its own isolated workspace.
"""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json


class SessionWorkspaceDB:
    """SQLite database for session-workspace mapping."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Store in thesis_data directory
            db_path = Path(__file__).parent.parent.parent / "thesis_data" / "sessions.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                workspace_id TEXT UNIQUE NOT NULL,
                user_id TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()
        print(f"✅ Session database initialized: {self.db_path}")
    
    def create_session(self, session_id: str, workspace_id: str, user_id: str = "default", metadata: Dict = None) -> Dict:
        """Create new session with workspace mapping."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            conn.execute("""
                INSERT INTO chat_sessions (session_id, workspace_id, user_id, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, workspace_id, user_id, metadata_json))
            conn.commit()
            print(f"✅ Created session: {session_id} → workspace: {workspace_id}")
        except sqlite3.IntegrityError as e:
            print(f"⚠️ Session already exists: {session_id}")
            # Session already exists, just return it
            pass
        finally:
            conn.close()
        
        return self.get_session(session_id)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM chat_sessions WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            # Parse metadata JSON
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    result['metadata'] = {}
            return result
        return None
    
    def get_session_by_workspace(self, workspace_id: str) -> Optional[Dict]:
        """Get session by workspace ID."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM chat_sessions WHERE workspace_id = ?
        """, (workspace_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    result['metadata'] = {}
            return result
        return None
    
    def update_last_accessed(self, session_id: str):
        """Update last accessed timestamp."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            UPDATE chat_sessions 
            SET last_accessed = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        conn.close()
    
    def update_metadata(self, session_id: str, metadata: Dict):
        """Update session metadata."""
        conn = sqlite3.connect(str(self.db_path))
        metadata_json = json.dumps(metadata)
        conn.execute("""
            UPDATE chat_sessions 
            SET metadata = ? 
            WHERE session_id = ?
        """, (metadata_json, session_id))
        conn.commit()
        conn.close()
    
    def list_user_sessions(self, user_id: str = "default", limit: int = 50) -> List[Dict]:
        """List all sessions for a user, ordered by last accessed."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM chat_sessions 
            WHERE user_id = ? 
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    result['metadata'] = {}
            results.append(result)
        return results
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("""
            DELETE FROM chat_sessions WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return self.get_session(session_id) is not None


# Singleton instance
session_workspace_db = SessionWorkspaceDB()
