"""
FastAPI Router for File Management Operations
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import shutil
from pathlib import Path
import datetime

router = APIRouter(prefix="/files", tags=["files"])

# Base path for thesis data
# Assumes this file is in backend/app/api/
# Thesis data is in backend/thesis_data/ (or ../../thesis_data relative to this file)
# But wait, the main app is in backend/
# Let's use a robust way to find the thesis_data directory.
# Based on server.py, it expects thesis_data at ../thesis_data relative to web-ui/server.py
# In backend context, it's likely backend/thesis_data
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "thesis_data"

class CreateFileRequest(BaseModel):
    path: str
    content: str = ""

class CreateFolderRequest(BaseModel):
    path: str

class RenameRequest(BaseModel):
    old_path: str
    new_path: str

class DeleteRequest(BaseModel):
    path: str

def get_safe_path(thesis_id: str, relative_path: str) -> Path:
    """
    Resolve and verify path is within thesis directory to prevent directory traversal.
    """
    thesis_dir = BASE_DIR / thesis_id
    # Normalize path to remove .. components
    target_path = (thesis_dir / relative_path).resolve()
    
    # Check if target_path is within thesis_dir
    if not str(target_path).startswith(str(thesis_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied: Path outside thesis directory")
    
    return target_path

@router.post("/{thesis_id}/create-file")
async def create_file(thesis_id: str, request: CreateFileRequest):
    try:
        file_path = get_safe_path(thesis_id, request.path)
        
        if file_path.exists():
            raise HTTPException(status_code=400, detail="File already exists")
            
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)
            
        return {"message": f"File created: {request.path}", "path": request.path}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{thesis_id}/create-folder")
async def create_folder(thesis_id: str, request: CreateFolderRequest):
    try:
        folder_path = get_safe_path(thesis_id, request.path)
        
        if folder_path.exists():
            raise HTTPException(status_code=400, detail="Folder already exists")
            
        folder_path.mkdir(parents=True, exist_ok=True)
        
        return {"message": f"Folder created: {request.path}", "path": request.path}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{thesis_id}/rename")
async def rename_item(thesis_id: str, request: RenameRequest):
    try:
        old_path = get_safe_path(thesis_id, request.old_path)
        new_path = get_safe_path(thesis_id, request.new_path)
        
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="Item not found")
            
        if new_path.exists():
            raise HTTPException(status_code=400, detail="Destination already exists")
            
        # Ensure parent of new path exists
        new_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(old_path), str(new_path))
        
        return {"message": f"Renamed {request.old_path} to {request.new_path}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{thesis_id}/delete")
async def delete_item(thesis_id: str, request: DeleteRequest):
    try:
        target_path = get_safe_path(thesis_id, request.path)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Item not found")
            
        if target_path.is_dir():
            shutil.rmtree(target_path)
            deleted_type = "Folder"
        else:
            os.remove(target_path)
            deleted_type = "File"
            
        return {"message": f"{deleted_type} deleted: {request.path}", "deleted_count": 1}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{thesis_id}/details/{path:path}")
async def get_details(thesis_id: str, path: str):
    try:
        target_path = get_safe_path(thesis_id, path)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Item not found")
            
        stat = target_path.stat()
        is_dir = target_path.is_dir()
        
        details = {
            "name": target_path.name,
            "path": path,
            "type": "folder" if is_dir else "file",
            "size": stat.st_size,
            "modified_iso": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_iso": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
        
        if not is_dir:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(target_path)
            details["mime_type"] = mime_type or "application/octet-stream"
            details["extension"] = target_path.suffix
        else:
            # Count children
            try:
                children = list(target_path.iterdir())
                details["child_count"] = len(children)
                # Calculate total size recursively (optional, might be slow for large folders)
                total_size = sum(f.stat().st_size for f in target_path.glob('**/*') if f.is_file())
                details["total_size"] = total_size
            except Exception:
                details["child_count"] = -1
                
        # Human readable size
        def format_bytes(size):
            power = 2**10
            n = 0
            power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
            while size > power:
                size /= power
                n += 1
            return f"{size:.1f} {power_labels[n]}B"
            
        details["size_human"] = format_bytes(details.get("total_size", details["size"]))
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
