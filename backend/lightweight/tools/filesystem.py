import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Define workspace root - ensure this matches your docker volume mount
WORKSPACE_ROOT = "/thesis_data"

class WriteFileInput(BaseModel):
    path: str = Field(..., description="Relative path to the file to write (e.g., 'hello.md' or 'subdir/test.txt')")
    content: str = Field(..., description="Content to write to the file")

class ReadFileInput(BaseModel):
    path: str = Field(..., description="Relative path to the file to read")

class ListFilesInput(BaseModel):
    path: str = Field(".", description="Relative path to the directory to list (default: root)")

def _get_full_path(path: str) -> str:
    """Securely resolve path to be within workspace."""
    # Remove leading slashes to ensure it's treated as relative
    clean_path = path.lstrip('/')
    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, clean_path))
    
    # Security check: ensure path is within workspace
    if not full_path.startswith(os.path.abspath(WORKSPACE_ROOT)):
        raise ValueError(f"Access denied: Path must be within {WORKSPACE_ROOT}")
    
    return full_path

def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write content to a file, creating parent directories if needed."""
    try:
        full_path = _get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return {"status": "success", "path": path, "message": f"File '{path}' written successfully."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def read_file(path: str) -> Dict[str, Any]:
    """Read content from a file."""
    try:
        full_path = _get_full_path(path)
        
        if not os.path.exists(full_path):
            return {"status": "error", "error": f"File '{path}' not found."}
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {"status": "success", "path": path, "content": content}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def list_files(path: str = ".") -> Dict[str, Any]:
    """List files in a directory recursively."""
    try:
        full_path = _get_full_path(path)
        
        if not os.path.exists(full_path):
            return {"status": "error", "error": f"Directory '{path}' not found."}
            
        files = []
        # Use os.walk for recursion
        for root, dirs, filenames in os.walk(full_path):
            # Calculate relative path from the requested path
            rel_root = os.path.relpath(root, full_path)
            if rel_root == ".":
                rel_root = ""
            
            # Add directories
            for d in dirs:
                rel_path = os.path.join(rel_root, d)
                files.append({
                    "name": d,
                    "type": "folder", # Frontend expects 'folder'
                    "path": rel_path.replace("\\", "/") # Ensure forward slashes
                })
                
            # Add files
            for f in filenames:
                rel_path = os.path.join(rel_root, f)
                files.append({
                    "name": f,
                    "type": "file",
                    "path": rel_path.replace("\\", "/")
                })
            
        return {"status": "success", "path": path, "files": files}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Tool Definitions for LLM
filesystem_tools = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the specified content. Use this to save code, markdown, or text.",
            "parameters": WriteFileInput.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": ReadFileInput.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path.",
            "parameters": ListFilesInput.model_json_schema()
        }
    }
]
