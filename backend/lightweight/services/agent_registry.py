"""
Agent Registry

Stores, versions, and retrieves generated agents.
Enables reuse of agents for similar datasets.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import hashlib
from datetime import datetime


class AgentRegistry:
    """Registry for storing and retrieving generated agents."""
    
    def __init__(self):
        self.agents_dir = Path("generated_agents")
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.agents_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load agent index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}
            self._save_index()
    
    def _save_index(self):
        """Save agent index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    async def save(
        self,
        agent_code: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Save generated agent with metadata.
        
        Args:
            agent_code: Python code for agent
            metadata: Dataset analysis and task info
            
        Returns:
            Agent ID
        """
        # Generate unique ID
        agent_id = self._generate_id(agent_code, metadata)
        
        # Save code file
        code_file = self.agents_dir / f"{agent_id}.py"
        with open(code_file, 'w') as f:
            f.write(agent_code)
        
        # Save metadata
        meta_file = self.agents_dir / f"{agent_id}.json"
        metadata_with_timestamp = {
            **metadata,
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat(),
            "code_hash": hashlib.sha256(agent_code.encode()).hexdigest()
        }
        with open(meta_file, 'w') as f:
            json.dump(metadata_with_timestamp, f, indent=2)
        
        # Update index
        self.index[agent_id] = {
            "created_at": metadata_with_timestamp["created_at"],
            "task": metadata.get("task", "unknown"),
            "dataset_type": metadata.get("file_info", {}).get("format", "unknown")
        }
        self._save_index()
        
        return agent_id
    
    async def load(self, agent_id: str) -> Optional[str]:
        """Load agent code by ID."""
        code_file = self.agents_dir / f"{agent_id}.py"
        if not code_file.exists():
            return None
        
        with open(code_file, 'r') as f:
            return f.read()
    
    async def get_metadata(self, agent_id: str) -> Optional[Dict]:
        """Get agent metadata."""
        meta_file = self.agents_dir / f"{agent_id}.json"
        if not meta_file.exists():
            return None
        
        with open(meta_file, 'r') as f:
            return json.load(f)
    
    async def find_similar(
        self,
        dataset_analysis: Dict[str, Any],
        task: str
    ) -> Optional[str]:
        """
        Find existing agent for similar dataset/task.
        
        Args:
            dataset_analysis: Current dataset analysis
            task: Current task description
            
        Returns:
            Agent ID if found, None otherwise
        """
        # Simple matching: same file type and similar column count
        current_format = dataset_analysis.get("file_info", {}).get("format")
        current_cols = dataset_analysis.get("schema", {}).get("columns", 0)
        
        for agent_id in self.index:
            metadata = await self.get_metadata(agent_id)
            if not metadata:
                continue
            
            # Check file format match
            agent_format = metadata.get("file_info", {}).get("format")
            if agent_format != current_format:
                continue
            
            # Check column count similarity (within 20%)
            agent_cols = metadata.get("schema", {}).get("columns", 0)
            if agent_cols > 0:
                diff_ratio = abs(agent_cols - current_cols) / agent_cols
                if diff_ratio < 0.2:
                    # Similar dataset structure
                    return agent_id
        
        return None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {"agent_id": agent_id, **info}
            for agent_id, info in self.index.items()
        ]
    
    def _generate_id(self, code: str, metadata: Dict) -> str:
        """Generate unique agent ID."""
        # Use hash of code + timestamp
        content = f"{code}{datetime.now().isoformat()}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
        
        # Add prefix based on task type
        task = metadata.get("task", "generic")
        prefix = "agent"
        if "analysis" in task.lower():
            prefix = "analyzer"
        elif "transform" in task.lower():
            prefix = "transformer"
        elif "report" in task.lower():
            prefix = "reporter"
        
        return f"{prefix}_{hash_val}"


# Global instance
agent_registry = AgentRegistry()
