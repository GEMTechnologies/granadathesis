"""
Multi-University Thesis Generation System

Supports multiple universities and thesis templates.
Each university has its own configuration, formatting rules, and structure.
"""

from .university_manager import UniversityManager
from .base_template import BaseThesisGenerator

__all__ = [
    "UniversityManager",
    "BaseThesisGenerator",
]
