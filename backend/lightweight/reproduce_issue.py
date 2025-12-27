import sys
import os
from pathlib import Path
import time

# Add parent directory to path to allow imports
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))
sys.path.append(str(current_dir.parent)) # backend

try:
    from services.workspace_service import WORKSPACES_DIR
except ImportError:
    # Fallback if import fails
    print("Could not import WORKSPACES_DIR, defining manually based on logic")
    WORKSPACES_DIR = Path("/home/gemtech/Desktop/thesis/thesis_data")

print(f"WORKSPACES_DIR: {WORKSPACES_DIR}")

def list_workspace_files(workspace_id: str, base_path: str = ""):
    print(f"Listing workspace: {workspace_id}")
    workspace_path = WORKSPACES_DIR / workspace_id
    
    if not workspace_path.exists():
        print(f"Workspace path does not exist: {workspace_path}")
        return []
    
    items = []
    search_path = workspace_path / base_path if base_path else workspace_path
    
    print(f"Searching in: {search_path}")
    
    start_time = time.time()
    count = 0
    try:
        for item in search_path.rglob("*"):
            count += 1
            if count % 100 == 0:
                print(f"Found {count} items...")
            
            # Skip hidden files
            if item.name.startswith('.'):
                continue
            
            # Get relative path
            try:
                rel_path = str(item.relative_to(workspace_path))
            except ValueError:
                print(f"Error getting relative path for {item}")
                continue
                
            stat = item.stat()
            items.append({
                "name": item.name,
                "path": rel_path
            })
    except Exception as e:
        print(f"Error listing files: {e}")
    
    end_time = time.time()
    print(f"Total items: {len(items)}")
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    return items

if __name__ == "__main__":
    list_workspace_files("default")
