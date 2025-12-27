"""
Image Generation & Editing Service

Integrated with autonomous agent brain.
Supports multiple image sources and editing without losing context.
"""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from pathlib import Path
import base64
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import requests
import json
from datetime import datetime


@dataclass
class ImageGeneration:
    """Generated or edited image."""
    image_id: str
    prompt: str
    file_path: str
    source: str  # 'dalle', 'python', 'search', 'edit'
    metadata: Dict
    created_at: str


class ImageCreator:
    """
    Image generation and editing integrated with agent brain.
    
    Capabilities:
    - Generate with DALL-E (if API key available)
    - Create with Python (PIL, matplotlib)
    - Search and download (Unsplash, Pexels)
    - Edit existing images
    - Maintain context (remembers previous edits)
    """
    
    def __init__(self, workspace_id: str, openai_api_key: Optional[str] = None):
        self.workspace_id = workspace_id
        self.openai_api_key = openai_api_key
        
        from config import get_images_dir
        self.images_dir = get_images_dir(workspace_id)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Context tracking (remembers image history)
        self.image_context: Dict[str, List[Dict]] = {}
    
    async def generate(
        self,
        prompt: str,
        method: Literal['dalle', 'python', 'search', 'auto'] = 'auto',
        size: str = "1024x1024",
        style: Optional[str] = None
    ) -> ImageGeneration:
        """
        Generate image using best available method.
        
        Methods:
        - 'dalle': DALL-E API (requires key)
        - 'python': Python PIL/matplotlib
        - 'search': Search Unsplash/Pexels
        - 'auto': Agent decides best method
        """
        
        if method == 'auto':
            method = self._choose_method(prompt)
        
        if method == 'dalle' and self.openai_api_key:
            return await self._generate_dalle(prompt, size, style)
        elif method == 'python':
            return await self._generate_python(prompt, size, style)
        elif method == 'search':
            return await self._search_and_download(prompt)
        else:
            # Fallback to Python generation
            return await self._generate_python(prompt, size, style)
    
    async def edit(
        self,
        image_id: str,
        edit_prompt: str,
        operations: List[Dict]
    ) -> ImageGeneration:
        """
        Edit existing image WITHOUT losing context.
        
        Operations can include:
        - resize, crop, rotate
        - brightness, contrast, saturation
        - filters (blur, sharpen, etc.)
        - add text, shapes
        - combine with other images
        """
        
        # Load original image
        original_path = self._get_image_path(image_id)
        img = Image.open(original_path)
        
        # Track edit context
        if image_id not in self.image_context:
            self.image_context[image_id] = []
        
        self.image_context[image_id].append({
            'prompt': edit_prompt,
            'operations': operations,
            'timestamp': datetime.now().isoformat()
        })
        
        # Apply operations
        for op in operations:
            img = self._apply_operation(img, op)
        
        # Save edited version
        edited_id = f"{image_id}_edit_{len(self.image_context[image_id])}"
        edited_path = self.images_dir / f"{edited_id}.png"
        img.save(edited_path)
        
        return ImageGeneration(
            image_id=edited_id,
            prompt=edit_prompt,
            file_path=str(edited_path),
            source='edit',
            metadata={
                'original_id': image_id,
                'edit_number': len(self.image_context[image_id]),
                'operations': operations,
                'context': self.image_context[image_id]
            },
            created_at=datetime.now().isoformat()
        )
    
    async def _generate_dalle(
        self,
        prompt: str,
        size: str,
        style: Optional[str]
    ) -> ImageGeneration:
        """Generate using DALL-E API."""
        
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": "hd" if style == "hd" else "standard"
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        image_url = result['data'][0]['url']
        
        # Download image
        img_response = requests.get(image_url)
        img = Image.open(io.BytesIO(img_response.content))
        
        # Save
        image_id = f"dalle_{int(datetime.now().timestamp())}"
        file_path = self.images_dir / f"{image_id}.png"
        img.save(file_path)
        
        return ImageGeneration(
            image_id=image_id,
            prompt=prompt,
            file_path=str(file_path),
            source='dalle',
            metadata={'model': 'dall-e-3', 'size': size},
            created_at=datetime.now().isoformat()
        )
    
    async def _generate_python(
        self,
        prompt: str,
        size: str,
        style: Optional[str]
    ) -> ImageGeneration:
        """
        Generate image using Python (PIL).
        
        Agent can create:
        - Diagrams, charts, visualizations
        - Geometric patterns
        - Gradients, backgrounds
        - Text-based images (posters, memes)
        """
        
        # Parse size
        width, height = map(int, size.split('x'))
        
        # Create image based on prompt keywords
        if any(word in prompt.lower() for word in ['gradient', 'background']):
            img = self._create_gradient(width, height, prompt)
        elif any(word in prompt.lower() for word in ['text', 'poster', 'meme']):
            img = self._create_text_image(width, height, prompt)
        elif any(word in prompt.lower() for word in ['pattern', 'geometric']):
            img = self._create_pattern(width, height, prompt)
        else:
            # Default: simple colored image
            img = self._create_simple(width, height, prompt)
        
        # Save
        image_id = f"python_{int(datetime.now().timestamp())}"
        file_path = self.images_dir / f"{image_id}.png"
        img.save(file_path)
        
        return ImageGeneration(
            image_id=image_id,
            prompt=prompt,
            file_path=str(file_path),
            source='python',
            metadata={'size': size, 'method': 'PIL'},
            created_at=datetime.now().isoformat()
        )
    
    async def _search_and_download(self, query: str) -> ImageGeneration:
        """Search Unsplash and download image."""
        
        # Unsplash API (no key needed for basic usage)
        url = f"https://source.unsplash.com/1024x1024/?{query}"
        
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        
        # Save
        image_id = f"search_{int(datetime.now().timestamp())}"
        file_path = self.images_dir / f"{image_id}.png"
        img.save(file_path)
        
        return ImageGeneration(
            image_id=image_id,
            prompt=query,
            file_path=str(file_path),
            source='search',
            metadata={'source': 'unsplash', 'query': query},
            created_at=datetime.now().isoformat()
        )
    
    def _create_gradient(self, width: int, height: int, prompt: str) -> Image.Image:
        """Create gradient image."""
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Parse colors from prompt or use defaults
        colors = [(255, 100, 100), (100, 100, 255)]  # Red to Blue
        
        for y in range(height):
            # Interpolate between colors
            ratio = y / height
            r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
            g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
            b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        return img
    
    def _create_text_image(self, width: int, height: int, prompt: str) -> Image.Image:
        """Create text-based image."""
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Extract text from prompt
        text = prompt.replace('create', '').replace('make', '').strip()
        
        # Add text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(0, 0, 0), font=font)
        
        return img
    
    def _create_pattern(self, width: int, height: int, prompt: str) -> Image.Image:
        """Create geometric pattern."""
        img = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Create grid pattern
        spacing = 50
        for x in range(0, width, spacing):
            for y in range(0, height, spacing):
                draw.ellipse([x, y, x + spacing - 10, y + spacing - 10],
                           fill=(100, 150, 200), outline=(50, 100, 150))
        
        return img
    
    def _create_simple(self, width: int, height: int, prompt: str) -> Image.Image:
        """Create simple colored background."""
        # Default blue
        return Image.new('RGB', (width, height), color=(100, 150, 200))
    
    def _apply_operation(self, img: Image.Image, operation: Dict) -> Image.Image:
        """Apply single editing operation."""
        op_type = operation.get('type')
        
        if op_type == 'resize':
            size = operation.get('size', (800, 600))
            return img.resize(size)
        
        elif op_type == 'crop':
            box = operation.get('box', (0, 0, img.width // 2, img.height // 2))
            return img.crop(box)
        
        elif op_type == 'rotate':
            angle = operation.get('angle', 90)
            return img.rotate(angle, expand=True)
        
        elif op_type == 'brightness':
            factor = operation.get('factor', 1.2)
            enhancer = ImageEnhance.Brightness(img)
            return enhancer.enhance(factor)
        
        elif op_type == 'contrast':
            factor = operation.get('factor', 1.2)
            enhancer = ImageEnhance.Contrast(img)
            return enhancer.enhance(factor)
        
        elif op_type == 'blur':
            radius = operation.get('radius', 5)
            return img.filter(ImageFilter.GaussianBlur(radius))
        
        elif op_type == 'sharpen':
            return img.filter(ImageFilter.SHARPEN)
        
        elif op_type == 'add_text':
            draw = ImageDraw.Draw(img)
            text = operation.get('text', 'Hello')
            position = operation.get('position', (50, 50))
            color = operation.get('color', (255, 255, 255))
            draw.text(position, text, fill=color)
            return img
        
        return img
    
    def _choose_method(self, prompt: str) -> str:
        """Agent decides best generation method."""
        prompt_lower = prompt.lower()
        
        # Keywords for each method
        if any(word in prompt_lower for word in ['realistic', 'photo', 'scene', 'portrait']):
            return 'dalle' if self.openai_api_key else 'search'
        
        elif any(word in prompt_lower for word in ['diagram', 'chart', 'graph', 'pattern']):
            return 'python'
        
        elif any(word in prompt_lower for word in ['find', 'search', 'get']):
            return 'search'
        
        return 'python'  # Default
    
    def _get_image_path(self, image_id: str) -> Path:
        """Get path to image file."""
        return self.images_dir / f"{image_id}.png"
    
    def get_image_history(self, image_id: str) -> List[Dict]:
        """Get full edit history for an image (maintains context)."""
        return self.image_context.get(image_id, [])
