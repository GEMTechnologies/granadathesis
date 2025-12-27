"""
Base Agent Class.

Provides common functionality for all agents, specifically:
1. Context Injection (Objective Store, Themes, Variables)
2. Unified LLM access
"""

from typing import Optional
from core.agent_context import AgentContext
from services.openrouter import openrouter_service

class BaseAgent:
    """
    Base class for all agents in the system.
    Automatically handles context injection from the Objective Store.
    """
    
    def __init__(self, thesis_id: Optional[str] = None):
        self.llm = openrouter_service
        self.thesis_id = thesis_id
        self.context = AgentContext(thesis_id) if thesis_id else None
        
    def get_context_prompt(self) -> str:
        """Get the injected context prompt."""
        if self.context:
            return self.context.get_injection_prompt()
        return ""

    async def generate(self, prompt: str, system_prompt: str = "You are a helpful academic assistant.", **kwargs) -> str:
        """
        Wrapper for LLM generation that injects context.
        """
        # Inject context into system prompt
        full_system_prompt = system_prompt + "\n" + self.get_context_prompt()
        
        return await self.llm.generate_content(
            prompt=prompt,
            system_prompt=full_system_prompt,
            model_key=kwargs.get("model_key", "deepseek"),
            temperature=kwargs.get("temperature", 0.7)
        )
