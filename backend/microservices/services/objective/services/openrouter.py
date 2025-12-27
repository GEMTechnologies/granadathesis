"""
OpenRouter Service - Multi-Model API Integration

Provides unified access to multiple LLM models via OpenRouter API:
- Claude 3.5 Sonnet (best for academic writing)
- GPT-4 Turbo (strong reasoning)
- DeepSeek Chat (cost-effective)
- Gemini 1.5 Pro (strong analysis)

Supports parallel calls for competitive objective generation.
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from app.core.config import settings


class OpenRouterService:
    """
    Service for calling multiple LLM models via OpenRouter API.
    
    Enables competitive objective generation where multiple models
    compete to produce the best objectives.
    """
    
    # Model configurations (Gemini removed per user request)
    MODELS = {
        "claude": {
            "id": "anthropic/claude-3.5-sonnet",
            "name": "Claude 3.5 Sonnet",
            "strengths": ["Academic writing", "Nuance", "PhD-level thinking"],
            "max_tokens": 4000
        },
        "gpt4": {
            "id": "openai/gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "strengths": ["Reasoning", "Rule following", "Balanced output"],
            "max_tokens": 4000
        },
        "deepseek": {
            "id": "deepseek/deepseek-chat",
            "name": "DeepSeek Chat",
            "strengths": ["Structured output", "Cost-effective", "Fast"],
            "max_tokens": 4000
        }
    }
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
    
    async def generate_content(
        self,
        prompt: str,
        model_key: str,
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate content from a specific model.
        
        Args:
            prompt: User prompt
            model_key: Model key (claude, gpt4, deepseek)
            system_prompt: System prompt
            temperature: Temperature for generation
            
        Returns:
            Generated content as string
        """
        if model_key not in self.MODELS:
            raise ValueError(f"Unknown model: {model_key}. Available: {list(self.MODELS.keys())}")
        
        # Use OpenRouter for all models
        model_config = self.MODELS[model_key]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://thesis.autogranada.com",
            "X-Title": "PhD Thesis Objective Generator"
        }
        
        payload = {
            "model": model_config["id"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": model_config["max_tokens"]
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise Exception(f"OpenRouter API error for {model_key}: {str(e)}")
    
    async def generate_parallel(
        self,
        prompt: str,
        model_keys: List[str],
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate content from multiple models in parallel.
        
        This is the key method for competitive generation where all models
        compete simultaneously.
        
        Args:
            prompt: User prompt
            model_keys: List of model keys to use
            system_prompt: System prompt
            temperature: Temperature for generation
            
        Returns:
            Dict mapping model_key -> generated content
        """
        tasks = []
        for model_key in model_keys:
            task = self.generate_content(
                prompt=prompt,
                model_key=model_key,
                system_prompt=system_prompt,
                temperature=temperature
            )
            tasks.append((model_key, task))
        
        # Run all tasks in parallel
        results = {}
        
        # Use asyncio.gather to run all tasks concurrently
        import asyncio
        task_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (model_key, _), result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results[model_key] = {
                    "success": False,
                    "content": None,
                    "model_name": self.MODELS[model_key]["name"],
                    "error": str(result)
                }
            else:
                results[model_key] = {
                    "success": True,
                    "content": result,
                    "model_name": self.MODELS[model_key]["name"],
                    "error": None
                }
        
        return results
    
    def get_model_info(self, model_key: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        return self.MODELS.get(model_key, {})
    
    def get_all_models(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available models."""
        return self.MODELS


# Singleton instance
openrouter_service = OpenRouterService()
