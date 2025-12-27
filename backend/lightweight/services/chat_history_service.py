"""
Chat History Service - Persistent chat history per user/session

Stores and retrieves chat messages for each user session.
Uses Redis for fast access and file system for persistence.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from core.cache import cache


class ChatHistoryService:
    """Manage persistent chat history per user/session."""
    
    @staticmethod
    async def save_message(session_id: str, user_id: str, message: str, response: str, metadata: Optional[Dict] = None):
        """
        Save a chat message and response to history.
        
        Args:
            session_id: Session ID
            user_id: User ID
            message: User's message
            response: AI response
            metadata: Optional metadata (workspace_id, etc.)
        """
        chat_entry = {
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # 1. Save to Redis (fast access) - handle gracefully if Redis unavailable
        try:
            redis_client = await cache.get_client()
            history_key = f"chat:history:{user_id}:{session_id}"
            await redis_client.lpush(history_key, json.dumps(chat_entry))
            await redis_client.ltrim(history_key, 0, 999)  # Keep last 1000 messages
            await redis_client.expire(history_key, 2592000)  # Expire after 30 days
        except Exception as e:
            print(f"⚠️ Failed to save to Redis (falling back to file only): {e}")
            # Continue to file system save
        
        # 2. Save to file system (persistence backup) - handle errors gracefully
        try:
            history_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / "_chat_history" / user_id
            history_dir.mkdir(parents=True, exist_ok=True)
            
            history_file = history_dir / f"{session_id}.jsonl"
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(chat_entry) + "\n")
        except Exception as e:
            print(f"⚠️ Failed to save chat history to file (non-critical): {e}")
    
    @staticmethod
    async def get_history(user_id: str, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Get chat history for a user session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of chat entries (most recent first)
        """
        messages = []
        
        # 1. Try Redis first (fail gracefully)
        try:
            redis_client = await cache.get_client()
            history_key = f"chat:history:{user_id}:{session_id}"
            redis_messages = await redis_client.lrange(history_key, 0, limit - 1)
            
            if redis_messages:
                for msg_json in redis_messages:
                    try:
                        messages.append(json.loads(msg_json))
                    except json.JSONDecodeError:
                        continue
                
                # Reverse to get chronological order (oldest first)
                messages.reverse()
                return messages
        except Exception as e:
            # Redis unavailable - fall back to file system
            print(f"⚠️ Error loading chat history from Redis (falling back to file): {e}")
        
        # 2. Fallback to file system
        try:
            history_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / "_chat_history" / user_id
            history_file = history_dir / f"{session_id}.jsonl"
            
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Get last N lines
                    for line in lines[-limit:]:
                        try:
                            messages.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"⚠️ Error loading chat history from file: {e}")
        
        return messages
    
    @staticmethod
    async def clear_history(user_id: str, session_id: str):
        """Clear chat history for a session."""
        # Clear Redis
        try:
            redis_client = await cache.get_client()
            history_key = f"chat:history:{user_id}:{session_id}"
            await redis_client.delete(history_key)
        except Exception as e:
            print(f"⚠️ Error clearing chat history from Redis: {e}")
        
        # Clear file
        try:
            history_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / "_chat_history" / user_id
            history_file = history_dir / f"{session_id}.jsonl"
            if history_file.exists():
                history_file.unlink()
        except Exception as e:
            print(f"⚠️ Error clearing chat history file: {e}")
    
    @staticmethod
    async def get_all_sessions(user_id: str) -> List[str]:
        """Get all session IDs for a user."""
        sessions = []
        
        # From file system
        try:
            history_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / "_chat_history" / user_id
            if history_dir.exists():
                for file in history_dir.glob("*.jsonl"):
                    sessions.append(file.stem)
        except Exception as e:
            print(f"⚠️ Error listing sessions: {e}")
        
        return list(set(sessions))  # Remove duplicates


# Singleton instance
chat_history_service = ChatHistoryService()

