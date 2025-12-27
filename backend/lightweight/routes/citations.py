"""
Citations API Endpoints
Provides citation management and formatting for thesis chapters
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/citations", tags=["citations"])


class AuthorModel(BaseModel):
    """Author information."""
    first_name: str
    last_name: str
    middle_initials: Optional[str] = None


class CitationRequest(BaseModel):
    """Request to create a citation."""
    citation_id: str
    authors: List[AuthorModel]
    year: int
    title: str
    source_type: str  # "journal", "book", "website", etc.
    publication_name: Optional[str] = None
    volume: Optional[int] = None
    issue: Optional[int] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    publication_city: Optional[str] = None


class InTextCitationRequest(BaseModel):
    """Request for in-text citation."""
    citation_id: str
    page: Optional[int] = None
    narrative: bool = False  # If True, returns narrative format


class BibliographyRequest(BaseModel):
    """Request to generate bibliography."""
    citation_ids: List[str]
    chapter_num: Optional[int] = None


@router.post("/add-citation")
async def add_citation(request: CitationRequest, workspace_id: str = "default"):
    """Add a new citation to the workspace."""
    try:
        from backend.lightweight.services.citation_manager import Citation, Author
        
        # Convert to internal format
        authors = [
            Author(
                first_name=a.first_name,
                last_name=a.last_name,
                middle_initials=a.middle_initials
            )
            for a in request.authors
        ]
        
        citation = Citation(
            citation_id=request.citation_id,
            authors=authors,
            year=request.year,
            title=request.title,
            source_type=request.source_type,
            publication_name=request.publication_name,
            volume=request.volume,
            issue=request.issue,
            pages=request.pages,
            doi=request.doi,
            url=request.url,
            publisher=request.publisher,
            publication_city=request.publication_city
        )
        
        from backend.lightweight.services.citation_manager import CitationManager
        manager = CitationManager(workspace_id)
        manager.add_citation(citation)
        
        logger.info(f"✅ Citation added: {request.citation_id}")
        
        return {
            "success": True,
            "citation_id": request.citation_id,
            "message": f"Citation '{request.citation_id}' added successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error adding citation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/in-text")
async def get_in_text_citation(
    citation_id: str,
    workspace_id: str = "default",
    page: Optional[int] = None,
    narrative: bool = False
):
    """Get in-text citation in APA 7 format."""
    try:
        from backend.lightweight.services.citation_manager import CitationManager
        manager = CitationManager(workspace_id)
        
        if narrative:
            citation_text = manager.get_narrative(citation_id, page)
        else:
            citation_text = manager.get_in_text(citation_id, page)
        
        if not citation_text:
            raise HTTPException(
                status_code=404,
                detail=f"Citation '{citation_id}' not found"
            )
        
        return {
            "success": True,
            "citation_id": citation_id,
            "citation": citation_text,
            "format": "narrative" if narrative else "parenthetical"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting in-text citation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reference")
async def get_reference(citation_id: str, workspace_id: str = "default"):
    """Get full reference in APA 7 format."""
    try:
        from backend.lightweight.services.citation_manager import CitationManager
        manager = CitationManager(workspace_id)
        
        reference = manager.get_reference(citation_id)
        
        if not reference:
            raise HTTPException(
                status_code=404,
                detail=f"Citation '{citation_id}' not found"
            )
        
        return {
            "success": True,
            "citation_id": citation_id,
            "reference": reference
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting reference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bibliography")
async def generate_bibliography(
    request: BibliographyRequest,
    workspace_id: str = "default"
):
    """Generate complete bibliography for citations."""
    try:
        from backend.lightweight.services.citation_manager import CitationManager
        manager = CitationManager(workspace_id)
        
        bibliography = manager.generate_bibliography(request.citation_ids)
        
        return {
            "success": True,
            "chapter": request.chapter_num,
            "citation_count": len(request.citation_ids),
            "bibliography": bibliography
        }
    
    except Exception as e:
        logger.error(f"❌ Error generating bibliography: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chapter-1")
async def get_chapter_1_citations(workspace_id: str = "default"):
    """Get all citations for Chapter 1."""
    try:
        from backend.lightweight.services.chapter_1_citations import (
            setup_chapter_1_citations,
            CHAPTER_1_REFERENCES
        )
        
        manager = setup_chapter_1_citations(workspace_id)
        
        return {
            "success": True,
            "chapter": 1,
            "citations": {
                "Grabowski2018": manager.get_reference("Grabowski2018"),
                "Koopmans2018": manager.get_reference("Koopmans2018"),
                "Mikac2022": manager.get_reference("Mikac2022"),
                "CoxDincecco2020": manager.get_reference("CoxDincecco2020"),
                "Baauw2019": manager.get_reference("Baauw2019"),
                "MangarioSjogren2017": manager.get_reference("MangarioSjogren2017"),
                "Iliyasov2021": manager.get_reference("Iliyasov2021"),
                "Icen2022": manager.get_reference("Icen2022")
            },
            "references_section": CHAPTER_1_REFERENCES
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting Chapter 1 citations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-all")
async def list_all_citations(workspace_id: str = "default"):
    """List all citations in workspace."""
    try:
        from backend.lightweight.services.citation_manager import CitationManager
        manager = CitationManager(workspace_id)
        
        citations_list = []
        for cid, citation in manager.citations.items():
            citations_list.append({
                "citation_id": cid,
                "authors": [a.full_name() for a in citation.authors],
                "year": citation.year,
                "title": citation.title,
                "type": citation.source_type
            })
        
        return {
            "success": True,
            "total": len(citations_list),
            "citations": citations_list
        }
    
    except Exception as e:
        logger.error(f"❌ Error listing citations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
