"""
Chat History Service

Manages chat history storage per workspace with conversation tracking.
Uses in-memory storage with optional persistence.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid
from dataclasses import dataclass, asdict


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    id: str
    timestamp: str
    role: str  # "user" or "assistant"
    content: str
    workspace_id: str
    conversation_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ChatHistoryService:
    """
    Service for managing chat history across multiple workspaces.
    
    Structure:
    {
        "workspace_id": {
            "conversation_id": [
                {id, timestamp, role, content, workspace_id, conversation_id},
                ...
            ]
        }
    }
    """
    
    def __init__(self, storage_dir: str = "thesis_data/chat_history"):
        """Initialize chat history service."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.conversations: Dict[str, Dict[str, List[ChatMessage]]] = {}
    
    async def add_message(
        self,
        workspace_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> ChatMessage:
        """
        Add a message to chat history.
        
        Args:
            workspace_id: Unique workspace identifier
            conversation_id: Unique conversation identifier
            role: "user" or "assistant"
            content: Message content
            
        Returns:
            The created ChatMessage
        """
        # Ensure workspace exists
        if workspace_id not in self.conversations:
            self.conversations[workspace_id] = {}
        
        # Ensure conversation exists
        if conversation_id not in self.conversations[workspace_id]:
            self.conversations[workspace_id][conversation_id] = []
        
        # Create message
        message = ChatMessage(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            workspace_id=workspace_id,
            conversation_id=conversation_id
        )
        
        # Add to conversation
        self.conversations[workspace_id][conversation_id].append(message)
        
        # Persist to disk
        await self._persist_conversation(workspace_id, conversation_id)
        
        return message
    
    async def get_conversation(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation.
        
        Args:
            workspace_id: Workspace ID
            conversation_id: Conversation ID
            
        Returns:
            List of message dictionaries
        """
        if workspace_id not in self.conversations:
            return []
        
        if conversation_id not in self.conversations[workspace_id]:
            # Try to load from disk
            await self._load_conversation(workspace_id, conversation_id)
        
        messages = self.conversations.get(workspace_id, {}).get(conversation_id, [])
        return [msg.to_dict() for msg in messages]
    
    async def get_workspace_history(
        self,
        workspace_id: str,
        limit: int = 50,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a workspace.
        
        Args:
            workspace_id: Workspace ID
            limit: Maximum number of messages to return
            conversation_id: Optional specific conversation to load
            
        Returns:
            List of message dictionaries (most recent first)
        """
        if workspace_id not in self.conversations:
            self.conversations[workspace_id] = {}
        
        # If specific conversation requested, load it
        if conversation_id:
            await self._load_conversation(workspace_id, conversation_id)
        else:
            # Load all conversations for workspace from disk
            await self._load_workspace_conversations(workspace_id)
        
        # Collect all messages
        all_messages = []
        for conv_id, messages in self.conversations.get(workspace_id, {}).items():
            all_messages.extend(messages)
        
        # Sort by timestamp, most recent first
        all_messages.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Return limited results
        return [msg.to_dict() for msg in all_messages[:limit]]
    
    async def get_conversations_list(
        self,
        workspace_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of all conversations in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            List of conversation summaries
        """
        # Load all conversations
        await self._load_workspace_conversations(workspace_id)
        
        conversations = []
        for conv_id, messages in self.conversations.get(workspace_id, {}).items():
            if messages:
                conversations.append({
                    "conversation_id": conv_id,
                    "message_count": len(messages),
                    "created_at": messages[0].timestamp,
                    "last_message_at": messages[-1].timestamp,
                    "last_message": messages[-1].content[:100]
                })
        
        # Sort by most recent first
        conversations.sort(key=lambda c: c["last_message_at"], reverse=True)
        return conversations
    
    async def clear_conversation(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> bool:
        """
        Clear a conversation.
        
        Args:
            workspace_id: Workspace ID
            conversation_id: Conversation ID
            
        Returns:
            True if successful
        """
        if workspace_id in self.conversations:
            if conversation_id in self.conversations[workspace_id]:
                del self.conversations[workspace_id][conversation_id]
        
        # Delete from disk
        conv_file = self.storage_dir / workspace_id / f"{conversation_id}.json"
        if conv_file.exists():
            conv_file.unlink()
        
        return True
    
    async def clear_workspace(self, workspace_id: str) -> bool:
        """
        Clear all conversations in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            True if successful
        """
        if workspace_id in self.conversations:
            del self.conversations[workspace_id]
        
        # Delete workspace directory
        workspace_dir = self.storage_dir / workspace_id
        if workspace_dir.exists():
            import shutil
            shutil.rmtree(workspace_dir)
        
        return True
    
    # Private methods for persistence
    
    async def _persist_conversation(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> None:
        """Persist a conversation to disk."""
        workspace_dir = self.storage_dir / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        conv_file = workspace_dir / f"{conversation_id}.json"
        messages = self.conversations.get(workspace_id, {}).get(conversation_id, [])
        
        data = {
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "messages": [msg.to_dict() for msg in messages],
            "created_at": messages[0].timestamp if messages else datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(conv_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _load_conversation(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> bool:
        """Load a conversation from disk."""
        conv_file = self.storage_dir / workspace_id / f"{conversation_id}.json"
        
        if not conv_file.exists():
            return False
        
        try:
            with open(conv_file, 'r') as f:
                data = json.load(f)
            
            # Ensure workspace exists
            if workspace_id not in self.conversations:
                self.conversations[workspace_id] = {}
            
            # Load messages
            messages = [
                ChatMessage(**msg_data) for msg_data in data.get("messages", [])
            ]
            self.conversations[workspace_id][conversation_id] = messages
            
            return True
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return False
    
    async def _load_workspace_conversations(self, workspace_id: str) -> None:
        """Load all conversations for a workspace from disk."""
        workspace_dir = self.storage_dir / workspace_id
        
        if not workspace_dir.exists():
            return
        
        if workspace_id not in self.conversations:
            self.conversations[workspace_id] = {}
        
        # Load all conversation files
        for conv_file in workspace_dir.glob("*.json"):
            conversation_id = conv_file.stem
            
            # Skip if already loaded
            if conversation_id not in self.conversations[workspace_id]:
                await self._load_conversation(workspace_id, conversation_id)


# Global instance
chat_history_service = ChatHistoryService()
