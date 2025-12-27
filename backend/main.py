from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import routers
try:
    from app.api.academic_search import router as search_router
    SEARCH_ROUTER_AVAILABLE = True
except ImportError:
    SEARCH_ROUTER_AVAILABLE = False

try:
    from app.api.thesis_endpoints import router as thesis_router
    THESIS_ROUTER_AVAILABLE = True
except ImportError:
    THESIS_ROUTER_AVAILABLE = False

app = FastAPI(title="PhD Thesis Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*", "Cache-Control", "Content-Type", "Last-Event-ID"],
    expose_headers=["*"],
)

# Include routers
from app.api.logs import router as logs_router

# Include routers
if SEARCH_ROUTER_AVAILABLE:
    app.include_router(search_router)

if THESIS_ROUTER_AVAILABLE:
    app.include_router(thesis_router)

# Include logs router
app.include_router(logs_router)

# Include files router
from app.api.files import router as files_router
app.include_router(files_router)

# Include workspace router
try:
    from app.api.workspace import router as workspace_router
    app.include_router(workspace_router)
    WORKSPACE_ROUTER_AVAILABLE = True
except ImportError:
    WORKSPACE_ROUTER_AVAILABLE = False

# Include session router
try:
    from app.api.session import router as session_router
    app.include_router(session_router)
    SESSION_ROUTER_AVAILABLE = True
except ImportError:
    SESSION_ROUTER_AVAILABLE = False

# Include chat router
try:
    from app.api.chat import router as chat_router
    app.include_router(chat_router)
    CHAT_ROUTER_AVAILABLE = True
except ImportError:
    CHAT_ROUTER_AVAILABLE = False

# Include stream router
try:
    from app.api.stream import router as stream_router
    app.include_router(stream_router)
    STREAM_ROUTER_AVAILABLE = True
except ImportError:
    STREAM_ROUTER_AVAILABLE = False

# Include code execution router
try:
    from app.api.code_execution import router as code_router
    app.include_router(code_router)
    CODE_ROUTER_AVAILABLE = True
except ImportError:
    CODE_ROUTER_AVAILABLE = False

# Include agent auto-call router
try:
    from app.api.agent_auto_call import router as agent_router
    app.include_router(agent_router)
    AGENT_ROUTER_AVAILABLE = True
except ImportError:
    AGENT_ROUTER_AVAILABLE = False

# Include markdown tools router
try:
    from app.api.markdown_tools import router as markdown_router
    app.include_router(markdown_router)
    MARKDOWN_ROUTER_AVAILABLE = True
except ImportError:
    MARKDOWN_ROUTER_AVAILABLE = False

# Include complete thesis generation router
try:
    from lightweight.routes.thesis_generation import router as thesis_generation_router
    app.include_router(thesis_generation_router)
    THESIS_GENERATION_ROUTER_AVAILABLE = True
except ImportError as e:
    THESIS_GENERATION_ROUTER_AVAILABLE = False
    print(f"⚠️  Complete thesis generation router not available: {e}")

# Include citations router
try:
    from lightweight.routes.citations import router as citations_router
    app.include_router(citations_router)
    CITATIONS_ROUTER_AVAILABLE = True
except ImportError as e:
    CITATIONS_ROUTER_AVAILABLE = False
    print(f"⚠️  Citations router not available: {e}")

# Include multi-university thesis generation router
try:
    from app.api.multi_university_thesis import router as multi_university_router
    app.include_router(multi_university_router)
    MULTI_UNIVERSITY_ROUTER_AVAILABLE = True
except ImportError as e:
    MULTI_UNIVERSITY_ROUTER_AVAILABLE = False
    print(f"⚠️  Multi-university thesis router not available: {e}")

# Startup event to launch Redis subscriber
@app.on_event("startup")
async def startup_event():
    import asyncio
    from app.api.logs import redis_subscriber
    asyncio.create_task(redis_subscriber())

@app.get("/")
async def root():
    return {"message": "PhD Thesis Generator API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
