"""
Conversation Memory Service

Long-term memory for chat conversations. Stores all messages and enables
semantic search to recall relevant context from any point in history.

Features:
- Persistent storage of all messages
- Semantic embeddings for similarity search
- Efficient retrieval of relevant past context
- Summarization of long conversation history
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

from services.workspace_service import WORKSPACES_DIR


@dataclass
class ChatMessage:
    """A single chat message."""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str
    job_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For semantic search
    embedding: Optional[List[float]] = None
    summary: Optional[str] = None


@dataclass 
class Conversation:
    """A conversation with full history."""
    conversation_id: str
    workspace_id: str
    created_at: str
    updated_at: str
    title: str
    messages: List[Dict] = field(default_factory=list)
    total_messages: int = 0
    
    # Memory optimization
    summary: str = ""  # Condensed summary of full history
    key_points: List[str] = field(default_factory=list)


class ConversationMemoryService:
    """
    Manages long-term conversation memory with semantic retrieval.
    
    Storage structure:
    workspace/conversations/
        {conversation_id}/
            metadata.json      # Conversation metadata + summary
            messages.jsonl     # All messages (append-only)
            embeddings.bin     # Vector embeddings for search
    """
    
    def __init__(self):
        self.max_context_messages = 20  # Max messages to include in prompt
        self.summary_threshold = 50  # Summarize when exceeding this
    
    def _get_conversations_dir(self, workspace_id: str) -> Path:
        """Get conversations directory for workspace."""
        conv_dir = WORKSPACES_DIR / workspace_id / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir
    
    def _get_conversation_dir(self, workspace_id: str, conversation_id: str) -> Path:
        """Get directory for a specific conversation."""
        conv_dir = self._get_conversations_dir(workspace_id) / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir
    
    def _generate_message_id(self, content: str, timestamp: str) -> str:
        """Generate unique message ID."""
        hash_input = f"{content}{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    async def create_conversation(
        self,
        workspace_id: str,
        title: str = "New Conversation"
    ) -> Conversation:
        """Create a new conversation."""
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        now = datetime.now().isoformat()
        
        conversation = Conversation(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            created_at=now,
            updated_at=now,
            title=title,
            messages=[],
            total_messages=0
        )
        
        # Save metadata
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        metadata_path = conv_dir / "metadata.json"
        metadata_path.write_text(json.dumps(asdict(conversation), indent=2), encoding='utf-8')
        
        # Create empty messages file
        (conv_dir / "messages.jsonl").touch()
        
        print(f"📝 Created conversation: {conversation_id}")
        return conversation
    
    async def add_message(
        self,
        workspace_id: str,
        conversation_id: str,
        role: str,
        content: str,
        job_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ChatMessage:
        """Add a message to conversation history."""
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        messages_path = conv_dir / "messages.jsonl"
        
        timestamp = datetime.now().isoformat()
        message_id = self._generate_message_id(content, timestamp)
        
        message = ChatMessage(
            id=message_id,
            role=role,
            content=content,
            timestamp=timestamp,
            job_id=job_id,
            metadata=metadata or {}
        )
        
        # Append to messages file (JSONL for efficient streaming)
        with open(messages_path, 'a', encoding='utf-8') as f:
            msg_dict = asdict(message)
            msg_dict.pop('embedding', None)  # Don't store embeddings in JSONL
            f.write(json.dumps(msg_dict) + '\n')
        
        # Update metadata
        await self._update_conversation_metadata(workspace_id, conversation_id)
        
        # ============ NEW: Index in vector database for semantic search ============
        try:
            from services.vector_service import vector_service
            
            # Only index substantive messages (skip system messages, short messages)
            if len(content) > 50 and role in ['user', 'assistant']:
                await vector_service.add_document(
                    workspace_id=workspace_id,
                    document_id=message_id,
                    chunks=[content],  # Single chunk for messages
                    metadata={
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "role": role,
                        "timestamp": timestamp,
                        "job_id": job_id or "",
                        "source": "conversation"
                    },
                    source="conversation"
                )
        except Exception as e:
            # Don't fail message saving if vector indexing fails
            print(f"⚠️ Vector indexing failed for message {message_id}: {e}")
        
        return message
    
    async def _update_conversation_metadata(
        self,
        workspace_id: str,
        conversation_id: str
    ):
        """Update conversation metadata after adding message."""
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        metadata_path = conv_dir / "metadata.json"
        messages_path = conv_dir / "messages.jsonl"
        
        # Count messages
        total = sum(1 for _ in open(messages_path, encoding='utf-8'))
        
        # Load and update metadata
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        else:
            metadata = {"workspace_id": workspace_id, "conversation_id": conversation_id}
        
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["total_messages"] = total
        
        # Auto-summarize if too many messages
        if total > self.summary_threshold and total % 50 == 0:
            await self._summarize_conversation(workspace_id, conversation_id)
        
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    
    async def get_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get messages from conversation with pagination."""
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        messages_path = conv_dir / "messages.jsonl"
        
        if not messages_path.exists():
            return []
        
        messages = []
        with open(messages_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if len(messages) >= limit:
                    break
                try:
                    messages.append(json.loads(line))
                except:
                    pass
        
        return messages
    
    async def get_all_messages(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> List[Dict]:
        """Get all messages (use carefully for large histories)."""
        return await self.get_messages(workspace_id, conversation_id, limit=100000)
    
    async def get_recent_context(
        self,
        workspace_id: str,
        conversation_id: str,
        num_messages: int = 10
    ) -> List[Dict]:
        """Get most recent messages for context."""
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        messages_path = conv_dir / "messages.jsonl"
        
        if not messages_path.exists():
            return []
        
        # Read last N lines efficiently
        messages = []
        with open(messages_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-num_messages:]:
                try:
                    messages.append(json.loads(line))
                except:
                    pass
        
        return messages
    
    async def search_messages(
        self,
        workspace_id: str,
        conversation_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search messages by keyword.
        
        For semantic search with embeddings, see search_messages_semantic().
        """
        query_lower = query.lower()
        results = []
        
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        messages_path = conv_dir / "messages.jsonl"
        
        if not messages_path.exists():
            return []
        
        with open(messages_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    content = msg.get('content', '').lower()
                    if query_lower in content:
                        results.append(msg)
                        if len(results) >= limit:
                            break
                except:
                    pass
        
        return results
    
    async def search_messages_semantic(
        self,
        workspace_id: str,
        conversation_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Semantic search using embeddings.
        
        Uses vector database to find relevant past messages based on meaning,
        not just keywords.
        """
        try:
            # Import vector service
            from services.vector_service import vector_service
            
            # Search vector DB for relevant message chunks
            results = await vector_service.search(
                workspace_id=workspace_id,
                query=query,
                n_results=limit,
                filter_metadata={"conversation_id": conversation_id, "source": "conversation"}
            )
            
            # Format results for conversation context
            relevant_messages = []
            for result in results.get('results', []):
                relevant_messages.append({
                    "role": result['metadata'].get('role', 'assistant'),
                    "content": result['text'],
                    "timestamp": result['metadata'].get('timestamp', ''),
                    "relevance_score": 1.0 - result.get('distance', 0),  # Convert distance to similarity
                    "message_id": result['metadata'].get('message_id', '')
                })
            
            return relevant_messages
        
        except Exception as e:
            print(f"Semantic search error: {e}")
            # Fallback to keyword search if vector search fails
            return await self.search_messages(workspace_id, conversation_id, query, limit)
    
    async def get_context_for_prompt(
        self,
        workspace_id: str,
        conversation_id: str,
        current_message: str
    ) -> str:
        """
        Build context string for LLM prompt.
        
        Combines:
        1. Conversation summary (if exists)
        2. Relevant past messages (semantic search)
        3. Recent messages
        """
        context_parts = []
        
        # 1. Get conversation summary
        summary = await self._get_conversation_summary(workspace_id, conversation_id)
        if summary:
            context_parts.append(f"## Conversation Summary\n{summary}\n")
        
        # 2. Search for relevant past messages
        relevant = await self.search_messages_semantic(
            workspace_id, conversation_id, current_message, limit=5
        )
        if relevant:
            context_parts.append("## Relevant Past Messages")
            for msg in relevant:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:500]
                context_parts.append(f"[{role}]: {content}")
            context_parts.append("")
        
        # 3. Get recent messages
        recent = await self.get_recent_context(workspace_id, conversation_id, num_messages=10)
        if recent:
            context_parts.append("## Recent Messages")
            for msg in recent[-5:]:  # Last 5 for recency
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:300]
                context_parts.append(f"[{role}]: {content}")
        
        return "\n".join(context_parts)
    
    async def _get_conversation_summary(
        self,
        workspace_id: str,
        conversation_id: str
    ) -> Optional[str]:
        """Get conversation summary if exists."""
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        metadata_path = conv_dir / "metadata.json"
        
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            return metadata.get('summary', '')
        
        return None
    
    async def _summarize_conversation(
        self,
        workspace_id: str,
        conversation_id: str
    ):
        """Generate summary of conversation history."""
        from core.llm_client import LLMClient
        
        # Get all messages
        messages = await self.get_all_messages(workspace_id, conversation_id)
        
        if len(messages) < 10:
            return
        
        # Build text for summarization
        text = "\n".join([
            f"[{m.get('role')}]: {m.get('content', '')[:200]}"
            for m in messages
        ])
        
        # Truncate if too long
        if len(text) > 10000:
            text = text[:10000] + "\n... (truncated)"
        
        # Generate summary
        llm = LLMClient()
        prompt = f"""Summarize this conversation concisely. Focus on:
1. Main topics discussed
2. Key decisions made
3. Important information shared
4. Current state/progress

Conversation:
{text}

Summary (2-3 paragraphs):"""

        summary = ""
        async for chunk in llm.stream_generate(prompt):
            summary += chunk
        
        # Save summary
        conv_dir = self._get_conversation_dir(workspace_id, conversation_id)
        metadata_path = conv_dir / "metadata.json"
        
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            metadata['summary'] = summary
            metadata['summary_updated_at'] = datetime.now().isoformat()
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        print(f"📋 Updated conversation summary for {conversation_id}")
    
    async def recall(
        self,
        workspace_id: str,
        conversation_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Recall information from conversation history.
        
        This is the main entry point for memory recall.
        Returns relevant context + summary.
        """
        # Search for relevant messages
        relevant = await self.search_messages_semantic(
            workspace_id, conversation_id, query, limit=10
        )
        
        # Get summary
        summary = await self._get_conversation_summary(workspace_id, conversation_id)
        
        # Build response
        return {
            "query": query,
            "relevant_messages": relevant,
            "summary": summary,
            "found_count": len(relevant)
        }
    
    def list_conversations(self, workspace_id: str) -> List[Dict]:
        """List all conversations in workspace."""
        conv_dir = self._get_conversations_dir(workspace_id)
        conversations = []
        
        for conv_path in conv_dir.iterdir():
            if conv_path.is_dir():
                metadata_path = conv_path / "metadata.json"
                if metadata_path.exists():
                    try:
                        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                        conversations.append(metadata)
                    except:
                        pass
        
        # Sort by updated_at descending
        conversations.sort(
            key=lambda x: x.get('updated_at', ''),
            reverse=True
        )
        
        return conversations


# Singleton instance
conversation_memory = ConversationMemoryService()
