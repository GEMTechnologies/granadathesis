"""
Complete Thesis Generation Endpoint.

Generates MS Word document with:
- Cover page
- Preliminary pages (approval, declaration, dedication, acknowledgement, abstract)
- Table of contents
- List of tables
- List of figures  
- Acronyms/Abbreviations
- Main chapters (1-6)
- Appendices
- Proper page numbering (cover: none, prelim: Roman, main: Arabic)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import logging
from ..services.thesis_formatter import ThesisFormatter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


class PreliminaryPages(BaseModel):
    """Preliminary pages content."""
    supervisor_approval: str = ""
    student_declaration: str = ""
    dedication: str = ""
    acknowledgement: str = ""
    abstract: str = ""


class ThesisGenerationRequest(BaseModel):
    """Request for complete thesis generation."""
    workspace_id: str
    title: str
    author_name: str
    index_no: str
    school: str
    department: str
    degree: str = "PhD"
    chapters: Dict[int, str]  # {1: "content", 2: "content", ...}
    preliminaries: Optional[PreliminaryPages] = None
    appendices: Optional[Dict[str, str]] = None


class ThesisGenerationResponse(BaseModel):
    """Response from thesis generation."""
    success: bool
    file_path: str
    file_name: str
    message: str


@router.post("/generate-complete", response_model=ThesisGenerationResponse)
async def generate_complete_thesis(request: ThesisGenerationRequest) -> ThesisGenerationResponse:
    """
    Generate complete thesis in MS Word format.
    
    Includes:
    - Cover page (no numbering)
    - Approval page (Roman numerals)
    - Declaration page
    - Dedication page
    - Acknowledgement page
    - Abstract page
    - Table of contents
    - List of tables
    - List of figures
    - Acronyms/Abbreviations
    - Main chapters (1-6)
    - Appendices (if provided)
    
    All with proper page numbering and formatting.
    """
    try:
        # Prepare preliminary pages
        prelim = request.preliminaries or PreliminaryPages()
        
        # Create formatter
        formatter = ThesisFormatter(workspace_id=request.workspace_id)
        
        # Generate thesis
        file_path = formatter.create_complete_thesis(
            title=request.title,
            author_name=request.author_name,
            index_no=request.index_no,
            school=request.school,
            department=request.department,
            degree=request.degree,
            chapters=request.chapters,
            supervisor_approval=prelim.supervisor_approval,
            student_declaration=prelim.student_declaration,
            dedication=prelim.dedication,
            acknowledgement=prelim.acknowledgement,
            abstract=prelim.abstract,
            appendices=request.appendices or {}
        )
        
        file_name = file_path.split('/')[-1]
        
        logger.info(f"✅ Complete thesis generated: {file_path}")
        
        return ThesisGenerationResponse(
            success=True,
            file_path=file_path,
            file_name=file_name,
            message=f"Complete thesis generated successfully with all preliminary pages, chapters, and appendices"
        )
    
    except Exception as e:
        logger.error(f"❌ Error generating complete thesis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate complete thesis: {str(e)}"
        )


@router.post("/add-preliminary-pages")
async def add_preliminary_pages(
    workspace_id: str,
    supervisor_approval: str = "",
    student_declaration: str = "",
    dedication: str = "",
    acknowledgement: str = "",
    abstract: str = ""
):
    """Add or update preliminary pages content."""
    try:
        from pathlib import Path
        import json
        
        workspace_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Store preliminary pages
        prelim_data = {
            "supervisor_approval": supervisor_approval,
            "student_declaration": student_declaration,
            "dedication": dedication,
            "acknowledgement": acknowledgement,
            "abstract": abstract
        }
        
        prelim_file = workspace_path / ".preliminary_pages.json"
        with open(prelim_file, 'w') as f:
            json.dump(prelim_data, f, indent=2)
        
        return {
            "success": True,
            "message": "Preliminary pages saved successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error saving preliminary pages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save preliminary pages: {str(e)}"
        )


@router.get("/preview-template")
async def get_thesis_template():
    """Get thesis template with all sections."""
    return {
        "cover_page": {
            "university": "UNIVERSITY OF JUBA",
            "school": "[SCHOOL NAME]",
            "department": "[DEPARTMENT NAME]",
            "topic": "[YOUR RESEARCH TOPIC]",
            "student_name": "[FULL NAME]",
            "index_no": "[INDEX NUMBER]",
            "degree": "PhD",
            "submission_text": "A RESEARCH PROPOSAL SUBMITTED TO THE SCHOOL OF [SCHOOL] IN PARTIAL FULFILMENT OF THE REQUIREMENT FOR THE AWARD OF A PhD"
        },
        "preliminary_pages": {
            "approval": "Write supervisor approval statement for your study",
            "declaration": "Write student declaration statement for your study",
            "dedication": "Write dedication for your study",
            "acknowledgement": "Write acknowledgement for your study",
            "abstract": "Write abstract for your study"
        },
        "main_sections": [
            "Table of Contents",
            "List of Tables",
            "List of Figures",
            "Acronyms/Abbreviations",
            "Chapter 1: Introduction",
            "Chapter 2: Literature Review",
            "Chapter 3: Methodology",
            "Chapter 4: Results",
            "Chapter 5: Discussion",
            "Chapter 6: Conclusion",
            "Appendices"
        ],
        "page_numbering": {
            "cover_page": "No numbering",
            "preliminary_pages": "Roman numerals (i, ii, iii, ...)",
            "main_content": "Arabic numerals (1, 2, 3, ...)"
        }
    }
