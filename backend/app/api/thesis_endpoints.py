"""
FastAPI Endpoints for Citation-Heavy Thesis Writer

Exposes chapter generation functionality via REST API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio

from app.services.chapter_generator import chapter_generator
from app.services.cited_content_generator import cited_content_generator

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


class ObjectiveModel(BaseModel):
    type: str  # "general" or "specific"
    text: str


class ChapterOneRequest(BaseModel):
    topic: str
    case_study: str
    objectives: Optional[List[ObjectiveModel]] = None
    research_questions: Optional[List[str]] = None
    citation_style: str = "APA"
    word_count: int = 500


class CitedSectionRequest(BaseModel):
    section_title: str
    topic: str
    word_count: int = 500
    target_density: float = 0.75
    citation_style: str = "APA"


@router.post("/generate-chapter-one")
async def generate_chapter_one_endpoint(request: ChapterOneRequest):
    """
    Generate Chapter 1: Introduction with heavy citations.
    
    Returns chapter content, references, and metadata.
    """
    try:
        # Convert objectives to dict
        objectives = [obj.dict() for obj in request.objectives] if request.objectives else []
        
        # Generate chapter
        result = await chapter_generator.generate_chapter_one(
            topic=request.topic,
            case_study=request.case_study,
            objectives=objectives,
            research_questions=request.research_questions or []
        )
        
        # Save DOCX to temp file
        import tempfile
        import os
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        chapter_generator.save_document(result['document'], temp_file.name)
        
        return {
            "success": True,
            "metadata": result['metadata'],
            "content_preview": result['content'][:500] + "...",
            "references": result['references'],
            "docx_path": temp_file.name,
            "message": f"Chapter generated successfully. DOCX saved to {temp_file.name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-cited-section")
async def generate_cited_section_endpoint(request: CitedSectionRequest):
    """
    Generate a heavily-cited section.
    
    Returns content with citations and references.
    """
    try:
        result = await cited_content_generator.generate_cited_section(
            section_title=request.section_title,
            topic=request.topic,
            word_count=request.word_count,
            target_density=request.target_density
        )
        
        return {
            "success": True,
            "section_title": result['section_title'],
            "content": result['content'],
            "references": result['references'],
            "metrics": result['metrics']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Citation-Heavy Thesis Writer",
        "features": [
            "Chapter generation",
            "Cited content generation",
            "MDAP citation agents",
            "APA/Harvard formatting"
        ]
    }
