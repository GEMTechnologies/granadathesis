"""
Content Service - Handles chapter and content generation.

This service uses DeepSeek Direct ONLY for:
- Chapter generation
- Citation-heavy content
- DOCX formatting
- All content writing

NO OpenRouter is used in this service.
"""
import sys
sys.path.insert(0, '../../shared')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from datetime import datetime
import tempfile
import os

# Import shared models
from shared.models import (
    ContentRequest,
    ContentResponse,
    ServiceStatus
)

# Import content generation logic
from services.chapter_generator import chapter_generator

app = FastAPI(
    title="Content Service",
    description="PhD thesis content generation with DeepSeek",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "content-service",
        "version": "1.0.0",
        "description": "Content generation with DeepSeek (direct API)",
        "provider": "DeepSeek Direct",
        "endpoints": [
            "/content/chapter (POST)",
            "/content/section (POST)",
            "/health (GET)"
        ]
    }


@app.get("/health")
async def health():
    """Health check."""
    return ServiceStatus(
        service="content-service",
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/content/chapter")
async def generate_chapter(request: ContentRequest):
    """
    Generate full chapter with citations.
    
    Uses DeepSeek Direct API (no OpenRouter).
    Returns DOCX file.
    """
    try:
        result = await chapter_generator.generate_chapter_one(
            topic=request.topic,
            case_study=request.case_study,
            objectives=request.objectives,
            research_questions=request.research_questions
        )
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        chapter_generator.save_document(result['document'], temp_file.name)
        
        return FileResponse(
            path=temp_file.name,
            filename=f"chapter_one_{request.thesis_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/content/section", response_model=ContentResponse)
async def generate_section(request: ContentRequest):
    """
    Generate single section with citations.
    
    Uses DeepSeek Direct API for fast, cheap content generation.
    """
    try:
        from services.cited_content_generator import cited_content_generator
        
        result = await cited_content_generator.generate_cited_section(
            section_title=request.section_title,
            topic=f"{request.topic} in {request.case_study}",
            word_count=request.word_count,
            target_density=0.75
        )
        
        return ContentResponse(
            content=result['content'],
            references=result.get('references', []),
            metrics=result.get('metrics', {}),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
