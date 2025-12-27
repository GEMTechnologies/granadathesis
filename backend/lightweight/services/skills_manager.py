"""
Skills Manager - Anthropic Skills-style System for DeepSeek Agents

Based on Anthropic's Skills system (https://github.com/anthropics/skills)
Adapted for DeepSeek agents and this codebase.

Skills are folders with instructions that teach agents how to perform
specialized tasks in a repeatable way.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Skill:
    """Represents a skill with metadata and instructions."""
    name: str
    description: str
    instructions: str
    path: Path
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SkillsManager:
    """
    Manages skills for agents - loads, stores, and provides skills.
    
    Skills are stored in folders with SKILL.md files containing:
    - YAML frontmatter (name, description, optional metadata)
    - Markdown instructions that guide the agent
    """
    
    def __init__(self, skills_directory: Optional[Path] = None):
        """
        Initialize the skills manager.
        
        Args:
            skills_directory: Path to skills directory (default: backend/lightweight/skills/)
        """
        if skills_directory is None:
            # Default to backend/lightweight/skills/
            base_path = Path(__file__).parent.parent
            skills_directory = base_path / "skills"
        
        self.skills_dir = Path(skills_directory)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self._skills: Dict[str, Skill] = {}
        self._load_all_skills()
    
    def _load_all_skills(self):
        """Load all skills from the skills directory."""
        if not self.skills_dir.exists():
            return
        
        for skill_folder in self.skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue
            
            skill_file = skill_folder / "SKILL.md"
            if not skill_file.exists():
                continue
            
            try:
                skill = self._load_skill(skill_file)
                if skill:
                    self._skills[skill.name] = skill
                    print(f"✅ Loaded skill: {skill.name}")
            except Exception as e:
                print(f"⚠️  Failed to load skill from {skill_folder}: {e}")
    
    def _load_skill(self, skill_file: Path) -> Optional[Skill]:
        """
        Load a skill from a SKILL.md file.
        
        Expected format:
        ---
        name: skill-name
        description: What this skill does
        [optional metadata]
        ---
        
        # Skill Instructions
        
        [Markdown content with instructions]
        """
        try:
            content = skill_file.read_text(encoding='utf-8')
            
            # Parse YAML frontmatter
            if not content.startswith('---'):
                return None
            
            # Split frontmatter and content
            parts = content.split('---', 2)
            if len(parts) < 3:
                return None
            
            frontmatter = parts[1].strip()
            instructions = parts[2].strip()
            
            # Parse YAML
            metadata = yaml.safe_load(frontmatter)
            if not metadata or 'name' not in metadata or 'description' not in metadata:
                return None
            
            # Create skill
            skill = Skill(
                name=metadata.pop('name'),
                description=metadata.pop('description'),
                instructions=instructions,
                path=skill_file.parent,
                metadata=metadata
            )
            
            return skill
        
        except Exception as e:
            print(f"⚠️  Error loading skill from {skill_file}: {e}")
            return None
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(skill_name)
    
    def list_skills(self) -> List[Skill]:
        """List all available skills."""
        return list(self._skills.values())
    
    def get_skill_instructions(self, skill_name: str) -> Optional[str]:
        """Get the instructions for a skill."""
        skill = self.get_skill(skill_name)
        return skill.instructions if skill else None
    
    def get_skills_for_task(self, task_description: str) -> List[Skill]:
        """
        Get skills that might be relevant for a task.
        
        Uses simple keyword matching on skill descriptions.
        For production, could use LLM to match skills to tasks.
        """
        task_lower = task_description.lower()
        relevant = []
        
        for skill in self._skills.values():
            desc_lower = skill.description.lower()
            name_lower = skill.name.lower()
            
            # Simple keyword matching
            if any(keyword in desc_lower or keyword in name_lower 
                   for keyword in task_lower.split() if len(keyword) > 3):
                relevant.append(skill)
        
        return relevant
    
    def inject_skill_instructions(self, skill_names: List[str], base_prompt: str) -> str:
        """
        Inject skill instructions into a base prompt.
        
        Args:
            skill_names: List of skill names to inject
            base_prompt: The base system prompt
            
        Returns:
            Enhanced prompt with skill instructions
        """
        if not skill_names:
            return base_prompt
        
        skill_sections = []
        for skill_name in skill_names:
            skill = self.get_skill(skill_name)
            if skill:
                skill_sections.append(f"## Skill: {skill.name}\n\n{skill.description}\n\n{skill.instructions}")
        
        if not skill_sections:
            return base_prompt
        
        skills_content = "\n\n---\n\n".join(skill_sections)
        
        enhanced_prompt = f"""{base_prompt}

---

## AVAILABLE SKILLS

The following skills are available to help you complete this task. Use their instructions and guidelines:

{skills_content}
"""
        return enhanced_prompt
    
    def reload_skills(self):
        """Reload all skills from disk."""
        self._skills.clear()
        self._load_all_skills()


# Singleton instance
_skills_manager: Optional[SkillsManager] = None


def get_skills_manager() -> SkillsManager:
    """Get or create the singleton skills manager."""
    global _skills_manager
    if _skills_manager is None:
        _skills_manager = SkillsManager()
    return _skills_manager




