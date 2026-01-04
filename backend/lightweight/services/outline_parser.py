"""
Outline Parser Service - Parse and manage custom thesis outlines

Allows users to provide their own thesis structure instead of hardcoded outlines.
Supports JSON/YAML formats and provides default templates.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from services.workspace_service import WORKSPACES_DIR


class OutlineParser:
    """Parse and manage thesis outlines."""
    
    DEFAULT_OUTLINES_DIR = Path(__file__).parent.parent / "outlines"
    
    @staticmethod
    def load_outline(workspace_id: str) -> Dict:
        """
        Load custom outline from workspace or use default.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Outline dict with chapters and sections
        """
        workspace_path = WORKSPACES_DIR / workspace_id
        outline_path = workspace_path / "outline.json"
        
        # Try custom outline first
        if outline_path.exists():
            try:
                with open(outline_path, 'r', encoding='utf-8') as f:
                    outline = json.load(f)
                print(f"✅ Loaded custom outline from workspace")
                return outline
            except Exception as e:
                print(f"⚠️ Error loading custom outline: {e}")
        
        # Fallback to default PhD outline
        return OutlineParser.get_default_outline("phd_dissertation")
    
    @staticmethod
    def save_outline(workspace_id: str, outline: Dict) -> bool:
        """
        Save custom outline to workspace.
        
        Args:
            workspace_id: Workspace ID
            outline: Outline dict
            
        Returns:
            True if successful
        """
        try:
            # Validate first
            if not OutlineParser.validate_outline(outline):
                print("⚠️ Invalid outline structure")
                return False
            
            workspace_path = WORKSPACES_DIR / workspace_id
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            outline_path = workspace_path / "outline.json"
            with open(outline_path, 'w', encoding='utf-8') as f:
                json.dump(outline, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved custom outline to workspace")
            return True
            
        except Exception as e:
            print(f"⚠️ Error saving outline: {e}")
            return False
    
    @staticmethod
    def validate_outline(outline: Dict) -> bool:
        """
        Validate outline structure.
        
        Args:
            outline: Outline dict
            
        Returns:
            True if valid
        """
        # Check required fields
        if "chapters" not in outline:
            return False
        
        if not isinstance(outline["chapters"], list):
            return False
        
        # Validate each chapter
        for chapter in outline["chapters"]:
            if "number" not in chapter or "title" not in chapter:
                return False
            
            if "sections" not in chapter or not isinstance(chapter["sections"], list):
                return False
        
        return True
    
    @staticmethod
    def get_chapter_structure(outline: Dict, chapter_num: int) -> Optional[Dict]:
        """
        Get structure for specific chapter.
        
        Args:
            outline: Outline dict
            chapter_num: Chapter number (1-based)
            
        Returns:
            Chapter dict with sections
        """
        for chapter in outline.get("chapters", []):
            if chapter.get("number") == chapter_num:
                return chapter
        
        return None
    
    @staticmethod
    def get_default_outline(outline_type: str = "phd_dissertation") -> Dict:
        """
        Get default outline template.
        
        Args:
            outline_type: Type of outline (phd_dissertation, masters_thesis, etc.)
            
        Returns:
            Default outline dict
        """
        # Default PhD dissertation outline
        if outline_type == "phd_dissertation":
            return {
                "thesis_type": "PhD Dissertation",
                "chapters": [
                    {
                        "number": 1,
                        "title": "Introduction",
                        "sections": [
                            "Background to the Study",
                            "Statement of the Problem",
                            "Purpose of the Study",
                            "Research Objectives",
                            "Research Questions",
                            "Significance of the Study",
                            "Scope and Limitations",
                            "Definition of Terms"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Literature Review",
                        "sections": [
                            "Introduction",
                            "Theoretical Framework",
                            "Empirical Literature",
                            "Research Gaps",
                            "Summary"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Research Methodology",
                        "sections": [
                            "Introduction",
                            "Research Design",
                            "Study Population",
                            "Sample Size and Sampling",
                            "Data Collection Methods",
                            "Data Analysis",
                            "Validity and Reliability",
                            "Ethical Considerations"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Data Analysis and Findings",
                        "sections": [
                            "Introduction",
                            "Demographic Characteristics",
                            "Findings by Objective",
                            "Summary of Findings"
                        ]
                    },
                    {
                        "number": 5,
                        "title": "Discussion, Conclusions and Recommendations",
                        "sections": [
                            "Introduction",
                            "Discussion of Findings",
                            "Conclusions",
                            "Recommendations",
                            "Areas for Further Research"
                        ]
                    }
                ]
            }
        
        # Masters thesis outline
        elif outline_type == "masters_thesis":
            return {
                "thesis_type": "Masters Thesis",
                "chapters": [
                    {
                        "number": 1,
                        "title": "Introduction",
                        "sections": [
                            "Background",
                            "Problem Statement",
                            "Objectives",
                            "Significance"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Literature Review",
                        "sections": [
                            "Theoretical Framework",
                            "Empirical Studies",
                            "Research Gaps"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Methodology",
                        "sections": [
                            "Research Design",
                            "Data Collection",
                            "Data Analysis"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Results and Discussion",
                        "sections": [
                            "Findings",
                            "Discussion",
                            "Implications"
                        ]
                    },
                    {
                        "number": 5,
                        "title": "Conclusion",
                        "sections": [
                            "Summary",
                            "Recommendations"
                        ]
                    }
                ]
            }
        
        # Default fallback
        return OutlineParser.get_default_outline("phd_dissertation")
    
    @staticmethod
    def list_templates() -> List[Dict]:
        """List available outline templates."""
        return [
            {
                "id": "phd_dissertation",
                "name": "PhD Dissertation",
                "description": "Standard 5-chapter PhD dissertation structure",
                "chapters": 5
            },
            {
                "id": "masters_thesis",
                "name": "Masters Thesis",
                "description": "Standard masters thesis structure",
                "chapters": 5
            }
        ]


# Singleton instance
outline_parser = OutlineParser()
