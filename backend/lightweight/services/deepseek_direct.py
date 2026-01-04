"""
DeepSeek Direct API Service

Uses DeepSeek's direct API (not OpenRouter) with:
- DeepSeek-V3.2: Official successor to V3.2-Exp (for general tasks)
- DeepSeek-V3.2-Speciale: Reasoning-first model for complex tasks (API-only)

Reasoning models are automatically used for complex tasks requiring reasoning.
"""

import httpx
from typing import Dict, Any, List, Optional
from core.config import settings


class DeepSeekDirectService:
    """Direct DeepSeek API service with reasoning model support."""
    
    # Available DeepSeek models
    MODELS = {
        "deepseek-v3.2": {
            "id": "deepseek-chat",
            "name": "DeepSeek-V3.2",
            "description": "Official successor to V3.2-Exp. General purpose.",
            "reasoning": False
        },
        "deepseek-reasoning": {
            "id": "deepseek-reasoner",  # Verify actual model ID
            "name": "DeepSeek-V3.2-Speciale",
            "description": "Reasoning-first model for complex tasks. API-only.",
            "reasoning": True
        },
        "deepseek-chat": {
            "id": "deepseek-chat",
            "name": "DeepSeek Chat",
            "description": "Standard DeepSeek Chat model",
            "reasoning": False
        }
    }
    
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        self.base_url = "https://api.deepseek.com"  # Updated to official base
        
        if not self.api_key:
            print("⚠️  WARNING: DEEPSEEK_API_KEY not configured. DeepSeek direct API will not work.")
    
    async def generate_content(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        use_reasoning: bool = False,
        model_key: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[callable] = None
    ) -> str:
        """
        Generate content using DeepSeek direct API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            use_reasoning: If True, uses reasoning model for complex tasks
            model_key: Specific model to use (default: auto-select)
            
        Returns:
            Generated content
        """
        if not self.api_key:
            return ""
        
        # Select model
        if model_key and model_key in self.MODELS:
            model_id = self.MODELS[model_key]["id"]
        elif use_reasoning:
            model_id = self.MODELS["deepseek-reasoning"]["id"]
        else:
            model_id = self.MODELS["deepseek-v3.2"]["id"]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                if stream:
                    # Streaming mode with callback
                    full_content = []
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status_code != 200:
                             err_body = await response.aread()
                             print(f"❌ DeepSeek Error {response.status_code}: {err_body}")
                             response.raise_for_status()
                        
                        async for line in response.aiter_lines():
                            if not line or line.strip() == "": continue
                            if line.startswith("data: "): line = line[6:]
                            if line.strip() == "[DONE]": break
                            
                            try:
                                import json
                                chunk_data = json.loads(line)
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_content.append(content)
                                        if stream_callback:
                                            await stream_callback(content)
                            except json.JSONDecodeError: continue
                    
                    return "".join(full_content)
                else:
                    # Non-streaming mode
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if response.status_code != 200:
                        response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"⚠️  DeepSeek API error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model_key: Optional[str] = None
    ):
        """
        Async generator for streaming content from DeepSeek.
        """
        if not self.api_key:
            yield "⚠️ DeepSeek API Key not configured."
            return

        # Select model
        if model_key and model_key in self.MODELS:
            model_id = self.MODELS[model_key]["id"]
        else:
            model_id = self.MODELS["deepseek-v3.2"]["id"]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        print(f"❌ DeepSeek streaming error: {response.status_code} - {error_text}")
                        yield f"❌ Error: {response.status_code}"
                        return

                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if line.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            chunk_data = json.loads(line)
                            if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"⚠️  DeepSeek Streaming API error: {e}")
            yield f"❌ Connection Error: {str(e)}"
    
    async def generate_with_reasoning(
        self,
        prompt: str,
        system_prompt: str = "You are an expert reasoning agent. Think step by step.",
        temperature: float = 0.7,
        max_tokens: int = 32000  # Increased for complex reasoning tasks
    ) -> str:
        """
        Generate content using DeepSeek reasoning model for complex tasks.
        
        This uses DeepSeek-V3.2-Speciale which is specifically designed
        for reasoning-first tasks and complex problem solving.
        """
        return await self.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_reasoning=True
        )
    
    def should_use_reasoning(self, prompt: str, task_type: str = None) -> bool:
        """
        Determine if a task requires reasoning model.
        
        Args:
            prompt: User prompt
            task_type: Type of task (planning, analysis, etc.)
            
        Returns:
            True if reasoning model should be used
        """
        # Keywords that suggest complex reasoning is needed
        reasoning_keywords = [
            "analyze", "compare", "evaluate", "explain why", "solve",
            "plan", "strategy", "reasoning", "logic", "complex",
            "multiple steps", "step by step", "think through"
        ]
        
        prompt_lower = prompt.lower()
        
        # Check for reasoning keywords
        if any(keyword in prompt_lower for keyword in reasoning_keywords):
            return True
        
        # Check task type
        if task_type in ["planning", "analysis", "reasoning", "complex"]:
            return True
        
        # Check prompt length (longer prompts often need more reasoning)
        if len(prompt.split()) > 100:
            return True
        
        return False
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available models."""
        return self.MODELS


# Singleton instance
deepseek_direct_service = DeepSeekDirectService()
deepseek_direct = deepseek_direct_service

