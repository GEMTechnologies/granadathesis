"""
Shared data models for all services.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ThesisBase(BaseModel):
    """Base thesis model."""
    topic: str
    case_study: str
    methodology: Optional[str] = None


class ObjectiveRequest(BaseModel):
    """Request to generate objectives."""
    thesis_id: str
    topic: str
    case_study: str
    methodology: Optional[str] = None
    k: int = Field(default=3, description="Voting threshold")
    mode: str = Field(default="voting", description="voting or competitive")


class ObjectiveResponse(BaseModel):
    """Response with generated objectives."""
    objectives: List[str]
    validation: Dict[str, Any]
    mode: str
    timestamp: str


class ContentRequest(BaseModel):
    """Request to generate content."""
    thesis_id: str
    topic: str
    case_study: str
    section_title: str
    word_count: int = 500
    objectives: Optional[List[Dict[str, Any]]] = None
    research_questions: Optional[List[str]] = None


class ContentResponse(BaseModel):
    """Response with generated content."""
    content: str
    references: List[str]
    metrics: Dict[str, Any]
    timestamp: str


class SearchRequest(BaseModel):
    """Request to search papers."""
    query: str
    max_results: int = 20


class SearchResponse(BaseModel):
    """Response with search results."""
    papers: List[Dict[str, Any]]
    total: int
    timestamp: str


class ServiceStatus(BaseModel):
    """Service health status."""
    service: str
    status: str  # "healthy" | "degraded" | "down"
    version: str
    timestamp: str
