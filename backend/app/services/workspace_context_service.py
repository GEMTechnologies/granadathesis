"""
Workspace Context Service
Manages user objectives, uploaded data, and study tools per workspace.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkspaceContextService:
    """Manage workspace-specific context: objectives, data, tools."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.context_dir = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}/.context")
        self.context_dir.mkdir(parents=True, exist_ok=True)
        
        self.objectives_file = self.context_dir / "objectives.json"
        self.data_file = self.context_dir / "user_data.json"
        self.tools_file = self.context_dir / "study_tools.json"
        self.config_file = self.context_dir / "workspace_config.json"
    
    # ===== OBJECTIVES MANAGEMENT =====
    
    async def set_objectives(self, general: str, specific: List[str], research_questions: Optional[List[str]] = None):
        """Store user's research objectives."""
        objectives = {
            "general": general,
            "specific": specific,
            "research_questions": research_questions or [],
            "updated_at": datetime.now().isoformat(),
            "source": "user_defined"
        }
        
        self.objectives_file.write_text(json.dumps(objectives, indent=2))
        logger.info(f"✅ Saved objectives for {self.workspace_id}")
        
        return objectives
    
    def get_objectives(self) -> Dict[str, Any]:
        """Retrieve stored objectives."""
        if self.objectives_file.exists():
            try:
                return json.loads(self.objectives_file.read_text())
            except Exception as e:
                logger.error(f"Error loading objectives: {e}")
        return {"general": "", "specific": [], "research_questions": []}
    
    async def add_specific_objective(self, objective: str):
        """Add a specific objective to existing ones."""
        data = self.get_objectives()
        if objective not in data["specific"]:
            data["specific"].append(objective)
            data["updated_at"] = datetime.now().isoformat()
            self.objectives_file.write_text(json.dumps(data, indent=2))
            logger.info(f"✅ Added objective: {objective[:50]}...")
        return data
    
    # ===== USER DATA STORAGE =====
    
    async def register_uploaded_dataset(self, filename: str, filepath: str, file_type: str, description: str = ""):
        """Register user-uploaded dataset."""
        data = self._load_json(self.data_file) or {"datasets": [], "documents": [], "study_data": []}
        
        dataset = {
            "filename": filename,
            "filepath": filepath,
            "type": file_type,  # csv, xlsx, json, pdf, docx, etc.
            "description": description,
            "uploaded_at": datetime.now().isoformat(),
            "size": Path(filepath).stat().st_size if Path(filepath).exists() else 0
        }
        
        data["datasets"].append(dataset)
        self.data_file.write_text(json.dumps(data, indent=2))
        
        logger.info(f"✅ Registered dataset: {filename}")
        return dataset
    
    async def register_uploaded_document(self, filename: str, filepath: str, doc_type: str, description: str = ""):
        """Register research paper, article, or other document."""
        data = self._load_json(self.data_file) or {"datasets": [], "documents": [], "study_data": []}
        
        document = {
            "filename": filename,
            "filepath": filepath,
            "type": doc_type,  # pdf, docx, txt, etc.
            "description": description,
            "uploaded_at": datetime.now().isoformat(),
            "size": Path(filepath).stat().st_size if Path(filepath).exists() else 0
        }
        
        data["documents"].append(document)
        self.data_file.write_text(json.dumps(data, indent=2))
        
        logger.info(f"✅ Registered document: {filename}")
        return document
    
    def get_user_data(self) -> Dict[str, Any]:
        """Get all user's uploaded data."""
        return self._load_json(self.data_file) or {"datasets": [], "documents": [], "study_data": []}
    
    def get_datasets(self) -> List[Dict]:
        """Get all uploaded datasets."""
        return self.get_user_data().get("datasets", [])
    
    def get_documents(self) -> List[Dict]:
        """Get all uploaded documents."""
        return self.get_user_data().get("documents", [])
    
    # ===== STUDY TOOLS REGISTRATION =====
    
    async def register_study_tool(self, tool_name: str, tool_type: str, filepath: str, description: str = ""):
        """Register a study tool (questionnaire, interview guide, observation checklist, etc.)."""
        tools = self._load_json(self.tools_file) or {"tools": []}
        
        tool = {
            "name": tool_name,
            "type": tool_type,  # questionnaire, interview_guide, observation_checklist, focus_group_guide, etc.
            "filepath": filepath,
            "description": description,
            "registered_at": datetime.now().isoformat(),
            "size": Path(filepath).stat().st_size if Path(filepath).exists() else 0
        }
        
        tools["tools"].append(tool)
        self.tools_file.write_text(json.dumps(tools, indent=2))
        
        logger.info(f"✅ Registered study tool: {tool_name} ({tool_type})")
        return tool
    
    def get_study_tools(self) -> List[Dict]:
        """Get all registered study tools."""
        tools = self._load_json(self.tools_file) or {"tools": []}
        return tools.get("tools", [])
    
    def get_study_tools_by_type(self, tool_type: str) -> List[Dict]:
        """Get study tools of specific type."""
        return [t for t in self.get_study_tools() if t["type"] == tool_type]
    
    # ===== WORKSPACE CONFIGURATION =====
    
    async def set_workspace_config(self, config: Dict[str, Any]):
        """Store workspace-wide configuration."""
        existing = self._load_json(self.config_file) or {}
        existing.update(config)
        existing["updated_at"] = datetime.now().isoformat()
        
        self.config_file.write_text(json.dumps(existing, indent=2))
        logger.info(f"✅ Updated workspace configuration")
        
        return existing
    
    def get_workspace_config(self) -> Dict[str, Any]:
        """Get workspace configuration."""
        return self._load_json(self.config_file) or {}
    
    # ===== CONTEXT FOR LLM PROMPTS =====
    
    def get_full_context_for_llm(self) -> str:
        """Generate comprehensive context string for LLM prompts."""
        context_parts = []
        
        # Objectives
        objectives = self.get_objectives()
        if objectives.get("general") or objectives.get("specific"):
            context_parts.append("## Research Objectives\n")
            if objectives.get("general"):
                context_parts.append(f"**General Objective**: {objectives['general']}\n")
            if objectives.get("specific"):
                context_parts.append("**Specific Objectives**:\n")
                for i, obj in enumerate(objectives["specific"], 1):
                    context_parts.append(f"{i}. {obj}\n")
            if objectives.get("research_questions"):
                context_parts.append("**Research Questions**:\n")
                for i, rq in enumerate(objectives["research_questions"], 1):
                    context_parts.append(f"{i}. {rq}\n")
        
        # User Data
        user_data = self.get_user_data()
        if user_data.get("datasets"):
            context_parts.append("\n## Available Datasets\n")
            for dataset in user_data["datasets"]:
                context_parts.append(f"- **{dataset['filename']}** ({dataset['type']}): {dataset['description']}\n")
        
        if user_data.get("documents"):
            context_parts.append("\n## Research Documents\n")
            for doc in user_data["documents"]:
                context_parts.append(f"- **{doc['filename']}** ({doc['type']}): {doc['description']}\n")
        
        # Study Tools
        tools = self.get_study_tools()
        if tools:
            context_parts.append("\n## Study Tools\n")
            for tool in tools:
                context_parts.append(f"- **{tool['name']}** ({tool['type']}): {tool['description']}\n")
        
        return "".join(context_parts) if context_parts else "No workspace context set yet."
    
    # ===== HELPER METHODS =====
    
    def _load_json(self, filepath: Path) -> Optional[Dict]:
        """Safely load JSON file."""
        try:
            if filepath.exists():
                return json.loads(filepath.read_text())
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
        return None


# Global instance per workspace
_context_services: Dict[str, WorkspaceContextService] = {}


def get_workspace_context(workspace_id: str = "default") -> WorkspaceContextService:
    """Get context service for workspace."""
    if workspace_id not in _context_services:
        _context_services[workspace_id] = WorkspaceContextService(workspace_id)
    return _context_services[workspace_id]
