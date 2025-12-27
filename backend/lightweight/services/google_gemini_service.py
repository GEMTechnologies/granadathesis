"""
Google Gemini Direct API Service

Provides direct access to Google Gemini API for:
- Vision capabilities (image understanding)
- Image generation (Imagen models)
- Multimodal conversations

Uses API key: AIzaSyBZidAshUk9cB3DuwY3kP2mPfnC4QXapj8
"""

import httpx
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from core.config import settings


class GoogleGeminiService:
    """Google Gemini direct API service for vision and image generation."""
    
    # Available Gemini models
    MODELS = {
        "gemini-pro-vision": {
            "id": "gemini-pro-vision",
            "name": "Gemini Pro Vision",
            "supports_vision": True,
            "supports_text": True
        },
        "gemini-1.5-pro": {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "supports_vision": True,
            "supports_text": True
        },
        "gemini-1.5-flash": {
            "id": "gemini-1.5-flash",
            "name": "Gemini 1.5 Flash",
            "supports_vision": True,
            "supports_text": True
        }
    }
    
    def __init__(self):
        # Use provided API key first, then check settings
        self.api_key = "AIzaSyBZidAshUk9cB3DuwY3kP2mPfnC4QXapj8"
        if not self.api_key:
            self.api_key = getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY_1', None)
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            print("⚠️  WARNING: Google Gemini API key not configured.")
    
    def _encode_image(self, image_path: Path) -> Dict[str, Any]:
        """Encode image to base64 and prepare for Gemini API."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Determine MIME type
        ext = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        return {
            "inline_data": {
                "mime_type": mime_type,
                "data": image_data
            }
        }
    
    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail. What do you see?",
        model: str = "gemini-1.5-pro",
        workspace_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze an image using Google Gemini Vision.
        
        Args:
            image_path: Path to image file
            prompt: Question/instruction about the image
            model: Gemini model to use
            workspace_id: Workspace ID if image is in workspace
            
        Returns:
            Analysis result
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Gemini API key not configured"
            }
        
        # Resolve image path
        image_file = self._resolve_image_path(image_path, workspace_id)
        
        if not image_file.exists():
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        try:
            # Encode image
            image_part = self._encode_image(image_file)
            
            # Prepare request
            model_id = self.MODELS.get(model, {}).get("id", "gemini-1.5-pro")
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            image_part,
                            {"text": prompt}
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract text from response
                if "candidates" in data and len(data["candidates"]) > 0:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    return {
                        "success": True,
                        "analysis": content,
                        "image_path": str(image_file),
                        "model": model_id,
                        "prompt": prompt
                    }
                else:
                    return {
                        "success": False,
                        "error": "No response from Gemini API"
                    }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "image_path": str(image_file)
            }
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "nano-banana",  # "nano-banana" (2.5-flash) or "nano-banana-pro" (3-pro)
        aspect_ratio: str = "1:1",
        resolution: str = "1K"  # For Pro only: "1K", "2K", "4K"
    ) -> Dict[str, Any]:
        """
        Generate an image using Google Gemini Nano Banana models.
        
        Models:
        - nano-banana (gemini-2.5-flash-image): Fast, cheap, 1024px
        - nano-banana-pro (gemini-3-pro-image-preview): Advanced, up to 4K
        
        Args:
            prompt: Image generation prompt
            model: Model to use ("nano-banana" or "nano-banana-pro")
            aspect_ratio: Aspect ratio (e.g., "1:1", "16:9", "4:3")
            resolution: Resolution for Pro model ("1K", "2K", "4K")
            
        Returns:
            Generated image result with base64 data or URL
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Gemini API key not configured"
            }
        
        # Map model names to API model IDs
        model_map = {
            "nano-banana": "gemini-2.5-flash-image",
            "nano-banana-pro": "gemini-3-pro-image-preview",
            "gemini-2.5-flash-image": "gemini-2.5-flash-image",
            "gemini-3-pro-image-preview": "gemini-3-pro-image-preview"
        }
        
        model_id = model_map.get(model, "gemini-2.5-flash-image")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Build request payload based on Google's API structure
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["IMAGE"]
                    }
                }
                
                # Add image config for aspect ratio
                image_config = {"aspectRatio": aspect_ratio}
                
                # For Pro model, also add resolution
                if model_id == "gemini-3-pro-image-preview":
                    image_config["imageSize"] = resolution
                
                payload["generationConfig"]["imageConfig"] = image_config
                
                response = await client.post(
                    f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    error_text = response.text[:500] if hasattr(response, 'text') else "Unknown error"
                    return {
                        "success": False,
                        "error": f"Gemini API returned {response.status_code}: {error_text}",
                        "model": model_id
                    }
                
                data = response.json()
                
                # Extract image from response (based on Google's API structure)
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            # Google API uses inline_data (snake_case) in responses
                            if "inline_data" in part:
                                inline_data = part["inline_data"]
                                image_data = inline_data.get("data")
                                mime_type = inline_data.get("mime_type", "image/png")
                            # Alternative: inlineData (camelCase) - check both
                            elif "inlineData" in part:
                                inline_data = part["inlineData"]
                                image_data = inline_data.get("data")
                                mime_type = inline_data.get("mimeType", "image/png")
                            else:
                                continue
                            
                            if image_data:
                                # Convert base64 to data URL for easy use
                                image_url = f"data:{mime_type};base64,{image_data}"
                                
                                return {
                                    "success": True,
                                    "url": image_url,
                                    "base64": image_data,
                                    "mime_type": mime_type,
                                    "model": model_id,
                                    "prompt": prompt,
                                    "aspect_ratio": aspect_ratio,
                                    "resolution": resolution if model_id == "gemini-3-pro-image-preview" else "1024px",
                                    "source": f"Google Gemini {model_id} (Nano Banana)"
                                }
                
                return {
                    "success": False,
                    "error": "No image generated in response",
                    "model": model_id
                }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Gemini image generation timeout",
                "model": model_id
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Gemini image generation failed: {str(e)}",
                "model": model_id
            }
    
    async def chat_with_image(
        self,
        image_path: str,
        user_message: str,
        conversation_history: List[Dict] = None,
        model: str = "gemini-1.5-pro",
        workspace_id: str = None
    ) -> Dict[str, Any]:
        """Have a conversation about an image."""
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Gemini API key not configured"
            }
        
        image_file = self._resolve_image_path(image_path, workspace_id)
        
        if not image_file.exists():
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        try:
            image_part = self._encode_image(image_file)
            
            # Build conversation history
            contents = []
            conversation_history = conversation_history or []
            
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    # User messages might have images
                    if isinstance(content, dict) and "image" in content:
                        contents.append({
                            "parts": [
                                self._encode_image(Path(content["image"])),
                                {"text": content.get("text", "")}
                            ]
                        })
                    else:
                        contents.append({
                            "parts": [{"text": str(content)}]
                        })
                else:
                    # Assistant messages are text only
                    contents.append({
                        "parts": [{"text": str(content)}],
                        "role": "model"
                    })
            
            # Add current message with image
            contents.append({
                "parts": [
                    image_part,
                    {"text": user_message}
                ]
            })
            
            model_id = self.MODELS.get(model, {}).get("id", "gemini-1.5-pro")
            
            payload = {
                "contents": contents
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    return {
                        "success": True,
                        "response": content,
                        "image_path": str(image_file),
                        "model": model_id
                    }
                else:
                    return {
                        "success": False,
                        "error": "No response from Gemini API"
                    }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _resolve_image_path(self, image_path: str, workspace_id: str = None) -> Path:
        """Resolve image path (absolute or relative to workspace)."""
        from services.workspace_service import WORKSPACES_DIR
        
        path = Path(image_path)
        
        if path.is_absolute():
            return path
        
        if workspace_id:
            workspace_path = WORKSPACES_DIR / workspace_id
            return workspace_path / path
        
        return Path.cwd() / path
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available models."""
        return self.MODELS


# Singleton instance
google_gemini_service = GoogleGeminiService()

