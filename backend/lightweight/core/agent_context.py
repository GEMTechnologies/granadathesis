"""
Agent Context Injection System.

This module provides a unified way to inject the "Central Brain" (Objective Store, Themes, Variables)
into every agent's prompt. This ensures all agents are aligned with the thesis objectives.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class AgentContext:
    """
    Loads and formats the full thesis context for agent injection.
    """
    
    def __init__(self, thesis_id: str):
        self.thesis_id = thesis_id
        self.base_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
        
        # Load data
        self.objective_store = self._load_json("objective_store.json")
        self.theme_map = self._load_json("theme_map.json")
        self.variable_map = self._load_json("variable_map.json")
        
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Helper to load JSON file safely."""
        path = self.base_dir / filename
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading {filename}: {e}")
        return {}

    def get_injection_prompt(self) -> str:
        """
        Returns a formatted string to be injected into the system prompt.
        """
        if not self.objective_store:
            return "" # No context available
            
        prompt = "\n\n=== THESIS CONTEXT (THE SOURCE OF TRUTH) ===\n"
        
        # 1. Objectives
        prompt += "OBJECTIVES:\n"
        if self.objective_store.get("general_objective"):
            prompt += f"General: {self.objective_store['general_objective']}\n"
        
        for obj in self.objective_store.get("specific_objectives", []):
            prompt += f"- {obj['id']}: {obj['text']}\n"
            
        # 2. Themes (if available)
        if self.theme_map:
            prompt += "\nRESEARCH THEMES (Chapter 2):\n"
            for obj_id, theme in self.theme_map.items():
                prompt += f"- {obj_id} -> {theme}\n"
                
        # 3. Variables (if available)
        if self.variable_map:
            prompt += "\nRESEARCH VARIABLES (Chapter 3-5):\n"
            for obj_id, vars in self.variable_map.items():
                prompt += f"- {obj_id}: IV={vars.get('IV', '?')}, DV={vars.get('DV', '?')}\n"
                
        prompt += "============================================\n\n"
        prompt += "INSTRUCTION: You MUST align all your work with the above Objectives, Themes, and Variables.\n"
        
        return prompt

    def validate_readiness(self) -> bool:
        """
        Check if the context is ready for agents to run.
        Returns True if critical data (objectives) exists.
        """
        return bool(self.objective_store and self.objective_store.get("specific_objectives"))
