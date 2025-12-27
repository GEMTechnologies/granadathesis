"""
University Manager - Manages multiple university thesis templates
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class UniversityType(str, Enum):
    """Supported universities"""
    UOJ_PHD = "uoj_phd"  # University of Juba PhD
    GENERIC = "generic"  # Generic/Base template


@dataclass
class UniversityConfig:
    """Configuration for a university thesis template"""
    name: str
    abbreviation: str
    type: UniversityType
    description: str
    cover_page_format: Dict[str, Any] = field(default_factory=dict)
    preliminary_sections: List[str] = field(default_factory=lambda: [
        "cover_page",
        "approval_page",
        "declaration",
        "dedication",
        "acknowledgement",
        "abstract",
        "table_of_contents",
        "list_of_tables",
        "list_of_figures",
        "acronyms"
    ])
    main_chapters: int = 6
    has_appendices: bool = True
    page_numbering_style: str = "complex"  # complex, simple, custom
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversityManager:
    """Manages university thesis templates and configurations"""

    def __init__(self):
        self.universities: Dict[str, UniversityConfig] = {}
        self._initialize_default_universities()

    def _initialize_default_universities(self):
        """Initialize default university templates"""
        
        # University of Juba PhD Template
        uoj_config = UniversityConfig(
            name="University of Juba",
            abbreviation="UoJ",
            type=UniversityType.UOJ_PHD,
            description="PhD thesis template for University of Juba",
            cover_page_format={
                "institution": "UNIVERSITY OF JUBA",
                "format_type": "official",
                "font": "Times New Roman",
                "font_size": 12,
                "alignment": "center",
                "spacing": "double",
            },
            preliminary_sections=[
                "cover_page",
                "approval_page",
                "declaration",
                "dedication",
                "acknowledgement",
                "abstract",
                "table_of_contents",
                "list_of_tables",
                "list_of_figures",
                "acronyms"
            ],
            main_chapters=6,
            has_appendices=True,
            page_numbering_style="complex",
            metadata={
                "school": "SCHOOL OF GRADUATE STUDIES",
                "location": "South Sudan",
                "established": 2011,
            }
        )
        self.universities[UniversityType.UOJ_PHD.value] = uoj_config

        # Generic Template (Base for other universities)
        generic_config = UniversityConfig(
            name="Generic University",
            abbreviation="GEN",
            type=UniversityType.GENERIC,
            description="Generic thesis template for any university",
            cover_page_format={
                "institution": "Your University Name",
                "format_type": "standard",
                "font": "Times New Roman",
                "font_size": 12,
                "alignment": "center",
                "spacing": "double",
            },
            preliminary_sections=[
                "cover_page",
                "approval_page",
                "abstract",
                "table_of_contents",
            ],
            main_chapters=6,
            has_appendices=True,
            page_numbering_style="simple",
            metadata={
                "customizable": True,
            }
        )
        self.universities[UniversityType.GENERIC.value] = generic_config

    def get_university(self, university_type: str) -> Optional[UniversityConfig]:
        """Get university configuration by type"""
        return self.universities.get(university_type)

    def list_universities(self) -> List[Dict[str, Any]]:
        """List all available universities"""
        return [
            {
                "type": config.type.value,
                "name": config.name,
                "abbreviation": config.abbreviation,
                "description": config.description,
                "main_chapters": config.main_chapters,
                "has_appendices": config.has_appendices,
            }
            for config in self.universities.values()
        ]

    def add_university(self, config: UniversityConfig) -> bool:
        """Add a new university template"""
        if config.type.value in self.universities:
            return False
        self.universities[config.type.value] = config
        return True

    def update_university(self, university_type: str, config: UniversityConfig) -> bool:
        """Update existing university template"""
        if university_type not in self.universities:
            return False
        self.universities[university_type] = config
        return True

    def get_preliminary_sections(self, university_type: str) -> List[str]:
        """Get preliminary sections for a university"""
        config = self.get_university(university_type)
        return config.preliminary_sections if config else []

    def get_main_chapters_count(self, university_type: str) -> int:
        """Get number of main chapters for a university"""
        config = self.get_university(university_type)
        return config.main_chapters if config else 6

    def get_page_numbering_style(self, university_type: str) -> str:
        """Get page numbering style for a university"""
        config = self.get_university(university_type)
        return config.page_numbering_style if config else "simple"

    def export_config(self, university_type: str) -> Optional[Dict[str, Any]]:
        """Export university configuration as dictionary"""
        config = self.get_university(university_type)
        if not config:
            return None
        
        return {
            "name": config.name,
            "abbreviation": config.abbreviation,
            "type": config.type.value,
            "description": config.description,
            "cover_page_format": config.cover_page_format,
            "preliminary_sections": config.preliminary_sections,
            "main_chapters": config.main_chapters,
            "has_appendices": config.has_appendices,
            "page_numbering_style": config.page_numbering_style,
            "metadata": config.metadata,
        }

    def validate_thesis_input(self, university_type: str, thesis_input: Dict[str, Any]) -> tuple[bool, str]:
        """Validate thesis input for a university"""
        config = self.get_university(university_type)
        if not config:
            return False, f"University type '{university_type}' not found"

        # Required fields for all universities
        required_fields = ["title", "author_name", "supervisor"]
        for field in required_fields:
            if field not in thesis_input or not thesis_input[field]:
                return False, f"Missing required field: {field}"

        # Validate chapter count
        if "chapters" in thesis_input:
            chapters = thesis_input.get("chapters", {})
            if len(chapters) > config.main_chapters:
                return False, f"Too many chapters. Maximum: {config.main_chapters}"

        return True, "Validation successful"
