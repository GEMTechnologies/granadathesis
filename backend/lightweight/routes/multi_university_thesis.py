"""
Multi-University Thesis Generation API Routes

Endpoints for generating theses for different universities
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

from .services.universities.university_manager import UniversityManager
from .services.universities.uoj_phd import UoJPhDGenerator
from .services.universities.uoj_general import UoJGeneralGenerator

router = APIRouter(prefix="/api/thesis", tags=["thesis"])

# Initialize managers
university_manager = UniversityManager()


class UniversityListResponse(BaseModel):
    """Response model for university list"""
    universities: List[Dict[str, Any]]


class ThesisGenerationRequest(BaseModel):
    """Request model for thesis generation"""
    university_type: str  # "uoj_phd", "generic", etc.
    title: str
    author_name: str
    supervisor: str
    workspace_id: Optional[str] = "default"
    topic: Optional[str] = None
    objectives: Optional[List[str]] = None
    abstract: Optional[str] = None
    chapters: Optional[Dict[int, str]] = None
    appendices: Optional[Dict[str, str]] = None


class TopicBasedThesisRequest(BaseModel):
    """Request model for topic-based thesis generation"""
    university_type: str
    title: str
    author_name: str
    supervisor: str
    topic: str
    workspace_id: Optional[str] = "default"
    objectives: Optional[List[str]] = None
    abstract: Optional[str] = None
    # Enhanced fields for General Flow
    case_study: Optional[str] = None
    country: Optional[str] = None
    sample_size: Optional[int] = None


class ThesisGenerationResponse(BaseModel):
    """Response model for thesis generation"""
    success: bool
    message: str
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UniversityConfigResponse(BaseModel):
    """Response model for university configuration"""
    university_type: str
    config: Dict[str, Any]


@router.get("/universities", response_model=UniversityListResponse)
async def list_universities():
    """
    List all available universities and their configurations
    
    Returns:
        List of available universities with their details
    """
    universities = university_manager.list_universities()
    return UniversityListResponse(universities=universities)


@router.get("/universities/{university_type}", response_model=UniversityConfigResponse)
async def get_university_config(university_type: str):
    """
    Get configuration for a specific university
    
    Args:
        university_type: University identifier (e.g., "uoj_phd")
    
    Returns:
        University configuration details
    """
    config = university_manager.export_config(university_type)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"University '{university_type}' not found")
    
    return UniversityConfigResponse(
        university_type=university_type,
        config=config
    )


@router.post("/generate", response_model=ThesisGenerationResponse)
async def generate_thesis(request: ThesisGenerationRequest):
    """
    Generate a complete thesis for a specific university
    
    Args:
        request: Thesis generation request with all details
    
    Returns:
        Generated thesis file path and metadata
    """
    try:
        # Validate university type
        config = university_manager.get_university(request.university_type)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"University type '{request.university_type}' not found"
            )

        # Validate input
        thesis_input = {
            "title": request.title,
            "author_name": request.author_name,
            "supervisor": request.supervisor,
            "topic": request.topic or "",
            "chapters": request.chapters or {},
            "abstract": request.abstract or "",
            "appendices": request.appendices or {},
        }

        is_valid, validation_message = university_manager.validate_thesis_input(
            request.university_type, thesis_input
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_message)

        # Generate thesis based on university type
        workspace_id = request.workspace_id or "default"
        
        if request.university_type == "uoj_phd":
            generator = UoJPhDGenerator(workspace_id)
            file_path = generator.generate_complete_thesis(thesis_input)
            metadata = generator.get_metadata()
        else:
            # Use generic/base generator
            from .services.universities.base_template import BaseThesisGenerator
            generator = BaseThesisGenerator(request.university_type, workspace_id)
            file_path = generator.generate_complete_thesis(thesis_input)
            metadata = generator.get_metadata()

        if not file_path:
            raise HTTPException(status_code=500, detail="Failed to generate thesis")

        return ThesisGenerationResponse(
            success=True,
            message=f"Thesis generated successfully for {config.name}",
            file_path=file_path,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating thesis: {str(e)}")


@router.post("/generate-from-topic", response_model=ThesisGenerationResponse)
async def generate_thesis_from_topic(request: TopicBasedThesisRequest):
    """
    Generate thesis from just a topic and objectives
    
    Useful for users who want to start with just a topic/objectives
    and let the system create a thesis structure
    
    Args:
        request: Topic-based generation request
    
    Returns:
        Generated thesis file path and metadata
    """
    try:
        # Validate university type
        config = university_manager.get_university(request.university_type)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"University type '{request.university_type}' not found"
            )

        # Validate required fields
        if not request.title or not request.author_name or not request.supervisor or not request.topic:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: title, author_name, supervisor, topic"
            )

        workspace_id = request.workspace_id or "default"

        # Generate thesis based on university type
        if request.university_type == "uoj_phd":
            generator = UoJPhDGenerator(workspace_id)
            
            topic_data = {
                "title": request.title,
                "author_name": request.author_name,
                "supervisor": request.supervisor,
                "topic": request.topic,
                "objectives": request.objectives or [],
                "abstract": request.abstract or "",
            }
            
            file_path = generator.generate_from_topic(topic_data)
            metadata = generator.get_metadata()
            
        elif request.university_type == "uoj_general":
            generator = UoJGeneralGenerator(workspace_id)
            
            topic_data = {
                "title": request.title,
                "author_name": request.author_name,
                "supervisor": request.supervisor,
                "topic": request.topic,
                "objectives": request.objectives or [],
                "abstract": request.abstract or "",
                
                # New fields
                "case_study": request.case_study,
                "country": request.country,
                "sample_size": request.sample_size
            }
            
            file_path = generator.generate_from_topic(topic_data)
            metadata = generator.get_metadata()
            
        else:
            # For other universities, use standard generation
            chapters = {}
            if request.objectives:
                for i, objective in enumerate(request.objectives, 1):
                    if i <= config.main_chapters:
                        chapters[i] = f"Chapter {i}: {objective}"
            else:
                for i in range(1, config.main_chapters + 1):
                    chapters[i] = f"Chapter {i}"

            thesis_input = {
                "title": request.title,
                "author_name": request.author_name,
                "supervisor": request.supervisor,
                "topic": request.topic,
                "chapters": chapters,
                "abstract": request.abstract or "",
            }

            from .services.universities.base_template import BaseThesisGenerator
            generator = BaseThesisGenerator(request.university_type, workspace_id)
            file_path = generator.generate_complete_thesis(thesis_input)
            metadata = generator.get_metadata()

        if not file_path:
            raise HTTPException(status_code=500, detail="Failed to generate thesis")

        return ThesisGenerationResponse(
            success=True,
            message=f"Thesis generated from topic for {config.name}",
            file_path=file_path,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating thesis: {str(e)}")


@router.get("/template/{university_type}")
async def get_thesis_template(university_type: str):
    """
    Get a template thesis structure for a specific university
    
    Args:
        university_type: University identifier
    
    Returns:
        Template structure showing expected format
    """
    config = university_manager.get_university(university_type)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"University '{university_type}' not found")

    template = {
        "university": config.name,
        "type": university_type,
        "chapters": config.main_chapters,
        "required_fields": {
            "title": "Your thesis title",
            "author_name": "Your full name",
            "supervisor": "Your supervisor name",
            "topic": "Your research topic (optional if using objectives)",
        },
        "optional_fields": {
            "objectives": ["Objective 1", "Objective 2", "..."],
            "abstract": "Abstract text (250-500 words)",
            "appendices": {
                "Appendix A": "Content...",
            }
        },
        "preliminary_sections": config.preliminary_sections,
        "chapter_structure": {
            i: f"Chapter {i}" for i in range(1, config.main_chapters + 1)
        }
    }

    return template
