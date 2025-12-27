"""
Search Service - Handles academic paper search and research context.

This service provides:
- Academic paper search (Semantic Scholar, PubMed)
- Research context gathering
- Zotero integration
- Caching for search results

NO LLM calls - pure academic API integration.
"""
import sys
sys.path.insert(0, '../../shared')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

# Import shared models
from shared.models import (
    SearchRequest,
    SearchResponse,
    ServiceStatus
)

# Import search services
from services.academic_search import academic_search_service

app = FastAPI(
    title="Search Service",
    description="Academic paper search and research context",
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
        "service": "search-service",
        "version": "1.0.0",
        "description": "Academic paper search and research APIs",
        "providers": ["Semantic Scholar", "PubMed", "Exa", "Zotero"],
        "endpoints": [
            "/search/papers (POST)",
            "/search/context (POST)",
            "/health (GET)"
        ]
    }


@app.get("/health")
async def health():
    """Health check."""
    return ServiceStatus(
        service="search-service",
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/search/papers", response_model=SearchResponse)
async def search_papers(request: SearchRequest):
    """
    Search academic papers.
    
    Uses Semantic Scholar API with retry logic.
    """
    try:
        papers = await academic_search_service.search_academic_papers(
            query=request.query,
            max_results=request.max_results
        )
        
        return SearchResponse(
            papers=papers,
            total=len(papers),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/context")
async def search_context(request: dict):
    """
    Get research context for topic and case study.
    
    Combines academic papers and web search results.
    """
    try:
        context = await academic_search_service.get_research_context(
            topic=request.get("topic"),
            case_study=request.get("case_study")
        )
        
        return {
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
