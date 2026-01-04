"""
Thesis Configuration Integration

Integrates the intelligent analysis system and research context manager
into the thesis generation pipeline.

This module:
1. Parses /uoj_phd commands to extract configuration
2. Saves configuration to database
3. Provides context to chapter generators
4. Ensures consistency across all chapters
"""

from typing import Dict, Any, Optional
import re
import sys
from pathlib import Path

# Try relative imports first (when used as module), fall back to direct imports (when run standalone)
try:
    from services.analysis_intelligence import (
        parse_research_command,
        AnalysisIntelligence,
        ResearchConfig,
        AnalysisType
    )
    from services.research_context_manager import ResearchContextManager
    from services.thesis_session_db import ThesisSessionDB
except ImportError:
    # Fallback for standalone execution
    sys.path.insert(0, str(Path(__file__).parent))
    from analysis_intelligence import (
        parse_research_command,
        AnalysisIntelligence,
        ResearchConfig,
        AnalysisType
    )
    from research_context_manager import ResearchContextManager
    from thesis_session_db import ThesisSessionDB


class ThesisConfigurationManager:
    """
    Manages thesis configuration throughout the generation pipeline.
    
    Responsibilities:
    - Parse user commands
    - Store configuration in database
    - Provide context to chapter generators
    - Ensure consistency across chapters
    """
    
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.db = ThesisSessionDB(workspace_id)
    
    def parse_command(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse thesis generation command to extract configuration.
        
        Args:
            message: User message (e.g., "/uoj_phd n=50 design=survey topic='...'")
        
        Returns:
            Configuration dict or None if not a thesis command
        """
        msg_lower = message.lower().strip()
        
        # Check if this is a thesis generation command
        thesis_keywords = ['/uoj_phd', '/generic', 'generate thesis', 'generate chapter']
        if not any(kw in msg_lower for kw in thesis_keywords):
            return None
        
        # Extract topic
        topic_match = re.search(r'topic[=:\s]+["\']([^"\']+)["\']', message, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'topic[=:\s]+(\w+(?:\s+\w+){0,5})', message, re.IGNORECASE)
        topic = topic_match.group(1) if topic_match else "Research Study"
        
        # Extract case study
        case_match = re.search(r'case[_\s]?study[=:\s]+["\']([^"\']+)["\']', message, re.IGNORECASE)
        if not case_match:
            case_match = re.search(r'case[_\s]?study[=:\s]+(\w+(?:\s+\w+){0,3})', message, re.IGNORECASE)
        case_study = case_match.group(1) if case_match else ""
        
        # Parse research configuration using analysis_intelligence
        research_config = parse_research_command(message)
        
        # Build complete configuration
        config = {
            'topic': topic,
            'case_study': case_study,
            'sample_size': research_config.sample_size,
            'research_design': research_config.research_design.value,
            'measurement_scale': research_config.measurement_scale,
            'data_collection_methods': research_config.data_collection_methods,
            'confidence_level': research_config.confidence_level,
            'preferred_analyses': [a.value for a in research_config.preferred_analyses],
            'excluded_analyses': [a.value for a in research_config.exclude_analyses],
            'has_hypotheses': research_config.has_hypotheses,
            'has_control_group': research_config.has_control_group,
            'is_longitudinal': research_config.is_longitudinal,
            'custom_instructions': re.search(r'custom[_\s]?instructions[=:\s]+["\']([^"\']+)["\']', message, re.IGNORECASE).group(1) if re.search(r'custom[_\s]?instructions[=:\s]+["\']([^"\']+)["\']', message, re.IGNORECASE) else ""
        }
        
        return config
    
    def save_configuration(self, config: Dict[str, Any]):
        """
        Save configuration to database.
        
        Args:
            config: Configuration dictionary
        """
        # Save session info
        self.db.create_session(
            topic=config['topic'],
            case_study=config.get('case_study', '')
        )
        
        # Save research configuration
        self.db.save_research_config(config)
        
        print(f"✅ Saved thesis configuration:")
        print(f"   - Topic: {config['topic']}")
        print(f"   - Sample size: {config['sample_size']}")
        print(f"   - Design: {config['research_design']}")
    
    def get_methodology_context(self) -> Dict[str, Any]:
        """
        Get complete methodology context for Chapter 3 generation.
        
        Returns:
            Dict with population, sampling, statistical approach, etc.
        """
        # Get stored configuration
        config = self.db.get_research_config()
        if not config:
            # Return defaults
            config = {
                'sample_size': 385,
                'research_design': 'survey',
                'topic': self.db.get_topic() or 'Research Study',
                'case_study': self.db.get_case_study() or '',
                'measurement_scale': 'likert',
                'custom_instructions': ''
            }
        
        # Create research context manager
        manager = ResearchContextManager(config)
        
        # Get complete methodology context
        return manager.get_methodology_context()
    
    def get_analysis_context(self) -> Dict[str, Any]:
        """
        Get complete analysis context for Chapter 4 generation.
        
        Returns:
            Dict with sample size, recommended tests, visualizations, etc.
        """
        # Get stored configuration
        config = self.db.get_research_config()
        if not config:
            config = {
                'sample_size': 385,
                'research_design': 'survey',
                'measurement_scale': 'likert'
            }
        
        # Create research context manager for statistical approach
        manager = ResearchContextManager(config)
        analysis_ctx = manager.get_analysis_context()
        
        # Get objectives for intelligent analysis selection
        objectives_data = self.db.get_objectives()
        objectives = objectives_data.get('specific', [])
        
        if objectives:
            # Create analysis intelligence
            research_config = ResearchConfig(
                sample_size=config.get('sample_size', 385),
                measurement_scale=config.get('measurement_scale', 'likert'),
                preferred_analyses=[AnalysisType(a) for a in config.get('preferred_analyses', [])],
                exclude_analyses=[AnalysisType(a) for a in config.get('excluded_analyses', [])]
            )
            
            ai = AnalysisIntelligence(research_config)
            analysis_plan = ai.generate_analysis_plan(objectives)
            
            # Merge with statistical approach
            analysis_ctx['analysis_plan'] = analysis_plan
            analysis_ctx['selected_analyses'] = analysis_plan['selected_analyses']
            analysis_ctx['analysis_sequence'] = analysis_plan['analysis_sequence']
            analysis_ctx['visualizations'] = analysis_plan['visualizations']
        
        return analysis_ctx
    
    def get_chapter_context(self, chapter_number: int) -> Dict[str, Any]:
        """
        Get context for any chapter generation.
        
        Args:
            chapter_number: Chapter number (1-6)
        
        Returns:
            Dict with all relevant context for that chapter
        """
        context = {
            'workspace_id': self.workspace_id,
            'topic': self.db.get_topic() or 'Research Study',
            'case_study': self.db.get_case_study() or '',
            'objectives': self.db.get_objectives(),
            'research_questions': self.db.get_questions(),
            'custom_instructions': self.db.get_research_config().get('custom_instructions', '') if self.db.get_research_config() else ''
        }
        
        # Chapter-specific context
        if chapter_number == 3:
            context['methodology'] = self.get_methodology_context()
        elif chapter_number == 4:
            context['analysis'] = self.get_analysis_context()
        
        return context


def integrate_with_understanding_agent(message: str, workspace_id: str) -> Optional[Dict[str, Any]]:
    """
    Integration point for the understanding agent.
    
    Call this from the understanding agent to check if the message
    is a thesis generation command and extract configuration.
    
    Args:
        message: User message
        workspace_id: Workspace ID
    
    Returns:
        Configuration dict if thesis command, None otherwise
    """
    manager = ThesisConfigurationManager(workspace_id)
    config = manager.parse_command(message)
    
    if config:
        # Save configuration
        manager.save_configuration(config)
        
        # Return configuration for agent context
        return {
            'is_thesis_command': True,
            'thesis_config': config,
            'intent': 'generate_thesis',
            'required_actions': ['spawn_thesis_generation']
        }
    
    return None


def get_chapter_generation_context(workspace_id: str, chapter_number: int) -> Dict[str, Any]:
    """
    Get context for chapter generation.
    
    Call this from chapter generators to get all necessary context.
    
    Args:
        workspace_id: Workspace ID
        chapter_number: Chapter number (1-6)
    
    Returns:
        Complete context for chapter generation
    """
    manager = ThesisConfigurationManager(workspace_id)
    return manager.get_chapter_context(chapter_number)


# Example usage and testing
if __name__ == "__main__":
    # Test command parsing
    test_commands = [
        "/uoj_phd n=50 design=case_study topic='Security Sector Reform' case_study='Juba'",
        "/uoj_phd n=385 design=survey analyses=pca,anova,sem topic='Political Stability'",
        "generate thesis on Healthcare Quality with n=150",
    ]
    
    for cmd in test_commands:
        print("=" * 80)
        print(f"Testing: {cmd}")
        print("=" * 80)
        
        manager = ThesisConfigurationManager("test_workspace")
        config = manager.parse_command(cmd)
        
        if config:
            print(f"\n✅ Parsed configuration:")
            print(f"   Topic: {config['topic']}")
            print(f"   Sample size: {config['sample_size']}")
            print(f"   Design: {config['research_design']}")
            print(f"   Analyses: {config['preferred_analyses']}")
        else:
            print("\n❌ Not a thesis command")
        
        print("\n")
