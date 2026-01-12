"""
Outline Parser Service - Parse and manage custom thesis outlines

Allows users to provide their own thesis structure instead of hardcoded outlines.
Supports JSON/YAML formats and provides default templates.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from services.workspace_service import WORKSPACES_DIR


class OutlineParser:
    """Parse and manage thesis outlines."""
    
    DEFAULT_OUTLINES_DIR = Path(__file__).parent.parent / "outlines"
    TEMPLATES_DB_PATH = Path(__file__).parent.parent / "data" / "outline_templates.db"

    @staticmethod
    def _get_templates_connection():
        OutlineParser.TEMPLATES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(OutlineParser.TEMPLATES_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _init_templates_db():
        conn = OutlineParser._get_templates_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outline_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                outline_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def _seed_builtin_templates():
        OutlineParser._init_templates_db()
        conn = OutlineParser._get_templates_connection()
        cursor = conn.cursor()

        for template in OutlineParser._builtin_template_list():
            cursor.execute("SELECT outline_json FROM outline_templates WHERE id = ?", (template["id"],))
            existing = cursor.fetchone()
            template_json = json.dumps(template["outline"], ensure_ascii=False)
            if existing:
                try:
                    existing_outline = json.loads(existing["outline_json"])
                except Exception:
                    existing_outline = None
                if existing_outline == template["outline"]:
                    continue
                cursor.execute(
                    """
                    UPDATE outline_templates
                    SET name = ?, description = ?, outline_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        template["name"],
                        template.get("description", ""),
                        template_json,
                        datetime.utcnow().isoformat(),
                        template["id"]
                    )
                )
                continue
            cursor.execute(
                """
                INSERT INTO outline_templates (id, name, description, outline_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    template["id"],
                    template["name"],
                    template.get("description", ""),
                    template_json,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                )
            )
        conn.commit()
        conn.close()
    
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
    def _builtin_template_list() -> List[Dict]:
        return [
            {
                "id": "phd_dissertation",
                "name": "PhD Dissertation",
                "description": "Standard 5-chapter PhD dissertation structure",
                "outline": OutlineParser._builtin_template("phd_dissertation")
            },
            {
                "id": "masters_thesis",
                "name": "Masters Thesis",
                "description": "Standard masters thesis structure",
                "outline": OutlineParser._builtin_template("masters_thesis")
            },
            {
                "id": "uoj_bsc_accounting_finance",
                "name": "UoJ BSc Accounting & Finance",
                "description": "University of Juba BSc Accounting and Finance structure",
                "outline": OutlineParser._builtin_template("uoj_bsc_accounting_finance")
            }
        ]

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
        OutlineParser._seed_builtin_templates()
        try:
            conn = OutlineParser._get_templates_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT outline_json FROM outline_templates WHERE id = ?", (outline_type,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row["outline_json"])
        except Exception as e:
            print(f"⚠️ Error reading outline template from DB: {e}")

        return OutlineParser._builtin_template(outline_type)

    @staticmethod
    def _builtin_template(outline_type: str) -> Dict:
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
        elif outline_type == "uoj_bsc_accounting_finance":
            return {
                "thesis_type": "BSc Accounting and Finance",
                "preliminary_pages": [
                    "Title Page (University of Juba format)",
                    "Declaration",
                    "Approval Page",
                    "Dedication (optional)",
                    "Acknowledgements",
                    "Abstract (not exceeding 300 words)",
                    "Table of Contents",
                    "List of Tables",
                    "List of Figures",
                    "List of Abbreviations"
                ],
                "chapters": [
                    {
                        "number": 1,
                        "title": "Introduction",
                        "sections": [
                            "1.1 Introduction",
                            "1.2 Background of the Study",
                            "1.3 Statement of the Problem",
                            "1.4 Objectives of the Study",
                            "1.4.1 General Objective",
                            "1.4.2 Specific Objectives",
                            "1.5 Research Questions / Research Hypotheses",
                            "1.6 Significance of the Study",
                            "1.7 Scope of the Study",
                            "1.7.1 Geographical Scope",
                            "1.7.2 Content Scope",
                            "1.7.3 Time Scope",
                            "1.8 Limitations of the Study",
                            "1.9 Operational Definition of Key Terms",
                            "1.10 Chapter One Summary"
                        ]
                    },
                    {
                        "number": 2,
                        "title": "Literature Review",
                        "sections": [
                            "2.1 Introduction",
                            "2.2 Theoretical Literature Review",
                            "2.3 Empirical Literature Review",
                            "2.4 Conceptual Framework",
                            "2.5 Research Gap",
                            "2.6 Chapter Two Summary"
                        ]
                    },
                    {
                        "number": 3,
                        "title": "Research Methodology",
                        "sections": [
                            "3.1 Introduction",
                            "3.2 Research Design",
                            "3.3 Study Area",
                            "3.4 Target Population",
                            "3.5 Sample Size and Sampling Techniques",
                            "3.6 Data Sources",
                            "3.6.1 Primary Data",
                            "3.6.2 Secondary Data",
                            "3.7 Data Collection Methods and Instruments",
                            "3.8 Validity and Reliability of Research Instruments",
                            "3.9 Data Analysis Techniques",
                            "3.10 Ethical Considerations",
                            "3.11 Chapter Three Summary"
                        ]
                    },
                    {
                        "number": 4,
                        "title": "Data Presentation, Analysis, and Discussion",
                        "sections": [
                            "4.1 Introduction",
                            "4.2 Response Rate",
                            "4.3 Demographic Characteristics of Respondents",
                            "4.4 Data Analysis and Findings",
                            "4.5 Discussion of Findings",
                            "4.6 Chapter Four Summary"
                        ]
                    },
                    {
                        "number": 5,
                        "title": "Summary, Conclusions, and Recommendations",
                        "sections": [
                            "5.1 Introduction",
                            "5.2 Summary of the Study",
                            "5.3 Conclusions",
                            "5.4 Recommendations",
                            "5.5 Suggestions for Further Research",
                            "5.6 Chapter Five Summary"
                        ]
                    }
                ],
                "references": {
                    "style": "APA (latest edition)",
                    "rule": "Only sources cited in the study should appear"
                },
                "appendices": [
                    "Questionnaire",
                    "Interview Guide",
                    "Research Permit",
                    "Ethical Clearance (if required)"
                ],
                "format_requirements": {
                    "font": "Times New Roman",
                    "font_size": 12,
                    "line_spacing": 1.5,
                    "margin": "1 inch (left, right, top, bottom)",
                    "page_numbers": {
                        "preliminary": "Roman",
                        "main_text": "Arabic"
                    },
                    "paper_size": "A4"
                },
                "defaults": {
                    "specific_objectives": 3,
                    "sample_size": 50
                },
                "length_requirements": {
                    "min_pages": 50,
                    "max_pages": 75,
                    "excludes": "appendices"
                }
            }
        
        # Default fallback
        return OutlineParser._builtin_template("phd_dissertation")
    
    @staticmethod
    def list_templates() -> List[Dict]:
        """List available outline templates."""
        OutlineParser._seed_builtin_templates()
        conn = OutlineParser._get_templates_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, outline_json FROM outline_templates ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        templates = []
        for row in rows:
            try:
                outline = json.loads(row["outline_json"])
                chapters = len(outline.get("chapters", []))
            except Exception:
                chapters = 0
            templates.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "chapters": chapters
            })
        return templates


# Singleton instance
outline_parser = OutlineParser()
