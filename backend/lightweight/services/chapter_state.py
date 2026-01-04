"""
Chapter State Definition
Shared state management for parallel chapter generation.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

@dataclass
class ResearchResult:
    title: str
    url: str
    snippet: str
    source: str = "google"
    year: str = ""
    authors: str = ""
    doi: str = ""
    
@dataclass
class SectionContent:
    title: str
    content: str
    citations: List[str] = field(default_factory=list)
    status: str = "pending" # pending, writing, reviewing, complete
    word_count: int = 0
    
@dataclass
class AgentStatus:
    name: str # e.g. "Theory Agent"
    state: str # idle, working, complete, error
    current_action: str = ""
    progress: int = 0 # 0-100

@dataclass  
class ChapterState:
    """Shared state for parallel agents."""
    topic: str
    case_study: str
    job_id: str
    session_id: str
    workspace_id: str = "default"
    
    # Chapter being generated (1, 2, 3, etc.)
    chapter_number: int = 1
    
    # Background style selection (user can choose)
    background_style: str = "inverted_pyramid"  # Default style
    
    # Thesis customization parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    university_type: str = "generic"
    thesis_type: str = "phd" # Added thesis_type field
    
    # Research results by scope
    research: Dict[str, List[ResearchResult]] = field(default_factory=dict)
    
    # Objectives and research questions from Chapter 1
    objectives: Dict[str, Any] = field(default_factory=dict)
    research_questions: List[str] = field(default_factory=list)  # For Chapter 2
    is_proposal: bool = False
    themes: List[Dict[str, Any]] = field(default_factory=list)  # Chapter 2 themes
    objective_variables: Dict[str, List[str]] = field(default_factory=dict)  # Golden Thread
    uploaded_sources_context: str = ""  # Context from uploaded PDFs
    
    # Sections content
    sections: Dict[str, SectionContent] = field(default_factory=dict)
    
    # Chapter 2 citation tracking
    chapter2_used_citations: set = field(default_factory=set)  # Track used DOIs/titles
    chapter2_citation_pool: List[ResearchResult] = field(default_factory=list)  # 100+ papers
    
    def mark_citation_used(self, citation: ResearchResult):
        """Mark a citation as used to prevent reuse."""
        identifier = citation.doi if citation.doi else citation.title
        self.chapter2_used_citations.add(identifier)
    
    def get_fresh_citations(self, count: int) -> List[ResearchResult]:
        """Get unused citations from the pool."""
        fresh = []
        for citation in self.chapter2_citation_pool:
            identifier = citation.doi if citation.doi else citation.title
            if identifier not in self.chapter2_used_citations:
                fresh.append(citation)
                self.mark_citation_used(citation)
                if len(fresh) >= count:
                    break
        return fresh
    
    def get_remaining_count(self) -> int:
        """Get count of unused citations."""
        return len(self.chapter2_citation_pool) - len(self.chapter2_used_citations)
    
    # Status tracking
    agents_status: Dict[str, AgentStatus] = field(default_factory=dict)
    
    # Final output
    final_content: str = ""
    total_citations: int = 0
    
    # Database instance (for persistence across chapters)
    db: Any = None
