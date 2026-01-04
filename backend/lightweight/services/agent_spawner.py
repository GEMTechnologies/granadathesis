"""
Agent Spawner - Central Factory for Creating and Managing Agents

This module:
1. Creates agent instances on demand
2. Manages agent lifecycle
3. Handles inter-agent communication via Redis
4. Tracks agent activities for UI display
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod


class AgentStatus(Enum):
    """Agent lifecycle states."""
    SPAWNING = "spawning"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(Enum):
    """Types of agents in the system."""
    UNDERSTANDING = "understanding"
    RESEARCH = "research"
    ACTION = "action"
    VERIFICATION = "verification"
    BROWSER = "browser"
    WRITER = "writer"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: str
    to_agent: str
    message_type: str  # "context", "request", "response", "handoff"
    content: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentContext:
    """Context passed to and built by agents."""
    user_message: str
    session_id: str
    workspace_id: str
    job_id: Optional[str] = None
    
    def __post_init__(self):
        """Enforce session-to-workspace coupling if requested."""
        if self.workspace_id == "default" or not self.workspace_id:
            if self.session_id:
                # Standard convention for this thesis system: ws_{session_id}
                self.workspace_id = f"ws_{self.session_id[:12]}"
    
    # Understanding results
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    required_actions: List[str] = field(default_factory=list)
    available_files: List[str] = field(default_factory=list)
    
    # Research results
    search_results: List[Dict] = field(default_factory=list)
    gathered_data: Dict[str, Any] = field(default_factory=dict)
    
    # User context
    user_name: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)
    
    # Action plan
    action_plan: List[Dict] = field(default_factory=list)
    completed_actions: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentContext':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def AgentAction(action: str, parameters: Dict[str, Any] = None, description: str = "") -> Dict[str, Any]:
    """Helper to create an action dictionary."""
    return {
        "action": action,
        "parameters": parameters or {},
        "description": description,
        "status": "pending"
    }


class BaseAgent(ABC):
    """
    Base class for all agents.
    
    Each agent:
    - Has a unique ID
    - Reports status to Redis
    - Receives and sends context
    - Can spawn child agents
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        session_id: str,
        parent_id: Optional[str] = None,
        job_id: Optional[str] = None
    ):
        self.id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.session_id = session_id
        self.parent_id = parent_id
        self.job_id = job_id or self.id
        self.status = AgentStatus.SPAWNING
        self.created_at = datetime.now()
        self.redis = None
        self.events = None
    
    async def _ensure_connections(self):
        """Ensure Redis and events connections."""
        if self.redis is None:
            try:
                import redis.asyncio as aioredis
                import os
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
                    redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
                self.redis = aioredis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                print(f"⚠️ Agent {self.id} Redis unavailable: {e}")
        
        if self.events is None:
            try:
                from core.events import events
                self.events = events
                await self.events.connect()
            except Exception as e:
                print(f"⚠️ Agent {self.id} events unavailable: {e}")
    
    async def report_status(self, status: AgentStatus, message: str = "", data: Dict = None):
        """Report agent status to Redis for UI display."""
        self.status = status
        await self._ensure_connections()
        
        status_data = {
            "agent_id": self.id,
            "agent": self.agent_type.value,  # Frontend expects "agent"
            "agent_type": self.agent_type.value,
            "status": status.value,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
            "job_id": self.job_id
        }
        
        print(f"🤖 [{self.agent_type.value.upper()}] {message}", flush=True)
        
        if self.redis:
            try:
                await self.redis.publish(f"agents:{self.session_id}", json.dumps(status_data))
                await self.redis.hset(f"agent:{self.id}", mapping={
                    "status": status.value,
                    "message": message,
                    "updated_at": datetime.now().isoformat()
                })
            except:
                pass
        
        if self.events:
            try:
                await self.events.publish(
                    self.job_id,  # Use job_id for channel consistency
                    "agent_activity",
                    status_data,
                    session_id=self.session_id
                )
            except:
                pass
    
    @abstractmethod
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main agent execution method.
        
        Args:
            context: Current context with all gathered information
            
        Returns:
            Updated context with agent's contributions
        """
        pass
    
    async def spawn_child(self, agent_type: AgentType, context: AgentContext) -> AgentContext:
        """Spawn a child agent and wait for its result."""
        from services.agent_spawner import agent_spawner
        return await agent_spawner.spawn_and_run(agent_type, self.session_id, context, parent_id=self.id)


class AgentSpawner:
    """
    Central factory for creating and managing agents.
    
    Features:
    - Creates agents on demand
    - Manages agent registry
    - Coordinates multi-agent workflows
    - Tracks all agent activities
    """
    
    def __init__(self):
        self.active_agents: Dict[str, BaseAgent] = {}
        self.agent_classes: Dict[AgentType, Type[BaseAgent]] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register built-in agent types."""
        # Will be populated when agent classes are imported
        pass
    
    def register_agent(self, agent_type: AgentType, agent_class: Type[BaseAgent]):
        """Register an agent class for a type."""
        self.agent_classes[agent_type] = agent_class
    
    async def spawn(
        self,
        agent_type: AgentType,
        session_id: str,
        parent_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> BaseAgent:
        """
        Spawn a new agent instance.
        
        Args:
            agent_type: Type of agent to spawn
            session_id: Session ID for context
            parent_id: Optional parent agent ID
            
        Returns:
            New agent instance
        """
        if agent_type not in self.agent_classes:
            # Lazy load agent classes
            await self._load_agent_class(agent_type)
        
        agent_class = self.agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent = agent_class(
            agent_type=agent_type,
            session_id=session_id,
            parent_id=parent_id,
            job_id=job_id
        )
        
        self.active_agents[agent.id] = agent
        await agent.report_status(AgentStatus.SPAWNING, f"Agent {agent_type.value} spawning...")
        
        return agent
    
    async def _load_agent_class(self, agent_type: AgentType):
        """Lazy load agent class based on type."""
        try:
            if agent_type == AgentType.UNDERSTANDING:
                from services.agents.understanding_agent import UnderstandingAgent
                self.agent_classes[AgentType.UNDERSTANDING] = UnderstandingAgent
            elif agent_type == AgentType.RESEARCH:
                from services.agents.research_agent import ResearchAgent
                self.agent_classes[AgentType.RESEARCH] = ResearchAgent
            elif agent_type == AgentType.ACTION:
                from services.agents.action_agent import ActionAgent
                self.agent_classes[AgentType.ACTION] = ActionAgent
            elif agent_type == AgentType.VERIFICATION:
                from services.agents.verification_agent import VerificationAgent
                self.agent_classes[AgentType.VERIFICATION] = VerificationAgent
        except ImportError as e:
            print(f"⚠️ Could not load agent {agent_type}: {e}")
    
    async def spawn_and_run(
        self,
        agent_type: AgentType,
        session_id: str,
        context: AgentContext,
        parent_id: Optional[str] = None
    ) -> AgentContext:
        """
        Spawn an agent and run it immediately.
        
        Args:
            agent_type: Type of agent to spawn
            session_id: Session ID
            context: Current context
            parent_id: Optional parent agent ID
            
        Returns:
            Updated context after agent execution
        """
        job_id = getattr(context, 'job_id', None)
        agent = await self.spawn(agent_type, session_id, parent_id, job_id=job_id)
        
        try:
            result = await agent.run(context)
            await agent.report_status(AgentStatus.COMPLETED, f"Agent {agent_type.value} completed")
            return result
        except Exception as e:
            await agent.report_status(AgentStatus.FAILED, f"Agent failed: {str(e)}")
            raise
        finally:
            # Cleanup
            if agent.id in self.active_agents:
                del self.active_agents[agent.id]
    
    async def run_workflow(
        self,
        session_id: str,
        context: AgentContext,
        workflow: List[AgentType]
    ) -> AgentContext:
        """
        Run a sequence of agents as a workflow.
        
        Args:
            session_id: Session ID
            context: Initial context
            workflow: List of agent types to run in sequence
            
        Returns:
            Final context after all agents complete
        """
        current_context = context
        
        for agent_type in workflow:
            current_context = await self.spawn_and_run(
                agent_type,
                session_id,
                current_context
            )
        
        return current_context
    
    def get_active_agents(self, session_id: str = None) -> List[Dict]:
        """Get all active agents, optionally filtered by session."""
        agents = []
        for agent in self.active_agents.values():
            if session_id is None or agent.session_id == session_id:
                agents.append({
                    "id": agent.id,
                    "type": agent.agent_type.value,
                    "status": agent.status.value,
                    "session_id": agent.session_id,
                    "parent_id": agent.parent_id,
                    "created_at": agent.created_at.isoformat()
                })
        return agents


# Global instance
agent_spawner = AgentSpawner()
