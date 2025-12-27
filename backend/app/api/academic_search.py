#!/usr/bin/env python3
"""
Academic Search API Endpoints

FastAPI endpoints for:
- Paper search (all APIs)
- PDF management
- Export to multiple formats
- Zotero sync
- Citation networks
- Full-text search
- Thesis integration
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

# Import services
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scholarly_search import ScholarlySearch
try:
    from scholarly_search_v2 import SearchFilters
except ImportError:
    SearchFilters = None

from app.services.cache_service import get_cache
from app.services.pdf_service import get_pdf_service
from app.utils.exporters import export_papers
from app.services.zotero_service import ZoteroService
from app.services.pubmed_api import PubMedAPI, pubmed_to_paper_dict
from app.services.citation_network import CitationNetwork, build_network_from_papers
from app.services.thesis_integration import ThesisResearchAssistant
from app.core.config import settings

# Create router
router = APIRouter(prefix="/api/search", tags=["Academic Search"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query")
    limit_per_source: int = Field(5, ge=1, le=20, description="Results per API")
    year_min: Optional[int] = Field(None, description="Minimum year")
    year_max: Optional[int] = Field(None, description="Maximum year")
    citations_min: Optional[int] = Field(None, description="Minimum citations")
    oa_only: bool = Field(False, description="Open access only")
    use_cache: bool = Field(True, description="Use cache")


class PaperResponse(BaseModel):
    """Paper response model."""
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    url: str
    source: str
    citations: int
    venue: str
    doi: str


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    total_results: int
    papers: List[Dict[str, Any]]
    cached: bool
    search_time_ms: int


class ExportRequest(BaseModel):
    """Export request model."""
    papers: List[Dict[str, Any]]
    formats: List[str] = Field(["json", "bibtex", "ris"], description="Export formats")
    output_name: str = Field("search_results", description="Output filename base")


class ZoteroSyncRequest(BaseModel):
    """Zotero sync request model."""
    papers: List[Dict[str, Any]]
    collection_name: Optional[str] = Field(None, description="Collection name")


class ThesisObjectiveRequest(BaseModel):
    """Thesis objective request model."""
    objective: str = Field(..., description="Thesis objective text")
    limit: int = Field(10, ge=1, le=50)
    year_min: int = Field(2018, description="Minimum publication year")


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_papers(request: SearchRequest):
    """
    Search for academic papers across all APIs.
    
    Returns papers from:
    - Semantic Scholar
    - CORE
    - CrossRef
    - Unpaywall
    - OpenAlex
    - Tavily
    - arXiv
    - PubMed
    """
    start_time = datetime.now()
    
    try:
        # Initialize searcher
        searcher = ScholarlySearch(enable_cache=request.use_cache)
        
        # Build filters
        filters = None
        if SearchFilters and any([request.year_min, request.year_max, request.citations_min, request.oa_only]):
            filters = SearchFilters(
                year_min=request.year_min,
                year_max=request.year_max,
                citations_min=request.citations_min,
                oa_only=request.oa_only
            )
        
        # Search
        papers = await searcher.run_search(
            request.query,
            limit_per_source=request.limit_per_source,
            filters=filters
        )
        
        # Calculate search time
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=request.query,
            total_results=len(papers),
            papers=[p.to_dict() if hasattr(p, 'to_dict') else p for p in papers],
            cached=request.use_cache and searcher.cache is not None,
            search_time_ms=int(search_time)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/pubmed")
async def search_pubmed(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    free_full_text: bool = Query(False, description="Only free full-text")
):
    """Search PubMed/PMC for biomedical papers."""
    try:
        pubmed = PubMedAPI()
        papers = await pubmed.search_and_fetch(query, limit, free_full_text)
        
        return {
            "query": query,
            "total_results": len(papers),
            "papers": [pubmed_to_paper_dict(p) for p in papers]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        cache = get_cache()
        stats = cache.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache entries."""
    try:
        cache = get_cache()
        deleted = cache.clear_all()
        return {"message": f"Cleared {deleted} cache entries"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.post("/export")
async def export_search_results(request: ExportRequest, background_tasks: BackgroundTasks):
    """
    Export papers to multiple formats.
    
    Supported formats:
    - json
    - bibtex
    - ris
    - csv
    - excel
    - word
    - markdown
    - endnote
    """
    try:
        output_dir = Path("thesis_data/exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export in background
        background_tasks.add_task(
            export_papers,
            request.papers,
            output_dir,
            request.output_name
        )
        
        return {
            "message": "Export started",
            "formats": request.formats,
            "output_dir": str(output_dir)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ZOTERO ENDPOINTS
# ============================================================================

@router.post("/zotero/sync")
async def sync_to_zotero(request: ZoteroSyncRequest):
    """Sync papers to Zotero library."""
    try:
        if not settings.ZOTERO_API_KEY or not settings.ZOTERO_USER_ID:
            raise HTTPException(
                status_code=400,
                detail="Zotero API key and User ID not configured"
            )
        
        zotero = ZoteroService(
            api_key=settings.ZOTERO_API_KEY,
            user_id=settings.ZOTERO_USER_ID
        )
        
        results = await zotero.bulk_add_papers(
            request.papers,
            collection_name=request.collection_name
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PDF ENDPOINTS
# ============================================================================

@router.post("/pdf/download")
async def download_pdf(paper: Dict[str, Any], background_tasks: BackgroundTasks):
    """Download and process PDF for a paper."""
    try:
        pdf_service = get_pdf_service()
        
        # Download in background
        background_tasks.add_task(
            pdf_service.download_and_process,
            paper,
            extract_images=True,
            use_ocr=False
        )
        
        return {"message": "PDF download started", "paper": paper.get("title")}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CITATION NETWORK ENDPOINTS
# ============================================================================

@router.post("/citations/network")
async def build_citation_network(papers: List[Dict[str, Any]]):
    """Build citation network from papers."""
    try:
        network = build_network_from_papers(papers)
        stats = network.get_statistics()
        
        # Get most cited
        most_cited = network.get_most_cited(10)
        
        # Get influential papers
        influential = network.get_influential_papers(10)
        
        return {
            "statistics": stats,
            "most_cited": [
                {
                    "paper_id": pid,
                    "citations": count,
                    "metadata": network.paper_metadata.get(pid, {})
                }
                for pid, count in most_cited
            ],
            "influential": [
                {
                    "paper_id": pid,
                    "pagerank_score": score,
                    "metadata": network.paper_metadata.get(pid, {})
                }
                for pid, score in influential
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# THESIS INTEGRATION ENDPOINTS
# ============================================================================

@router.post("/thesis/find-papers")
async def find_papers_for_objective(request: ThesisObjectiveRequest):
    """Find relevant papers for a thesis objective."""
    try:
        assistant = ThesisResearchAssistant()
        result = await assistant.find_papers_for_objective(
            request.objective,
            limit=request.limit,
            year_min=request.year_min
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thesis/literature-review")
async def generate_literature_review(
    topic: str = Query(..., description="Research topic"),
    num_papers: int = Query(20, ge=5, le=100)
):
    """Generate literature review outline with papers."""
    try:
        assistant = ThesisResearchAssistant()
        outline = await assistant.generate_literature_review_outline(topic, num_papers)
        return outline
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thesis/research-gaps")
async def identify_research_gaps(topic: str = Query(..., description="Research topic")):
    """Analyze papers to identify research gaps."""
    try:
        assistant = ThesisResearchAssistant()
        gaps = await assistant.suggest_research_gap(topic)
        return gaps
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "apis_available": 8,
        "features": [
            "search",
            "cache",
            "export",
            "zotero",
            "pdf",
            "citations",
            "thesis_integration"
        ]
    }
