from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ThesisStatus(str, Enum):
    PLANNING = "planning"
    RESEARCHING = "researching"
    WRITING = "writing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"

class SectionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"

class ThesisBase(BaseModel):
    topic: str
    student_name: Optional[str] = None
    university: str = "University of Juba"

class ThesisCreate(ThesisBase):
    pass

class Thesis(ThesisBase):
    id: str
    status: ThesisStatus = ThesisStatus.PLANNING
    created_at: datetime
    updated_at: datetime
    objectives: List[str] = []
    objectives_validated: bool = False
    coherence_score: Optional[float] = None
    
class Chapter(BaseModel):
    id: str
    thesis_id: str
    title: str
    order: int
    content: Optional[str] = None
    status: SectionStatus = SectionStatus.PENDING

class Section(BaseModel):
    id: str
    chapter_id: str
    title: str
    order: int
    content: Optional[str] = None
    status: SectionStatus = SectionStatus.PENDING
    research_notes: Optional[str] = None

# ============================================================================
# Objective Agent Models
# ============================================================================

class ObjectiveValidation(BaseModel):
    """Validation result for thesis objectives"""
    is_valid: bool
    overall_score: int  # 0-100
    issues: List[Dict[str, str]] = []
    strengths: List[str] = []
    recommendations: List[str] = []
    validated_at: datetime = datetime.now()

class CoherenceCheck(BaseModel):
    """Coherence check result for a thesis section"""
    section_id: str
    section_title: str
    aligned_objectives: List[int] = []
    alignment_score: int  # 0-100
    deviations: List[Dict[str, str]] = []
    coherence_issues: List[str] = []
    recommendations: List[str] = []
    checked_at: datetime = datetime.now()

class AgentWarning(BaseModel):
    """Warning emitted by objective agent to other agents"""
    warning_id: str
    source: str = "objective_agent"
    target_agent: Optional[str] = None
    severity: str  # "minor", "moderate", "critical"
    message: str
    details: Optional[Dict] = None
    suggested_action: str
    created_at: datetime = datetime.now()
    resolved: bool = False

class ReplanEvent(BaseModel):
    """Event triggered when replanning is needed"""
    event_id: str
    thesis_id: str
    triggered_by: str = "objective_agent"
    reason: str
    issues: List[str] = []
    timestamp: datetime = datetime.now()
    status: str = "pending"  # pending, in_progress, completed

# ============================================================================
# Competitive Multi-Model Models
# ============================================================================

class ModelSubmission(BaseModel):
    """Objective submission from a single model in competition"""
    model_key: str
    model_name: str
    objectives: List[str]
    success: bool
    error: Optional[str] = None

class CompetitionRanking(BaseModel):
    """Ranking entry for a model in competition"""
    model: str
    rank: int
    score: int  # 0-100
    strengths: List[str] = []
    weaknesses: List[str] = []
    quality_score: Optional[int] = None
    resilience_score: Optional[int] = None
    critique_score: Optional[int] = None
    excellence_score: Optional[int] = None

class CompetitionResult(BaseModel):
    """Full competition result with all submissions and rankings"""
    competition_id: str
    topic: str
    case_study: str
    methodology: Optional[str] = None
    timestamp: datetime
    participants: List[str]
    submissions: Dict[str, List[str]]
    critiques: Dict[str, Dict[str, str]]
    winner: Dict[str, Any]
    rankings: List[CompetitionRanking] = []
    detailed_reasoning: Optional[str] = None
    lessons_learned: List[str] = []
    mode: str = "competitive"
