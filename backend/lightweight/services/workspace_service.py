"""
Complete Workspace Service - UUID-based with Metadata

Features:
- UUID-based workspace IDs for unique URLs
- Standard folder structure (sections/, sources/, outputs/, data/)
- workspace.json metadata tracking
- Workspace listing and management
- Workspace settings for search filtering (year ranges, sources, etc.)
"""
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

import os

# Check for Docker volume mount first
if os.path.exists("/thesis_data"):
    WORKSPACES_DIR = Path("/thesis_data")
else:
    # Fallback for local execution - use absolute path to ensure consistency
    # This is the thesis_data folder in the project root
    WORKSPACES_DIR = Path("/home/gemtech/Desktop/thesis/thesis_data")


# Default workspace search settings
# Note: year_from of None means "5 years ago" (calculated dynamically)
DEFAULT_WORKSPACE_SETTINGS = {
    "search": {
        "year_from": None,      # None = dynamic (current year - 5)
        "year_to": None,        # None = current year
        "years_back": 5,        # Default: past 5 years of papers
        "sources": [            # Which APIs to use
            "semantic_scholar",
            "crossref", 
            "openalex",
            "arxiv",
            "pubmed",
            "core",
            "dblp"
        ],
        "max_results_per_source": 10,   # Results per API
        "max_total_results": 50,        # Max papers to return
        "require_abstract": True,
        "require_open_access": False,
        "language": "en",               # Preferred language
        "sort_by": "relevance",         # relevance, citations, year
    },
    "indexing": {
        "auto_download_pdfs": True,
        "extract_text": True,
        "generate_summaries": False,
        "max_sources": 500,     # Max papers to store
    },
    "citations": {
        "style": "apa",  # apa, mla, chicago, ieee, harvard
        "include_doi": True,
        "include_url": True,
    }
}


class WorkspaceService:
    """Complete workspace management with sessions and metadata."""
    
    @staticmethod
    async def create_workspace(
        topic: str = "",
        context: str = "",
        workspace_id: Optional[str] = None
    ) -> Dict:
        """
        Create a new workspace with UUID and metadata.
        
        Args:
            topic: Research topic
            context: Case study or context
            workspace_id: Optional custom ID (otherwise UUID generated)
            
        Returns:
            Dict with workspace_id, url, path, and metadata
        """
        # Generate workspace ID from topic name if not provided
        if not workspace_id:
            # Use topic name as workspace ID (sanitized)
            import re
            if topic:
                # Sanitize topic to create workspace name
                safe_name = re.sub(r'[^a-z0-9]+', '_', topic.lower().strip())
                safe_name = re.sub(r'_+', '_', safe_name).strip('_')
                # Limit length
                safe_name = safe_name[:50] if len(safe_name) > 50 else safe_name
                if not safe_name:
                    safe_name = "workspace"
                
                # Check if workspace with this name already exists, add suffix if needed
                base_name = safe_name
                counter = 1
                while (WORKSPACES_DIR / safe_name).exists():
                    safe_name = f"{base_name}_{counter}"
                    counter += 1
                
                workspace_id = safe_name
            else:
                workspace_id = str(uuid.uuid4())
        
        workspace_path = WORKSPACES_DIR / workspace_id
        
        # Create standard folder structure
        folders = {
            "sections": workspace_path / "sections",
            "sources": workspace_path / "sources",
            "outputs": workspace_path / "outputs",
            "data": workspace_path / "data"
        }
        
        created_folders = []
        for name, folder_path in folders.items():
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                created_folders.append(name)
                print(f"   ✓ Created {name}/ folder")
        
        # Create references.bib
        bib_file = workspace_path / "references.bib"
        if not bib_file.exists():
            bib_file.write_text("% BibTeX References\n% Auto-generated\n\n", encoding='utf-8')
            print(f"   ✓ Created references.bib")
        
        # Create workspace metadata with default settings
        metadata = {
            "workspace_id": workspace_id,
            "topic": topic,
            "context": context,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
            "version": "1.0",
            "settings": DEFAULT_WORKSPACE_SETTINGS.copy()
        }
        
        metadata_file = workspace_path / "workspace.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(f"   ✓ Created workspace.json with default settings")
        
        return {
            "workspace_id": workspace_id,
            "url": f"/workspace/{workspace_id}",
            "path": str(workspace_path),
            "metadata": metadata,
            "created_folders": created_folders
        }
    
    @staticmethod
    def get_workspace_metadata(workspace_id: str) -> Optional[Dict]:
        """Get workspace metadata from workspace.json."""
        metadata_file = WORKSPACES_DIR / workspace_id / "workspace.json"
        
        if metadata_file.exists():
            try:
                return json.loads(metadata_file.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"   ⚠️ Error reading metadata for {workspace_id}: {e}")
                return None
        
        return None
    
    @staticmethod
    def update_workspace_metadata(workspace_id: str, updates: Dict) -> bool:
        """Update workspace metadata."""
        metadata_file = WORKSPACES_DIR / workspace_id / "workspace.json"
        
        if not metadata_file.exists():
            return False
        
        try:
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            metadata.update(updates)
            metadata["updated_at"] = datetime.now().isoformat()
            
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            return True
        except Exception as e:
            print(f"   ⚠️ Error updating metadata: {e}")
            return False
    
    @staticmethod
    def get_workspace_settings(workspace_id: str) -> Dict:
        """
        Get workspace settings, with defaults fallback.
        
        Returns merged settings (defaults + any custom overrides).
        """
        metadata = WorkspaceService.get_workspace_metadata(workspace_id)
        
        if metadata and "settings" in metadata:
            # Merge with defaults to ensure all keys exist
            settings = DEFAULT_WORKSPACE_SETTINGS.copy()
            for category, values in metadata["settings"].items():
                if category in settings and isinstance(values, dict):
                    settings[category].update(values)
                else:
                    settings[category] = values
            return settings
        
        return DEFAULT_WORKSPACE_SETTINGS.copy()
    
    @staticmethod
    def update_workspace_settings(workspace_id: str, settings_updates: Dict) -> bool:
        """
        Update workspace settings.
        
        Args:
            workspace_id: Workspace ID
            settings_updates: Dict with settings to update, e.g.:
                {"search": {"year_from": 2015, "year_to": 2024}}
        
        Returns:
            True if successful
        """
        metadata = WorkspaceService.get_workspace_metadata(workspace_id)
        
        if not metadata:
            return False
        
        # Ensure settings key exists
        if "settings" not in metadata:
            metadata["settings"] = DEFAULT_WORKSPACE_SETTINGS.copy()
        
        # Deep merge settings
        for category, values in settings_updates.items():
            if category in metadata["settings"] and isinstance(values, dict):
                metadata["settings"][category].update(values)
            else:
                metadata["settings"][category] = values
        
        return WorkspaceService.update_workspace_metadata(workspace_id, {"settings": metadata["settings"]})
    
    @staticmethod
    def get_search_filters(workspace_id: str) -> Dict:
        """
        Get search-specific settings formatted for API calls.
        
        Calculates year_from dynamically based on years_back if not explicitly set.
        
        Returns dict with:
            - year_from: int (calculated or explicit)
            - year_to: int (current year or explicit)
            - sources: List[str]
            - max_results: int
            - max_total_results: int
            - require_abstract: bool
            - require_open_access: bool
        """
        settings = WorkspaceService.get_workspace_settings(workspace_id)
        search_settings = settings.get("search", {})
        
        current_year = datetime.now().year
        
        # Calculate year_from: explicit value OR (current_year - years_back)
        year_from = search_settings.get("year_from")
        if year_from is None:
            years_back = search_settings.get("years_back", 5)
            year_from = current_year - years_back
        
        # year_to defaults to current year
        year_to = search_settings.get("year_to") or current_year
        
        return {
            "year_from": year_from,
            "year_to": year_to,
            "sources": search_settings.get("sources", ["semantic_scholar", "crossref", "openalex", "arxiv"]),
            "max_results": search_settings.get("max_results_per_source", 10),
            "max_total_results": search_settings.get("max_total_results", 50),
            "require_abstract": search_settings.get("require_abstract", True),
            "require_open_access": search_settings.get("require_open_access", False),
            "language": search_settings.get("language", "en"),
            "sort_by": search_settings.get("sort_by", "relevance"),
        }
    
    @staticmethod
    def list_workspaces() -> List[Dict]:
        """List all workspaces with metadata."""
        if not WORKSPACES_DIR.exists():
            WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
            return []
        
        workspaces = []
        for workspace_dir in WORKSPACES_DIR.iterdir():
            if workspace_dir.is_dir():
                metadata = WorkspaceService.get_workspace_metadata(workspace_dir.name)
                if metadata:
                    workspaces.append(metadata)
                else:
                    # Workspace without metadata - create basic entry
                    workspaces.append({
                        "workspace_id": workspace_dir.name,
                        "topic": "Unknown",
                        "created_at": datetime.fromtimestamp(workspace_dir.stat().st_mtime).isoformat(),
                        "status": "legacy"
                    })
        
        # Sort by creation date (newest first)
        return sorted(workspaces, key=lambda x: x.get('created_at', ''), reverse=True)
    
    @staticmethod
    def workspace_exists(workspace_id: str) -> bool:
        """Check if workspace exists."""
        return (WORKSPACES_DIR / workspace_id).exists()
    
    @staticmethod
    def get_workspace_path(workspace_id: str) -> Path:
        """Get the path to a workspace."""
        return WORKSPACES_DIR / workspace_id
    
    @staticmethod
    def delete_workspace(workspace_id: str) -> bool:
        """Delete a workspace (use with caution)."""
        import shutil
        
        workspace_path = WORKSPACES_DIR / workspace_id
        
        if not workspace_path.exists():
            return False
        
        try:
            shutil.rmtree(workspace_path)
            print(f"   🗑️ Deleted workspace: {workspace_id}")
            return True
        except Exception as e:
            print(f"   ⚠️ Error deleting workspace: {e}")
            return False


# Singleton instance
workspace_service = WorkspaceService()

