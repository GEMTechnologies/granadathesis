"""
Multi-University Thesis Generation API
Handles thesis generation for multiple universities
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


# ============================================================================
# DATA MODELS
# ============================================================================

class UniversityInfo(BaseModel):
    """University information"""
    type: str
    name: str
    abbreviation: str
    description: str


class UniversitiesResponse(BaseModel):
    """Response with list of universities"""
    universities: List[UniversityInfo]


class ThesisGenerationRequest(BaseModel):
    """Request to generate a thesis"""
    university_type: str
    title: str
    topic: str
    objectives: List[str]
    workspace_id: Optional[str] = None


class ThesisGenerationResponse(BaseModel):
    """Response from thesis generation"""
    success: bool
    message: str
    file_path: Optional[str] = None
    university_type: str
    title: str


# ============================================================================
# UNIVERSITIES DATA
# ============================================================================

UNIVERSITIES = {
    "uoj_phd": {
        "type": "uoj_phd",
        "name": "University of Juba PhD",
        "abbreviation": "UoJ",
        "description": "PhD thesis template for University of Juba with institutional formatting and requirements"
    },
    "generic": {
        "type": "generic",
        "name": "Generic University",
        "abbreviation": "GEN",
        "description": "Generic thesis template compatible with most universities"
    }
}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/universities", response_model=UniversitiesResponse)
async def list_universities():
    """
    List all available universities for thesis generation
    
    Returns:
        UniversitiesResponse: List of universities with metadata
    """
    try:
        universities = [
            UniversityInfo(**info)
            for info in UNIVERSITIES.values()
        ]
        return UniversitiesResponse(universities=universities)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading universities: {str(e)}"
        )


@router.get("/universities/{university_type}", response_model=UniversityInfo)
async def get_university_info(university_type: str):
    """
    Get information about a specific university
    
    Args:
        university_type: The university type (e.g., 'uoj_phd', 'generic')
        
    Returns:
        UniversityInfo: University information
    """
    if university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"University type '{university_type}' not found"
        )
    
    return UniversityInfo(**UNIVERSITIES[university_type])


@router.get("/template/{university_type}")
async def get_thesis_template(university_type: str):
    """
    Get thesis template structure for a university
    
    Args:
        university_type: The university type
        
    Returns:
        dict: Template structure with sections and formatting
    """
    if university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"University type '{university_type}' not found"
        )
    
    templates = {
        "uoj_phd": {
            "cover_page": {
                "institution": "UNIVERSITY OF JUBA",
                "fields": ["title", "author", "supervisor", "date"]
            },
            "preliminary_sections": [
                "approval_page",
                "declaration",
                "dedication",
                "acknowledgements",
                "abstract",
                "table_of_contents"
            ],
            "chapters": 6,
            "appendices": True,
            "page_numbering": "roman_then_arabic"
        },
        "generic": {
            "cover_page": {
                "institution": "University",
                "fields": ["title", "author", "supervisor", "date"]
            },
            "preliminary_sections": [
                "approval_page",
                "table_of_contents",
                "abstract"
            ],
            "chapters": 6,
            "appendices": True,
            "page_numbering": "arabic"
        }
    }
    
    return templates.get(university_type, {})


@router.post("/generate", response_model=ThesisGenerationResponse)
async def generate_thesis(request: ThesisGenerationRequest):
    """
    Generate a complete thesis
    
    Args:
        request: Thesis generation request with title, topic, objectives
        
    Returns:
        ThesisGenerationResponse: Generation result with file path
    """
    if request.university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid university type: {request.university_type}"
        )
    
    if not request.title or not request.topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and topic are required"
        )
    
    if not request.objectives or len(request.objectives) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one objective is required"
        )
    
    try:
        # Import the appropriate generator based on university type
        if request.university_type == "uoj_phd":
            from app.services.thesis_generator import generate_uoj_thesis
            file_path = generate_uoj_thesis(
                title=request.title,
                topic=request.topic,
                objectives=request.objectives,
                workspace_id=request.workspace_id
            )
        else:  # generic
            from app.services.thesis_generator import generate_generic_thesis
            file_path = generate_generic_thesis(
                title=request.title,
                topic=request.topic,
                objectives=request.objectives,
                workspace_id=request.workspace_id
            )
        
        return ThesisGenerationResponse(
            success=True,
            message=f"Thesis generated successfully for {UNIVERSITIES[request.university_type]['name']}",
            file_path=str(file_path),
            university_type=request.university_type,
            title=request.title
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating thesis: {str(e)}"
        )


@router.post("/generate-from-topic", response_model=ThesisGenerationResponse)
async def generate_thesis_from_topic(request: ThesisGenerationRequest):
    """
    Generate thesis from topic with auto-generated objectives
    
    Args:
        request: Thesis generation request
        
    Returns:
        ThesisGenerationResponse: Generation result
    """
    if request.university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid university type: {request.university_type}"
        )
    
    if not request.title or not request.topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and topic are required"
        )
    
    try:
        # Auto-generate objectives from topic if not provided
        objectives = request.objectives or [
            f"Examine the current state of {request.topic}",
            f"Identify challenges and opportunities in {request.topic}",
            f"Propose frameworks for addressing {request.topic}"
        ]
        
        # Call the appropriate generator
        if request.university_type == "uoj_phd":
            from app.services.thesis_generator import generate_uoj_thesis
            file_path = generate_uoj_thesis(
                title=request.title,
                topic=request.topic,
                objectives=objectives,
                workspace_id=request.workspace_id
            )
        else:  # generic
            from app.services.thesis_generator import generate_generic_thesis
            file_path = generate_generic_thesis(
                title=request.title,
                topic=request.topic,
                objectives=objectives,
                workspace_id=request.workspace_id
            )
        
        return ThesisGenerationResponse(
            success=True,
            message=f"Thesis generated successfully for {UNIVERSITIES[request.university_type]['name']}",
            file_path=str(file_path),
            university_type=request.university_type,
            title=request.title
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating thesis: {str(e)}"
        )
