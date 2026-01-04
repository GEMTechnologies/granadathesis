"""
Central Brain - Redis-Backed Distributed AI Coordinator

This module implements a distributed "central brain" that:
1. Tracks actions and context in Redis (persists across restarts)
2. Communicates with workers via Redis pub/sub
3. Detects follow-up commands using conversation context
4. Coordinates API calls and learning
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import json
import re
import asyncio


class ActionType(Enum):
    """Types of actions the system can perform."""
    FILE_CREATE = "file_create"
    FILE_EDIT = "file_edit"
    FILE_READ = "file_read"
    SEARCH_WEB = "search_web"
    SEARCH_PAPER = "search_paper"
    IMAGE_SEARCH = "image_search"
    IMAGE_GENERATE = "image_generate"
    CHAT_RESPONSE = "chat_response"
    NONE = "none"


@dataclass
class LastAction:
    """Tracks the last action performed."""
    action_type: str  # ActionType value as string for JSON serialization
    timestamp: str  # ISO format
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LastAction':
        return cls(
            action_type=data.get("action_type", "none"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            params=data.get("params", {})
        )


@dataclass
class ConversationContext:
    """Full context of the conversation."""
    last_action: Optional[LastAction] = None
    recent_files: List[str] = field(default_factory=list)
    recent_searches: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "last_action": self.last_action.to_dict() if self.last_action else None,
            "recent_files": self.recent_files,
            "recent_searches": self.recent_searches,
            "user_preferences": self.user_preferences
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationContext':
        last_action = None
        if data.get("last_action"):
            last_action = LastAction.from_dict(data["last_action"])
        return cls(
            last_action=last_action,
            recent_files=data.get("recent_files", []),
            recent_searches=data.get("recent_searches", []),
            user_preferences=data.get("user_preferences", {})
        )


class CentralBrain:
    """
    Distributed Central Brain with Redis backing.
    
    Features:
    - Redis persistence for state (survives restarts)
    - Pub/sub for worker communication
    - Follow-up detection with conversation context
    - Action memory and learning
    """
    
    def __init__(self):
        self.redis = None
        self._local_cache: Dict[str, ConversationContext] = {}  # Fallback if Redis unavailable
        self._redis_available = False
    
    async def _ensure_redis(self):
        """Ensure Redis connection is available."""
        if self.redis is None:
            try:
                import redis.asyncio as aioredis
                import os
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                # Handle Docker/local difference
                if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
                    redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
                
                self.redis = aioredis.from_url(redis_url, decode_responses=True)
                await self.redis.ping()
                self._redis_available = True
                print("🧠 Central Brain connected to Redis", flush=True)
            except Exception as e:
                print(f"⚠️ Central Brain Redis unavailable, using local cache: {e}", flush=True)
                self._redis_available = False
    
    async def get_context(self, session_id: str) -> ConversationContext:
        """Get context from Redis or local cache."""
        await self._ensure_redis()
        
        if self._redis_available:
            try:
                data = await self.redis.get(f"brain:context:{session_id}")
                if data:
                    return ConversationContext.from_dict(json.loads(data))
            except Exception as e:
                print(f"Redis get error: {e}")
        
        # Fallback to local cache
        if session_id not in self._local_cache:
            self._local_cache[session_id] = ConversationContext()
        return self._local_cache[session_id]
    
    async def save_context(self, session_id: str, ctx: ConversationContext):
        """Save context to Redis and local cache."""
        self._local_cache[session_id] = ctx
        
        await self._ensure_redis()
        if self._redis_available:
            try:
                await self.redis.set(
                    f"brain:context:{session_id}",
                    json.dumps(ctx.to_dict()),
                    ex=86400  # 24h TTL
                )
            except Exception as e:
                print(f"Redis save error: {e}")
    
    async def record_action(self, session_id: str, action_type: ActionType, params: Dict[str, Any] = None):
        """Record an action that was just performed."""
        ctx = await self.get_context(session_id)
        
        ctx.last_action = LastAction(
            action_type=action_type.value,
            timestamp=datetime.now().isoformat(),
            params=params or {}
        )
        
        # Track files
        if action_type in [ActionType.FILE_CREATE, ActionType.FILE_EDIT]:
            filepath = params.get("filepath", params.get("filename", ""))
            if filepath and filepath not in ctx.recent_files:
                ctx.recent_files.insert(0, filepath)
                ctx.recent_files = ctx.recent_files[:10]
        
        # Track searches
        if action_type in [ActionType.SEARCH_WEB, ActionType.SEARCH_PAPER, ActionType.IMAGE_SEARCH]:
            query = params.get("query", "")
            if query and query not in ctx.recent_searches:
                ctx.recent_searches.insert(0, query)
                ctx.recent_searches = ctx.recent_searches[:10]
        
        await self.save_context(session_id, ctx)
        
        # Publish action event for other components
        await self._publish_event("brain:actions", {
            "session_id": session_id,
            "action_type": action_type.value,
            "params": params
        })
    
    async def _publish_event(self, channel: str, data: dict):
        """Publish event to Redis pub/sub."""
        await self._ensure_redis()
        if self._redis_available:
            try:
                await self.redis.publish(channel, json.dumps(data))
            except Exception as e:
                print(f"Redis publish error: {e}")
    
    async def analyze_followup(self, message: str, session_id: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Analyze if this message is a follow-up to a previous action.
        """
        ctx = await self.get_context(session_id)
        msg_lower = message.lower().strip()
        words = msg_lower.split()
        
        result = {
            "is_followup": False,
            "followup_type": None,
            "target_action": None,
            "extracted_params": {},
            "routing_override": None
        }
        
        if not ctx.last_action:
            return result
        
        last = ctx.last_action
        
        # ============================================================
        # FOLLOW-UP DETECTION PATTERNS
        # ============================================================
        
        # Pattern 1: Short modification phrases after FILE_CREATE/FILE_EDIT
        if last.action_type in [ActionType.FILE_CREATE.value, ActionType.FILE_EDIT.value]:
            modification_patterns = [
                r"^with\s+(?:word|words|text|content)?\s*(.+)$",
                r"^add\s+(.+)$",
                r"^change\s+(?:it\s+)?to\s+(.+)$",
                r"^instead\s+(?:use\s+)?(.+)$",
                r"^(?:make\s+it|put)\s+(.+)$",
                r"^(?:update|modify)\s+(?:with|to)\s+(.+)$",
                r"^just\s+(.+)$",
                r"^only\s+(.+)$",
            ]
            
            for pattern in modification_patterns:
                match = re.match(pattern, msg_lower)
                if match:
                    new_content = match.group(1).strip()
                    result["is_followup"] = True
                    result["followup_type"] = "modify_file"
                    result["target_action"] = last.to_dict()
                    result["extracted_params"] = {
                        "new_content": new_content,
                        "original_filename": last.params.get("filename"),
                        "original_filepath": last.params.get("filepath"),
                    }
                    result["routing_override"] = "file_update"
                    return result
            
            # Very short message after file creation = likely content update
            # BUT NOT if it's a question or informational request!
            if len(words) <= 3 and len(msg_lower) < 50:
                # EXCLUDE questions and information requests - these should go to LLM, not file update
                question_patterns = [
                    "who", "what", "where", "when", "why", "how", "is", "are", "can", "do", "does",
                    "my name", "your name", "am i", "are you", "tell me", "explain", "describe",
                    "please", "help", "thanks", "thank", "okay", "ok", "yes", "no", "sure", "right"
                ]
                is_question_or_request = any(q in msg_lower for q in question_patterns)
                
                # Check for URLs
                has_url = any(u in msg_lower for u in [".com", ".org", ".net", ".edu", "http://", "https://"])
                
                command_words = [
                    "create", "make", "search", "find", "generate", "delete", "open", "close", 
                    "hi", "hello", "go", "visit", "browse", "view", "read", "write", "save"
                ]
                if not any(w in words for w in command_words) and not is_question_or_request and not has_url:
                    result["is_followup"] = True
                    result["followup_type"] = "modify_file"
                    result["target_action"] = last.to_dict()
                    result["extracted_params"] = {
                        "new_content": message.strip(),
                        "original_filename": last.params.get("filename"),
                        "original_filepath": last.params.get("filepath"),
                    }
                    result["routing_override"] = "file_update"
                    return result
        
        # Pattern 2: "more" / "another one" / "again"
        continuation_words = ["more", "another", "again", "continue", "next"]
        if any(w in words for w in continuation_words) and len(words) < 5:
            result["is_followup"] = True
            result["followup_type"] = "continue_action"
            result["target_action"] = last.to_dict()
            result["routing_override"] = last.action_type
            return result
        
        # Pattern 3: "that file" / "the file" references
        if any(ref in msg_lower for ref in ["that file", "the file", "this file"]):
            if ctx.recent_files:
                result["is_followup"] = True
                result["followup_type"] = "reference_file"
                result["extracted_params"] = {"referenced_file": ctx.recent_files[0]}
                return result
        
        return result
    
    async def learn_from_message(self, message: str, session_id: str):
        """Extract and learn user information from messages."""
        ctx = await self.get_context(session_id)
        msg_lower = message.lower().strip()
        
        # Pattern 1: "am {name}" or "i'm {name}" or "my name is {name}"
        name_patterns = [
            r"(?:^|\s)(?:am|i'm|i am)\s+([a-zA-Z]+)(?:\s|$|,|\.)",
            r"my name is\s+([a-zA-Z]+)",
            r"call me\s+([a-zA-Z]+)",
            r"(?:^|\s)name(?:'s)?\s+([a-zA-Z]+)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                potential_name = match.group(1).strip()
                # Filter out common words that aren't names
                not_names = ["here", "fine", "good", "well", "okay", "ok", "ready", "back", "done", "tired"]
                if potential_name and len(potential_name) > 1 and potential_name not in not_names:
                    ctx.user_preferences["name"] = potential_name.capitalize()
                    await self.save_context(session_id, ctx)
                    print(f"🧠 Learned user name: {potential_name.capitalize()}", flush=True)
                    break
    
    def get_user_context_prompt(self, ctx: ConversationContext) -> str:
        """Build a context string for the LLM about what we know of the user."""
        parts = []
        
        if ctx.user_preferences.get("name"):
            parts.append(f"The user's name is {ctx.user_preferences['name']}.")
        
        if ctx.recent_files:
            parts.append(f"Recent files: {', '.join(ctx.recent_files[:3])}")
        
        return " ".join(parts) if parts else ""
    
    async def think(self, message: str, session_id: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Central brain thinking - analyze message and decide routing.
        """
        # First, learn from the message
        await self.learn_from_message(message, session_id)
        
        # Then check for follow-ups
        followup = await self.analyze_followup(message, session_id, conversation_history)
        
        ctx = await self.get_context(session_id)
        user_context = self.get_user_context_prompt(ctx)
        
        if followup["is_followup"]:
            return {
                "decision": "followup",
                "followup_info": followup,
                "context": ctx.to_dict(),
                "user_context": user_context
            }
        
        return {
            "decision": "classify",
            "followup_info": None,
            "context": ctx.to_dict(),
            "user_context": user_context
        }
    
    # Synchronous wrappers for compatibility
    def record_action_sync(self, session_id: str, action_type: ActionType, params: Dict[str, Any] = None):
        """Synchronous wrapper for record_action."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.record_action(session_id, action_type, params))
            else:
                loop.run_until_complete(self.record_action(session_id, action_type, params))
        except Exception as e:
            print(f"Error in record_action_sync: {e}")
            # Fallback to local cache
            if session_id not in self._local_cache:
                self._local_cache[session_id] = ConversationContext()
            ctx = self._local_cache[session_id]
            ctx.last_action = LastAction(
                action_type=action_type.value,
                timestamp=datetime.now().isoformat(),
                params=params or {}
            )
    
    async def run_agent_workflow(
        self,
        message: str,
        session_id: str,
        workspace_id: str = "default",
        conversation_history: List[Dict] = None,
        job_id: str = None
    ) -> Dict[str, Any]:
        """
        Run the full agent workflow for a user message.
        
        Flow:
        1. Understanding Agent (ALWAYS first)
        2. Based on understanding, spawn appropriate agents
        3. Return final result
        
        Args:
            message: User's message
            session_id: Session ID
            workspace_id: Workspace ID
            conversation_history: Previous messages
            
        Returns:
            Workflow result with all gathered data
        """
        from services.agent_spawner import agent_spawner, AgentContext, AgentType
        
        # Build initial context
        ctx = await self.get_context(session_id)
        
        agent_context = AgentContext(
            user_message=message,
            session_id=session_id,
            workspace_id=workspace_id,
            job_id=job_id,
            user_name=ctx.user_preferences.get("name"),
            user_preferences=ctx.user_preferences,
            conversation_history=conversation_history or []
        )
        
        # NEW: List available files in workspace for agent context
        try:
            from services.workspace_service import WORKSPACES_DIR
            ws_path = WORKSPACES_DIR / workspace_id
            if ws_path.exists():
                files = [f.name for f in ws_path.glob("*") if f.is_file() and not f.name.startswith(".")]
                agent_context.available_files = files
        except Exception as e:
            print(f"⚠️ Failed to list workspace files for brain: {e}")
        
        print(f"🧠 Central Brain: Starting agent workflow for: {message[:50]}...", flush=True)

        # NEW: Auto-generate a title based on the first message if needed
        try:
            from services.session_service import session_service
            session = session_service.get_session(session_id)
            if session:
                metadata = session.get("metadata", {})
                current_title = metadata.get("title", "New Conversation")
                if current_title == "New Conversation" or not current_title:
                    new_title = message.strip()[:40]
                    if len(message) > 40: new_title += "..."
                    metadata["title"] = new_title
                    session_service.db.update_metadata(session_id, metadata)
                    
                    # Also update conversation_memory metadata if it exists
                    from services.workspace_service import WORKSPACES_DIR
                    # Use coupled workspace_id from agent_context
                    conv_dir = WORKSPACES_DIR / agent_context.workspace_id / "conversations" / session_id
                    if conv_dir.exists():
                        meta_path = conv_dir / "metadata.json"
                        if meta_path.exists():
                            import json
                            with open(meta_path, 'r') as f:
                                c_meta = json.load(f)
                            c_meta["title"] = new_title
                            with open(meta_path, 'w') as f:
                                json.dump(c_meta, f, indent=2)
                    print(f"📝 Auto-updated title to: {new_title}")
        except Exception as e:
            print(f"⚠️ Failed to auto-update title: {e}")
        
        # Step 1: ALWAYS run Understanding Agent first
        agent_context = await agent_spawner.spawn_and_run(
            AgentType.UNDERSTANDING,
            session_id,
            agent_context
        )
        
        # Step 2: Based on understanding, run appropriate agents
        required_actions = agent_context.required_actions
        
        if "spawn_research_agent" in required_actions:
            agent_context = await agent_spawner.spawn_and_run(
                AgentType.RESEARCH,
                session_id,
                agent_context
            )
        
        if "spawn_action_agent" in required_actions:
            agent_context = await agent_spawner.spawn_and_run(
                AgentType.ACTION,
                session_id,
                agent_context
            )
        
        # Step 3: Optionally verify (for complex tasks)
        if len(required_actions) > 3 or "spawn_verification_agent" in required_actions:
            agent_context = await agent_spawner.spawn_and_run(
                AgentType.VERIFICATION,
                session_id,
                agent_context
            )
        
        result = {
            "success": True,
            "intent": agent_context.intent,
            "goals": agent_context.goals,
            "completed_actions": agent_context.completed_actions,
            "search_results": agent_context.search_results,
            "gathered_data": agent_context.gathered_data,
            "action_plan": agent_context.action_plan
        }
        
        print(f"🧠 Central Brain: Workflow complete. Goals: {len(agent_context.goals)}, Actions: {len(agent_context.completed_actions)}", flush=True)
        
        return result


# Global instance
central_brain = CentralBrain()

