"""
API Gateway - Main entry point for thesis system.

Routes requests to appropriate microservices:
- /objectives/* → Objective Service (8001)
- /content/* → Content Service (8002)
- /search/* → Search Service (8003)

Handles user input and orchestration.
"""
import sys
sys.path.insert(0, '../shared')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from datetime import datetime
import os

# Import shared models
from shared.models import (
    ObjectiveRequest,
    Content Request,
    Search Request,
    ServiceStatus
)

app = FastAPI(
    title="Thesis API Gateway",
    description="Main entry point for thesis generation system",
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

# Service URLs
OBJECTIVE_SERVICE = os.getenv("OBJECTIVE_SERVICE_URL", "http://localhost:8001")
CONTENT_SERVICE = os.getenv("CONTENT_SERVICE_URL", "http://localhost:8002")
SEARCH_SERVICE = os.getenv("SEARCH_SERVICE_URL", "http://localhost:8003")


@app.get("/")
async def root():
    """Gateway info."""
    return {
        "service": "thesis-api-gateway",
        "version": "1.0.0",
        "description": "Microservices-based thesis generation system",
        "services": {
            "objective": OBJECTIVE_SERVICE,
            "content": CONTENT_SERVICE,
            "search": SEARCH_SERVICE
        }
    }


@app.get("/health")
async def health():
    """Health check for all services."""
    try:
        async with httpx.AsyncClient() as client:
            objective_health = await client.get(f"{OBJECTIVE_SERVICE}/health", timeout=5.0)
            content_health = await client.get(f"{CONTENT_SERVICE}/health", timeout=5.0)
            search_health = await client.get(f"{SEARCH_SERVICE}/health", timeout=5.0)
        
        return {
            "gateway": "healthy",
            "services": {
                "objective": objective_health.json(),
                "content": content_health.json(),
                "search": search_health.json()
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "gateway": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# === OBJECTIVE ROUTES ===

@app.post("/objectives/generate")
async def generate_objectives(request: ObjectiveRequest):
    """Generate objectives (routes to objective service)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OBJECTIVE_SERVICE}/objectives/generate",
            json=request.dict(),
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()


@app.post("/objectives/competitive")
async def generate_objectives_competitive(request: ObjectiveRequest):
    """Generate objectives competitively (routes to objective service)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OBJECTIVE_SERVICE}/objectives/competitive",
            json=request.dict(),
            timeout=180.0
        )
        response.raise_for_status()
        return response.json()


# === CONTENT ROUTES ===

@app.post("/content/chapter")
async def generate_chapter(request: ContentRequest):
    """Generate chapter (routes to content service)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTENT_SERVICE}/content/chapter",
            json=request.dict(),
            timeout=300.0
        )
        response.raise_for_status()
        return response.content  # Returns DOCX file


@app.post("/content/section")
async def generate_section(request: ContentRequest):
    """Generate section (routes to content service)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONTENT_SERVICE}/content/section",
            json=request.dict(),
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()


# === SEARCH ROUTES ===

@app.post("/search/papers")
async def search_papers(request: SearchRequest):
    """Search papers (routes to search service)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SEARCH_SERVICE}/search/papers",
            json=request.dict(),
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
