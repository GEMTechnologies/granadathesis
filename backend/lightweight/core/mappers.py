"""
Objective Mapping Systems.

This module implements the logic to map Objectives to:
1. Themes (for Chapter 2)
2. Variables (for Chapter 3, 4, 5)

It uses the LLM to generate these mappings automatically based on the Objective Store.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from services.openrouter import openrouter_service

class BaseMapper:
    """Base class for mappers."""
    
    def __init__(self, thesis_id: str, objective_store: Dict[str, Any]):
        self.thesis_id = thesis_id
        self.store = objective_store
        self.base_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
        
    def _save_json(self, filename: str, data: Any):
        """Save data to JSON file."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / filename
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✅ Saved {filename}")

class ThemeMapper(BaseMapper):
    """Maps Specific Objectives to Themes for Chapter 2."""
    
    async def generate(self) -> Dict[str, str]:
        """
        Generate theme_map.json.
        Format: {"SO1": "Theme 1: ...", "SO2": "Theme 2: ..."}
        """
        print(f"🎨 Generating Theme Map for {self.thesis_id}...")
        
        objectives_text = "\n".join([
            f"{obj['id']}: {obj['text']}" 
            for obj in self.store.get("specific_objectives", [])
        ])
        
        prompt = f"""
        You are an expert academic thesis architect.
        
        TASK:
        Convert the following Specific Objectives into distinct Research Themes for a Literature Review (Chapter 2).
        Each objective should map to exactly ONE primary theme.
        
        OBJECTIVES:
        {objectives_text}
        
        OUTPUT FORMAT:
        Return ONLY a valid JSON object mapping Objective IDs to Theme Titles.
        Example:
        {{
            "SO1": "Theme 1: The Impact of Digital Learning on Student Engagement",
            "SO2": "Theme 2: Teacher Readiness and Technological Adoption",
            "SO3": "Theme 3: Infrastructure Challenges in Rural Education"
        }}
        """
        
        try:
            response = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="gpt4", # Strong reasoning for structure
                system_prompt="You are a JSON generator. Output ONLY valid JSON.",
                temperature=0.2
            )
            
            # Clean response
            response = response.replace("```json", "").replace("```", "").strip()
            theme_map = json.loads(response)
            
            # Save
            self._save_json("theme_map.json", theme_map)
            return theme_map
            
        except Exception as e:
            print(f"❌ Error generating theme map: {e}")
            # Fallback
            fallback = {
                obj['id']: f"Theme {i+1}: Related to {obj['text'][:30]}..."
                for i, obj in enumerate(self.store.get("specific_objectives", []))
            }
            self._save_json("theme_map.json", fallback)
            return fallback

class VariableMapper(BaseMapper):
    """Maps Specific Objectives to Variables (IV, DV, etc.)."""
    
    async def generate(self) -> Dict[str, Any]:
        """
        Generate variable_map.json.
        """
        print(f"🔬 Generating Variable Map for {self.thesis_id}...")
        
        objectives_text = "\n".join([
            f"{obj['id']}: {obj['text']}" 
            for obj in self.store.get("specific_objectives", [])
        ])
        
        prompt = f"""
        You are an expert quantitative researcher.
        
        TASK:
        Analyze each Specific Objective and extract the research variables.
        For each objective, identify:
        1. Independent Variable (IV)
        2. Dependent Variable (DV)
        3. Moderators (if any)
        4. Mediators (if any)
        5. Key Indicators (how to measure them)
        
        OBJECTIVES:
        {objectives_text}
        
        OUTPUT FORMAT:
        Return ONLY a valid JSON object.
        Example:
        {{
          "SO1": {{
            "IV": "Digital Learning Tools",
            "DV": "Student Performance",
            "moderators": ["Teacher Experience"],
            "mediators": ["Student Motivation"],
            "indicators": {{
               "Digital Learning Tools": ["Frequency of use", "Type of platform"],
               "Student Performance": ["Test scores", "Grade point average"]
            }}
          }}
        }}
        """
        
        try:
            response = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="gpt4", # Strong reasoning for variable extraction
                system_prompt="You are a JSON generator. Output ONLY valid JSON.",
                temperature=0.2
            )
            
            # Clean response
            response = response.replace("```json", "").replace("```", "").strip()
            variable_map = json.loads(response)
            
            # Save
            self._save_json("variable_map.json", variable_map)
            return variable_map
            
        except Exception as e:
            print(f"❌ Error generating variable map: {e}")
            return {}
