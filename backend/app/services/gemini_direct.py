"""
Gemini Direct Service - Direct Google Gemini API Integration

Bypasses OpenRouter to use Gemini directly since it's not working via OpenRouter.
Uses google-generativeai library for native Gemini access.
"""

import google.generativeai as genai
from typing import Optional
from app.core.config import settings


class GeminiDirectService:
    """
    Direct Gemini API integration.
    
    Uses Google's native API instead of OpenRouter for better reliability.
    """
    
    def __init__(self):
        self.api_keys = [
            settings.GEMINI_API_KEY_1,
            settings.GEMINI_API_KEY_2,
            settings.GEMINI_API_KEY_3
        ]
        
        # Filter out None keys
        self.api_keys = [k for k in self.api_keys if k]
        
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEY configured")
        
        # Configure with first key
        genai.configure(api_key=self.api_keys[0])
        
        # Use Gemini 1.5 Flash (correct model name for API)
        # Note: Use 'gemini-1.5-flash-latest' for the latest version
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        print(f"✓ Gemini Direct initialized with {len(self.api_keys)} API key(s)")
    
    async def generate_content(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful academic assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate content using Gemini.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Temperature for generation
            
        Returns:
            Generated content as string
        """
        try:
            # Combine system prompt and user prompt
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Generate content
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=4096
                )
            )
            
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            
            # Provide specific error guidance
            if "404" in error_msg:
                raise Exception(
                    f"Gemini API 404 error - Model may not exist. "
                    f"Try updating to 'gemini-1.5-pro-latest' or check Google AI Studio for available models. "
                    f"Error: {error_msg}"
                )
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                raise Exception(
                    f"Gemini API rate limit exceeded. "
                    f"Try again in a few seconds or use a different API key. "
                    f"Error: {error_msg}"
                )
            elif "api_key" in error_msg.lower():
                raise Exception(
                    f"Gemini API key invalid. "
                    f"Check your GEMINI_API_KEY in .env file. "
                    f"Error: {error_msg}"
                )
            else:
                raise Exception(f"Gemini API error: {error_msg}")
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": "Gemini 1.5 Pro",
            "provider": "Google",
            "strengths": ["Analysis", "Long context", "Multimodal"],
            "api_keys_available": len(self.api_keys)
        }


# Singleton instance
gemini_direct_service = GeminiDirectService()
