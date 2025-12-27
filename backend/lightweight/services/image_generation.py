"""
Image Generation Service

Supports:
- Google Gemini Nano Banana (Direct API) - PRIMARY (cheap, nice images)
  - gemini-2.5-flash-image (Nano Banana) - fast, cheap
  - gemini-3-pro-image-preview (Nano Banana Pro) - advanced, up to 4K
- DALL-E (via OpenRouter)
- Stable Diffusion (via OpenRouter)
- DALL-E (Direct OpenAI API) - fallback
- Stable Diffusion (Replicate) - fallback
"""

import httpx
from typing import Dict, List, Any, Optional
from core.config import settings


class ImageGenerationService:
    """Generate images using AI models."""
    
    def __init__(self):
        # Google API key (provided by user)
        self.google_key = "AIzaSyBZidAshUk9cB3DuwY3kP2mPfnC4QXapj8"
        if not self.google_key:
            self.google_key = getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY_1', None)
        
        # OpenAI API key (provided by user for DALL-E fallback)
        self.openai_key = "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"
        if not self.openai_key:
            self.openai_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        self.replicate_key = getattr(settings, 'REPLICATE_API_TOKEN', None)
        self.stability_key = getattr(settings, 'STABILITY_API_KEY', None)
        
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: Optional[str] = None,
        model: str = "nano-banana"  # "nano-banana" (default, cheap), "dalle", "stable-diffusion", "nano-banana-pro"
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image
            size: Image size (e.g., "1024x1024", "512x512")
            style: Optional style guide
            model: Model to use ("dalle", "stable-diffusion", "imagen")
            
        Returns:
            Generated image URL and metadata
        """
        errors = []
        
        # 1. Try explicitly requested model first
        if model == "dalle":
            if self.openai_key:
                result = await self._generate_dalle(prompt, size)
                if result.get("success"):
                    return result
                errors.append(f"DALL-E: {result.get('error', 'Unknown error')}")
            else:
                errors.append("DALL-E: OpenAI API key not configured")
        
        elif model.startswith("stable"):
            if self.replicate_key:
                result = await self._generate_stable_diffusion(prompt, size, model)
                if result.get("success"):
                    return result
                errors.append(f"Stable Diffusion: {result.get('error', 'Unknown error')}")
            else:
                errors.append("Stable Diffusion: Replicate API key not configured")
        
        elif model in ["nano-banana", "google", "gemini", "nano-banana-pro"]:
            if self.google_key:
                result = await self._generate_nano_banana(prompt, size, model)
                if result.get("success"):
                    return result
                # If Nano Banana errors, try DALL-E as fallback immediately
                errors.append(f"Google Nano Banana: {result.get('error', 'Unknown error')}")
                if self.openai_key:
                    print("🔄 Nano Banana failed, trying DALL-E fallback...")
                    dalle_result = await self._generate_dalle(prompt, size)
                    if dalle_result.get("success"):
                        return dalle_result
                    errors.append(f"DALL-E (fallback): {dalle_result.get('error', 'Unknown error')}")
            else:
                errors.append("Google Nano Banana: Google API key not configured")
        
        # 2. Fallback: Try available services in order (skip if already tried)
        # Try Google Gemini Nano Banana first (cheap, nice images) - DEFAULT
        if model not in ["nano-banana", "google", "gemini", "nano-banana-pro"] and self.google_key:
            result = await self._generate_nano_banana(prompt, size)
            if result.get("success"):
                return result
            errors.append(f"Google Nano Banana (fallback): {result.get('error', 'Unknown error')}")
            # If Nano Banana errors, try DALL-E as fallback
            if self.openai_key:
                print("🔄 Nano Banana failed, trying DALL-E fallback...")
                dalle_result = await self._generate_dalle(prompt, size)
                if dalle_result.get("success"):
                    return dalle_result
                errors.append(f"DALL-E (fallback): {dalle_result.get('error', 'Unknown error')}")
        
        # Try DALL-E direct (fallback for other models)
        if model != "dalle" and self.openai_key:
            result = await self._generate_dalle(prompt, size)
            if result.get("success"):
                return result
            errors.append(f"DALL-E Direct (fallback): {result.get('error', 'Unknown error')}")
        
        # Try Stable Diffusion direct (fallback)
        if not model.startswith("stable") and self.replicate_key:
            result = await self._generate_stable_diffusion(prompt, size, "stable-diffusion")
            if result.get("success"):
                return result
            errors.append(f"Stable Diffusion Direct (fallback): {result.get('error', 'Unknown error')}")
        
        # 3. Return helpful error message
        error_msg = "Image generation failed with all available services."
        if errors:
            # Show most relevant error
            main_error = errors[0] if errors else "No services configured"
            error_msg = f"Image generation failed: {main_error}"
        
        return {
            "success": False,
            "error": error_msg,
            "errors": errors[:3],  # Limit to first 3 errors
            "suggestion": "Please configure GOOGLE_API_KEY for Nano Banana (cheap, recommended), OPENAI_API_KEY for DALL-E, or REPLICATE_API_TOKEN for Stable Diffusion. Alternatively, use image search instead.",
            "prompt": prompt
        }
    
    async def _generate_nano_banana(self, prompt: str, size: str, model: str = "nano-banana") -> Dict[str, Any]:
        """Generate image using Google Gemini Nano Banana (cheap, nice images)."""
        from services.google_gemini_service import google_gemini_service
        
        # Convert size to aspect ratio
        aspect_ratio = "1:1"  # default
        if "x" in size:
            parts = size.split("x")
            if len(parts) == 2:
                try:
                    width = int(parts[0])
                    height = int(parts[1])
                    ratio = width / height
                    if abs(ratio - 1.0) < 0.1:
                        aspect_ratio = "1:1"
                    elif abs(ratio - 16/9) < 0.1:
                        aspect_ratio = "16:9"
                    elif abs(ratio - 4/3) < 0.1:
                        aspect_ratio = "4:3"
                    elif abs(ratio - 3/4) < 0.1:
                        aspect_ratio = "3:4"
                    # Add more ratios as needed
                except:
                    pass
        
        result = await google_gemini_service.generate_image(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            resolution="1K"  # Default, can be "2K" or "4K" for Pro
        )
        
        return result
    
    async def _generate_dalle_openrouter(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using DALL-E via OpenRouter."""
        from services.openrouter import openrouter_service
        
        if not openrouter_service.api_key:
            return {"success": False, "error": "OpenRouter API key not configured"}
        
        try:
            # OpenRouter may support image generation models - need to check available models
            # For now, return not available
            return {
                "success": False,
                "error": "DALL-E via OpenRouter not yet implemented",
                "suggestion": "Use direct OpenAI API or Google Nano Banana instead"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_stable_diffusion_openrouter(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using Stable Diffusion via OpenRouter."""
        from services.openrouter import openrouter_service
        
        if not openrouter_service.api_key:
            return {"success": False, "error": "OpenRouter API key not configured"}
        
        try:
            # OpenRouter may support image generation models - need to check available models
            # For now, return not available
            return {
                "success": False,
                "error": "Stable Diffusion via OpenRouter not yet implemented",
                "suggestion": "Use Replicate API or Google Nano Banana instead"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_dalle(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using DALL-E 3."""
        try:
            # Truncate prompt if too long (DALL-E 3 has a 4000 char limit)
            if len(prompt) > 3500:
                prompt = prompt[:3500] + "..."
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",  # Explicitly use DALL-E 3
                        "prompt": prompt,
                        "n": 1,
                        "size": size,
                        "quality": "standard",
                        "response_format": "url"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("data") and len(data["data"]) > 0:
                    return {
                        "success": True,
                        "url": data["data"][0]["url"],
                        "image_url": data["data"][0]["url"],  # Alias for compatibility
                        "revised_prompt": data["data"][0].get("revised_prompt", ""),
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "size": size,
                        "source": "OpenAI DALL-E 3"
                    }
                else:
                    return {"success": False, "error": "No image generated"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_imagen(self, prompt: str, size: str) -> Dict[str, Any]:
        """
        Generate image using Google's Imagen API.
        
        Note: Imagen API endpoint structure may need verification.
        This implementation provides a structure that can be adjusted.
        """
        if not self.google_key:
            return {"success": False, "error": "Google API key not configured"}
        
        # Parse size
        width, height = 1024, 1024
        if "x" in size:
            parts = size.split("x")
            if len(parts) == 2:
                try:
                    width = int(parts[0])
                    height = int(parts[1])
                except:
                    pass
        
        try:
            # Note: Imagen API endpoint may differ - this is a placeholder structure
            # Google's Imagen API documentation should be consulted for exact endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Attempt Imagen API call
                # The actual endpoint and structure may need to be verified
                try:
                    response = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3:generateImages?key={self.google_key}",
                        json={
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "number_of_images": 1
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Parse response based on actual API structure
                        if "images" in data and len(data["images"]) > 0:
                            image_data = data["images"][0]
                            image_url = image_data.get("url") or image_data.get("base64") or image_data.get("bytesBase64Encoded")
                            
                            return {
                                "success": True,
                                "url": image_url,
                                "model": "imagen-3",
                                "prompt": prompt,
                                "size": size,
                                "source": "Google Imagen 3"
                            }
                    
                    # If status is not 200, check error
                    error_text = response.text[:200] if hasattr(response, 'text') else "Unknown error"
                    return {
                        "success": False,
                        "error": f"Imagen API returned {response.status_code}: {error_text}",
                        "fallback": True
                    }
                except httpx.HTTPStatusError as e:
                    # Endpoint may not exist or have wrong structure
                    error_msg = f"HTTP {e.response.status_code}"
                    if e.response.status_code == 404:
                        error_msg = "Imagen API endpoint not available (404)"
                    elif e.response.status_code == 400:
                        error_msg = "Imagen API request invalid (400)"
                    elif e.response.status_code == 403:
                        error_msg = "Imagen API access denied (403) - check API key permissions"
                    
                    return {
                        "success": False,
                        "error": error_msg,
                        "fallback": True
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Imagen API timeout",
                "fallback": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Imagen generation failed: {str(e)}",
                "fallback": True
            }
    
    async def _generate_stable_diffusion(self, prompt: str, size: str, model: str) -> Dict[str, Any]:
        """Generate image using Stable Diffusion via Replicate."""
        if not self.replicate_key:
            return {"success": False, "error": "Replicate API key not configured"}
        
        # Parse size
        width, height = 1024, 1024
        if "x" in size:
            parts = size.split("x")
            if len(parts) == 2:
                try:
                    width = int(parts[0])
                    height = int(parts[1])
                except:
                    pass
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Use Replicate API
                model_id = "stability-ai/stable-diffusion-xl-base-1.0" if "xl" in model else "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
                
                response = await client.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={
                        "Authorization": f"Token {self.replicate_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "version": model_id.split(":")[1] if ":" in model_id else None,
                        "input": {
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "num_outputs": 1
                        }
                    }
                )
                response.raise_for_status()
                prediction = response.json()
                
                # Poll for result
                prediction_id = prediction.get("id")
                if not prediction_id:
                    return {"success": False, "error": "Failed to create prediction"}
                
                # Wait for completion (simplified - in production use webhooks)
                import asyncio
                for _ in range(30):  # Max 30 attempts (5 minutes)
                    await asyncio.sleep(10)
                    status_response = await client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Token {self.replicate_key}"}
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    if status_data.get("status") == "succeeded":
                        output = status_data.get("output")
                        if output and len(output) > 0:
                            return {
                                "success": True,
                                "url": output[0] if isinstance(output, list) else output,
                                "model": model,
                                "prompt": prompt,
                                "size": size,
                                "source": "Stable Diffusion (Replicate)"
                            }
                    elif status_data.get("status") == "failed":
                        return {"success": False, "error": status_data.get("error", "Generation failed")}
                
                return {"success": False, "error": "Generation timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
image_generation_service = ImageGenerationService()

