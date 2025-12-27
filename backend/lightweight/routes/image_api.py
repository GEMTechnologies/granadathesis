"""
Image Generation API

Endpoints for image creation, editing, and management.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Literal
import os

router = APIRouter(prefix="/api/image", tags=["Image Generation"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GenerateImageRequest(BaseModel):
    prompt: str
    workspace_id: str
    method: Literal['dalle', 'python', 'search', 'auto'] = 'auto'
    size: str = "1024x1024"
    style: Optional[str] = None


class EditImageRequest(BaseModel):
    image_id: str
    workspace_id: str
    edit_prompt: str
    operations: List[dict]  # [{type: 'resize', size: (800, 600)}, ...]


class ImageResponse(BaseModel):
    image_id: str
    prompt: str
    file_path: str
    url: str
    source: str
    metadata: dict
    created_at: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/generate", response_model=ImageResponse)
async def generate_image(request: GenerateImageRequest):
    """
    Generate image using agent brain.
    
    Methods:
    - 'dalle': DALL-E API (best quality, requires key)
    - 'python': Python PIL (diagrams, patterns, text)
    - 'search': Unsplash search (real photos)
    - 'auto': Agent chooses best method
    
    Examples:
      "Create a sunset over mountains" → DALL-E or search
      "Make a gradient background" → Python
      "Generate a bar chart" → Python
    """
    from services.image_creator import ImageCreator
    
    # Get API key from environment
    openai_key = os.getenv('OPENAI_API_KEY')
    
    creator = ImageCreator(
        workspace_id=request.workspace_id,
        openai_api_key=openai_key
    )
    
    try:
        result = await creator.generate(
            prompt=request.prompt,
            method=request.method,
            size=request.size,
            style=request.style
        )
        
        return ImageResponse(
            image_id=result.image_id,
            prompt=result.prompt,
            file_path=result.file_path,
            url=f"/api/image/view/{result.image_id}?workspace_id={request.workspace_id}",
            source=result.source,
            metadata=result.metadata,
            created_at=result.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit", response_model=ImageResponse)
async def edit_image(request: EditImageRequest):
    """
    Edit existing image WITHOUT losing context.
    
    Operations:
      - {type: 'resize', size: (800, 600)}
      - {type: 'crop', box: (0, 0, 500, 500)}
      - {type: 'rotate', angle: 90}
      - {type: 'brightness', factor: 1.2}
      - {type: 'contrast', factor: 1.5}
      - {type: 'blur', radius: 5}
      - {type: 'sharpen'}
      - {type: 'add_text', text: 'Hello', position: (50, 50)}
    
    Context is maintained - all edits are tracked!
    """
    from services.image_creator import ImageCreator
    
    creator = ImageCreator(workspace_id=request.workspace_id)
    
    try:
        result = await creator.edit(
            image_id=request.image_id,
            edit_prompt=request.edit_prompt,
            operations=request.operations
        )
        
        return ImageResponse(
            image_id=result.image_id,
            prompt=result.prompt,
            file_path=result.file_path,
            url=f"/api/image/view/{result.image_id}?workspace_id={request.workspace_id}",
            source=result.source,
            metadata=result.metadata,
            created_at=result.created_at
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/view/{image_id}")
async def view_image(image_id: str, workspace_id: str):
    """View/download generated image."""
    from pathlib import Path
    
    from config import get_images_dir
    image_path = get_images_dir(workspace_id) / f"{image_id}.png"
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path, media_type="image/png")


@router.get("/history/{image_id}")
async def get_image_history(image_id: str, workspace_id: str):
    """
    Get full edit history for an image.
    
    Returns all edits with context - never lose track!
    """
    from services.image_creator import ImageCreator
    
    creator = ImageCreator(workspace_id=workspace_id)
    history = creator.get_image_history(image_id)
    
    return {
        "image_id": image_id,
        "edit_count": len(history),
        "history": history
    }


@router.get("/workspace/{workspace_id}/images")
async def list_workspace_images(workspace_id: str):
    """List all images in workspace."""
    from pathlib import Path
    
    from config import get_images_dir
    images_dir = get_images_dir(workspace_id)
    
    if not images_dir.exists():
        return {"images": [], "count": 0}
    
    images = []
    for img_file in images_dir.glob("*.png"):
        images.append({
            "image_id": img_file.stem,
            "filename": img_file.name,
            "url": f"/api/image/view/{img_file.stem}?workspace_id={workspace_id}",
            "size_bytes": img_file.stat().st_size
        })
    
    return {"images": images, "count": len(images)}
