"""
Agent Stream Factory - Factory pattern for agent-specific streaming to preview tabs.

Each agent type (writer, editor, researcher, etc.) can stream their work
to dedicated preview tabs in real-time.
"""
from typing import Dict, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from core.events import events


class AgentStreamHandler(ABC):
    """Base class for agent-specific streaming handlers."""
    
    def __init__(self, job_id: str, workspace_id: str):
        self.job_id = job_id
        self.workspace_id = workspace_id
        self.tab_id = f"{self.agent_type}-{job_id}"
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent type identifier (e.g., 'writer', 'editor', 'researcher')."""
        pass
    
    @abstractmethod
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream a chunk of content to the preview tab."""
        pass
    
    @abstractmethod
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark streaming as complete."""
        pass


class WriterAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Writer agent - streams content to preview tab."""
    
    @property
    def agent_type(self) -> str:
        return "writer"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream writing chunk to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "writer",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "content",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark writing as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "writer",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "content",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class EditorAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Editor agent - streams edits to preview tab."""
    
    @property
    def agent_type(self) -> str:
        return "editor"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream editing chunk to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "editor",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "edit",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark editing as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "editor",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "edit",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class ResearcherAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Researcher agent - streams research results to preview tab."""
    
    @property
    def agent_type(self) -> str:
        return "researcher"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream research chunk to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "researcher",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "research",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark research as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "researcher",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "research",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class SearchAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Search agent - streams search results to preview tab."""
    
    @property
    def agent_type(self) -> str:
        return "search"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream search chunk to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "search",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "search",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark search as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "search",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "search",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_search_results(self, query: str, results: list, metadata: Optional[Dict] = None):
        """Stream search results to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "search",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": "",
            "type": "search",
            "query": query,
            "results": results,
            "completed": False,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class PlannerAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Planner agent - ONLY plans, does NOT write content."""
    
    @property
    def agent_type(self) -> str:
        return "planner"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream planning chunk to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "planning",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark planning as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "planning",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class InternetSearchAgentStreamHandler(AgentStreamHandler):
    """Stream handler for Internet Search agent - searches for updated real-time data."""
    
    @property
    def agent_type(self) -> str:
        return "internet_search"
    
    async def stream_chunk(self, chunk: str, metadata: Optional[Dict] = None):
        """Stream search progress to preview tab."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "internet_search",
            "tab_id": self.tab_id,
            "chunk": chunk,
            "type": "search",
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_complete(self, content: str, metadata: Optional[Dict] = None):
        """Mark internet search as complete."""
        await events.publish(self.job_id, "agent_stream", {
            "agent": "internet_search",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": content,
            "type": "search",
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })
    
    async def stream_search_results(self, query: str, results: list, metadata: Optional[Dict] = None):
        """Stream internet search results to preview tab."""
        # Format results as readable content
        results_md = f"## 🌐 Internet Search: {query}\n\n"
        for i, result in enumerate(results[:10], 1):
            title = result.get('title', 'No title')
            url = result.get('url', result.get('link', ''))
            snippet = result.get('snippet', result.get('description', ''))[:200]
            results_md += f"### {i}. {title}\n{snippet}\n[Source]({url})\n\n"
        
        await events.publish(self.job_id, "agent_stream", {
            "agent": "internet_search",
            "tab_id": self.tab_id,
            "chunk": "",
            "content": results_md,
            "type": "search",
            "query": query,
            "results": results,
            "completed": True,
            "workspace_id": self.workspace_id,
            "metadata": metadata or {}
        })


class AgentStreamFactory:
    """Factory for creating agent-specific stream handlers."""
    
    _handlers = {
        "writer": WriterAgentStreamHandler,
        "editor": EditorAgentStreamHandler,
        "researcher": ResearcherAgentStreamHandler,
        "search": SearchAgentStreamHandler,
        "planner": PlannerAgentStreamHandler,
        "internet_search": InternetSearchAgentStreamHandler,
        "academic": ResearcherAgentStreamHandler,  # Uses researcher handler for scholarly content
        "verifier": WriterAgentStreamHandler,  # Uses writer handler for verification output
    }
    
    @classmethod
    def create_handler(cls, agent_type: str, job_id: str, workspace_id: str) -> AgentStreamHandler:
        """Create a stream handler for the specified agent type."""
        handler_class = cls._handlers.get(agent_type.lower())
        if not handler_class:
            # Default to writer if unknown
            handler_class = WriterAgentStreamHandler
        
        return handler_class(job_id, workspace_id)
    
    @classmethod
    def register_handler(cls, agent_type: str, handler_class: type):
        """Register a custom agent stream handler."""
        cls._handlers[agent_type.lower()] = handler_class


# Convenience function
def get_agent_stream_handler(agent_type: str, job_id: str, workspace_id: str) -> AgentStreamHandler:
    """Get an agent stream handler."""
    return AgentStreamFactory.create_handler(agent_type, job_id, workspace_id)

