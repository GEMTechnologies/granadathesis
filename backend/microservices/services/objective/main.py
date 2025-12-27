"""
Objective Service - Handles objective generation with competitive models.

This service uses OpenRouter ONLY for:
- MAKER voting-based objective generation
- Competitive multi-model generation (Claude, GPT-4, DeepSeek)
- Academic rigor validation
"""
import sys
sys.path.insert(0, '../../shared')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

# Import shared models
from shared.models import (
    ObjectiveRequest,
    ObjectiveResponse,
    ServiceStatus
)

# Import objective generation logic
from agents.objective import objective_agent

app = FastAPI(
    title="Objective Service",
    description="PhD thesis objective generation with competitive models",
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
        "service": "objective-service",
        "version": "1.0.0",
        "description": "Objective generation with OpenRouter",
        "models": ["claude", "gpt4", "deepseek"],
        "endpoints": [
            "/objectives/generate (POST)",
            "/objectives/competitive (POST)",
            "/health (GET)"
        ]
    }


@app.get("/health")
async def health():
    """Health check."""
    return ServiceStatus(
        service="objective-service",
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/objectives/generate", response_model=ObjectiveResponse)
async def generate_objectives(request: ObjectiveRequest):
    """
    Generate objectives using MAKER voting.
    
    Uses voting with DeepSeek via OpenRouter for fast, reliable generation.
    """
    try:
        result = await objective_agent.generate_objectives_with_voting(
            topic=request.topic,
            case_study=request.case_study,
            methodology=request.methodology,
            k=request.k,
            thesis_id=request.thesis_id
        )
        
        return ObjectiveResponse(
            objectives=result["objectives"],
            validation=result["validation"],
            mode=result["mode"],
            timestamp=result["timestamp"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/objectives/competitive", response_model=ObjectiveResponse)
async def generate_objectives_competitive(request: ObjectiveRequest):
    """
    Generate objectives using competitive multi-model approach.
    
    All models (Claude, GPT-4, DeepSeek) compete via OpenRouter.
    """
    try:
        # Extract models from request or use defaults
        models = request.dict().get("models", ["claude", "gpt4", "deepseek"])
        
        result = await objective_agent.generate_objectives_competitive(
            topic=request.topic,
            case_study=request.case_study,
            methodology=request.methodology,
            models=models
        )
        
        winner = result["winner"]
        return ObjectiveResponse(
            objectives=winner.get("objectives", []),
            validation={"score": winner.get("score", 0)},
            mode=result["mode"],
            timestamp=result["timestamp"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
