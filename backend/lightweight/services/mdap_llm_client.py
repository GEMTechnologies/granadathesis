"""
MDAP LLM Client - Wrapper for microagent LLM calls

Uses DeepSeek directly for cost efficiency (not OpenRouter).
"""

import httpx
from typing import Optional
from app.core.config import settings


class MDAPlLMClient:
    """
    LLM client for MDAP microagents.
    
    Uses DeepSeek API directly for cost-effective citations.
    """
    
    def __init__(
        self,
        model_key: str = "deepseek",  # Only deepseek supported
        temperature: float = 0.1,
        max_tokens: int = 500
    ):
        self.model_key = model_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1"
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured in .env")
    
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Call DeepSeek API with system and user prompts.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            LLM response as string
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temp,
            "max_tokens": tokens
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
            raise RuntimeError(f"DeepSeek API call failed: {str(e)}")


# Singleton instance
mdap_llm_client = MDAPlLMClient()
