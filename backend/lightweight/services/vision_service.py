"""
Vision Service - Image Understanding with Vision-Capable LLMs

Supports:
- Google Gemini Pro Vision (Direct API) - PRIMARY
- GPT-4 Vision (OpenAI via OpenRouter)
- Claude 3.5 Sonnet (Anthropic) - has vision
- Analyzing uploaded images
- Analyzing downloaded images in workspace
- Multimodal conversations (text + images)
"""

import httpx
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from core.config import settings
from services.openrouter import openrouter_service
from services.google_gemini_service import google_gemini_service
from services.workspace_service import WORKSPACES_DIR


class VisionService:
    """Service for understanding images using vision-capable LLMs."""
    
    # Vision-capable models
    VISION_MODELS = {
        "gemini-vision": {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro (Direct)",
            "provider": "google-direct",
            "supports_vision": True,
            "direct_api": True
        },
        "gpt4-vision": {
            "id": "openai/gpt-4-vision-preview",
            "name": "GPT-4 Vision",
            "provider": "openai",
            "supports_vision": True,
            "direct_api": False
        },
        "claude-vision": {
            "id": "anthropic/claude-3.5-sonnet",
            "name": "Claude 3.5 Sonnet",
            "provider": "anthropic",
            "supports_vision": True,
            "direct_api": False
        }
    }
    
    def __init__(self):
        self.openrouter = openrouter_service
        self.gemini = google_gemini_service
        self.default_model = "gemini-vision"  # Use Google Gemini by default
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _get_image_mime_type(self, image_path: Path) -> str:
        """Get MIME type based on file extension."""
        ext = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    async def analyze_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail. What do you see?",
        model_key: str = None,
        workspace_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze an image using a vision-capable LLM.
        
        Args:
            image_path: Path to image file (can be absolute or relative to workspace)
            prompt: Question/instruction about the image
            model_key: Vision model to use (default: claude-vision)
            workspace_id: Workspace ID if image is in workspace
            
        Returns:
            Analysis result with description and insights
        """
        # Resolve image path
        image_file = self._resolve_image_path(image_path, workspace_id)
        
        if not image_file.exists():
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        # Validate it's an image
        if not self._is_image_file(image_file):
            return {
                "success": False,
                "error": f"File is not an image: {image_path}"
            }
        
        # Use default model if not specified
        model_key = model_key or self.default_model
        
        if model_key not in self.VISION_MODELS:
            return {
                "success": False,
                "error": f"Unknown vision model: {model_key}. Available: {list(self.VISION_MODELS.keys())}"
            }
        
        model_config = self.VISION_MODELS[model_key]
        
        # Use Google Gemini Direct API if available
        if model_config.get("direct_api") and model_config["provider"] == "google-direct":
            try:
                result = await self.gemini.analyze_image(
                    image_path=str(image_file),
                    prompt=prompt,
                    model="gemini-1.5-pro",
                    workspace_id=workspace_id
                )
                return result
            except Exception as e:
                print(f"⚠️ Gemini direct API failed, falling back: {e}")
        
        try:
            # Encode image
            base64_image = self._encode_image(image_file)
            mime_type = self._get_image_mime_type(image_file)
            
            # Format message based on model provider
            if model_config["provider"] == "openai":
                # OpenAI format
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            elif model_config["provider"] == "anthropic":
                # Claude format
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            else:
                # Generic format (try OpenAI-style)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            
            # Call OpenRouter with vision model
            headers = {
                "Authorization": f"Bearer {self.openrouter.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://thesis.autogranada.com",
                "X-Title": "Vision Analysis Service"
            }
            
            payload = {
                "model": model_config["id"],
                "messages": messages,
                "max_tokens": 2000
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.openrouter.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "image_path": str(image_file),
                    "analysis": content,
                    "model": model_config["name"],
                    "prompt": prompt
                }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "image_path": str(image_file)
            }
    
    async def analyze_multiple_images(
        self,
        image_paths: List[str],
        prompt: str = "Describe what you see in these images. Compare and contrast them.",
        model_key: str = None,
        workspace_id: str = None
    ) -> Dict[str, Any]:
        """Analyze multiple images together."""
        model_key = model_key or self.default_model
        
        if model_key not in self.VISION_MODELS:
            return {
                "success": False,
                "error": f"Unknown vision model: {model_key}"
            }
        
        # Resolve all image paths
        images_data = []
        for img_path in image_paths:
            image_file = self._resolve_image_path(img_path, workspace_id)
            if image_file.exists() and self._is_image_file(image_file):
                base64_image = self._encode_image(image_file)
                mime_type = self._get_image_mime_type(image_file)
                images_data.append({
                    "path": str(image_file),
                    "base64": base64_image,
                    "mime_type": mime_type
                })
        
        if not images_data:
            return {
                "success": False,
                "error": "No valid images found"
            }
        
        try:
            model_config = self.VISION_MODELS[model_key]
            
            # Build message with multiple images
            if model_config["provider"] == "openai":
                content = [{"type": "text", "text": prompt}]
                for img in images_data:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{img['base64']}"
                        }
                    })
                messages = [{"role": "user", "content": content}]
            elif model_config["provider"] == "anthropic":
                content = []
                for img in images_data:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["mime_type"],
                            "data": img["base64"]
                        }
                    })
                content.append({"type": "text", "text": prompt})
                messages = [{"role": "user", "content": content}]
            else:
                # Generic format
                content = [{"type": "text", "text": prompt}]
                for img in images_data:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{img['base64']}"
                        }
                    })
                messages = [{"role": "user", "content": content}]
            
            headers = {
                "Authorization": f"Bearer {self.openrouter.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://thesis.autogranada.com",
                "X-Title": "Vision Analysis Service"
            }
            
            payload = {
                "model": model_config["id"],
                "messages": messages,
                "max_tokens": 3000
            }
            
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.openrouter.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "image_paths": [img["path"] for img in images_data],
                    "analysis": content,
                    "model": model_config["name"],
                    "prompt": prompt
                }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def chat_with_image(
        self,
        image_path: str,
        user_message: str,
        conversation_history: List[Dict] = None,
        model_key: str = None,
        workspace_id: str = None
    ) -> Dict[str, Any]:
        """
        Have a conversation about an image (multimodal chat).
        
        Args:
            image_path: Path to image
            user_message: User's question/message about the image
            conversation_history: Previous messages in conversation
            model_key: Vision model to use
            workspace_id: Workspace ID if image is in workspace
            
        Returns:
            Conversation response with image context
        """
        # Resolve image path
        image_file = self._resolve_image_path(image_path, workspace_id)
        
        if not image_file.exists():
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        model_key = model_key or self.default_model
        conversation_history = conversation_history or []
        
        try:
            base64_image = self._encode_image(image_file)
            mime_type = self._get_image_mime_type(image_file)
            model_config = self.VISION_MODELS[model_key]
            
            # Build messages with history and image
            messages = []
            
            # Add conversation history (without images for now)
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # Add current message with image
            if model_config["provider"] == "anthropic":
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": user_message
                        }
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_message
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                })
            
            headers = {
                "Authorization": f"Bearer {self.openrouter.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://thesis.autogranada.com",
                "X-Title": "Vision Chat Service"
            }
            
            payload = {
                "model": model_config["id"],
                "messages": messages,
                "max_tokens": 2000
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.openrouter.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "response": content,
                    "image_path": str(image_file),
                    "model": model_config["name"]
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
        path = Path(image_path)
        
        # If absolute path, use as-is
        if path.is_absolute():
            return path
        
        # If workspace_id provided, resolve relative to workspace
        if workspace_id:
            workspace_path = WORKSPACES_DIR / workspace_id
            return workspace_path / path
        
        # Otherwise, try as relative to current directory
        return Path.cwd() / path
    
    def _is_image_file(self, file_path: Path) -> bool:
        """Check if file is an image."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
        return file_path.suffix.lower() in image_extensions
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available vision models."""
        return self.VISION_MODELS


# Singleton instance
vision_service = VisionService()

