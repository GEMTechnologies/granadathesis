from typing import Dict, Any, Optional
import httpx
from app.core.config import settings

class DeepSeekService:
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1"  # Verify exact endpoint
        
    async def generate_content(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7
    ) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API Key is not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat", # or deepseek-coder, check availability
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000 # Adjust as needed
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

deepseek_service = DeepSeekService()
