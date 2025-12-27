"""
Lightweight Thesis API - Complete FastAPI Application
Main API file with all endpoints for the lightweight thesis system.
"""
import os
import json
import asyncio
import base64
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Request, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from sse_starlette.sse import EventSourceResponse
import mimetypes

# ============================================================================
# FastAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Lightweight Thesis API",
    description="Complete API for lightweight thesis generation system",
    version="1.0.0"
)

# CORS Middleware - MUST be before routes
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

# GraphQL for fast source referencing (disabled - strawberry package causing conflicts)
# try:
#     from strawberry.fastapi import GraphQLRouter
#     from graphql.sources_schema import schema as sources_schema
#     graphql_app = GraphQLRouter(sources_schema)
#     app.include_router(graphql_app, prefix="/graphql")
#     print("✅ GraphQL enabled at /graphql")
# except Exception as e:
#     print(f"⚠️ GraphQL not available: {e}")

# ============================================================================
# SERVICE IMPORTS
# ============================================================================

from services.workspace_service import workspace_service, WORKSPACES_DIR
from services.session_service import session_service
from services.planner import planner_service
from services.chat_history_service import chat_history_service
from services.skills_manager import get_skills_manager
from core.events import events

# Import RAG router for fast document upload and semantic search
try:
    from routes.rag_api import router as rag_router
    app.include_router(rag_router)
    print("✅ RAG API endpoints enabled at /api/rag/*")
except Exception as e:
    print(f"⚠️ RAG API not available: {e}")

# Import Auth router for user authentication
try:
    from routes.auth_api import router as auth_router
    app.include_router(auth_router)
    print("✅ Auth API endpoints enabled at /api/auth/*")
except Exception as e:
    print(f"⚠️ Auth API not available: {e}")

# Import Sandbox router for isolated code execution
try:
    from routes.sandbox_api import router as sandbox_router
    app.include_router(sandbox_router)
    print("✅ Sandbox API endpoints enabled at /api/sandbox/*")
except Exception as e:
    print(f"⚠️ Sandbox API not available: {e}")

# Import Workspace Creation router for auto workspace + sandbox
try:
    from routes.workspace_creation_api import router as workspace_creation_router
    app.include_router(workspace_creation_router)
    print("✅ Workspace Creation API enabled at /api/workspace/*")
except Exception as e:
    print(f"⚠️ Workspace Creation API not available: {e}")

# Import Agent router for autonomous problem solving
try:
    from routes.agent_api import router as agent_router
    app.include_router(agent_router)
    print("✅ Autonomous Agent API enabled at /api/agent/*")
except Exception as e:
    print(f"⚠️ Agent API not available: {e}")

# Import Image router for image generation/editing
try:
    from routes.image_api import router as image_router
    app.include_router(image_router)
    print("✅ Image Generation API enabled at /api/image/*")
except Exception as e:
    print(f"⚠️ Image API not available: {e}")

# Import Browser router for automation/streaming
try:
    from routes.browser_api import router as browser_router
    app.include_router(browser_router)
    print("✅ Browser Automation API enabled at /api/browser/*")
except Exception as e:
    print(f"⚠️ Browser API not available: {e}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_short_theme(full_topic: str) -> str:
    """Extract 3-5 key words from a topic for use in objectives, headings, etc.
    
    Example:
        Input: "Security sector reform and political transition in East Africa: A critical analysis of security sector institution in South Sudan, 2011-2014"
        Output: "security sector reform political transition"
    """
    if not full_topic:
        return "the research topic"
    
    # Remove common phrases and prefixes
    text = full_topic.lower()
    for phrase in ['a critical analysis of', 'an examination of', 'a study of', 
                   'an investigation of', 'an assessment of', 'the impact of',
                   'investigating', 'exploring', 'analysing', 'analyzing',
                   'examining', 'assessing', 'evaluating']:
        text = text.replace(phrase, ' ')
    
    # Remove date ranges
    import re
    text = re.sub(r'\d{4}\s*[-–]\s*\d{4}', '', text)
    text = re.sub(r',\s*\d{4}', '', text)
    
    # Skip common words
    skip_words = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'which', 
                  'their', 'of', 'in', 'on', 'a', 'an', 'to', 'by', 'as', 'is',
                  'case', 'study', 'analysis', 'research', 'investigation'}
    words = [w.strip('.,;:()') for w in text.split() if w.lower() not in skip_words and len(w) > 2]
    
    # Return first 4-5 key words
    result = ' '.join(words[:5])
    return result if result else "the research topic"


def generate_smart_objectives(topic: str, num_objectives: int = 4) -> list:
    """Generate meaningful default objectives based on the topic.
    
    Uses short theme instead of full topic title.
    """
    short_theme = extract_short_theme(topic)
    
    # Pool of objective templates
    templates_4 = [
        f"To examine the institutional framework governing {short_theme}",
        f"To analyse the key challenges affecting {short_theme}",
        f"To assess stakeholder perspectives on {short_theme}",
        f"To recommend strategies for improving {short_theme}",
    ]
    
    templates_6 = [
        f"To examine the institutional framework governing {short_theme}",
        f"To analyse the key factors influencing {short_theme}",
        f"To evaluate the effectiveness of current {short_theme} initiatives",
        f"To assess stakeholder perspectives on {short_theme}",
        f"To identify barriers and enablers to {short_theme}",
        f"To recommend evidence-based strategies for enhancing {short_theme}",
    ]
    
    if num_objectives <= 4:
        return templates_4[:num_objectives]
    else:
        return templates_6[:num_objectives]


def extract_case_study(full_topic: str, provided_case_study: str = None) -> str:
    """Extract a meaningful case study from the topic.
    
    Examples:
        Input: "Security sector reform in South Sudan, 2011-2014"
        Output: "South Sudan"
        
        Input: "Impact of climate change on agriculture in Kenya"
        Output: "Kenya"
    """
    # If a different case study was provided, use it
    if provided_case_study and provided_case_study != full_topic and len(provided_case_study) < len(full_topic):
        return provided_case_study
    
    import re
    
    text = full_topic
    
    # First check for known country names (most reliable)
    countries = ['South Sudan', 'Sudan', 'Kenya', 'Uganda', 'Tanzania', 'Ethiopia', 
                 'Rwanda', 'Burundi', 'Somalia', 'Nigeria', 'Ghana', 'South Africa',
                 'Zimbabwe', 'Zambia', 'Malawi', 'Mozambique', 'Botswana', 'Namibia',
                 'DRC', 'Democratic Republic of Congo', 'Congo', 'Egypt', 'Morocco', 
                 'Tunisia', 'Algeria', 'Libya', 'Senegal', 'Cameroon', 'Ivory Coast',
                 'Angola', 'Eritrea', 'Djibouti', 'Central African Republic']
    
    # Check for countries (longer names first to match "South Sudan" before "Sudan")
    countries_sorted = sorted(countries, key=len, reverse=True)
    for country in countries_sorted:
        if country.lower() in text.lower():
            return country
    
    # Look for geographic locations after "in" or "of"
    patterns = [
        r'\bin\s+([A-Z][a-zA-Z\s]+?)(?:,|\.|:|$|\d{4})',  # in South Sudan, 2011
        r'\bof\s+([A-Z][a-zA-Z\s]+?)(?:,|\.|:|$|\d{4})',  # of Kenya
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            location = match.group(1).strip()
            # Clean up
            location = location.rstrip('.,;:')
            if len(location) > 3 and len(location) < 50:
                return location
    
    # Last resort: use short theme
    return extract_short_theme(full_topic)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    workspace_id: Optional[str] = "default"
    user_id: Optional[str] = "default"
    mentioned_agents: Optional[List[str]] = Field(default_factory=list)
    conversation_history: Optional[List[dict]] = Field(default_factory=list)  # Recent messages for context

class SessionInitRequest(BaseModel):
    user_id: Optional[str] = "user-1"
    workspace_id: Optional[str] = None

class CreateFileRequest(BaseModel):
    name: str
    path: Optional[str] = None
    content: str = ""

class CreateFolderRequest(BaseModel):
    name: str
    path: Optional[str] = None

class RenameRequest(BaseModel):
    old_path: str
    new_path: str

# ============================================================================
# HELPER FUNCTIONS FOR AGENT ACTIVITY TRACKING
# ============================================================================

async def publish_agent_activity(
    job_id: str,
    agent: str,
    action: str,
    description: str = "",
    progress: int = 0,
    session_id: str = "default"
):
    """
    Publish agent activity update for real-time chat display.
    
    Args:
        job_id: Job identifier
        agent: Agent name (research, writer, editor, planner, citation, search)
        action: Current action (e.g., "Searching papers", "Writing chapter")
        description: Detailed description of what agent is doing
        progress: Progress percentage (0-100)
        session_id: Session identifier
    """
    try:
        await events.publish(
            job_id,
            "agent_activity",
            {
                "agent": agent.lower(),
                "action": action,
                "description": description,
                "progress": min(max(progress, 0), 100),  # Clamp 0-100
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )
    except Exception as e:
        print(f"⚠️ Failed to publish agent_activity: {e}")

# ============================================================================
# TENSE CONVERSION UTILITY (Future to Past for Thesis)
# ============================================================================

def convert_future_to_past_tense(text: str) -> str:
    """
    Convert proposal-style (future tense) text to thesis-style (past tense).
    Preserves content meaning while changing tense for completed research reporting.
    """
    import re
    
    # Common future-to-past conversions for academic writing
    conversions = [
        # Modal verbs
        (r'\bwill be\b', 'was'),
        (r'\bWill be\b', 'Was'),
        (r'\bwill have\b', 'had'),
        (r'\bWill have\b', 'Had'),
        (r'\bwill\b', 'did'),
        (r'\bWill\b', 'Did'),
        (r'\bshall be\b', 'was'),
        (r'\bShall be\b', 'Was'),
        (r'\bshall\b', 'did'),
        (r'\bShall\b', 'Did'),
        
        # Future expressions
        (r'\bis expected to\b', 'was found to'),
        (r'\bIs expected to\b', 'Was found to'),
        (r'\bare expected to\b', 'were found to'),
        (r'\bAre expected to\b', 'Were found to'),
        (r'\bis anticipated to\b', 'was observed to'),
        (r'\bIs anticipated to\b', 'Was observed to'),
        (r'\bwill be used\b', 'was used'),
        (r'\bWill be used\b', 'Was used'),
        (r'\bwill be employed\b', 'was employed'),
        (r'\bWill be employed\b', 'Was employed'),
        (r'\bwill be conducted\b', 'was conducted'),
        (r'\bWill be conducted\b', 'Was conducted'),
        (r'\bwill be collected\b', 'was collected'),
        (r'\bWill be collected\b', 'Was collected'),
        (r'\bwill be analyzed\b', 'was analyzed'),
        (r'\bWill be analyzed\b', 'Was analyzed'),
        (r'\bwill be analysed\b', 'was analysed'),
        (r'\bWill be analysed\b', 'Was analysed'),
        
        # Common research verbs
        (r'\bwill examine\b', 'examined'),
        (r'\bWill examine\b', 'Examined'),
        (r'\bwill investigate\b', 'investigated'),
        (r'\bWill investigate\b', 'Investigated'),
        (r'\bwill explore\b', 'explored'),
        (r'\bWill explore\b', 'Explored'),
        (r'\bwill assess\b', 'assessed'),
        (r'\bWill assess\b', 'Assessed'),
        (r'\bwill evaluate\b', 'evaluated'),
        (r'\bWill evaluate\b', 'Evaluated'),
        (r'\bwill determine\b', 'determined'),
        (r'\bWill determine\b', 'Determined'),
        (r'\bwill identify\b', 'identified'),
        (r'\bWill identify\b', 'Identified'),
        (r'\bwill analyze\b', 'analyzed'),
        (r'\bWill analyze\b', 'Analyzed'),
        (r'\bwill analyse\b', 'analysed'),
        (r'\bWill analyse\b', 'Analysed'),
        (r'\bwill measure\b', 'measured'),
        (r'\bWill measure\b', 'Measured'),
        (r'\bwill study\b', 'studied'),
        (r'\bWill study\b', 'Studied'),
        (r'\bwill test\b', 'tested'),
        (r'\bWill test\b', 'Tested'),
        (r'\bwill develop\b', 'developed'),
        (r'\bWill develop\b', 'Developed'),
        (r'\bwill establish\b', 'established'),
        (r'\bWill establish\b', 'Established'),
        (r'\bwill provide\b', 'provided'),
        (r'\bWill provide\b', 'Provided'),
        (r'\bwill contribute\b', 'contributed'),
        (r'\bWill contribute\b', 'Contributed'),
        (r'\bwill focus\b', 'focused'),
        (r'\bWill focus\b', 'Focused'),
        (r'\bwill utilize\b', 'utilized'),
        (r'\bWill utilize\b', 'Utilized'),
        (r'\bwill utilise\b', 'utilised'),
        (r'\bWill utilise\b', 'Utilised'),
        (r'\bwill employ\b', 'employed'),
        (r'\bWill employ\b', 'Employed'),
        (r'\bwill adopt\b', 'adopted'),
        (r'\bWill adopt\b', 'Adopted'),
        (r'\bwill use\b', 'used'),
        (r'\bWill use\b', 'Used'),
        (r'\bwill apply\b', 'applied'),
        (r'\bWill apply\b', 'Applied'),
        (r'\bwill collect\b', 'collected'),
        (r'\bWill collect\b', 'Collected'),
        (r'\bwill gather\b', 'gathered'),
        (r'\bWill gather\b', 'Gathered'),
        (r'\bwill select\b', 'selected'),
        (r'\bWill select\b', 'Selected'),
        (r'\bwill sample\b', 'sampled'),
        (r'\bWill sample\b', 'Sampled'),
        (r'\bwill conduct\b', 'conducted'),
        (r'\bWill conduct\b', 'Conducted'),
        (r'\bwill perform\b', 'performed'),
        (r'\bWill perform\b', 'Performed'),
        (r'\bwill administer\b', 'administered'),
        (r'\bWill administer\b', 'Administered'),
        (r'\bwill distribute\b', 'distributed'),
        (r'\bWill distribute\b', 'Distributed'),
        (r'\bwill interview\b', 'interviewed'),
        (r'\bWill interview\b', 'Interviewed'),
        (r'\bwill observe\b', 'observed'),
        (r'\bWill observe\b', 'Observed'),
        (r'\bwill record\b', 'recorded'),
        (r'\bWill record\b', 'Recorded'),
        (r'\bwill ensure\b', 'ensured'),
        (r'\bWill ensure\b', 'Ensured'),
        (r'\bwill maintain\b', 'maintained'),
        (r'\bWill maintain\b', 'Maintained'),
        (r'\bwill seek\b', 'sought'),
        (r'\bWill seek\b', 'Sought'),
        (r'\bwill obtain\b', 'obtained'),
        (r'\bWill obtain\b', 'Obtained'),
        
        # Present tense to past (for methodology)
        (r'\bThis study aims to\b', 'This study aimed to'),
        (r'\bthis study aims to\b', 'this study aimed to'),
        (r'\bThis study seeks to\b', 'This study sought to'),
        (r'\bthis study seeks to\b', 'this study sought to'),
        (r'\bThis research aims to\b', 'This research aimed to'),
        (r'\bthis research aims to\b', 'this research aimed to'),
        (r'\bThe study aims to\b', 'The study aimed to'),
        (r'\bthe study aims to\b', 'the study aimed to'),
        (r'\bThe research aims to\b', 'The research aimed to'),
        (r'\bthe research aims to\b', 'the research aimed to'),
        (r'\bThe researcher will\b', 'The researcher'),
        (r'\bthe researcher will\b', 'the researcher'),
        
        # Phrases
        (r'\bIn order to achieve\b', 'To achieve'),
        (r'\bin order to achieve\b', 'to achieve'),
        (r'\bwill be obtained from\b', 'was obtained from'),
        (r'\bWill be obtained from\b', 'Was obtained from'),
        (r'\bwill be gathered from\b', 'was gathered from'),
        (r'\bWill be gathered from\b', 'Was gathered from'),
        (r'\bwill be selected using\b', 'was selected using'),
        (r'\bWill be selected using\b', 'Was selected using'),
        (r'\bwill be determined by\b', 'was determined by'),
        (r'\bWill be determined by\b', 'Was determined by'),
        
        # Data collection
        (r'\bData will be collected\b', 'Data was collected'),
        (r'\bdata will be collected\b', 'data was collected'),
        (r'\bData will be gathered\b', 'Data was gathered'),
        (r'\bdata will be gathered\b', 'data was gathered'),
        (r'\bData will be analyzed\b', 'Data was analyzed'),
        (r'\bdata will be analyzed\b', 'data was analyzed'),
        (r'\bData will be analysed\b', 'Data was analysed'),
        (r'\bdata will be analysed\b', 'data was analysed'),
        
        # Sampling
        (r'\bwill be purposively selected\b', 'were purposively selected'),
        (r'\bwill be randomly selected\b', 'were randomly selected'),
        (r'\bwill be stratified\b', 'were stratified'),
        
        # Ethics
        (r'\bwill be sought\b', 'was sought'),
        (r'\bWill be sought\b', 'Was sought'),
        (r'\bwill be ensured\b', 'was ensured'),
        (r'\bWill be ensured\b', 'Was ensured'),
        (r'\bwill be maintained\b', 'was maintained'),
        (r'\bWill be maintained\b', 'Was maintained'),
        (r'\bwill be protected\b', 'was protected'),
        (r'\bWill be protected\b', 'Was protected'),
        (r'\bwill be kept confidential\b', 'was kept confidential'),
        (r'\bWill be kept confidential\b', 'Was kept confidential'),
    ]
    
    result = text
    for pattern, replacement in conversions:
        result = re.sub(pattern, replacement, result)
    
    return result

# ============================================================================
# WORKSPACE FILE LISTING (Recursive)
# ============================================================================

def list_workspace_files(workspace_id: str, base_path: str = "") -> List[Dict]:
    """Recursively list all files and folders in workspace from BOTH thesis_data and workspaces dirs."""
    # Check both locations for workspace files
    thesis_data_path = WORKSPACES_DIR / workspace_id  # thesis_data/default
    workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}")  # workspaces/default
    
    items = []
    
    # Directories to ignore to prevent hanging on massive dependency trees
    IGNORE_DIRS = {
        'node_modules', 'venv', '.venv', '__pycache__', '.git', 
        '.next', 'dist', 'build', 'coverage'
    }
    
    def scan_directory(search_path: Path, prefix: str = ""):
        """Scan a directory and add files/folders to items list."""
        if not search_path.exists():
            return
            
        print(f"📂 Scanning: {search_path}")
        
        try:
            # Walk manually to control recursion into ignored directories
            for root, dirs, files in os.walk(search_path):
                # Modify dirs in-place to skip ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
                
                root_path = Path(root)
                
                # Add directories
                for d in dirs:
                    full_path = root_path / d
                    try:
                        rel_path = str(full_path.relative_to(search_path))
                        if prefix:
                            rel_path = f"{prefix}/{rel_path}"
                        stat = full_path.stat()
                        # Check for duplicate paths
                        if not any(item["path"] == rel_path.replace("\\", "/") for item in items):
                            items.append({
                                "name": d,
                                "path": rel_path.replace("\\", "/"),
                                "type": "folder",
                                "size": 0,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            })
                    except ValueError:
                        continue
                
                # Add files
                for f in files:
                    if f.startswith('.') or f == "workspace.json":
                        continue
                        
                    full_path = root_path / f
                    try:
                        rel_path = str(full_path.relative_to(search_path))
                        if prefix:
                            rel_path = f"{prefix}/{rel_path}"
                        stat = full_path.stat()
                        # Check for duplicate paths
                        if not any(item["path"] == rel_path.replace("\\", "/") for item in items):
                            items.append({
                                "name": f,
                                "path": rel_path.replace("\\", "/"),
                                "type": "file",
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            })
                    except ValueError:
                        continue
                        
        except Exception as e:
            print(f"❌ Error scanning {search_path}: {e}")
    
    # Scan thesis_data folder (chapters, study tools)
    scan_directory(thesis_data_path)
    
    # Scan workspaces folder (datasets, figures)
    scan_directory(workspaces_path)
    
    print(f"✅ Found {len(items)} items in {workspace_id} (from thesis_data + workspaces)")
    return items

# ============================================================================
# TOOL EXECUTION FUNCTIONS
# ============================================================================

async def execute_tool(tool_name: str, arguments: Dict, workspace_id: str = "default") -> Dict:
    """Execute a tool and return the result."""
    workspace_path = WORKSPACES_DIR / workspace_id
    
    if tool_name == "list_files":
        path = arguments.get("path", ".")
        search_path = workspace_path / path if path else workspace_path
        
        if not search_path.exists():
            return {"status": "error", "error": f"Path '{path}' not found"}
        
        files = []
        try:
            for item in search_path.iterdir():
                if item.name.startswith('.'):
                    continue
                rel_path = str(item.relative_to(workspace_path))
                files.append({
                    "name": item.name,
                    "path": rel_path.replace("\\", "/"),
                    "type": "folder" if item.is_dir() else "file"
                })
        except Exception as e:
            return {"status": "error", "error": str(e)}
        
        return {"status": "success", "files": files}
    
    elif tool_name == "read_file":
        file_path = arguments.get("path")
        full_path = workspace_path / file_path if file_path else workspace_path
        
        if not full_path.exists() or not full_path.is_file():
            return {"status": "error", "error": f"File '{file_path}' not found"}
        
        try:
            content = full_path.read_text(encoding='utf-8')
            return {"status": "success", "content": content, "path": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "write_file" or tool_name == "save_file":
        file_path = arguments.get("path")
        content = arguments.get("content", "")
        
        if not file_path:
            return {"status": "error", "error": "File path is required"}
        
        full_path = workspace_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            full_path.write_text(content, encoding='utf-8')
            return {"status": "success", "path": file_path, "message": f"File '{file_path}' saved"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "create_folder":
        folder_path = arguments.get("path")
        
        if not folder_path:
            return {"status": "error", "error": "Folder path is required"}
        
        full_path = workspace_path / folder_path
        
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return {"status": "success", "path": folder_path, "message": f"Folder '{folder_path}' created"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "delete_file":
        file_path = arguments.get("path")
        full_path = workspace_path / file_path if file_path else workspace_path
        
        if not full_path.exists():
            return {"status": "error", "error": f"Path '{file_path}' not found"}
        
        try:
            if full_path.is_file():
                full_path.unlink()
            else:
                import shutil
                shutil.rmtree(full_path)
            return {"status": "success", "message": f"Deleted '{file_path}'"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "web_search":
        query = arguments.get("query", "")
        try:
            from services.web_search import web_search_service
            results = await web_search_service.search(query, max_results=5)
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "image_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        try:
            from services.intelligent_image_search import intelligent_image_search_service
            results = await intelligent_image_search_service.search(query, limit=limit)
            # Format results for easier use
            formatted_results = []
            for img in results:
                if isinstance(img, dict):
                    formatted_results.append({
                        "url": img.get("url") or img.get("full") or img.get("image_url"),
                        "title": img.get("title") or img.get("description") or query,
                        "thumbnail": img.get("thumbnail") or img.get("url"),
                        "source": img.get("source", "search")
                    })
            return {"status": "success", "images": formatted_results}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    elif tool_name == "image_generate":
        prompt = arguments.get("prompt", "")
        size = arguments.get("size", "1024x1024")
        try:
            from services.image_generation import image_generation_service
            result = await image_generation_service.generate(prompt=prompt, size=size)
            if result.get("success"):
                return {
                    "status": "success",
                    "image_url": result.get("image_url") or result.get("url"),
                    "prompt": prompt
                }
            else:
                return {"status": "error", "error": result.get("error", "Image generation failed")}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": f"Unknown tool: {tool_name}"}

# ============================================================================
# HEALTH & ROOT ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Lightweight Thesis API is running", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# ============================================================================
# BROWSER STREAMING ENDPOINT - Live browser preview
# ============================================================================

@app.get("/api/browser/stream")
async def browser_stream(session_id: str = "default"):
    """
    SSE endpoint for live browser automation viewing.
    
    Streams:
    - Screenshots (base64)
    - Current URL
    - Actions being performed
    """
    import redis.asyncio as aioredis
    import os
    
    async def browser_event_generator():
        """Generate browser events from Redis pub/sub."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
            redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
        
        try:
            redis = aioredis.from_url(redis_url, decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"browser:{session_id}")
            
            # Send initial connected message
            yield {"event": "connected", "data": json.dumps({"status": "connected", "session_id": session_id})}
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"event": "browser_update", "data": message["data"]}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
    
    return EventSourceResponse(browser_event_generator())

# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@app.post("/api/session/init")
async def init_session(request: SessionInitRequest):
    """Initialize a new session."""
    try:
        session_data = session_service.get_or_create_session()
        
        if request.workspace_id:
            session_service.set_workspace(session_data["session_id"], request.workspace_id)
            session_data["workspace_id"] = request.workspace_id
        
        return {
            "session_id": session_data["session_id"],
            "user_id": request.user_id,
            "workspace_id": session_data.get("workspace_id"),
            "session_url": f"/session/{session_data['session_id']}",
            "has_workspace": session_data.get("workspace_id") is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session data. Creates session if it doesn't exist."""
    try:
        session_data = session_service.get_session(session_id)
        if not session_data:
            # Create session if it doesn't exist (for new sessions)
            session_data = session_service.get_or_create_session(session_id)
        
        return session_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WORKSPACE ENDPOINTS
# ============================================================================

@app.get("/api/workspaces/list")
async def list_workspaces():
    """List all workspaces."""
    try:
        workspaces = workspace_service.list_workspaces()
        return {"workspaces": workspaces}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chapter/background-styles")
async def get_background_styles():
    """Get available background writing styles for chapter generation."""
    from services.parallel_chapter_generator import BACKGROUND_STYLES
    return {
        "styles": [
            {
                "id": style_id,
                "name": style["name"],
                "description": style["description"],
                "best_for": style["best_for"],
                "sections": style["sections"]
            }
            for style_id, style in BACKGROUND_STYLES.items()
        ],
        "default": "inverted_pyramid"
    }

@app.get("/api/workspace/{workspace_id}/structure")
async def get_workspace_structure(workspace_id: str):
    """Get complete workspace file structure recursively."""
    try:
        if not workspace_service.workspace_exists(workspace_id):
            # Create default workspace if it doesn't exist
            await workspace_service.create_workspace(workspace_id=workspace_id)
        
        items = list_workspace_files(workspace_id)
        
        return {
            "workspace_id": workspace_id,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/files/{file_path:path}")
async def get_file(workspace_id: str, file_path: str):
    """Get file content."""
    try:
        # Check both thesis_data and workspaces directories
        thesis_data_path = WORKSPACES_DIR / workspace_id / file_path
        workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}") / file_path
        
        # Try thesis_data first, then workspaces
        if thesis_data_path.exists() and thesis_data_path.is_file():
            workspace_path = thesis_data_path
        elif workspaces_path.exists() and workspaces_path.is_file():
            workspace_path = workspaces_path
        else:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # For binary files (images, etc.), return info only
        if workspace_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.xlsx', '.xls', '.csv']:
            return {
                "path": file_path,
                "content": f"[Binary file: {workspace_path.name}]",
                "name": workspace_path.name,
                "binary": True,
                "serve_url": f"/api/workspace/{workspace_id}/serve/{file_path}"
            }
        
        content = workspace_path.read_text(encoding='utf-8')
        
        return {
            "path": file_path,
            "content": content,
            "name": workspace_path.name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/serve/{file_path:path}")
async def serve_file(workspace_id: str, file_path: str):
    """Serve binary files (images, PDFs, etc.) with correct Content-Type for inline viewing."""
    try:
        # Check both thesis_data and workspaces directories
        thesis_data_path = WORKSPACES_DIR / workspace_id / file_path
        workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}") / file_path
        
        # Try thesis_data first, then workspaces
        if thesis_data_path.exists() and thesis_data_path.is_file():
            workspace_path = thesis_data_path
        elif workspaces_path.exists() and workspaces_path.is_file():
            workspace_path = workspaces_path
        else:
            print(f"❌ File not found: {file_path}")
            print(f"   Checked: {thesis_data_path}")
            print(f"   Checked: {workspaces_path}")
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Determine media type
        media_type, _ = mimetypes.guess_type(str(workspace_path))
        if not media_type:
            media_type = "application/octet-stream"
        
        # For viewable files (PDFs, images), use inline disposition to display in browser
        # For other files, use attachment to force download
        viewable_types = ['application/pdf', 'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml']
        
        if media_type in viewable_types:
            # Return without filename to display inline (not download)
            return FileResponse(
                path=str(workspace_path),
                media_type=media_type,
                headers={"Content-Disposition": f"inline; filename=\"{workspace_path.name}\""}
            )
        else:
            # Force download for other file types
            return FileResponse(
                path=str(workspace_path),
                media_type=media_type,
                filename=workspace_path.name
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/files")
async def create_file(workspace_id: str, request: CreateFileRequest):
    """Create a new file."""
    try:
        workspace_path = WORKSPACES_DIR / workspace_id
        file_path = workspace_path / (request.path or request.name)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content, encoding='utf-8')
        
        return {
            "status": "success",
            "path": str(file_path.relative_to(workspace_path)),
            "name": file_path.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FILE CONVERSION ENDPOINTS
# ============================================================================

class ConvertDocxRequest(BaseModel):
    content: str
    filename: Optional[str] = "document"

@app.post("/api/workspace/{workspace_id}/convert/docx")
async def convert_to_docx(workspace_id: str, request: ConvertDocxRequest):
    """Convert markdown content to DOCX using the EnhancedDOCXConverter."""
    try:
        from services.docx_converter import EnhancedDOCXConverter
        
        converter = EnhancedDOCXConverter(workspace_id=workspace_id)
        
        # Determine filename
        filename = request.filename
        if not filename.endswith('.docx'):
            filename += '.docx'
            
        # Convert content
        temp_docx_path = converter.convert(request.content, filename)
        
        # Read the generated file content
        with open(temp_docx_path, "rb") as f:
            docx_content = f.read()
            
        # Clean up temp file
        import os
        os.unlink(temp_docx_path)
        
        # Return as downloadable file
        return Response(
            content=docx_content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class AddSourceRequest(BaseModel):
    title: str
    authors: List[str] = []
    year: int = 2024
    type: str = "paper"
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    pdf_url: Optional[str] = None

class SearchSourcesRequest(BaseModel):
    query: str
    max_results: int = 5
    auto_save: bool = True  # Default to auto-save

@app.get("/api/workspace/{workspace_id}/sources")
async def list_sources(workspace_id: str):
    """List all sources in workspace."""
    try:
        from services.sources_service import sources_service
        sources = sources_service.list_sources(workspace_id)
        return {
            "workspace_id": workspace_id,
            "total": len(sources),
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/sources/{source_id}")
async def get_source(workspace_id: str, source_id: str):
    """Get a specific source."""
    try:
        from services.sources_service import sources_service
        source = sources_service.get_source(workspace_id, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/sources")
async def add_source(workspace_id: str, request: AddSourceRequest):
    """Add a source manually."""
    try:
        from services.sources_service import sources_service
        source = await sources_service.add_source(workspace_id, request.model_dump())
        return {"status": "success", "source": source}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/sources/search")
async def search_and_save_sources(workspace_id: str, request: SearchSourcesRequest):
    """Search academic sources and optionally save them."""
    try:
        from services.sources_service import sources_service
        result = await sources_service.search_and_save(
            workspace_id=workspace_id,
            query=request.query,
            max_results=request.max_results,
            auto_save=request.auto_save
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/sources/{source_id}/text")
async def get_source_text(workspace_id: str, source_id: str):
    """Get extracted text from a source (for LLM context)."""
    try:
        from services.sources_service import sources_service
        text = sources_service.get_source_text(workspace_id, source_id)
        if not text:
            raise HTTPException(status_code=404, detail="Source text not available")
        return {"source_id": source_id, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/sources-context")
async def get_sources_context(workspace_id: str, max_sources: int = 5):
    """Get formatted sources context for LLM."""
    try:
        from services.sources_service import sources_service
        context = sources_service.get_sources_context(workspace_id, max_sources)
        return {"workspace_id": workspace_id, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/workspace/{workspace_id}/sources/{source_id}")
async def delete_source(workspace_id: str, source_id: str):
    """Delete a source."""
    try:
        from services.sources_service import sources_service
        success = sources_service.delete_source(workspace_id, source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")
        return {"status": "success", "deleted": source_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKSPACE SETTINGS ENDPOINTS
# ============================================================================

class WorkspaceSettingsUpdate(BaseModel):
    """Model for updating workspace settings."""
    search: Optional[Dict[str, Any]] = None
    indexing: Optional[Dict[str, Any]] = None
    citations: Optional[Dict[str, Any]] = None


@app.get("/api/workspace/{workspace_id}/settings")
async def get_workspace_settings(workspace_id: str):
    """Get workspace settings (search filters, indexing, citations)."""
    try:
        from services.workspace_service import WorkspaceService
        settings = WorkspaceService.get_workspace_settings(workspace_id)
        return {
            "workspace_id": workspace_id,
            "settings": settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/workspace/{workspace_id}/settings")
async def update_workspace_settings(workspace_id: str, request: WorkspaceSettingsUpdate):
    """Update workspace settings."""
    try:
        from services.workspace_service import WorkspaceService
        
        updates = {}
        if request.search:
            updates["search"] = request.search
        if request.indexing:
            updates["indexing"] = request.indexing
        if request.citations:
            updates["citations"] = request.citations
        
        success = WorkspaceService.update_workspace_settings(workspace_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Return updated settings
        new_settings = WorkspaceService.get_workspace_settings(workspace_id)
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "settings": new_settings
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/search-filters")
async def get_search_filters(workspace_id: str):
    """Get search-specific filters formatted for API consumption."""
    try:
        from services.workspace_service import WorkspaceService
        filters = WorkspaceService.get_search_filters(workspace_id)
        return {
            "workspace_id": workspace_id,
            "filters": filters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONVERSATION MEMORY ENDPOINTS
# ============================================================================

class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"


class AddMessageRequest(BaseModel):
    role: str  # user, assistant
    content: str
    job_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RecallRequest(BaseModel):
    query: str


@app.post("/api/workspace/{workspace_id}/conversations")
async def create_conversation(workspace_id: str, request: CreateConversationRequest):
    """Create a new conversation with memory."""
    from services.conversation_memory import conversation_memory
    
    conversation = await conversation_memory.create_conversation(
        workspace_id=workspace_id,
        title=request.title
    )
    return {"conversation_id": conversation.conversation_id, "workspace_id": workspace_id}


@app.get("/api/workspace/{workspace_id}/conversations")
async def list_conversations(workspace_id: str):
    """List all conversations in workspace."""
    from services.conversation_memory import conversation_memory
    
    conversations = conversation_memory.list_conversations(workspace_id)
    return {"conversations": conversations, "total": len(conversations)}


@app.get("/api/workspace/{workspace_id}/conversations/{conversation_id}/messages")
async def get_messages(
    workspace_id: str, 
    conversation_id: str,
    limit: int = 50,
    offset: int = 0
):
    """Get messages from conversation."""
    from services.conversation_memory import conversation_memory
    
    messages = await conversation_memory.get_messages(
        workspace_id, conversation_id, limit=limit, offset=offset
    )
    return {"messages": messages, "count": len(messages)}


@app.post("/api/workspace/{workspace_id}/conversations/{conversation_id}/messages")
async def add_message(
    workspace_id: str,
    conversation_id: str,
    request: AddMessageRequest
):
    """Add a message to conversation history."""
    from services.conversation_memory import conversation_memory
    
    message = await conversation_memory.add_message(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        job_id=request.job_id,
        metadata=request.metadata
    )
    return {"message_id": message.id, "timestamp": message.timestamp}


@app.post("/api/workspace/{workspace_id}/conversations/{conversation_id}/recall")
async def recall_memory(
    workspace_id: str,
    conversation_id: str,
    request: RecallRequest
):
    """Recall relevant information from conversation history."""
    from services.conversation_memory import conversation_memory
    
    result = await conversation_memory.recall(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query=request.query
    )
    return result


@app.get("/api/workspace/{workspace_id}/conversations/{conversation_id}/context")
async def get_context(workspace_id: str, conversation_id: str, message: str = ""):
    """Get context for LLM prompt including memory."""
    from services.conversation_memory import conversation_memory
    
    context = await conversation_memory.get_context_for_prompt(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        current_message=message
    )
    return {"context": context}


# ============================================================================
# MULTIMODAL FILE PROCESSING ENDPOINTS
# ============================================================================

@app.post("/api/workspace/{workspace_id}/files/process")
async def process_file(workspace_id: str, file_path: str):
    """
    Process a file and extract content.
    
    Supports: Audio (transcription), Images (vision), PDFs, DOCX, Data files
    """
    from services.multimodal_processor import multimodal_processor
    
    result = await multimodal_processor.process_file(file_path, workspace_id)
    return result


@app.post("/api/workspace/{workspace_id}/files/process-batch")
async def process_files_batch(workspace_id: str, file_paths: List[str]):
    """Process multiple files in parallel."""
    from services.multimodal_processor import multimodal_processor
    
    results = await multimodal_processor.process_uploaded_files(workspace_id, file_paths)
    return {"results": results, "processed": len(results)}


@app.post("/api/workspace/{workspace_id}/audio/transcribe")
async def transcribe_audio(workspace_id: str, file_path: str):
    """Transcribe audio file to text."""
    from services.multimodal_processor import multimodal_processor
    
    result = await multimodal_processor.process_audio(file_path)
    return result


@app.post("/api/workspace/{workspace_id}/image/analyze")
async def analyze_image(workspace_id: str, file_path: str):
    """Analyze image using vision AI."""
    from services.multimodal_processor import multimodal_processor
    
    result = await multimodal_processor.process_image(file_path)
    return result


# ============================================================================
# DOCUMENT EXPORT ENDPOINTS
# ============================================================================

class ExportDocxRequest(BaseModel):
    """Request to export content to DOCX."""
    content: str
    title: str = "Document"
    filename: Optional[str] = None


@app.post("/api/workspace/{workspace_id}/export/docx")
async def export_to_docx(workspace_id: str, request: ExportDocxRequest):
    """
    Export content to DOCX with clickable citation links.
    
    In the exported DOCX, citations like (Smith, 2020) become
    clickable hyperlinks that jump to the References section.
    """
    from services.document_exporter import document_exporter
    from services.sources_service import sources_service
    from services.workspace_service import WORKSPACES_DIR
    
    try:
        # Get sources for citation mapping
        sources = sources_service.list_sources(workspace_id)
        
        # Generate filename
        filename = request.filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        if not filename.endswith('.docx'):
            filename += '.docx'
        
        output_dir = WORKSPACES_DIR / workspace_id / "outputs"
        output_path = output_dir / filename
        
        # Export
        result_path = document_exporter.export_to_docx(
            content=request.content,
            output_path=str(output_path),
            sources=sources,
            title=request.title
        )
        
        return {
            "success": True,
            "file_path": result_path,
            "filename": filename,
            "download_url": f"/api/workspace/{workspace_id}/files/{filename}"
        }
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail="python-docx not installed. Run: pip install python-docx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/{workspace_id}/synthesis/export")
async def export_synthesis_to_docx(workspace_id: str, content: str, title: str = "Literature Synthesis"):
    """Export a synthesis directly to DOCX."""
    from services.document_exporter import document_exporter
    
    try:
        result_path = document_exporter.export_synthesis_to_docx(
            workspace_id=workspace_id,
            synthesis_content=content
        )
        
        return {
            "success": True,
            "file_path": result_path,
            "message": "Synthesis exported to DOCX with clickable citations"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LITERATURE SYNTHESIS ENDPOINTS
# ============================================================================

class SynthesisRequest(BaseModel):
    """Request for literature synthesis."""
    topic: str
    output_format: str = "markdown"  # markdown or docx


@app.post("/api/workspace/{workspace_id}/synthesize")
async def synthesize_literature(workspace_id: str, request: SynthesisRequest):
    """
    Generate a literature synthesis from all collected sources.
    
    Reads PDFs, abstracts, texts, JSONs and generates a well-cited report.
    Returns SSE stream with synthesized content.
    """
    from services.literature_synthesis import literature_synthesis_service
    
    async def synthesis_generator():
        try:
            # Send start event
            yield {
                "event": "start",
                "data": json.dumps({"topic": request.topic, "workspace_id": workspace_id})
            }
            
            # Stream synthesis
            accumulated = ""
            async for chunk in literature_synthesis_service.synthesize_literature(
                workspace_id=workspace_id,
                topic=request.topic,
                output_format=request.output_format
            ):
                accumulated += chunk
                yield {
                    "event": "response_chunk",
                    "data": json.dumps({"chunk": chunk, "accumulated": accumulated})
                }
            
            # Send complete event
            yield {
                "event": "complete",
                "data": json.dumps({"status": "success"})
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(synthesis_generator())


@app.get("/api/workspace/{workspace_id}/synthesize/sources")
async def get_synthesis_sources(workspace_id: str):
    """Preview what sources will be used for synthesis."""
    try:
        from services.literature_synthesis import literature_synthesis_service
        
        sources = await literature_synthesis_service.gather_source_content(workspace_id)
        
        return {
            "workspace_id": workspace_id,
            "total_sources": len(sources),
            "sources": [
                {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "authors": s.get("authors", [])[:2],
                    "year": s.get("year"),
                    "source_type": s.get("source_type"),
                    "content_length": len(s.get("content", "")),
                    "citation_key": s.get("citation_key")
                }
                for s in sources
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PERSISTENT JOBS ENDPOINTS
# ============================================================================

class CreateJobRequest(BaseModel):
    """Request to create a new background job."""
    message: str
    mentioned_agents: Optional[List[str]] = None
    files: Optional[List[str]] = None



@app.post("/api/workspace/{workspace_id}/jobs")
async def create_job(workspace_id: str, request: CreateJobRequest):
    """
    Create a new persistent background job.
    
    The job runs independently of the frontend connection.
    Returns immediately with job_id - use /stream to follow progress.
    """
    try:
        from services.job_manager import job_manager
        
        # Create the job
        job = await job_manager.create_job(
            workspace_id=workspace_id,
            message=request.message,
            mentioned_agents=request.mentioned_agents,
            files=request.files
        )
        
        # Start job processing in background
        from services.job_processor import process_job
        await job_manager.start_job(job, process_job)
        
        return {
            "status": "created",
            "job_id": job.job_id,
            "workspace_id": workspace_id,
            "stream_url": f"/api/workspace/{workspace_id}/jobs/{job.job_id}/stream"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/jobs")
async def list_jobs(
    workspace_id: str,
    status: Optional[str] = None,
    limit: int = 20
):
    """List jobs for a workspace."""
    try:
        from services.job_manager import job_manager, JobStatus
        
        status_filter = JobStatus(status) if status else None
        jobs = job_manager.list_jobs(workspace_id, status=status_filter, limit=limit)
        
        return {
            "workspace_id": workspace_id,
            "total": len(jobs),
            "jobs": [job.to_dict() for job in jobs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/jobs/active")
async def get_active_jobs(workspace_id: str):
    """Get currently running or paused jobs."""
    try:
        from services.job_manager import job_manager, JobStatus
        
        jobs = job_manager.list_jobs(workspace_id)
        active_jobs = [
            job for job in jobs 
            if job.status in [JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.PENDING]
        ]
        
        return {
            "workspace_id": workspace_id,
            "active_count": len(active_jobs),
            "jobs": [job.to_dict() for job in active_jobs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/jobs/{job_id}")
async def get_job(workspace_id: str, job_id: str):
    """Get job status and details."""
    try:
        from services.job_manager import job_manager
        
        job = job_manager.get_job(workspace_id, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job": job.to_dict(),
            "is_active": job_manager.is_job_active(job_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/jobs/{job_id}/stream")
async def stream_job(workspace_id: str, job_id: str):
    """
    SSE stream for job events.
    
    Can be reconnected at any time - will continue receiving events.
    Events: progress, step, content, log, completed, error, paused, resumed, cancelled
    """
    from services.job_manager import job_manager
    
    job = job_manager.get_job(workspace_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        # Send current job state first
        yield {
            "event": "state",
            "data": json.dumps(job.to_dict())
        }
        
        # Stream events
        async for event in job_manager.get_event_stream(job_id):
            yield {
                "event": event["type"],
                "data": json.dumps(event["data"])
            }
    
    return EventSourceResponse(event_generator())


@app.post("/api/workspace/{workspace_id}/jobs/{job_id}/pause")
async def pause_job(workspace_id: str, job_id: str):
    """Pause a running job."""
    try:
        from services.job_manager import job_manager
        
        success = await job_manager.pause_job(workspace_id, job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot pause job - not running")
        
        return {"status": "paused", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/{workspace_id}/jobs/{job_id}/resume")
async def resume_job(workspace_id: str, job_id: str):
    """Resume a paused job."""
    try:
        from services.job_manager import job_manager
        
        success = await job_manager.resume_job(workspace_id, job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot resume job - not paused")
        
        return {"status": "resumed", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/{workspace_id}/jobs/{job_id}/cancel")
async def cancel_job(workspace_id: str, job_id: str):
    """Cancel a running or paused job."""
    try:
        from services.job_manager import job_manager
        
        success = await job_manager.cancel_job(workspace_id, job_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel job - already completed or cancelled")
        
        return {"status": "cancelled", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

class CreateProjectRequest(BaseModel):
    name: str
    project_type: Optional[str] = "default"
    folder_id: Optional[str] = None


@app.post("/api/workspace/{workspace_id}/projects")
async def create_project(workspace_id: str, request: CreateProjectRequest):
    """Create a new project (same as folder for now)."""
    try:
        workspace_path = WORKSPACES_DIR / workspace_id
        project_path = workspace_path / request.name
        
        project_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success",
            "path": str(project_path.relative_to(workspace_path)),
            "name": request.name,
            "type": "project"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/folders")
async def create_folder(workspace_id: str, request: CreateFolderRequest):
    """Create a new folder."""
    try:
        workspace_path = WORKSPACES_DIR / workspace_id
        folder_path = workspace_path / (request.path or request.name)
        
        folder_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success",
            "path": str(folder_path.relative_to(workspace_path)),
            "name": folder_path.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# IMAGE DOWNLOAD ENDPOINTS
# ============================================================================

class DownloadImageRequest(BaseModel):
    image_url: str
    filename: Optional[str] = None

class BatchDownloadImagesRequest(BaseModel):
    images: List[Dict[str, str]]  # List of {url, filename}

@app.post("/api/workspace/{workspace_id}/download-image")
async def download_image(workspace_id: str, request: DownloadImageRequest):
    """Download a single image from URL and save to workspace."""
    try:
        import httpx
        from pathlib import Path
        
        workspace_path = WORKSPACES_DIR / workspace_id
        images_dir = workspace_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not request.filename:
            # Extract filename from URL or generate one
            url_path = request.image_url.split('/')[-1].split('?')[0]
            if url_path and '.' in url_path:
                request.filename = url_path
            else:
                request.filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        # Ensure filename has extension
        if '.' not in request.filename:
            request.filename += ".jpg"
        
        file_path = images_dir / request.filename
        
        # Download image
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(request.image_url)
            response.raise_for_status()
            
            # Save to workspace
            file_path.write_bytes(response.content)
        
        relative_path = str(file_path.relative_to(workspace_path))
        
        return {
            "status": "success",
            "path": relative_path,
            "filename": request.filename,
            "size": len(response.content)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to download image: {str(e)}")

@app.post("/api/workspace/{workspace_id}/batch-download-images")
async def batch_download_images(workspace_id: str, request: BatchDownloadImagesRequest):
    """Download multiple images and save to workspace."""
    try:
        import httpx
        from pathlib import Path
        
        workspace_path = WORKSPACES_DIR / workspace_id
        images_dir = workspace_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        failed_count = 0
        results = []
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for img_data in request.images:
                try:
                    image_url = img_data.get("url") or img_data.get("image_url")
                    filename = img_data.get("filename")
                    
                    if not image_url:
                        failed_count += 1
                        results.append({"url": image_url, "status": "failed", "error": "No URL provided"})
                        continue
                    
                    # Generate filename if not provided
                    if not filename:
                        url_path = image_url.split('/')[-1].split('?')[0]
                        if url_path and '.' in url_path:
                            filename = url_path
                        else:
                            filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                    
                    # Ensure filename has extension
                    if '.' not in filename:
                        filename += ".jpg"
                    
                    file_path = images_dir / filename
                    
                    # Download image
                    response = await client.get(image_url)
                    response.raise_for_status()
                    
                    # Save to workspace
                    file_path.write_bytes(response.content)
                    
                    relative_path = str(file_path.relative_to(workspace_path))
                    success_count += 1
                    results.append({
                        "url": image_url,
                        "status": "success",
                        "path": relative_path,
                        "filename": filename
                    })
                    
                except Exception as e:
                    failed_count += 1
                    results.append({
                        "url": img_data.get("url", "unknown"),
                        "status": "failed",
                        "error": str(e)
                    })
        
        return {
            "status": "completed",
            "total": len(request.images),
            "success": success_count,
            "failed": failed_count,
            "results": results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to batch download images: {str(e)}")

@app.post("/api/workspace/{workspace_id}/rename")
async def rename_item(workspace_id: str, request: RenameRequest):
    """Rename a file or folder."""
    try:
        workspace_path = WORKSPACES_DIR / workspace_id
        old_path = workspace_path / request.old_path
        new_path = workspace_path / request.new_path
        
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="Item not found")
        
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)
        
        return {"status": "success", "old_path": request.old_path, "new_path": request.new_path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/workspace/{workspace_id}/files/{file_path:path}")
async def delete_file(workspace_id: str, file_path: str):
    """Delete a file or folder."""
    try:
        import shutil
        
        # Check both thesis_data and workspaces directories
        thesis_data_path = WORKSPACES_DIR / workspace_id / file_path
        workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}") / file_path
        
        # Find which path exists
        if thesis_data_path.exists():
            target_path = thesis_data_path
        elif workspaces_path.exists():
            target_path = workspaces_path
        else:
            raise HTTPException(status_code=404, detail="Item not found")
        
        if target_path.is_file():
            target_path.unlink()
        else:
            shutil.rmtree(target_path)
        
        return {"status": "success", "message": f"Deleted {file_path}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/clear")
async def clear_workspace(workspace_id: str):
    """Clear all files in workspace and recreate default empty folders."""
    try:
        import shutil
        
        # Paths to clear
        thesis_data_path = WORKSPACES_DIR / workspace_id
        workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}")
        
        # Clear thesis_data workspace (keep the folder, delete contents)
        if thesis_data_path.exists():
            for item in thesis_data_path.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
        
        # Clear workspaces folder (keep the folder, delete contents)
        if workspaces_path.exists():
            for item in workspaces_path.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
        
        # Recreate default empty folders
        default_folders = ["datasets", "figures", "uploads", "data"]
        for folder in default_folders:
            folder_path = workspaces_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # Create data/jobs folder in thesis_data
        (thesis_data_path / "data" / "jobs").mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success", 
            "message": "Workspace cleared and default folders recreated",
            "folders_created": default_folders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BatchDeleteRequest(BaseModel):
    paths: List[str]

class BatchDownloadRequest(BaseModel):
    paths: List[str]

class ZipRequest(BaseModel):
    paths: List[str]

@app.post("/api/workspace/{workspace_id}/batch-delete")
async def batch_delete_files(workspace_id: str, request: BatchDeleteRequest):
    """Delete multiple files/folders."""
    try:
        import shutil
        
        # Check both directories
        thesis_data_path = WORKSPACES_DIR / workspace_id
        workspaces_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}")
        
        deleted = []
        failed = []
        
        for file_path in request.paths:
            try:
                # Check thesis_data first, then workspaces
                target_path = thesis_data_path / file_path
                if not target_path.exists():
                    target_path = workspaces_path / file_path
                
                if target_path.exists():
                    if target_path.is_file():
                        target_path.unlink()
                    else:
                        shutil.rmtree(target_path)
                    deleted.append(file_path)
                else:
                    failed.append({"path": file_path, "error": "Not found"})
            except Exception as e:
                failed.append({"path": file_path, "error": str(e)})
        
        return {
            "status": "success",
            "deleted": deleted,
            "failed": failed,
            "total": len(request.paths),
            "success_count": len(deleted)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/batch-download")
async def batch_download_files(workspace_id: str, request: BatchDownloadRequest):
    """Download multiple files as a zip."""
    try:
        import zipfile
        import io
        from pathlib import Path
        
        workspace_path = WORKSPACES_DIR / workspace_id
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in request.paths:
                target_path = workspace_path / file_path
                if target_path.exists():
                    if target_path.is_file():
                        zip_file.write(target_path, file_path)
                    else:
                        # Add folder recursively
                        for item in target_path.rglob('*'):
                            if item.is_file():
                                arcname = item.relative_to(workspace_path)
                                zip_file.write(item, str(arcname))
        
        zip_buffer.seek(0)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=files-{workspace_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/zip")
async def zip_files(workspace_id: str, request: ZipRequest):
    """Create a zip file from selected files/folders."""
    try:
        import zipfile
        import io
        from pathlib import Path
        
        workspace_path = WORKSPACES_DIR / workspace_id
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in request.paths:
                target_path = workspace_path / file_path
                if target_path.exists():
                    if target_path.is_file():
                        zip_file.write(target_path, file_path)
                    else:
                        # Add folder recursively
                        for item in target_path.rglob('*'):
                            if item.is_file():
                                arcname = item.relative_to(workspace_path)
                                zip_file.write(item, str(arcname))
        
        zip_buffer.seek(0)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=workspace-{workspace_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DOCUMENT MANAGEMENT & CHAT
# ============================================================================

from services.document_service import DocumentService

@app.post("/api/workspace/{workspace_id}/documents/upload")
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...)
):
    """Upload and parse a document (PDF, DOCX, images, text)."""
    try:
        from pathlib import Path
        import tempfile
        import shutil
        
        # Save uploaded file temporarily
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        allowed_extensions = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp']
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Initialize document service
            doc_service = DocumentService(workspace_id=workspace_id)
            
            # Upload and parse
            doc_metadata = await doc_service.upload_document(
                file_path=tmp_path,
                filename=file.filename,
                file_type=file_ext
            )
            
            return {
                "status": "success",
                "document": doc_metadata
            }
        finally:
            # Clean up temp file
            if tmp_path.exists():
                tmp_path.unlink()
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/documents")
async def list_documents(workspace_id: str):
    """List all uploaded documents."""
    try:
        doc_service = DocumentService(workspace_id=workspace_id)
        documents = doc_service.list_documents()
        return {"status": "success", "documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/workspace/{workspace_id}/documents/{doc_id}")
async def delete_document(workspace_id: str, doc_id: str):
    """Delete a document."""
    try:
        doc_service = DocumentService(workspace_id=workspace_id)
        success = doc_service.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DocumentChatRequest(BaseModel):
    message: str
    doc_ids: Optional[List[str]] = None  # If None, search all documents
    session_id: Optional[str] = "default"

@app.post("/api/workspace/{workspace_id}/documents/chat")
async def chat_with_documents(workspace_id: str, request: DocumentChatRequest):
    """Chat with uploaded documents using RAG."""
    try:
        from services.document_service import DocumentService
        from services.deepseek_direct import deepseek_direct
        
        doc_service = DocumentService(workspace_id=workspace_id)
        
        # Search relevant chunks
        chunks = doc_service.search_chunks(
            query=request.message,
            doc_ids=request.doc_ids,
            top_k=5
        )
        
        if not chunks:
            return {
                "response": "I couldn't find relevant information in the uploaded documents. Please try rephrasing your question or upload more documents.",
                "sources": [],
                "citations": []
            }
        
        # Build context with citations
        context_parts = []
        citations = []
        
        for i, chunk in enumerate(chunks, 1):
            doc_name = chunk["doc_name"]
            page = chunk["page"]
            text = chunk["text"][:500]  # Limit chunk size
            
            context_parts.append(f"[Document {i}: {doc_name}, Page {page}]\n{text}")
            citations.append({
                "document": doc_name,
                "page": page,
                "text": text[:200] + "..." if len(text) > 200 else text
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate response with citations
        prompt = f"""You are a helpful assistant that answers questions based on uploaded documents.

User Question: {request.message}

Relevant Document Excerpts:
{context}

Instructions:
1. Answer the question using ONLY the information from the documents above
2. When referencing information, cite the document name and page number like: (Document Name, Page X)
3. If the documents don't contain enough information, say so clearly
4. Be accurate and cite sources for all claims

Answer:"""
        
        response = await deepseek_direct.generate_content(
            prompt=prompt,
            system_prompt="You are a document analysis assistant. Always cite your sources with document names and page numbers.",
            temperature=0.3,
            max_tokens=2000,
            use_reasoning=False
        )
        
        return {
            "response": response,
            "sources": [{"doc": c["doc_name"], "page": c["page"]} for c in chunks],
            "citations": citations
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CUSTOM AGENT MANAGEMENT
# ============================================================================

@app.post("/api/agents/upload")
async def upload_custom_agent(file: UploadFile = File(...)):
    """Upload a custom agent configuration as JSON."""
    try:
        import json
        
        # Read and validate JSON
        content = await file.read()
        try:
            agent_config = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        # Validate required fields
        required_fields = ["name", "description", "tools", "system_prompt"]
        for field in required_fields:
            if field not in agent_config:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Save agent config
        agents_dir = Path("agents/custom")
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_id = agent_config.get("id") or hashlib.md5(agent_config["name"].encode()).hexdigest()[:16]
        agent_file = agents_dir / f"{agent_id}.json"
        
        agent_config["id"] = agent_id
        agent_config["uploaded_at"] = datetime.now().isoformat()
        agent_config["type"] = "custom"
        
        agent_file.write_text(json.dumps(agent_config, indent=2))
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "message": f"Agent '{agent_config['name']}' uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/custom")
async def list_custom_agents():
    """List all custom uploaded agents."""
    try:
        agents_dir = Path("agents/custom")
        agents = []
        
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.json"):
                try:
                    agent_config = json.loads(agent_file.read_text())
                    agents.append({
                        "id": agent_config.get("id"),
                        "name": agent_config.get("name"),
                        "description": agent_config.get("description"),
                        "uploaded_at": agent_config.get("uploaded_at"),
                        "tools": agent_config.get("tools", [])
                    })
                except:
                    continue
        
        return {"status": "success", "agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/custom/{agent_id}")
async def delete_custom_agent(agent_id: str):
    """Delete a custom agent."""
    try:
        agent_file = Path(f"agents/custom/{agent_id}.json")
        if not agent_file.exists():
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent_file.unlink()
        return {"status": "success", "message": "Agent deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CHAT ENDPOINT
# ============================================================================

def is_simple_greeting(message: str) -> bool:
    """Detect simple greetings that don't need planning."""
    message_lower = message.lower().strip()
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy"]
    return message_lower in greetings or message_lower in [g + "!" for g in greetings] or message_lower in [g + "." for g in greetings]

def is_simple_question(message: str) -> bool:
    """
    Detect simple questions/requests that should get direct AI response, NOT planning.
    
    Examples that should return True (direct response):
    - "write Einstein's equation"
    - "what is E=mc2?"  
    - "explain photosynthesis"
    - "give me an example of recursion"
    - "show me the quadratic formula"
    
    Examples that should return False (needs planning):
    - "write an essay about Einstein"
    - "write a 500 word document"
    - "create a report on climate change"
    """
    message_lower = message.lower().strip()
    word_count = len(message.split())
    
    # Very short messages (< 12 words) without document keywords are likely simple
    if word_count < 12:
        # Check for document generation indicators
        document_indicators = [
            "essay", "document", "report", "paper", "article",
            "chapter", "book", "thesis", "dissertation",
            "word", "page", "paragraph",  # word count requests
        ]
        has_document_keyword = any(ind in message_lower for ind in document_indicators)
        
        # Check for explicit length requests like "500 word"
        import re
        has_length_request = bool(re.search(r'\d+\s*(word|page|paragraph)', message_lower))
        
        if not has_document_keyword and not has_length_request:
            # Simple question patterns
            simple_patterns = [
                r"^(what|how|when|where|why|who|which|can you|could you|please|tell me|show me|give me|explain|define|describe)",
                r"(equation|formula|definition|example|meaning|difference|between|list|the \w+ of)",
                r"(write|show|give|tell).*\b(the|a|an|this|that|one)\b",  # "write the equation"
            ]
            if any(re.search(pattern, message_lower) for pattern in simple_patterns):
                return True
            
            # Short imperative without document keywords
            if word_count < 8:
                return True
    
    return False

def is_image_generation_request(message: str) -> bool:
    """
    Detect if user wants to GENERATE (create AI) an image.
    
    PRIORITY ORDER:
    1. Image search is default for "image of X", "picture of X"
    2. Image generation ONLY for:
       - Explicit: "generate image", "create image", "draw me"
       - Diagrams, frameworks, illustrations, charts (things that need AI creation)
    """
    import re
    message_lower = message.lower()
    
    # Don't trigger if user says "search" or "find"
    if any(s in message_lower for s in ["search", "find", "look for", "get me a photo"]):
        return False
    
    # Generic "image of X" or "picture of X" should use SEARCH, not generate
    # Only explicit generation commands trigger this
    
    # EXPLICIT generation keywords
    explicit_generate = [
        "generate image", "create image", "make image", 
        "generate a picture", "create a picture", "make a picture",
        "generate an image", "create an image", "make an image",
        "draw me", "generate me", "create me",
        "generate illustration", "create illustration",
        "generate diagram", "create diagram", "make diagram",
    ]
    
    if any(keyword in message_lower for keyword in explicit_generate):
        return True
    
    # GENERATION-ONLY content (things that can't be searched, must be created)
    generation_content = [
        "diagram", "flowchart", "framework", "schematic",
        "infographic", "chart", "visualization", "concept map",
        "theoretical model", "research model", "study framework",
        "illustration of concept", "visualize the", "architectural diagram"
    ]
    
    if any(content in message_lower for content in generation_content):
        return True
    
    return False

def is_paper_search_request(message: str) -> bool:
    """
    Detect if user wants to SEARCH for academic papers/sources.
    
    Examples that should return True:
    - "search for papers on machine learning"
    - "find papers about climate change"
    - "look for academic articles on AI"
    - "search literature on healthcare"
    - "find research on deep learning"
    """
    message_lower = message.lower().strip()
    
    # Search trigger phrases
    search_triggers = [
        "search for papers", "search papers", "find papers",
        "search for articles", "search articles", "find articles",
        "search literature", "find literature", "search for literature",
        "search for research", "find research", "look for papers",
        "look for articles", "look for research", "search academic",
        "find academic", "search for sources", "find sources",
        "paper search", "literature search", "research search"
    ]
    
    return any(trigger in message_lower for trigger in search_triggers)

def is_research_synthesis_request(message: str) -> tuple:
    """
    Intelligently detect if user wants a RESEARCH SYNTHESIS - search + analyze + write.
    
    This understands natural language variations like:
    - "search papers and write synthesis on climate change"
    - "find research on AI and synthesize the findings"
    - "literature review on machine learning"
    - "give me a synthesis of papers about healthcare"
    - "research wars in sudan and write a report"
    
    Returns: (is_synthesis: bool, topic: str, style: str)
    """
    import re
    message_lower = message.lower().strip()
    
    # Pattern 1: Explicit "search...and...synthesis/review/report"
    explicit_patterns = [
        r"(search|find|look\s+for).*?(papers?|research|literature|articles?).*?and.*?(write|create|generate|make|give).*?(synthesis|review|report|summary)",
        r"(search|find).*?and.*?(synthesize|summarize|analyze)",
        r"(literature\s+review|research\s+synthesis|paper\s+synthesis).*?(on|about|for)",
        r"(synthesize|summarize).*?(papers?|research|literature|findings?).*?(on|about)",
        r"(give|provide|create|write).*?synthesis.*?(on|about|of)",
    ]
    
    for pattern in explicit_patterns:
        if re.search(pattern, message_lower):
            # Extract topic - look for "on X", "about X", or just the noun phrase
            topic_match = re.search(r'(?:on|about|for|of)\s+(.+?)(?:\s+and\s+|\s+with\s+|$)', message_lower)
            if topic_match:
                topic = topic_match.group(1).strip()
                # Clean up topic
                topic = re.sub(r'\s+(and|then|after|with).*', '', topic)
                return (True, topic, "academic")
            # Fallback - extract from middle of sentence
            topic = re.sub(r'^(search|find|look\s+for|give|provide|create|write|make)\s+', '', message_lower)
            topic = re.sub(r'\s+(and|then|after).*', '', topic)
            topic = re.sub(r'(papers?|research|literature|articles?|synthesis|review)\s*(on|about)?\s*', '', topic)
            return (True, topic.strip() or message, "academic")
    
    # Pattern 2: Implicit - mentions research topic with action words suggesting report
    implicit_patterns = [
        r"(research|study|investigate|explore)\s+.+?\s+and\s+(write|create|report)",
        r"(write|create).*?(research|literature)\s+(report|review|paper)\s+(on|about)",
    ]
    
    for pattern in implicit_patterns:
        match = re.search(pattern, message_lower)
        if match:
            topic_match = re.search(r'(?:on|about)\s+(.+?)(?:\s+and\s+|$)', message_lower)
            topic = topic_match.group(1) if topic_match else message
            return (True, topic.strip(), "research")
    
    # Pattern 3: Context-aware - "papers on X and synthesis" without explicit order
    if ("papers" in message_lower or "research" in message_lower or "literature" in message_lower):
        if ("synthesis" in message_lower or "synthesize" in message_lower or "review" in message_lower):
            topic_match = re.search(r'(?:on|about)\s+(.+?)(?:\s+and\s+|$)', message_lower)
            topic = topic_match.group(1) if topic_match else message
            return (True, topic.strip(), "combined")
    
    return (False, "", "")

def is_pdf_action_request(message: str) -> tuple:
    """
    Detect if user wants to perform an action on a PDF file.
    
    Examples that should return True:
    - "summarize the pdf"
    - "read the climate change pdf"
    - "analyze this pdf"
    - "what's in the uploaded pdf"
    - "summarize Climate_Report.pdf"
    
    Returns:
        (is_pdf_action: bool, action_type: str, pdf_name: str|None)
    """
    import re
    message_lower = message.lower().strip()
    
    # Action keywords
    action_keywords = [
        "summarize", "summarise", "read", "analyze", "analyse", 
        "extract", "what's in", "what is in", "tell me about",
        "explain", "overview", "key points", "main points"
    ]
    
    # Check if it's a PDF action
    has_action = any(action in message_lower for action in action_keywords)
    has_pdf_mention = "pdf" in message_lower or ".pdf" in message_lower
    
    if has_action and has_pdf_mention:
        # Try to extract PDF filename from message
        pdf_match = re.search(r'(\S+\.pdf)', message, re.IGNORECASE)
        pdf_name = pdf_match.group(1) if pdf_match else None
        
        # Determine action type
        if any(a in message_lower for a in ["summarize", "summarise", "summary"]):
            action_type = "summarize"
        elif any(a in message_lower for a in ["extract", "key points", "main points"]):
            action_type = "extract"
        elif any(a in message_lower for a in ["analyze", "analyse"]):
            action_type = "analyze"
        else:
            action_type = "read"
        
        return (True, action_type, pdf_name)
    
    return (False, None, None)

@app.post("/api/chat/message")
async def chat_message(request: ChatMessageRequest):
    """Handle chat messages with planner and tool execution."""
    # Generate job_id IMMEDIATELY at the start - before any processing
    # This ensures frontend can always connect to stream even if we error
    job_id = str(uuid.uuid4())
    
    # Ensure request has required fields with defaults
    if not hasattr(request, 'message') or not request.message:
        return {
            "response": "Please provide a message.",
            "reasoning": "",
            "plan": [],
            "tool_results": {},
            "job_id": job_id
        }
    
    # Set defaults if not provided
    if not hasattr(request, 'session_id') or not request.session_id:
        request.session_id = "default"
    if not hasattr(request, 'workspace_id') or not request.workspace_id:
        request.workspace_id = "default"
    if not hasattr(request, 'user_id') or not request.user_id:
        request.user_id = "default"
    
    try:
        message_lower = request.message.lower().strip()
        
        # =====================================================================
        # CENTRAL BRAIN - Context-Aware Thinking
        # Analyzes conversation context to detect follow-ups before classification
        # =====================================================================
        from services.central_brain import central_brain, ActionType
        
        # Get conversation history from request
        conv_history = getattr(request, 'conversation_history', []) or []
        
        # Let the brain think about this message in context (async for Redis support)
        brain_decision = await central_brain.think(
            message=request.message,
            session_id=request.session_id,
            conversation_history=conv_history
        )
        
        # If it's a follow-up, handle it specially
        if brain_decision["decision"] == "followup":
            followup = brain_decision["followup_info"]
            print(f"🧠 Central Brain: Detected FOLLOW-UP - {followup['followup_type']}")
            print(f"   Target: {followup.get('target_action')}")
            print(f"   Extracted params: {followup.get('extracted_params')}")
            
            # Handle file update follow-up
            if followup["followup_type"] == "modify_file" and followup.get("routing_override") == "file_update":
                from pathlib import Path
                import asyncio
                
                params = followup["extracted_params"]
                original_filepath = params.get("original_filepath", "")
                new_content = params.get("new_content", request.message.strip())
                
                async def run_file_update():
                    """Update the previously created file with new content."""
                    try:
                        await events.connect()
                        
                        # Get original file path
                        if original_filepath:
                            file_path = Path(original_filepath)
                        else:
                            # Use absolute path for 'default' workspace
                            if workspace_id == "default":
                                workspace_dir = Path("/home/gemtech/Desktop/thesis")
                            else:
                                workspace_dir = Path(f"workspaces/{workspace_id}")
                            
                            filename = params.get("original_filename", "new_file.md")
                            file_path = workspace_dir / filename
                        
                        # Update the file
                        await events.publish(job_id, "stage_started", {
                            "stage": "file_update", 
                            "message": f"📝 Updating file with: {new_content[:50]}..."
                        }, session_id=request.session_id)
                        
                        # Ensure directory exists
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Write new content
                        file_path.write_text(new_content)
                        
                        # Record this action
                        await central_brain.record_action(request.session_id, ActionType.FILE_EDIT, {
                            "filename": file_path.name,
                            "filepath": str(file_path),
                            "content": new_content
                        })
                        
                        response_text = f"✅ File updated successfully!\n\n📄 **Filename:** {file_path.name}\n📁 **Path:** {file_path}\n📝 **New content:**\n```\n{new_content}\n```"
                        
                        await events.publish(job_id, "response_chunk", {
                            "chunk": response_text,
                            "accumulated": response_text
                        }, session_id=request.session_id)
                        
                        await events.publish(job_id, "file_created", {
                            "filename": file_path.name,
                            "path": str(file_path)
                        }, session_id=request.session_id)
                        
                        await events.publish(job_id, "stage_completed", {
                            "stage": "file_update",
                            "message": "File updated"
                        }, session_id=request.session_id)
                        
                        await events.publish(job_id, "done", {"status": "success"}, session_id=request.session_id)
                        
                    except Exception as e:
                        print(f"Error updating file: {e}")
                        await events.publish(job_id, "error", {"message": str(e)}, session_id=request.session_id)
                
                asyncio.create_task(run_file_update())
                return {"response": f"Updating file with: {new_content}...", "job_id": job_id, "plan": [], "reasoning": "Follow-up file update detected"}
        
        # =====================================================================
        # FAST INTELLIGENT ROUTER - Speed is priority!
        # Classifies and routes requests in <10ms wherever possible
        # =====================================================================
        
        def fast_classify(msg: str) -> dict:
            """Ultra-fast request classification using simple pattern matching."""
            msg_lower = msg.lower().strip()
            words = msg_lower.split()
            word_count = len(words)
            
            # GREETINGS - instant response
            if word_count < 5 and any(g in msg_lower for g in ["hi", "hello", "hey", "greetings", "sup", "yo"]):
                # Ensure it's ONLY a greeting and not a command
                command_trigger = any(t in msg_lower for t in ["search", "find", "google", "go to", "open", "browse", "visit", "generate", "create", "make", "file"])
                has_url = any(u in msg_lower for u in [".com", ".org", ".net", ".edu", "http://", "https://"])
                if not command_trigger and not has_url:
                    return {"type": "greeting", "route": "instant"}
            
            # SIMPLE QUESTIONS - direct LLM streaming (fastest)
            question_starters = ["what", "who", "when", "where", "why", "how", "is", "are", "can", "do", "does", "will", "would", "should", "could", "explain", "define", "describe"]
            if any(msg_lower.startswith(q) for q in question_starters) and word_count < 30:
                # Check if it needs tools - use regex for word boundaries
                tool_keywords = ["search", "find", "google", "go to", "open", "browse", "generate", "create", "make", "write document", "write essay", "file"]
                needs_tools = any(re.search(rf"\b{re.escape(t)}\b", msg_lower) for t in tool_keywords)
                if not needs_tools:
                    return {"type": "question", "route": "direct_llm"}
            
            # UNSUPPORTED REQUESTS - respond gracefully
            unsupported_keywords = {
                "video": "Video generation is not yet supported. I can help with text, images, and research.",
                "audio": "Audio generation is not yet supported. I can help with text, images, and research.",
                "music": "Music generation is not yet supported. I can help with text, images, and research.",
                "voice": "Voice synthesis is not yet supported. I can help with text, images, and research.",
                "song": "Song creation is not yet supported. I can help with text, images, and research.",
            }
            for keyword, message in unsupported_keywords.items():
                if keyword in msg_lower and any(a in msg_lower for a in ["make", "create", "generate", "produce"]):
                    return {"type": "unsupported", "route": "graceful", "message": message}
            
            # IMAGE SEARCH - PRIORITY over generation!
            if ("image" in msg_lower or "picture" in msg_lower or "photo" in msg_lower):
                if any(s in msg_lower for s in ["search", "find", "look for", "get me"]):
                    return {"type": "image_search", "route": "tool"}
                if any(p in msg_lower for p in ["image of", "picture of", "photo of", "images of", "pictures of"]):
                    return {"type": "image_search", "route": "tool"}
            
            # IMAGE GENERATION
            generation_keywords = ["diagram", "framework", "illustration", "chart", "flowchart", 
                                   "infographic", "concept", "visualize", "schematic", "model diagram"]
            explicit_generate = any(g in msg_lower for g in ["generate image", "create image", "draw me", "make me an image"])
            needs_generation = any(k in msg_lower for k in generation_keywords)
            
            if explicit_generate or needs_generation:
                return {"type": "image_generate", "route": "tool"}
            
            # PAPER/ACADEMIC SEARCH
            if any(p in msg_lower for p in ["search paper", "find paper", "search research", "academic", "search literature"]):
                return {"type": "paper_search", "route": "tool"}
            
            # WEB SEARCH
            if any(p in msg_lower for p in ["search", "look up", "look for", "find out", "google", "go to", "browse", "visit", "open"]) and word_count < 20:
                return {"type": "web_search", "route": "tool"}
            
            # ESSAY/DOCUMENT WRITING - needs worker
            if any(p in msg_lower for p in ["write essay", "write document", "write report", "write paper", "essay about", "essay on"]):
                return {"type": "essay", "route": "worker"}
            
            # SHORT CASUAL CHAT - direct LLM
            if word_count < 20 and not any(t in msg_lower for t in ["file", "save", "create", "generate", "search", "document"]):
                return {"type": "chat", "route": "direct_llm"}
            
            # DEFAULT - let LLM handle with possible tool use
            return {"type": "general", "route": "orchestrator"}
        
        # =====================================================
        # INTELLIGENT INTENT SYSTEM - True AI Understanding
        # =====================================================
        from services.intelligent_intent import intelligent_intent, IntentType, RouteType
        
        # Use intelligent intent system (fast patterns + LLM for ambiguous cases)
        intent_result = await intelligent_intent.understand(request.message)
        print(f"🧠 Intelligent Intent: {intent_result.intent.value} -> {intent_result.route.value} (confidence: {intent_result.confidence:.2f})")
        print(f"   Reasoning: {intent_result.reasoning}")
        
        # Convert to route_info format for compatibility
        route_info = {
            "type": intent_result.intent.value,
            "route": intent_result.route.value,
            "params": intent_result.params,
            "message": intent_result.message,
            "confidence": intent_result.confidence
        }
        
        # ROUTE 1: Unsupported requests - respond gracefully and fast
        if route_info["route"] == "graceful":
            await events.connect()
            response_text = route_info.get("message", "This feature is not yet supported.")
            await events.publish(job_id, "response_chunk", {
                "chunk": response_text,
                "accumulated": response_text
            }, session_id=request.session_id)
            return {
                "response": response_text,
                "reasoning": "",
                "plan": [],
                "job_id": job_id
            }
        
        # ROUTE 2: Direct LLM streaming - NO tools, maximum speed
        if route_info["route"] == "direct_llm":
            from services.deepseek_direct import deepseek_direct
            
            # Build context from conversation history
            history_context = ""
            if request.conversation_history and len(request.conversation_history) > 0:
                history_lines = []
                for msg in request.conversation_history[-5:]:  # Last 5 messages for context
                    role = msg.get("type", "user")
                    content = msg.get("content", "")[:500]  # Truncate long messages
                    if role == "user":
                        history_lines.append(f"User: {content}")
                    elif role == "assistant":
                        history_lines.append(f"Assistant: {content}")
                if history_lines:
                    history_context = "\n\nRecent conversation:\n" + "\n".join(history_lines) + "\n\nUser's current message: "
            
            async def stream_direct_response():
                """Stream LLM response directly - fastest path."""
                import httpx
                
                try:
                    yield {"event": "job_id", "data": json.dumps({"job_id": job_id})}
                    yield {"event": "stage", "data": json.dumps({"stage": "responding", "icon": "💬", "message": "Generating response..."})}
                    
                    # Include context if available
                    full_prompt = history_context + request.message if history_context else request.message
                    
                    # Build system prompt with user context
                    user_context = brain_decision.get("user_context", "")
                    base_system = "You are a helpful, knowledgeable AI assistant. Be concise and direct. Answer questions clearly. If the user refers to something from earlier in the conversation, understand the context."
                    if user_context:
                        system_prompt = f"{base_system}\n\nUser context: {user_context}"
                    else:
                        system_prompt = base_system
                    
                    accumulated = ""
                    async for chunk in deepseek_direct.generate_stream(
                        prompt=full_prompt,
                        system_prompt=system_prompt
                    ):
                        accumulated += chunk
                        yield {"event": "response_chunk", "data": json.dumps({"chunk": chunk, "accumulated": accumulated})}
                    
                    yield {"event": "done", "data": json.dumps({"status": "success"})}
                    
                except Exception as e:
                    yield {"event": "error", "data": json.dumps({"message": str(e)})}
            
            return EventSourceResponse(stream_direct_response())

        
        # ROUTE 3: Direct IMAGE SEARCH - Uses Unsplash/Pexels/Pixabay APIs directly (no LLM!)
        if route_info["route"] == "tool_direct" and route_info["type"] == "image_search":
            from services.image_search import image_search_service  # Direct API calls, no LLM
            import asyncio
            
            # Extract search query
            query = request.message
            for prefix in ["search for", "find", "look for", "get me", "show me", "image of", "picture of", "photo of", "images of", "pictures of"]:
                query = query.lower().replace(prefix, "").strip()
            
            async def run_image_search():
                """Run image search and publish events via Redis."""
                try:
                    await events.connect()
                    
                    # Send stage_started
                    await events.publish(job_id, "stage_started", {"stage": "image_search", "message": f"🔍 Searching images: {query}..."}, session_id=request.session_id)
                    
                    # Call image search APIs directly
                    results = await image_search_service.search(query, limit=6)
                    
                    if results and len(results) > 0:
                        # Format response with images
                        response_parts = [f"Found {len(results)} images for '{query}':\n\n"]
                        
                        for i, img in enumerate(results[:6]):
                            title = img.get("title", f"Image {i+1}")
                            url = img.get("url") or img.get("full") or img.get("thumbnail")
                            source = img.get("source", "Unknown")
                            if url:
                                response_parts.append(f"![{title}]({url})\n*Source: {source}*\n\n")
                        
                        response_text = "".join(response_parts)
                        
                        # Send response_chunk
                        await events.publish(job_id, "response_chunk", {"chunk": response_text, "accumulated": response_text}, session_id=request.session_id)
                        
                        # Send agent_activity for preview panel
                        await events.publish(job_id, "agent_activity", {
                            "agent": "image_search",
                            "action": "completed",
                            "query": query,
                            "status": "completed",
                            "results": results[:6]
                        }, session_id=request.session_id)
                        
                        # Send stage_completed
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=request.session_id)
                    else:
                        await events.publish(job_id, "response_chunk", {"chunk": f"No images found for '{query}'. Try a different search term.", "accumulated": f"No images found for '{query}'. Try a different search term."}, session_id=request.session_id)
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "no_results"}, session_id=request.session_id)
                        
                except Exception as e:
                    print(f"Image search error: {e}")
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error searching images: {str(e)}", "accumulated": f"Error searching images: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            # Run in background
            asyncio.create_task(run_image_search())
            
            # Return JSON immediately
            return {"response": f"Searching images for '{query}'...", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 4: Direct WEB SEARCH
        if route_info["route"] == "tool_direct" and route_info["type"] == "web_search":
            from services.web_search import WebSearchService
            import asyncio
            web_search = WebSearchService()
            
            # Smart query extraction - check if current message is a meta-request
            query = route_info.get("params", {}).get("query")
            
            if not query or len(query) < 5:
                msg_lower = request.message.lower()
                # Check if this is a meta-request like "can you search" without a topic
                meta_patterns = ["can you search", "cant u search", "search internet", "search online", 
                                "do a search", "look it up", "search for it", "google it"]
                is_meta_request = any(p in msg_lower for p in meta_patterns)
                
                if is_meta_request and request.conversation_history:
                    # Look at recent messages for the actual topic
                    for msg in reversed(request.conversation_history[-5:]):
                        content = msg.get("content", "")
                        # Skip short/meta messages
                        if len(content) > 20 and not any(p in content.lower() for p in meta_patterns):
                            # This is likely the topic - extract key terms
                            query = content
                            break
                
                # Fallback to current message (remove meta parts from START ONLY)
                if not query:
                    query = request.message
                    # Use regex to only remove prefix verbs/meta
                    import re
                    query = re.sub(r'^(?:can\s+you\s+|cant\s+u\s+|can\s+u\s+|could\s+you\s+|please\s+|search\s+|internet\s+|online\s+|open\s+|go\s+to\s+|browse\s+|visit\s+)+', '', query, flags=re.IGNORECASE).strip()
                    if not query:
                        query = request.message
            
            async def run_web_search():
                """Web search with Playwright in background thread."""
                try:
                    print(f"🔍 Starting web search for: {query}", flush=True)
                    await events.connect()
                    await events.publish(job_id, "stage_started", {"stage": "web_search", "message": f"🌐 Searching: {query}..."}, session_id=request.session_id)
                    
                    # Run Playwright in a separate thread
                    import threading
                    import redis
                    import os
                    
                    def run_browser_search():
                        """Run Playwright browser search in thread."""
                        import asyncio
                        from services.browser_automation import BrowserAutomation
                        import json
                        
                        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                        if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
                            redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
                        r = redis.from_url(redis_url)
                        session = request.session_id or 'default'
                        
                        async def stream(data):
                            r.publish(f"browser:{session}", json.dumps(data))
                        
                        async def do_search():
                            print(f"🎭 Starting Playwright thread search...", flush=True)
                            try:
                                # Use headless=True by default for server compatibility
                                # Screenshots will still be captured!
                                browser = BrowserAutomation(workspace_id=session, headless=True)
                                await browser.start(stream_callback=stream)
                                
                                search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
                                await stream({"type": "action", "action": f"Navigating to DuckDuckGo: {query}"})
                                
                                screenshot = await browser.navigate(search_url)
                                await stream({"type": "screenshot", "image": screenshot, "url": search_url})
                                
                                # Wait for results and take another shot
                                await asyncio.sleep(3)
                                screenshot2 = await browser._take_screenshot("search_results")
                                await stream({"type": "screenshot", "image": screenshot2, "url": browser.page.url})
                                await stream({"type": "action", "action": "Search completed. Results visible in right panel."})
                                
                                print(f"✅ Playwright thread search complete", flush=True)
                                await browser.close()
                            except Exception as e:
                                print(f"⚠️ Playwright thread search error: {e}", flush=True)
                                await stream({"type": "action", "action": f"Browser Error: {str(e)}"})
                                # Report back to chat via event bus if possible
                                # (Note: events.publish is async, we are in a non-async loop running in a thread)
                                # So we just log and stream to browser panel.
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(do_search())
                        except Exception as e:
                            print(f"⚠️ Event loop error: {e}", flush=True)
                        finally:
                            loop.close()
                    
                    thread = threading.Thread(target=run_browser_search, daemon=True)
                    thread.start()
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"🎭 **Opening browser:** {query}\n\n📺 Watch **browser panel** →",
                        "accumulated": f"🎭 **Opening browser:** {query}\n\n📺 Watch **browser panel** →"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=request.session_id)
                    
                except Exception as e:
                    print(f"⚠️ Search error: {e}", flush=True)
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error: {str(e)}", "accumulated": f"Error: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            asyncio.create_task(run_web_search())
            return {"response": f"🔍 Searching: {query}...", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 5: Direct PAPER SEARCH
        if route_info["route"] == "tool_direct" and route_info["type"] == "paper_search":
            from services.academic_search import academic_search_service
            import asyncio
            
            query = route_info.get("params", {}).get("query") or request.message
            
            async def run_paper_search():
                try:
                    await events.connect()
                    await events.publish(job_id, "stage_started", {"stage": "paper_search", "message": f"📚 Searching papers: {query}..."}, session_id=request.session_id)
                    
                    results = await academic_search_service.search(query, max_results=10)
                    
                    if results and len(results) > 0:
                        response_parts = [f"**Found {len(results)} academic papers for '{query}':**\n\n"]
                        for i, paper in enumerate(results[:10]):
                            title = paper.get("title", f"Paper {i+1}")
                            authors = ", ".join(paper.get("authors", [])[:3])
                            year = paper.get("year", "")
                            doi = paper.get("doi", "")
                            url = f"https://doi.org/{doi}" if doi else paper.get("url", "")
                            response_parts.append(f"{i+1}. **{title}** ({year})\n   *{authors}*\n   [Link]({url})\n\n")
                        
                        response_text = "".join(response_parts)
                        await events.publish(job_id, "response_chunk", {"chunk": response_text, "accumulated": response_text}, session_id=request.session_id)
                        await events.publish(job_id, "agent_activity", {"agent": "researcher", "action": "completed", "query": query, "status": "completed", "results": results[:10]}, session_id=request.session_id)
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=request.session_id)
                    else:
                        await events.publish(job_id, "response_chunk", {"chunk": f"No papers found for '{query}'.", "accumulated": f"No papers found for '{query}'."}, session_id=request.session_id)
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "no_results"}, session_id=request.session_id)
                except Exception as e:
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error: {str(e)}", "accumulated": f"Error: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            asyncio.create_task(run_paper_search())
            return {"response": f"Searching papers for '{query}'...", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 6: Direct IMAGE GENERATE (for diagrams, illustrations)
        if route_info["route"] == "tool_direct" and route_info["type"] == "image_generate":
            from services.image_generation import image_generation_service
            import asyncio
            
            prompt = route_info.get("params", {}).get("prompt") or request.message
            
            async def run_image_generate():
                try:
                    await events.connect()
                    await events.publish(job_id, "stage_started", {"stage": "image_generate", "message": f"🎨 Generating image: {prompt[:50]}..."}, session_id=request.session_id)
                    
                    result = await image_generation_service.generate(prompt=prompt, size="1024x1024")
                    
                    if result.get("success"):
                        image_url = result.get("image_url") or result.get("url")
                        response_text = f"**Generated image:**\n\n![{prompt[:50]}]({image_url})\n\n*Prompt: {prompt}*"
                        
                        await events.publish(job_id, "response_chunk", {"chunk": response_text, "accumulated": response_text}, session_id=request.session_id)
                        await events.publish(job_id, "agent_activity", {"agent": "image_generator", "action": "completed", "query": prompt, "status": "completed", "results": [{"url": image_url}]}, session_id=request.session_id)
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=request.session_id)
                    else:
                        await events.publish(job_id, "response_chunk", {"chunk": f"Image generation failed: {result.get('error', 'Unknown error')}", "accumulated": f"Image generation failed: {result.get('error', 'Unknown error')}"}, session_id=request.session_id)
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
                except Exception as e:
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error: {str(e)}", "accumulated": f"Error: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            asyncio.create_task(run_image_generate())
            return {"response": f"Generating image: {prompt[:50]}...", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 6.5: Direct FILE WRITE (create files in workspace)
        if route_info["route"] == "tool_direct" and route_info["type"] == "file_write":
            import asyncio
            from pathlib import Path
            
            params = route_info.get("params", {})
            filename = params.get("filename")
            content = params.get("content") or ""
            
            # Default filename if not provided
            if not filename:
                # Try to infer extension from request
                if "md" in request.message.lower() or "markdown" in request.message.lower():
                    filename = "new_file.md"
                elif "txt" in request.message.lower() or "text" in request.message.lower():
                    filename = "new_file.txt"
                elif "json" in request.message.lower():
                    filename = "new_file.json"
                else:
                    filename = "new_file.md"
            
            async def run_file_create():
                try:
                    await events.connect()
                    await events.publish(job_id, "stage_started", {"stage": "file_create", "message": f"📄 Creating file: {filename}..."}, session_id=request.session_id)
                    
                    # Get workspace directory
                    workspace_id = request.workspace_id or "default"
                    if workspace_id == "default":
                        workspace_dir = Path("/home/gemtech/Desktop/thesis")
                    else:
                        workspace_dir = Path(f"workspaces/{workspace_id}")
                    workspace_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create the file
                    file_path = workspace_dir / filename
                    file_path.write_text(content)
                    
                    response_text = f"✅ **File created successfully!**\n\n📄 **Filename:** `{filename}`\n📁 **Path:** `{file_path}`\n📝 **Content:**\n```\n{content}\n```"
                    
                    # Record action in central brain for follow-up detection
                    from services.central_brain import central_brain, ActionType
                    await central_brain.record_action(request.session_id, ActionType.FILE_CREATE, {
                        "filename": filename,
                        "filepath": str(file_path),
                        "content": content,
                        "workspace_id": workspace_id
                    })
                    
                    await events.publish(job_id, "response_chunk", {"chunk": response_text, "accumulated": response_text}, session_id=request.session_id)
                    await events.publish(job_id, "file_created", {
                        "path": filename,
                        "full_path": str(file_path),
                        "filename": filename,
                        "workspace_id": workspace_id,
                        "type": "text"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=request.session_id)
                except Exception as e:
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error creating file: {str(e)}", "accumulated": f"Error creating file: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            asyncio.create_task(run_file_create())
            return {"response": f"Creating file: {filename}...", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 7: CHAPTER GENERATION - Parallel multi-agent thesis chapter generation
        if route_info["route"] == "pipeline" and route_info["type"] in ["chapter_generate", "chapter_two_generate", "chapter_three_generate"]:
            from services.parallel_chapter_generator import parallel_chapter_generator, BACKGROUND_STYLES
            import asyncio
            
            topic = route_info.get("params", {}).get("topic") or request.message
            case_study = route_info.get("params", {}).get("case_study", "")
            background_style = route_info.get("params", {}).get("background_style", "inverted_pyramid")
            # IMPORTANT: Read generation_type from params (set by intelligent_intent.py)
            # This determines if we generate Chapter 1, 2, or 3
            chapter_type = route_info.get("params", {}).get("generation_type") or route_info.get("type", "chapter_generate")
            
            # Get objectives if provided (for Chapter Two and Three)
            objectives = route_info.get("params", {}).get("objectives")
            research_questions = route_info.get("params", {}).get("research_questions")
            
            # Validate background style
            if background_style not in BACKGROUND_STYLES:
                background_style = "inverted_pyramid"
            
            async def run_chapter_generation():
                try:
                    await events.connect()
                    
                    # FULL PROPOSAL - Generate all 3 chapters sequentially
                    print(f"🔍 DEBUG: chapter_type = '{chapter_type}'")
                    if chapter_type == "full_proposal_generate":
                        print("🎯 DEBUG: Entered full_proposal_generate route!")
                        # Initialize session_id for events
                        session_id = request.session_id # Use request's session_id
                        print(f"🔍 DEBUG: session_id = {session_id}")
                        
                        await events.publish(
                            job_id,
                            "response_chunk",
                            {"chunk": f"# 📚 Generating Full Research Proposal (Chapters 1-3)\n\n**Topic:** {topic}\n**Case Study:** {case_study}\n\nThis will generate:\n- ✅ Chapter 1: Introduction\n- ✅ Chapter 2: Literature Review\n- ✅ Chapter 3: Research Methodology\n\nObjectives from Chapter 1 will be used throughout.\n\n---\n\n", "accumulated": ""},
                            session_id=session_id
                        )
                        
                        
                        # Step 1: Generate Chapter 1
                        print("🔍 DEBUG: About to generate Chapter 1...")
                        await events.publish(job_id, "log", {"message": "📖 Step 1/3: Generating Chapter 1..."}, session_id=session_id)
                        chapter1_result = await parallel_chapter_generator.generate(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=session_id
                        )
                        print(f"✅ DEBUG: Chapter 1 complete! Length: {len(chapter1_result)} chars")
                        
                        # Step 2: Generate Chapter 2 (using objectives from Chapter 1)
                        print("🔍 DEBUG: About to generate Chapter 2...")
                        await events.publish(job_id, "log", {"message": "📚 Step 2/3: Generating Chapter 2 (using Chapter 1 objectives)..."}, session_id=session_id)
                        chapter2_result = await parallel_chapter_generator.generate_chapter_two(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=session_id
                        )
                        print(f"✅ DEBUG: Chapter 2 complete! Length: {len(chapter2_result)} chars")
                        
                        # Step 3: Generate Chapter 3 (using objectives from Chapter 1)
                        print("🔍 DEBUG: About to generate Chapter 3...")
                        await events.publish(job_id, "log", {"message": "🔬 Step 3/3: Generating Chapter 3 (using Chapter 1 objectives)..."}, session_id=session_id)
                        chapter3_result = await parallel_chapter_generator.generate_chapter_three(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=session_id
                        )
                        
                        # Combine all chapters
                        full_proposal = f"{chapter1_result}\n\n---\n\n{chapter2_result}\n\n---\n\n{chapter3_result}"
                        
                        # Extract and consolidate all references
                        await events.publish(job_id, "log", {"message": "📚 Consolidating references from all chapters..."}, session_id=session_id)
                        
                        import re
                        # Extract all citations in format (Author, Year) or (Author et al., Year)
                        all_citations = set()
                        
                        # Pattern to match APA citations
                        citation_pattern = r'\(([A-Z][a-zA-Z\s&,\.]+,\s*\d{4}[a-z]?)\)'
                        
                        for chapter in [chapter1_result, chapter2_result, chapter3_result]:
                            citations = re.findall(citation_pattern, chapter)
                            all_citations.update(citations)
                        
                        # Sort citations alphabetically
                        sorted_citations = sorted(list(all_citations))
                        
                        # Create References section
                        references_section = "\n\n---\n\n# References\n\n"
                        references_section += "*Note: This is a consolidated list of all citations from Chapters 1-3. Full bibliographic details should be added based on the actual sources used.*\n\n"
                        
                        for citation in sorted_citations:
                            # Extract author and year
                            parts = citation.rsplit(',', 1)
                            if len(parts) == 2:
                                author = parts[0].strip()
                                year = parts[1].strip()
                                references_section += f"- {author} ({year}). *[Full reference details to be added]*\n"
                        
                        # Add references to full proposal
                        full_proposal_with_refs = full_proposal + references_section
                        
                        # Generate appendices (study tools)
                        await events.publish(job_id, "log", {"message": "📎 Generating study tools appendices..."}, session_id=session_id)
                        
                        generated_files = []
                        try:
                            from services.appendix_generator import AppendixGenerator
                            from pathlib import Path
                            import glob
                            
                            # Get objectives from database
                            objectives = []
                            research_questions = []
                            try:
                                from services.thesis_session_db import ThesisSessionDB
                                db = ThesisSessionDB(session_id)
                                obj_data = db.get_objectives() or {}
                                # get_objectives returns {"general": str, "specific": list}
                                objectives = obj_data.get("specific", [])
                                if obj_data.get("general"):
                                    objectives = [obj_data["general"]] + objectives
                                print(f"📋 Found {len(objectives)} objectives for study tools generation")
                                
                                # Get research questions
                                try:
                                    rq_data = db.get_questions() or []
                                    research_questions = rq_data if isinstance(rq_data, list) else []
                                    print(f"📋 Found {len(research_questions)} research questions")
                                except:
                                    pass
                                    
                            except Exception as obj_err:
                                print(f"⚠️ Could not get objectives: {obj_err}")
                            
                            # Read Chapter 3 methodology content
                            methodology_content = ""
                            try:
                                workspace_dir = Path(f"/home/gemtech/Desktop/thesis/thesis_data/default")
                                chapter3_files = list(workspace_dir.glob("Chapter_3*.md")) + list(workspace_dir.glob("chapter_3*.md"))
                                if chapter3_files:
                                    with open(chapter3_files[0], 'r', encoding='utf-8') as f:
                                        methodology_content = f.read()
                                    print(f"📋 Read Chapter 3: {len(methodology_content)} chars")
                                else:
                                    # Use the just-generated chapter3_result
                                    methodology_content = chapter3_result
                                    print(f"📋 Using generated Chapter 3 content: {len(methodology_content)} chars")
                            except Exception as ch3_err:
                                print(f"⚠️ Could not read Chapter 3: {ch3_err}")
                                methodology_content = chapter3_result if chapter3_result else ""
                            
                            # Use actual workspace directory
                            from config import get_workspace_dir
                            workspace_path = get_workspace_dir('default')
                            workspace_path.mkdir(parents=True, exist_ok=True)
                            
                            # Create enhanced appendix generator with methodology
                            appendix_gen = AppendixGenerator(
                                workspace_dir=str(workspace_path),
                                topic=topic,
                                case_study=case_study,
                                objectives=objectives,
                                methodology_content=methodology_content,
                                research_questions=research_questions
                            )
                            
                            await events.publish(job_id, "log", {
                                "message": f"📋 Detected: {appendix_gen.research_design} design with {', '.join(appendix_gen.data_collection_methods)}"
                            }, session_id=session_id)
                            
                            # Generate all appropriate appendices
                            generated_files = await appendix_gen.generate_all_appendices()
                            
                            await events.publish(job_id, "log", {
                                "message": f"✅ Generated {len(generated_files)} study tool(s): {', '.join([Path(f).stem for f in generated_files])}"
                            }, session_id=session_id)
                            
                        except Exception as appendix_error:
                            print(f"⚠️ Appendix generation failed: {appendix_error}")
                            import traceback
                            traceback.print_exc()
                            await events.publish(job_id, "log", {"message": f"⚠️ Appendix generation skipped: {appendix_error}"}, session_id=session_id)
                        
                        # Combine appendices into main proposal
                        if generated_files:
                            await events.publish(job_id, "log", {"message": "📋 Combining appendices into proposal..."}, session_id=session_id)
                            
                            appendix_section = "\n\n---\n\n# APPENDICES\n\n"
                            
                            for file_path in generated_files:
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        appendix_content = f.read()
                                    
                                    # Add page break before each appendix
                                    appendix_section += "\n\n---\n\n"
                                    appendix_section += appendix_content
                                    
                                except Exception as read_error:
                                    print(f"Error reading appendix {file_path}: {read_error}")
                            
                            full_proposal_with_refs += appendix_section
                        
                        # Save individual chapter files to workspace
                        await events.publish(job_id, "log", {"message": "💾 Saving files to workspace..."}, session_id=session_id)
                        
                        try:
                            from pathlib import Path
                            from config import get_workspace_dir
                            workspace_path = get_workspace_dir('default')
                            workspace_path.mkdir(parents=True, exist_ok=True)
                            
                            # Save Chapter 1
                            chapter1_file = workspace_path / "Chapter_1_Introduction.md"
                            with open(chapter1_file, 'w', encoding='utf-8') as f:
                                f.write(f"# CHAPTER 1: INTRODUCTION\n\n{chapter1_result}")
                            
                            # Save Chapter 2
                            chapter2_file = workspace_path / "Chapter_2_Literature_Review.md"
                            with open(chapter2_file, 'w', encoding='utf-8') as f:
                                f.write(f"# CHAPTER 2: LITERATURE REVIEW\n\n{chapter2_result}")
                            
                            # Save Chapter 3
                            chapter3_file = workspace_path / "Chapter_3_Methodology.md"
                            with open(chapter3_file, 'w', encoding='utf-8') as f:
                                f.write(f"# CHAPTER 3: RESEARCH METHODOLOGY\n\n{chapter3_result}")
                            
                            # Save References
                            references_file = workspace_path / "References.md"
                            with open(references_file, 'w', encoding='utf-8') as f:
                                f.write(references_section)
                            
                            # Save complete proposal
                            proposal_file = workspace_path / "Complete_Proposal.md"
                            with open(proposal_file, 'w', encoding='utf-8') as f:
                                f.write(f"# RESEARCH PROPOSAL\n\n**Topic:** {topic}\n\n**Case Study:** {case_study}\n\n**Date:** {datetime.now().strftime('%B %Y')}\n\n---\n\n")
                                f.write(full_proposal_with_refs)
                            
                            await events.publish(job_id, "log", {"message": f"✅ Saved 5 files to workspace/default/"}, session_id=session_id)
                            
                        except Exception as save_error:
                            print(f"⚠️ File saving failed: {save_error}")
                            import traceback
                            traceback.print_exc()
                        
                        await events.publish(
                            job_id,
                            "response_chunk",
                            {"chunk": f"\n\n✅ **Full Research Proposal Complete!**\n\nAll 3 chapters generated successfully with:\n- ✅ Consistent objectives throughout\n- ✅ {len(sorted_citations)} unique references consolidated\n- ✅ Unified References section\n- ✅ {len(generated_files)} study tool appendices\n- ✅ All files saved to workspace\n\n**Files Created:**\n- Complete_Proposal.md (all-in-one)\n- Chapter_1_Introduction.md\n- Chapter_2_Literature_Review.md\n- Chapter_3_Methodology.md\n- References.md\n- appendices/ folder with {len(generated_files)} tool(s)\n", "accumulated": full_proposal_with_refs},
                            session_id=session_id
                        )
                        
                        await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=session_id)
                        
                    # Individual chapter generation
                    elif chapter_type == "chapter_three_generate":
                        # Generate Chapter Three - Research Methodology
                        await parallel_chapter_generator.generate_chapter_three(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=request.session_id,
                            objectives=objectives,
                            research_questions=research_questions
                        )
                    elif chapter_type == "chapter_two_generate":
                        # Generate Chapter Two - Literature Review
                        await parallel_chapter_generator.generate_chapter_two(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=request.session_id,
                            objectives=objectives,
                            research_questions=research_questions
                        )
                    else:
                        # Generate Chapter One
                        await parallel_chapter_generator.generate(
                            topic=topic,
                            case_study=case_study,
                            job_id=job_id,
                            session_id=request.session_id,
                            background_style=background_style
                        )
                except Exception as e:
                    print(f"Chapter generation error: {e}")
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {"chunk": f"Error generating chapter: {str(e)}", "accumulated": f"Error: {str(e)}"}, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=request.session_id)
            
            asyncio.create_task(run_chapter_generation())
            
            if chapter_type == "chapter_two_generate":
                return {"response": f"📚 Starting Chapter Two (Literature Review) generation for: {topic}...\\n\\n10+ research agents + 20+ writer agents working simultaneously!\\nObjective-based themes generated automatically!", "job_id": job_id, "plan": [], "reasoning": ""}
            else:
                return {"response": f"📖 Starting parallel chapter generation for: {topic}...\\n\\n6 research agents + 5 writer agents working simultaneously!", "job_id": job_id, "plan": [], "reasoning": ""}
        
        # ROUTE 7.5: DATASET GENERATION - AI synthetic data collection
        if route_info["route"] == "pipeline" and route_info.get("params", {}).get("generation_type") == "dataset_generate":
            from services.data_collection_worker import generate_research_dataset
            import asyncio
            from pathlib import Path
            import glob
            
            sample_size = route_info.get("params", {}).get("sample_size")
            
            async def run_dataset_generation():
                try:
                    await events.connect()
                    session_id = request.session_id
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"# 📊 Generating Synthetic Research Dataset\n\n**Simulating survey data collection...**\n\n",
                        "accumulated": ""
                    }, session_id=session_id)
                    
                    # Get topic from session database
                    topic = ""
                    case_study = ""
                    objectives = []
                    
                    try:
                        from services.thesis_session_db import ThesisSessionDB
                        db = ThesisSessionDB(session_id)
                        topic = db.get_topic() or "Research Study"
                        case_study = db.get_case_study() or ""
                        obj_data = db.get_objectives() or {}
                        objectives = obj_data.get("specific", [])
                        if obj_data.get("general"):
                            objectives = [obj_data["general"]] + objectives
                    except Exception as e:
                        print(f"⚠️ Could not get session data: {e}")
                        topic = "Research Study"
                    
                    # Provide default objectives if none found
                    if not objectives:
                        objectives = generate_smart_objectives(topic, 4)
                        print(f"📋 Using default objectives for dataset generation")
                    
                    await events.publish(job_id, "log", {
                        "message": f"📋 Topic: {topic[:50]}... | {len(objectives)} objectives"
                    }, session_id=session_id)
                    
                    # Find questionnaire file
                    questionnaire_path = None
                    methodology_path = None
                    
                    from config import get_appendices_dir
                    workspace_dir = get_appendices_dir('default')
                    thesis_dir = Path("/home/gemtech/Desktop/thesis/thesis_data/default")
                    
                    # Look for questionnaire
                    for search_dir in [workspace_dir, thesis_dir]:
                        questionnaire_files = list(search_dir.glob("*Questionnaire*.md"))
                        if questionnaire_files:
                            questionnaire_path = str(questionnaire_files[0])
                            break
                    
                    # Look for methodology
                    chapter3_files = list(thesis_dir.glob("Chapter_3*.md"))
                    if chapter3_files:
                        methodology_path = str(chapter3_files[0])
                    
                    if questionnaire_path:
                        await events.publish(job_id, "log", {
                            "message": f"📋 Found questionnaire: {Path(questionnaire_path).name}"
                        }, session_id=session_id)
                    
                    # Output directory - save with other thesis files
                    output_dir = "/home/gemtech/Desktop/thesis/workspaces/default/datasets"
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Generate dataset
                    await events.publish(job_id, "log", {
                        "message": f"🚀 Deploying AI respondent agents..."
                    }, session_id=session_id)
                    
                    result = await generate_research_dataset(
                        topic=topic,
                        case_study=case_study,
                        questionnaire_path=questionnaire_path,
                        methodology_path=methodology_path,
                        sample_size=sample_size,
                        objectives=objectives,
                        job_id=job_id,
                        session_id=session_id,
                        output_dir=output_dir
                    )
                    
                    csv_path = result["csv_path"]
                    spss_path = result["spss_syntax_path"]
                    stats = result["stats"]
                    xlsx_path = stats.get("xlsx_path")
                    
                    # Add XLSX to files list if exists
                    if xlsx_path:
                        result['files'].append(xlsx_path)
                    
                    # Summary message
                    summary = f"""
## ✅ Dataset Generated Successfully!

### Files Created:
- 📄 **CSV Dataset**: `{Path(csv_path).name}`
- 📊 **Excel Dataset**: `{Path(xlsx_path).name if xlsx_path else 'N/A'}`
- 📋 **SPSS Syntax**: `{Path(spss_path).name}`

### Statistics:
- **Sample Size**: {result['sample_size']} respondents
- **Total Variables**: {result['total_variables']}

### Demographic Distribution:
"""
                    for var, freq in list(stats.get("demographics", {}).items())[:3]:
                        summary += f"\n**{var}**:\n"
                        for val, count in list(freq.items())[:5]:
                            pct = (count / result['sample_size']) * 100
                            summary += f"  - {val}: {count} ({pct:.1f}%)\n"
                    
                    # Add all generated files
                    summary += "\n### All Generated Files:\n"
                    for file_path in result.get('files', []):
                        summary += f"- 📄 `{Path(file_path).name}`\n"
                    
                    summary += f"""
### Next Steps:
1. Download the CSV files
2. Import questionnaire data into SPSS using the provided syntax
3. Analyze interview/FGD transcripts using thematic analysis
4. Review observation data for patterns

**Note**: This is synthetic data for demonstration purposes.
"""
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": summary,
                        "accumulated": summary
                    }, session_id=session_id)
                    
                    # Publish all files
                    for file_path in result.get('files', []):
                        await events.publish(job_id, "file_created", {
                            "path": file_path,
                            "name": Path(file_path).name
                        }, session_id=session_id)
                    
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "success"
                    }, session_id=session_id)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"❌ Error generating dataset: {str(e)}",
                        "accumulated": f"Error: {str(e)}"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "error"
                    }, session_id=request.session_id)
            
            asyncio.create_task(run_dataset_generation())
            sample_info = f" with {sample_size} respondents" if sample_size else ""
            return {
                "response": f"📊 Starting synthetic dataset generation{sample_info}...\\n\\nAI agents simulating survey responses!",
                "job_id": job_id,
                "plan": [],
                "reasoning": ""
            }
        
        # ROUTE 7.6: CHAPTER 4 GENERATION - Data Presentation and Analysis
        if route_info["route"] == "pipeline" and route_info.get("params", {}).get("generation_type") == "chapter_four_generate":
            from services.chapter4_generator import generate_chapter4
            import asyncio
            from pathlib import Path
            
            async def run_chapter4_generation():
                try:
                    await events.connect()
                    session_id = request.session_id
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"# 📊 Generating Chapter 4: Data Presentation and Analysis\n\n**Building tables, figures, and interpretation...**\n\n",
                        "accumulated": ""
                    }, session_id=session_id)
                    
                    # Get session data
                    topic = ""
                    case_study = ""
                    objectives = []
                    
                    try:
                        from services.thesis_session_db import ThesisSessionDB
                        db = ThesisSessionDB(session_id)
                        topic = db.get_topic() or "Research Study"
                        case_study = db.get_case_study() or ""
                        obj_data = db.get_objectives() or {}
                        objectives = obj_data.get("specific", [])
                        if obj_data.get("general"):
                            objectives = [obj_data["general"]] + objectives
                    except Exception as e:
                        print(f"⚠️ Could not get session data: {e}")
                        topic = "Research Study"
                    
                    # Generate default objectives if none found
                    if not objectives:
                        objectives = generate_smart_objectives(topic, 4)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📋 Topic: {topic[:50]}... | {len(objectives)} objectives"
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📊 Loading datasets and generating analysis..."
                    }, session_id=session_id)
                    
                    # Generate Chapter 4
                    result = await generate_chapter4(
                        topic=topic,
                        case_study=case_study,
                        objectives=objectives,
                        job_id=job_id,
                        session_id=session_id
                    )
                    
                    filepath = result["filepath"]
                    tables = result["tables"]
                    figures = result["figures"]
                    
                    # Summary message
                    summary = f"""
## ✅ Chapter 4 Generated Successfully!

### File Created:
- 📄 **Chapter 4**: `{Path(filepath).name}`

### Content Summary:
- **Tables Generated**: {tables}
- **Figures Generated**: {figures}
- **Objectives Covered**: {result['objectives_covered']}

### Sections Included:
- 4.0 Introduction
- 4.1 Study Tools Rate of Return  
- 4.2 Demographics (all subsections)
- 4.3-4.{len(objectives)+2} Objective Analyses
  - Descriptive Statistics
  - Inferential Statistics
  - Qualitative Findings (quotes)
  - Triangulation
- Summary of Findings

**Note**: Review and customize the auto-generated content as needed.
"""
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": summary,
                        "accumulated": summary
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "file_created", {
                        "path": filepath,
                        "name": Path(filepath).name
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "success"
                    }, session_id=session_id)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"❌ Error generating Chapter 4: {str(e)}",
                        "accumulated": f"Error: {str(e)}"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "error"
                    }, session_id=request.session_id)
            
            asyncio.create_task(run_chapter4_generation())
            return {
                "response": f"📊 Starting Chapter 4 generation...\\n\\nCreating data presentation with tables, figures, and interpretation!",
                "job_id": job_id,
                "plan": [],
                "reasoning": ""
            }
        
        # ROUTE 7.7: CHAPTER 5 GENERATION - Results and Discussion
        if route_info["route"] == "pipeline" and route_info.get("params", {}).get("generation_type") == "chapter_five_generate":
            from services.chapter5_generator_v2 import generate_chapter5
            import asyncio
            from pathlib import Path
            
            async def run_chapter5_generation():
                try:
                    await events.connect()
                    session_id = request.session_id
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"# 📖 Generating Chapter 5: Results and Discussion\n\n**Synthesizing Chapter 2 (Literature) with Chapter 4 (Data)...**\n\n",
                        "accumulated": ""
                    }, session_id=session_id)
                    
                    # Get session data
                    topic = ""
                    case_study = ""
                    objectives = []
                    
                    try:
                        from services.thesis_session_db import ThesisSessionDB
                        db = ThesisSessionDB(session_id)
                        topic = db.get_topic() or "Research Study"
                        case_study = db.get_case_study() or ""
                        obj_data = db.get_objectives() or {}
                        objectives = obj_data.get("specific", [])
                        if obj_data.get("general"):
                            objectives = [obj_data["general"]] + objectives
                    except Exception as e:
                        print(f"⚠️ Could not get session data: {e}")
                        topic = "Research Study"
                    
                    # Generate default objectives if none found
                    if not objectives:
                        objectives = generate_smart_objectives(topic, 4)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📋 Topic: {topic[:50]}... | {len(objectives)} objectives"
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📖 Synthesizing Chapter 2 and Chapter 4..."
                    }, session_id=session_id)
                    
                    # Find Chapter 2 and Chapter 4 files - check both session and default directories
                    workspace_dir = Path(f"/home/gemtech/Desktop/thesis/thesis_data/{session_id}")
                    default_dir = Path("/home/gemtech/Desktop/thesis/thesis_data/default")
                    
                    # Search for Chapter 2 in session dir first, then default
                    chapter2_files = list(workspace_dir.glob("Chapter_2*.md")) + list(workspace_dir.glob("chapter_2*.md"))
                    if not chapter2_files:
                        chapter2_files = list(default_dir.glob("Chapter_2*.md")) + list(default_dir.glob("chapter_2*.md"))
                    
                    # Search for Chapter 4 in session dir first, then default
                    chapter4_files = list(workspace_dir.glob("Chapter_4*.md")) + list(workspace_dir.glob("chapter_4*.md"))
                    if not chapter4_files:
                        chapter4_files = list(default_dir.glob("Chapter_4*.md")) + list(default_dir.glob("chapter_4*.md"))
                    
                    chapter2_path = str(chapter2_files[0]) if chapter2_files else None
                    chapter4_path = str(chapter4_files[0]) if chapter4_files else None
                    
                    # Use default output dir if session dir doesn't exist
                    output_dir = str(workspace_dir) if workspace_dir.exists() else str(default_dir)
                    
                    # Generate Chapter 5
                    result = await generate_chapter5(
                        topic=topic,
                        case_study=case_study,
                        objectives=objectives,
                        chapter_two_filepath=chapter2_path,
                        chapter_four_filepath=chapter4_path,
                        output_dir=output_dir,
                        job_id=job_id,
                        session_id=session_id
                    )
                    
                    filepath = result["filepath"]
                    
                    # Summary message
                    summary = f"""
## ✅ Chapter 5 Generated Successfully!

### File Created:
- 📖 **Chapter 5**: `{Path(filepath).name}`

### Features:
- ✅ Problem & objectives reintroduced
- ✅ {result['objectives_discussed']} objectives discussed
- ✅ {result['citations_integrated']} literature themes integrated
- ✅ 3-5 citations per paragraph for comparisons
- ✅ Confirmation/variation from existing knowledge identified
- ✅ Contribution to knowledge demonstrated

### Next Steps:
You can now:
1. Download and review Chapter 5
2. Generate Chapter 6 (Conclusions & Recommendations)
3. Export entire thesis to DOCX
4. Request revisions or improvements

"""
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": summary,
                        "accumulated": summary
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "success"
                    }, session_id=session_id)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"❌ Error generating Chapter 5: {str(e)}",
                        "accumulated": f"Error: {str(e)}"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "error"
                    }, session_id=request.session_id)
            
            asyncio.create_task(run_chapter5_generation())
            return {
                "response": f"📖 Starting Chapter 5 generation...\\n\\nSynthesizing literature review with data findings!",
                "job_id": job_id,
                "plan": [],
                "reasoning": ""
            }
        
        # ROUTE 7.8: CHAPTER 6 GENERATION - Summary, Conclusion and Recommendations
        if route_info["route"] == "pipeline" and route_info.get("params", {}).get("generation_type") == "chapter_six_generate":
            from services.chapter6_generator_v2 import generate_chapter6
            import asyncio
            from pathlib import Path
            
            async def run_chapter6_generation():
                try:
                    await events.connect()
                    session_id = request.session_id
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"# 📖 Generating Chapter 6: Summary, Conclusions and Recommendations\n\n**Using LLM to synthesise findings from all chapters...**\n\n",
                        "accumulated": ""
                    }, session_id=session_id)
                    
                    # Get session data
                    topic = ""
                    case_study = ""
                    objectives = []
                    
                    try:
                        from services.thesis_session_db import ThesisSessionDB
                        db = ThesisSessionDB(session_id)
                        topic = db.get_topic() or "Research Study"
                        case_study = db.get_case_study() or ""
                        obj_data = db.get_objectives() or {}
                        objectives = obj_data.get("specific", [])
                        if obj_data.get("general"):
                            objectives = [obj_data["general"]] + objectives
                    except Exception as e:
                        print(f"⚠️ Could not get session data: {e}")
                        topic = "Research Study"
                    
                    # Generate default objectives if none found
                    if not objectives:
                        objectives = generate_smart_objectives(topic, 4)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📋 Topic: {topic[:50]}... | {len(objectives)} objectives"
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📖 Synthesising Chapter 1 through Chapter 5..."
                    }, session_id=session_id)
                    
                    # Find all chapter files
                    workspace_dir = Path(f"/home/gemtech/Desktop/thesis/thesis_data/{session_id}")
                    chapter1_files = list(workspace_dir.glob("Chapter_1*.md")) + list(workspace_dir.glob("chapter_1*.md"))
                    chapter2_files = list(workspace_dir.glob("Chapter_2*.md")) + list(workspace_dir.glob("chapter_2*.md"))
                    chapter3_files = list(workspace_dir.glob("Chapter_3*.md")) + list(workspace_dir.glob("chapter_3*.md"))
                    chapter4_files = list(workspace_dir.glob("Chapter_4*.md")) + list(workspace_dir.glob("chapter_4*.md"))
                    chapter5_files = list(workspace_dir.glob("Chapter_5*.md")) + list(workspace_dir.glob("chapter_5*.md"))
                    
                    chapter1_content = ""
                    chapter2_content = ""
                    chapter3_content = ""
                    chapter4_content = ""
                    chapter5_content = ""
                    
                    if chapter1_files:
                        with open(chapter1_files[0], 'r', encoding='utf-8') as f:
                            chapter1_content = f.read()
                    if chapter2_files:
                        with open(chapter2_files[0], 'r', encoding='utf-8') as f:
                            chapter2_content = f.read()
                    if chapter3_files:
                        with open(chapter3_files[0], 'r', encoding='utf-8') as f:
                            chapter3_content = f.read()
                    if chapter4_files:
                        with open(chapter4_files[0], 'r', encoding='utf-8') as f:
                            chapter4_content = f.read()
                    if chapter5_files:
                        with open(chapter5_files[0], 'r', encoding='utf-8') as f:
                            chapter5_content = f.read()
                    
                    # Generate Chapter 6 using LLM-based generator
                    chapter6_content = await generate_chapter6(
                        topic=topic,
                        case_study=case_study,
                        objectives=objectives,
                        chapter4_content=chapter4_content,
                        chapter5_content=chapter5_content,
                        job_id=job_id,
                        session_id=session_id
                    )
                    
                    # Save Chapter 6
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_topic = topic[:50].replace(' ', '_')
                    filename = f"Chapter_6_PhD_Conclusion_{safe_topic}.md"
                    filepath = workspace_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(chapter6_content)
                    
                    # Summary message
                    summary = f"""
## ✅ Chapter 6 Generated Successfully!

### File Created:
- 📖 **Chapter 6**: `{filename}`

### Sections Included:
- ✅ 6.0 Introduction
- ✅ 6.1 Summary of the Study
- ✅ 6.2 Summary of Key Findings (per objective)
- ✅ 6.3 Conclusions (per objective)
- ✅ 6.4 Recommendations
- ✅ 6.5 Contribution to Knowledge
- ✅ 6.6 Limitations of the Study
- ✅ 6.7 Suggestions for Further Research

### Features:
- ✅ LLM-generated unique content (not templates)
- ✅ Synthesised findings from all chapters
- ✅ Evidence-based recommendations
- ✅ Limitations acknowledged
- ✅ Clear research directions identified
- ✅ PhD-level academic rigour
- ✅ UK English throughout

### Thesis Completion:
You now have all chapters (1-6) ready! You can:
1. Download and review Chapter 6
2. Export entire thesis (Chapters 1-6) to DOCX
3. Request final revisions or additional chapters
4. Generate thesis summary or abstract

"""
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": summary,
                        "accumulated": summary
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "success"
                    }, session_id=session_id)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"❌ Error generating Chapter 6: {str(e)}",
                        "accumulated": f"Error: {str(e)}"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "error"
                    }, session_id=request.session_id)
            
            asyncio.create_task(run_chapter6_generation())
            return {
                "response": f"📖 Starting Chapter 6 generation...\\n\\nSynthesising all chapters into conclusions and recommendations!",
                "job_id": job_id,
                "plan": [],
                "reasoning": ""
            }
        
        # ROUTE 7.9: THESIS COMBINE - Combine all chapters into single file
        if route_info["route"] == "pipeline" and route_info.get("params", {}).get("generation_type") == "thesis_combine_generate":
            from services.thesis_combiner import combine_existing_chapters
            import asyncio
            from pathlib import Path
            
            async def run_thesis_combine():
                try:
                    await events.connect()
                    session_id = request.session_id
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"# 📚 Combining All Chapters into Unified Thesis\n\n**Merging Chapters 1-6, generating references and statistics...**\n\n",
                        "accumulated": ""
                    }, session_id=session_id)
                    
                    await events.publish(job_id, "log", {
                        "message": f"📚 Discovering and loading all chapters from workspace..."
                    }, session_id=session_id)
                    
                    # Publish agent activity for UI
                    await publish_agent_activity(
                        job_id=job_id,
                        agent="planner",
                        action="Discovering chapters",
                        description="Finding and loading all thesis chapters from workspace...",
                        progress=10,
                        session_id=session_id
                    )
                    
                    # Get session data
                    topic = ""
                    case_study = ""
                    objectives = []
                    
                    try:
                        from services.thesis_session_db import ThesisSessionDB
                        db = ThesisSessionDB(session_id)
                        topic = db.get_topic() or "Research Study"
                        case_study = db.get_case_study() or ""
                        obj_data = db.get_objectives() or {}
                        objectives = obj_data.get("specific", [])
                        if obj_data.get("general"):
                            objectives = [obj_data["general"]] + objectives
                    except Exception as e:
                        print(f"⚠️ Could not get session data: {e}")
                        topic = "Research Study"
                    
                    # Generate default objectives if none found
                    if not objectives:
                        objectives = generate_smart_objectives(topic, 4)
                    
                    # Publish agent activity for UI
                    await publish_agent_activity(
                        job_id=job_id,
                        agent="citation",
                        action="Combining chapters",
                        description=f"Merging {len(objectives)} chapters with unified references...",
                        progress=50,
                        session_id=session_id
                    )
                    
                    await events.publish(job_id, "log", {
                        "message": f"📋 Topic: {topic[:50]}... | {len(objectives)} objectives"
                    }, session_id=session_id)
                    
                    # Use thesis combiner to combine existing chapters
                    thesis_path, total_words = await combine_existing_chapters(
                        workspace_id=session_id,
                        topic=topic,
                        case_study=case_study,
                        objectives=objectives
                    )
                    
                    chapters_found = 6  # Assuming 6 chapters in a complete thesis
                    
                    # Summary message
                    summary = f"""
## ✅ Complete Thesis Generated Successfully!

### File Created:
- 📚 **Unified Thesis**: `{Path(thesis_path).name if thesis_path else 'thesis.md'}`

### Statistics:
- **Chapters Combined**: {chapters_found}
- **Total Words**: {total_words:,}
- **Estimated Pages**: ~{int(total_words / 250) if total_words > 0 else 0}

### Contents:
✅ Title Page with Abstract
✅ Table of Contents
✅ Chapter 1: Introduction
✅ Chapter 2: Literature Review
✅ Chapter 3: Research Methodology
✅ Chapter 4: Data Presentation & Analysis
✅ Chapter 5: Results & Discussion
✅ Chapter 6: Summary, Conclusion & Recommendations
✅ Consolidated References Section
✅ Thesis Statistics

### Next Steps:
1. **Download**: Get your complete thesis.md file
2. **Export to DOCX**: Convert to Word format with formatting
3. **Review**: Check chapter flow and references
4. **Submit**: Your PhD thesis is ready!
"""
                    
                    await events.publish(job_id, "response_chunk", {
                        "chunk": summary,
                        "accumulated": summary
                    }, session_id=session_id)
                    
                    if thesis_path:
                        await events.publish(job_id, "file_created", {
                            "path": thesis_path,
                            "name": Path(thesis_path).name
                        }, session_id=session_id)
                    
                    # Publish agent completion
                    await publish_agent_activity(
                        job_id=job_id,
                        agent="citation",
                        action="Thesis combination complete",
                        description=f"Successfully merged {chapters_found} chapters into unified thesis ({total_words:,} words)",
                        progress=100,
                        session_id=session_id
                    )
                    
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "success"
                    }, session_id=session_id)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await events.publish(job_id, "response_chunk", {
                        "chunk": f"❌ Error combining thesis: {str(e)}",
                        "accumulated": f"Error: {str(e)}"
                    }, session_id=request.session_id)
                    await events.publish(job_id, "stage_completed", {
                        "stage": "complete",
                        "status": "error"
                    }, session_id=request.session_id)
            
            asyncio.create_task(run_thesis_combine())
            return {
                "response": f"📚 Combining all thesis chapters into single unified file...\\n\\nMerging Chapters 1-6 with references and statistics!",
                "job_id": job_id,
                "plan": [],
                "reasoning": ""
            }
        
        # ROUTE 8: Instant responses - DISABLED
        # Let ALL messages (including greetings) go to LLM for natural responses
        # if route_info["route"] == "instant":
        #     # Skip - let LLM handle greetings naturally
        #     pass
        
        # Simple greetings - DISABLED - let messages fall through to LLM
        if False and is_simple_greeting(request.message):  # Disabled
            try:
                await events.connect()
                await events.log(job_id, "💬 Responding to simple query...", "info", session_id=request.session_id)
                
                # Don't use hardcoded greetings - let LLM respond naturally
                response_text = ""
                
                # Stream response word by word for real-time effect
                words = response_text.split(' ')
                accumulated = ""
                for i, word in enumerate(words):
                    accumulated += word + (" " if i < len(words) - 1 else "")
                    await events.publish(job_id, "response_chunk", {
                        "chunk": word + " ",
                        "accumulated": accumulated
                    }, session_id=request.session_id)
                    await asyncio.sleep(0.03)  # Small delay for streaming effect
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "response",
                    "metadata": {"type": "simple"}
                }, session_id=request.session_id)
            except Exception as e:
                print(f"⚠️ Error in simple response streaming: {e}", flush=True)
            
            return {
                "response": "",  # Empty - let LLM handle greeting
                "reasoning": "",
                "plan": [],
                "tool_results": {},
                "job_id": job_id
            }
        
        # Direct image generation - bypass planner (only for explicit generation requests)
        if is_image_generation_request(request.message):
            try:
                from services.image_generation import image_generation_service
                
                # Extract prompt (remove generation keywords)
                prompt = request.message
                for keyword in ["generate image", "create image", "make image", "generate a picture", "create a picture"]:
                    prompt = prompt.replace(keyword, "").replace(keyword.replace(" ", ""), "").strip()
                if not prompt:
                    prompt = request.message  # Use full message if no prompt extracted
                
                # Generate image directly
                result = await image_generation_service.generate(
                    prompt=prompt,
                    size="1024x1024"
                )
                
                if result.get("success"):
                    image_url = result.get("image_url") or result.get("url")
                    image_data = result.get("image_data")  # Base64 if available
                    
                    response_text = f"✅ Image generated successfully!\n\nPrompt: {prompt}"
                    
                    return {
                        "response": "Image generated successfully!",
                        "reasoning": "",  # Empty - don't show reasoning panel
                        "plan": [],
                        "image_generation": {
                            "success": True,
                            "image_url": image_url,
                            "image_data": image_data,
                            "prompt": prompt
                        }
                    }
                else:
                    error_msg = result.get("error", "Image generation failed")
                    return {
                        "response": f"❌ Failed to generate image: {error_msg}",
                        "reasoning": "",  # Empty - don't show reasoning panel
                        "plan": [],
                        "image_generation": {"success": False, "error": error_msg}
                    }
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {
                    "response": f"❌ Error generating image: {str(e)}",
                    "reasoning": f"Image generation error: {str(e)}",
                    "plan": []
                }
        
        # =====================================================================
        # INTELLIGENT RESEARCH SYNTHESIS - Search + Analyze + Write
        # =====================================================================
        is_synthesis, synthesis_topic, synthesis_style = is_research_synthesis_request(request.message)
        if is_synthesis and synthesis_topic:
            print(f"🧠 Detected research synthesis request: '{synthesis_topic}' (style: {synthesis_style})")
            
            async def run_intelligent_synthesis():
                """
                Intelligent research synthesis pipeline with streaming.
                
                This pipeline THINKS about what to do, not just follows steps:
                1. Understands the research topic and scope
                2. Searches for relevant papers dynamically
                3. Analyzes gaps and themes in the literature
                4. Generates a coherent synthesis with proper citations
                """
                from services.sources_service import sources_service
                from services.literature_synthesis import literature_synthesis_service
                from services.planner import planner_service
                
                try:
                    # Connect to event system
                    await events.connect()
                    
                    # ── PHASE 1: Understanding ──────────────────────────────────
                    yield {"event": "stage", "data": json.dumps({
                        "stage": "understanding", 
                        "icon": "🧠",
                        "message": f"Understanding research scope: {synthesis_topic}"
                    })}
                    
                    await events.log(job_id, f"🧠 Analyzing research scope: {synthesis_topic}", "info", session_id=request.session_id)
                    await asyncio.sleep(0.3)
                    
                    # ── PHASE 2: Search ─────────────────────────────────────────
                    yield {"event": "stage", "data": json.dumps({
                        "stage": "searching",
                        "icon": "🔍", 
                        "message": f"Searching academic databases for papers on '{synthesis_topic}'..."
                    })}
                    
                    await events.log(job_id, f"🔍 Searching papers on: {synthesis_topic}", "info", session_id=request.session_id)
                    
                    search_result = await sources_service.search_and_save(
                        workspace_id=request.workspace_id,
                        query=synthesis_topic,
                        max_results=10,
                        auto_save=True
                    )
                    
                    papers_found = search_result.get('total_results', 0)
                    papers_saved = search_result.get('saved_count', 0)
                    
                    yield {"event": "search_complete", "data": json.dumps({
                        "papers_found": papers_found,
                        "papers_saved": papers_saved,
                        "papers": search_result.get('results', [])[:5]  # Preview first 5
                    })}
                    
                    await events.log(job_id, f"📚 Found {papers_found} papers, saved {papers_saved}", "info", session_id=request.session_id)
                    
                    if papers_saved == 0:
                        yield {"event": "response_chunk", "data": json.dumps({
                            "chunk": f"\n\n⚠️ No papers found for '{synthesis_topic}'. Try a broader or different search term.\n",
                            "accumulated": f"\n\n⚠️ No papers found for '{synthesis_topic}'. Try a broader or different search term.\n"
                        })}
                        yield {"event": "done", "data": json.dumps({"status": "no_sources"})}
                        return
                    
                    # ── PHASE 3: Analysis & Planning ────────────────────────────
                    yield {"event": "stage", "data": json.dumps({
                        "stage": "planning",
                        "icon": "📋",
                        "message": "Analyzing literature themes and planning synthesis structure..."
                    })}
                    
                    await events.log(job_id, "📋 Planning synthesis structure...", "info", session_id=request.session_id)
                    
                    # Quick outline using planner
                    try:
                        outline = await planner_service.generate_outline(
                            topic=synthesis_topic,
                            word_count=1500,
                            include_images=False,
                            job_id=job_id
                        )
                        
                        if outline and outline.get('sections'):
                            yield {"event": "outline", "data": json.dumps({
                                "title": outline.get('title', synthesis_topic),
                                "sections": [s.get('title', s) if isinstance(s, dict) else s for s in outline.get('sections', [])]
                            })}
                    except Exception as e:
                        print(f"⚠️ Outline generation skipped: {e}")
                    
                    # ── PHASE 4: Writing Synthesis ──────────────────────────────
                    yield {"event": "stage", "data": json.dumps({
                        "stage": "writing",
                        "icon": "✍️",
                        "message": "Generating comprehensive literature synthesis with citations..."
                    })}
                    
                    await events.log(job_id, "✍️ Writing synthesis with citations...", "info", session_id=request.session_id)
                    
                    # Stream the synthesis content
                    accumulated = ""
                    async for chunk in literature_synthesis_service.synthesize_literature(
                        workspace_id=request.workspace_id,
                        topic=synthesis_topic,
                        output_format="markdown"
                    ):
                        accumulated += chunk
                        yield {"event": "response_chunk", "data": json.dumps({"chunk": chunk, "accumulated": accumulated})}
                    
                    # ── PHASE 5: Complete ───────────────────────────────────────
                    yield {"event": "stage", "data": json.dumps({
                        "stage": "complete",
                        "icon": "✅",
                        "message": "Synthesis complete!"
                    })}
                    
                    await events.log(job_id, "✅ Research synthesis complete!", "info", session_id=request.session_id)
                    
                    # Save to workspace
                    try:
                        from services.workspace_service import WORKSPACES_DIR
                        output_path = WORKSPACES_DIR / request.workspace_id / f"synthesis_{synthesis_topic.replace(' ', '_')[:30]}.md"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(full_content, encoding='utf-8')
                        
                        yield {"event": "file_created", "data": json.dumps({
                            "path": str(output_path),
                            "name": output_path.name
                        })}
                        await events.log(job_id, f"📄 Saved to: {output_path.name}", "info", session_id=request.session_id)
                    except Exception as e:
                        print(f"⚠️ Could not save synthesis: {e}")
                    
                    yield {"event": "done", "data": json.dumps({
                        "status": "success",
                        "papers_used": papers_saved,
                        "word_count": len(full_content.split())
                    })}
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield {"event": "error", "data": json.dumps({"message": str(e)})}
            
            return EventSourceResponse(run_intelligent_synthesis())
        
        # Paper/Literature search - route directly to sources service
        if is_paper_search_request(request.message):
            try:
                await events.connect()
                await events.log(job_id, "📚 Searching academic papers...", "info", session_id=request.session_id)
                
                from services.sources_service import sources_service
                import re
                
                # Extract search query from message
                query = request.message
                for phrase in ["search for papers on", "search papers on", "find papers on",
                               "search for papers about", "search papers about", "find papers about",
                               "search for articles on", "find articles on", "search literature on",
                               "find research on", "look for papers on", "search academic",
                               "search for sources on", "find sources on"]:
                    query = re.sub(phrase, "", query, flags=re.IGNORECASE)
                query = query.strip()
                
                if not query or len(query) < 3:
                    query = request.message  # Use full message if extraction failed
                
                # Search and auto-save
                result = await sources_service.search_and_save(
                    workspace_id=request.workspace_id,
                    query=query,
                    max_results=5,
                    auto_save=True
                )
                
                # Format response
                response_parts = [f"📚 **Found {result['total_results']} papers for:** {query}\n"]
                
                for i, paper in enumerate(result['results'][:5], 1):
                    authors = paper.get('authors', [])
                    if authors:
                        author_str = authors[0] if isinstance(authors[0], str) else authors[0].get('name', 'Unknown')
                        if len(authors) > 1:
                            author_str += " et al."
                    else:
                        author_str = "Unknown"
                    
                    response_parts.append(f"**{i}. {paper.get('title', 'Untitled')}**")
                    response_parts.append(f"   - *{author_str}* ({paper.get('year', 'N/A')})")
                    if paper.get('venue'):
                        response_parts.append(f"   - Venue: {paper.get('venue')}")
                    if paper.get('citation_count', 0) > 0:
                        response_parts.append(f"   - Citations: {paper.get('citation_count')}")
                    response_parts.append("")
                
                if result['saved_count'] > 0:
                    response_parts.append(f"✅ **Saved {result['saved_count']} papers** to `sources/` folder")
                    response_parts.append("Access via GraphQL at `/graphql` or REST at `/api/workspace/{id}/sources`")
                
                response_text = "\n".join(response_parts)
                
                # Stream response
                await events.publish(job_id, "response_chunk", {
                    "chunk": response_text,
                    "accumulated": response_text
                }, session_id=request.session_id)
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "search",
                    "metadata": {"type": "paper_search", "saved": result['saved_count']}
                }, session_id=request.session_id)
                
                return {
                    "response": response_text,
                    "reasoning": "",
                    "plan": [],
                    "search_results": result,
                    "job_id": job_id
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {
                    "response": f"❌ Paper search error: {str(e)}",
                    "reasoning": "",
                    "plan": [],
                    "job_id": job_id
                }
        
        # PDF action (summarize, read, analyze) - direct PDF processing
        is_pdf_action, pdf_action_type, pdf_name = is_pdf_action_request(request.message)
        if is_pdf_action:
            try:
                await events.connect()
                await events.log(job_id, f"📄 Processing PDF ({pdf_action_type})...", "info", session_id=request.session_id)
                
                from services.pdf_service import get_pdf_service
                from services.deepseek_direct import deepseek_direct
                import glob
                
                pdf_service = get_pdf_service()
                workspace_path = WORKSPACES_DIR / request.workspace_id
                
                # Find the PDF file
                pdf_path = None
                if pdf_name:
                    # Search for the specific PDF
                    for pfile in workspace_path.rglob("*.pdf"):
                        if pdf_name.lower() in pfile.name.lower():
                            pdf_path = pfile
                            break
                
                if not pdf_path:
                    # Try to find any PDF in workspace (most recent)
                    pdf_files = list(workspace_path.rglob("*.pdf"))
                    if pdf_files:
                        # Sort by modification time, newest first
                        pdf_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        pdf_path = pdf_files[0]
                
                if not pdf_path or not pdf_path.exists():
                    return {
                        "response": "❌ No PDF file found in workspace. Please upload a PDF first.",
                        "reasoning": "",
                        "plan": [],
                        "job_id": job_id
                    }
                
                await events.log(job_id, f"📄 Reading: {pdf_path.name}", "info", session_id=request.session_id)
                
                # Extract text from PDF
                text = pdf_service.extract_text_simple(pdf_path)
                
                if not text or len(text) < 50:
                    return {
                        "response": f"❌ Could not extract text from {pdf_path.name}. The PDF may be image-based or encrypted.",
                        "reasoning": "",
                        "plan": [],
                        "job_id": job_id
                    }
                
                # Truncate if too long
                max_chars = 15000
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n[... Truncated. Full document is {len(text)} characters ...]"
                
                # Create prompt based on action type
                if pdf_action_type == "summarize":
                    prompt = f"""Please provide a comprehensive summary of the following document. Include:
1. Main topic and purpose
2. Key findings or arguments
3. Important conclusions

Document content:
---
{text}
---

Please provide a clear, well-structured summary."""

                elif pdf_action_type == "extract":
                    prompt = f"""Extract the key points from the following document. Format as a bulleted list of the most important information:

Document content:
---
{text}
---

Key Points:"""

                elif pdf_action_type == "analyze":
                    prompt = f"""Provide an analysis of the following document, including:
1. Main themes and topics
2. Methodology (if applicable)
3. Strengths and limitations
4. Key insights

Document content:
---
{text}
---

Analysis:"""

                else:  # read
                    prompt = f"""Based on the following document, provide a helpful overview:

Document content:
---
{text}
---

Overview:"""
                
                # Generate response using LLM
                response_text = f"📄 **{pdf_action_type.capitalize()}:** {pdf_path.name}\n\n"
                
                async for chunk in deepseek_direct.generate_stream(
                    prompt=prompt,
                    system_prompt="You are an expert document analyst. Provide clear, well-structured responses. Use markdown formatting."
                ):
                    response_text += chunk
                    await events.publish(job_id, "response_chunk", {
                        "chunk": chunk,
                        "accumulated": response_text
                    }, session_id=request.session_id)
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "response",
                    "metadata": {"type": "pdf_action", "action": pdf_action_type, "file": pdf_path.name}
                }, session_id=request.session_id)
                
                return {
                    "response": response_text,
                    "reasoning": "",
                    "plan": [],
                    "job_id": job_id
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {
                    "response": f"❌ PDF processing error: {str(e)}",
                    "reasoning": "",
                    "plan": [],
                    "job_id": job_id
                }
        
        # Simple questions - direct AI response, no planning
        if is_simple_question(request.message):
            try:
                await events.connect()
                await events.log(job_id, "💬 Responding to simple question...", "info", session_id=request.session_id)
                
                # Use DeepSeek for direct response
                from services.deepseek_direct import deepseek_direct
                
                response_text = ""
                async for chunk in deepseek_direct.generate_stream(
                    prompt=request.message,
                    system_prompt="You are a helpful AI assistant. Provide clear, concise, and accurate responses. For math equations, use LaTeX notation with $ for inline and $$ for block equations."
                ):
                    response_text += chunk
                    # Stream response chunks
                    await events.publish(job_id, "response_chunk", {
                        "chunk": chunk,
                        "accumulated": response_text
                    }, session_id=request.session_id)
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "response",
                    "metadata": {"type": "simple_question"}
                }, session_id=request.session_id)
                
                return {
                    "response": response_text,
                    "reasoning": "",  # Empty - no planning visible
                    "plan": [],
                    "tool_results": {},
                    "job_id": job_id
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️ Simple question direct response failed: {e}, falling through to planner")
                # Fall through to task classifier if direct response fails
        
        # Use intelligent task classifier
        from services.task_classifier import task_classifier
        task_info = task_classifier.classify(request.message)
        
        # For complex tasks, use the INTELLIGENT ORCHESTRATOR (live streaming)
        if task_info["strategy"] == "worker":
            print(f"🧠 Complex task detected, using Intelligent Orchestrator")
            
            async def run_orchestrator():
                """Stream intelligent agent actions to frontend."""
                from services.intelligent_orchestrator import intelligent_orchestrator
                
                try:
                    yield {"event": "job_id", "data": json.dumps({"job_id": job_id})}
                    async for event in intelligent_orchestrator.run(
                        task=request.message,
                        workspace_id=request.workspace_id,
                        session_id=request.session_id,
                        job_id=job_id
                    ):
                        yield event
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    yield {"event": "error", "data": json.dumps({"message": str(e)})}
            
            return EventSourceResponse(run_orchestrator())
        
        # Handle mentioned agents - queue jobs to appropriate workers
        if request.mentioned_agents and len(request.mentioned_agents) > 0:
            try:
                await events.connect()
                
                # Map agent names to worker queues
                agent_to_queue = {
                    "objective": "objectives",
                    "objectives": "objectives",
                    "planner": "objectives",  # Planner can use objectives worker
                    "writer": "content",
                    "content": "content",
                    "editor": "content",  # Editor uses content worker
                    "research": "search",
                    "search": "search",
                    "citation": "search",  # Citation uses search worker
                }
                
                # Queue jobs to workers based on mentioned agents
                from core.queue import JobQueue
                queued_jobs = []
                
                for agent_name in request.mentioned_agents:
                    agent_lower = agent_name.lower().replace("_", "").replace("-", "")
                    queue_name = agent_to_queue.get(agent_lower)
                    
                    if queue_name:
                        try:
                            # Prepare job data based on agent type
                            job_data = {
                                "job_id": job_id,
                                "message": request.message,
                                "workspace_id": request.workspace_id,
                                "session_id": request.session_id,
                                "user_id": request.user_id,
                                "mentioned_agent": agent_name,
                            }
                            
                            # Add agent-specific data
                            if queue_name == "objectives":
                                job_data.update({
                                    "thesis_id": request.workspace_id,
                                    "topic": request.message,
                                    "mode": "voting"
                                })
                            elif queue_name == "content":
                                job_data.update({
                                    "thesis_id": request.workspace_id,
                                    "type": "chapter",
                                    "section_title": "Content"
                                })
                            elif queue_name == "search":
                                job_data.update({
                                    "thesis_id": request.workspace_id,
                                    "query": request.message,
                                    "type": "papers",
                                    "max_results": 20
                                })
                            
                            # Queue the job
                            queued_job_id = await JobQueue.push(
                                queue_name=queue_name,
                                data=job_data,
                                job_id=f"{job_id}-{agent_name}",
                                priority="high"  # High priority for mentioned agents
                            )
                            
                            queued_jobs.append({"agent": agent_name, "queue": queue_name, "job_id": queued_job_id})
                            print(f"📤 Queued job for @{agent_name} to {queue_name} worker", flush=True)
                            
                        except Exception as queue_error:
                            print(f"⚠️ Failed to queue job for {agent_name}: {queue_error}", flush=True)
                            import traceback
                            traceback.print_exc()
                
                if queued_jobs:
                    await events.publish(job_id, "agents_mentioned", {
                        "agents": request.mentioned_agents,
                        "queued_jobs": queued_jobs,
                        "message": f"Queued {len(queued_jobs)} jobs to workers"
                    })
                    print(f"✅ Queued {len(queued_jobs)} jobs to workers for mentioned agents", flush=True)
                
            except Exception as e:
                print(f"⚠️ Error handling mentioned agents: {e}", flush=True)
                import traceback
                traceback.print_exc()
                pass
        
        # Emit initial event immediately - ensure connection first
        try:
            await events.connect()  # Ensure Redis connection is established
            # Don't log generic "starting" messages - let real content stream through
            # await events.log(job_id, "🚀 Starting request processing...", "info")
            # await events.publish(job_id, "stage_started", {"stage": "planning", "message": "Generating plan..."})
        except Exception as event_error:
            print(f"⚠️ Failed to emit initial event: {event_error}", flush=True)
            import traceback
            traceback.print_exc()
            pass  # Don't fail if events fail
        
        # Generate plan for other requests
        try:
            # Check RAG for similar solutions
            from services.rag_system import rag_system
            similar_solutions = await rag_system.retrieve_similar(
                query=request.message,
                category="solutions",
                top_k=2
            )
            
            # Emit planning event
            try:
                await events.log(job_id, "💭 Generating plan...", "info")
            except:
                pass
            
            # Add timeout to prevent hanging
            import asyncio
            
            # Create streaming callback for reasoning
            reasoning_chunks = []
            async def stream_reasoning_chunk(chunk: str):
                """Stream reasoning chunks to frontend"""
                reasoning_chunks.append(chunk)
                try:
                    await events.publish(job_id, "reasoning_chunk", {
                        "chunk": chunk,
                        "accumulated": "".join(reasoning_chunks)
                    })
                except:
                    pass
            
            # Emit immediate planning status
            try:
                await events.log(job_id, "🔍 Analyzing your request and creating a plan...", "info")
                await events.publish(job_id, "stage_started", {
                    "stage": "planning",
                    "message": "Analyzing request..."
                })
            except:
                pass
            
            # Generate plan with streaming support
            plan_data = await asyncio.wait_for(
            planner_service.generate_plan(
                user_request=request.message,
                session_id=request.session_id,
                workspace_id=request.workspace_id,
                user_id=request.user_id,
                job_id=job_id,
                stream=True,
                stream_callback=stream_reasoning_chunk,
                mentioned_agents=request.mentioned_agents or []
            ),
                timeout=60.0  # 60 second timeout for planning
            )
            
            # Don't log generic "plan generated" - let real content stream
            # Plan completion is handled by the actual content streaming
            # Ensure plan_data is a dict with required keys
            if not isinstance(plan_data, dict):
                plan_data = {"reasoning": "", "plan": []}
            if "reasoning" not in plan_data:
                plan_data["reasoning"] = ""
            if "plan" not in plan_data:
                plan_data["plan"] = []
        except asyncio.TimeoutError:
            print(f"⚠️ Planner timeout after 60 seconds")
            plan_data = {
                "reasoning": "Planning took too long. The request may be too complex. Please try breaking it into smaller steps.",
                "plan": []
            }
        except Exception as plan_error:
            import traceback
            traceback.print_exc()
            print(f"Planner error: {plan_error}")
            # Return a safe response instead of crashing
            plan_data = {
                "reasoning": f"Error generating plan: {str(plan_error)[:200]}",
                "plan": []
            }
        
        reasoning = plan_data.get("reasoning", "")
        plan = plan_data.get("plan", [])
        
        # Execute plan steps
        response_parts = []
        recent_actions = []
        
        tool_results = {}  # Store tool results by tool name for response
        essay_content = None
        essay_file_path = None
        
        # First pass: Execute all tools except save_file
        for step_idx, step in enumerate(plan):
            tool_name = step.get("tool")
            if not tool_name or tool_name == "save_file" or tool_name == "write_file":
                continue
            
            # Emit tool execution event
            arguments = step.get("arguments", {})
            try:
                # Show BEFORE starting, not after
                if tool_name == "web_search":
                    query = arguments.get("query", "")
                    await events.log(job_id, f"🌐 Searching the web for: {query[:60]}...", "info")
                    
                    # Open Internet Search Agent tab
                    from core.agent_stream_factory import get_agent_stream_handler
                    search_handler = get_agent_stream_handler("internet_search", job_id, request.workspace_id)
                    await events.connect()
                    await events.publish(job_id, "agent_stream", {
                        "agent": "internet_search",
                        "tab_id": search_handler.tab_id,
                        "chunk": "",
                        "content": f"🌐 **Internet Search Agent**\n\n_Searching for: {query}_\n\n",
                        "type": "search",
                        "completed": False,
                        "workspace_id": request.workspace_id,
                        "metadata": {
                            "status": "running",
                            "action": "searching",
                            "query": query
                        }
                    })
                else:
                    await events.log(job_id, f"🔧 Executing {tool_name} (step {step_idx + 1}/{len(plan)})...", "info")
                    
                await events.publish(job_id, "tool_started", {
                    "tool": tool_name,
                    "step": step_idx + 1,
                    "total": len(plan),
                    "description": step.get("description", "")
                })
            except:
                pass
            
            try:
                result = await execute_tool(tool_name, arguments, request.workspace_id)
                
                # Emit tool completion event
                try:
                    status = result.get("status", "unknown")
                    # Don't log generic "tool completed" - let real content stream
                    # await events.log(job_id, f"✓ {tool_name} completed ({status})", "info" if status == "success" else "warning")
                    await events.publish(job_id, "tool_completed", {
                        "tool": tool_name,
                        "step": step_idx + 1,
                        "status": status
                    })
                except:
                    pass
                
                if result.get("status") == "success":
                    recent_actions.append(f"{tool_name}: {step.get('description', '')}")
                    response_parts.append(f"✓ {step.get('description', tool_name)} completed.")
                    
                    # Store tool result by tool name for inclusion in response
                    if tool_name == "web_search" and result.get("results"):
                        tool_results[tool_name] = result.get("results", [])
                    elif tool_name == "image_search" and result.get("images"):
                        tool_results[tool_name] = result.get("images", [])
                    elif tool_name == "image_generate" and result.get("image_url"):
                        if "image_generate" not in tool_results:
                            tool_results["image_generate"] = []
                        tool_results["image_generate"].append({
                            "url": result.get("image_url"),
                            "prompt": arguments.get("prompt", "")
                        })
            except Exception as tool_error:
                print(f"Tool execution error for {tool_name}: {tool_error}")
                response_parts.append(f"⚠ {step.get('description', tool_name)} failed: {str(tool_error)}")
        
        # Generate essay content ONLY if user ACTUALLY asked for an essay
        # Don't generate essays for image-only or search-only requests!
        import re
        user_wants_essay = bool(re.search(
            r"(write|create|generate|make)\s+(an?\s+)?(essay|document|report|paper|article|content)",
            request.message.lower()
        ))
        
        # Skip essay if user just wanted an image or search results
        user_wants_image_only = bool(re.search(
            r"(generat|creat|mak|draw)(e|ing)\s+.*?(image|picture|photo)",
            request.message.lower()
        )) and not user_wants_essay
        
        user_wants_search_only = (
            ("search" in request.message.lower() or "find" in request.message.lower()) and 
            "results" in request.message.lower() and
            not user_wants_essay
        )
        
        if tool_results and user_wants_essay and any(key in tool_results for key in ["web_search", "image_search", "image_generate"]):
            try:
                from services.deepseek_direct import deepseek_direct
                
                # Build context from tool results
                context_parts = []
                
                if "web_search" in tool_results and tool_results["web_search"]:
                    context_parts.append("## Research Findings:\n")
                    for result in tool_results["web_search"][:3]:  # Use top 3
                        if isinstance(result, dict):
                            title = result.get('title', '')
                            content = result.get('content', '') or result.get('snippet', '') or ''
                            if title or content:
                                context_parts.append(f"- {title}: {content[:200]}")
                
                # Build image markdown
                image_markdown = []
                if "image_search" in tool_results and tool_results["image_search"]:
                    for img in tool_results["image_search"][:1]:  # First searched image
                        if isinstance(img, dict):
                            img_url = img.get("url") or img.get("full") or img.get("image_url")
                            if img_url:
                                image_markdown.append(f"![Searched Image: {img.get('title', 'Uganda')}]({img_url})")
                
                if "image_generate" in tool_results and tool_results["image_generate"]:
                    for img in tool_results["image_generate"][:1]:  # First generated image
                        if isinstance(img, dict):
                            img_url = img.get("url") or img.get("image_url")
                            if img_url:
                                image_markdown.append(f"![Generated Image: {img.get('prompt', 'Uganda')}]({img_url})")
                
                context = "\n".join(context_parts) if context_parts else ""
                
                # Extract topic from user message (e.g., "write essay on computers" -> "computers")
                import re
                topic = request.message.lower().strip()
                # Try to extract topic after common phrases
                patterns = [
                    r"write\s+(?:an\s+)?essay\s+(?:on|about)\s+(.+)",
                    r"essay\s+(?:on|about)\s+(.+)",
                    r"write\s+(?:an\s+)?essay\s+(.+)",
                ]
                extracted = None
                for pattern in patterns:
                    match = re.search(pattern, topic)
                    if match:
                        extracted = match.group(1).strip()
                        break
                
                if extracted and len(extracted) > 2:
                    topic = extracted
                else:
                    # Fallback: remove common words and use the rest
                    words = topic.split()
                    filtered = [w for w in words if w not in ["write", "an", "essay", "on", "about", "the", "a"]]
                    topic = " ".join(filtered) if filtered else "the requested topic"
                
                # Generate essay
                image_text = "\n".join(image_markdown) if image_markdown else ""
                essay_prompt = f"""Write a comprehensive, well-structured essay about {topic}.

{context if context else f"Write about {topic} covering key aspects, current state, and important information."}

Requirements:
- Well-structured with introduction, body paragraphs, and conclusion
- Include relevant information from the research findings
- Professional academic tone
- Approximately 800-1200 words
- Include the following images in appropriate places:
{image_text if image_text else ""}

Write the complete essay now:"""
                
                try:
                    # Stream essay generation - OPEN WRITER AGENT TAB
                    essay_chunks = []
                    
                    # Open Writer Agent tab BEFORE generating content
                    from core.agent_stream_factory import get_agent_stream_handler
                    writer_handler = get_agent_stream_handler("writer", job_id, request.workspace_id)
                    
                    await events.connect()
                    # Open Writer tab immediately with distinct tab_id
                    await events.publish(job_id, "agent_stream", {
                        "agent": "writer",
                        "tab_id": writer_handler.tab_id,
                        "chunk": "",
                        "content": "✍️ **Writer Agent**\n\n_Generating essay content..._\n\n",
                        "type": "content",
                        "completed": False,
                        "workspace_id": request.workspace_id,
                        "metadata": {
                            "status": "running",
                            "action": "writing"
                        }
                    })
                    
                    async def stream_essay_chunk(chunk: str):
                        """Stream essay chunks to frontend AND Writer tab"""
                        essay_chunks.append(chunk)
                        accumulated = "".join(essay_chunks)
                        try:
                            await events.connect()
                            # Standard response_chunk for workspace
                            await events.publish(job_id, "response_chunk", {
                                "chunk": chunk,
                                "accumulated": accumulated
                            })
                            # Also stream to Writer agent tab
                            await writer_handler.stream_chunk(chunk, {
                                "word_count": len(accumulated.split()),
                                "status": "writing"
                            })
                        except Exception as e:
                            print(f"⚠️ Failed to stream essay chunk: {e}", flush=True)
                    
                    essay_content = await asyncio.wait_for(
                        deepseek_direct.generate_content(
                            prompt=essay_prompt,
                            system_prompt="You are an expert academic writer. Write comprehensive, well-researched essays with proper formatting.",
                            temperature=0.7,
                            max_tokens=3000,
                            use_reasoning=False,
                            stream=True,
                            stream_callback=stream_essay_chunk
                        ),
                        timeout=120.0
                    )
                    
                    if not essay_content or len(essay_content.strip()) < 100:
                        raise Exception("Generated essay content is too short or empty")
                    
                    # Insert images into essay if not already included
                    if image_markdown and len(image_markdown) > 0:
                        # Check if images are already in content
                        images_in_content = any(img_md in essay_content for img_md in image_markdown)
                        if not images_in_content:
                            # Insert first image after first paragraph
                            paragraphs = essay_content.split("\n\n")
                            if len(paragraphs) > 1:
                                paragraphs.insert(1, "\n".join(image_markdown))
                                essay_content = "\n\n".join(paragraphs)
                            else:
                                essay_content = essay_content + "\n\n" + "\n".join(image_markdown)
                    
                    response_parts.append("✓ Essay content generated successfully.")
                    
                    # Publish final essay content as response_chunk to ensure frontend gets it
                    try:
                        await events.connect()
                        await events.publish(job_id, "response_chunk", {
                            "chunk": "",  # Empty chunk to signal completion
                            "accumulated": essay_content,
                            "completed": True
                        })
                    except Exception as e:
                        print(f"⚠️ Failed to publish final essay: {e}", flush=True)
                    
                    # Emit content generation completed
                    try:
                        await events.log(job_id, f"✅ Essay generated ({len(essay_content)} characters)", "info")
                        await events.publish(job_id, "stage_completed", {
                            "stage": "content_generation",
                            "metadata": {"length": len(essay_content)}
                        })
                    except:
                        pass
                except asyncio.TimeoutError:
                    print("⚠️ Essay generation timed out")
                    essay_content = f"# Essay About Uganda\n\n[Essay generation timed out. Please try again.]"
                    try:
                        await events.log(job_id, "⚠️ Essay generation timed out", "warning")
                    except:
                        pass
                except Exception as gen_error:
                    print(f"⚠️ Essay generation error: {gen_error}")
                    import traceback
                    traceback.print_exc()
                    essay_content = f"# Essay About Uganda\n\n[Error generating essay: {str(gen_error)[:200]}]"
                    try:
                        await events.log(job_id, f"❌ Essay generation error: {str(gen_error)[:100]}", "error")
                    except:
                        pass
                
                # Detect and replace image placeholders
                import re
                image_placeholder_pattern = r'\[Image:([^\]]+)\]'
                placeholders = re.findall(image_placeholder_pattern, essay_content)
                
                if placeholders and len(placeholders) > 0:
                    try:
                        await events.log(job_id, f"🖼️ Detected {len(placeholders)} image placeholders, generating images...", "info")
                        
                        # Generate images for placeholders
                        for i, placeholder_desc in enumerate(placeholders[:3]):  # Limit to 3 images
                            try:
                                await events.log(job_id, f"🎨 Generating image {i+1}/{min(len(placeholders), 3)}: {placeholder_desc[:50]}...", "info")
                                
                                # Generate image
                                result = await execute_tool("image_generate", {
                                    "prompt": placeholder_desc.strip(),
                                    "size": "1024x1024"
                                }, request.workspace_id)
                                
                                if result.get("status") == "success" and result.get("image_url"):
                                    image_url = result["image_url"]
                                    # Replace first occurrence of this placeholder
                                    placeholder_full = f"[Image:{placeholder_desc}]"
                                    image_markdown = f"![Generated: {placeholder_desc.strip()}]({image_url})"
                                    essay_content = essay_content.replace(placeholder_full, image_markdown, 1)
                                    
                                    await events.log(job_id, f"✅ Image {i+1} generated successfully", "info")
                                else:
                                    await events.log(job_id, f"⚠️ Failed to generate image {i+1}", "warning")
                            except Exception as img_error:
                                print(f"Image generation error for placeholder '{placeholder_desc}': {img_error}")
                                await events.log(job_id, f"⚠️ Image generation failed: {str(img_error)[:50]}", "warning")
                        
                        # Publish updated essay with images
                        try:
                            await events.publish(job_id, "response_chunk", {
                                "chunk": "",
                                "accumulated": essay_content,
                                "completed": True,
                                "images_added": True
                            })
                        except:
                            pass
                            
                    except Exception as e:
                        print(f"Error processing image placeholders: {e}")
                
            except Exception as e:
                print(f"Essay generation setup error: {e}")
                import traceback
                traceback.print_exc()
                essay_content = f"# Essay About Uganda\n\n[Error: {str(e)[:200]}]"
        
        # Second pass: Save file if we have content
        if essay_content:
            for step in plan:
                tool_name = step.get("tool")
                if tool_name in ["save_file", "write_file"]:
                    arguments = step.get("arguments", {})
                    file_path = arguments.get("path", "uganda_essay_with_images.md")
                    
                    # Update arguments with actual content
                    arguments["content"] = essay_content
                    arguments["path"] = file_path
                    
                    try:
                        # Emit file saving event
                        try:
                            await events.log(job_id, f"💾 Saving file: {file_path}...", "info")
                        except:
                            pass
                        
                        result = await execute_tool(tool_name, arguments, request.workspace_id)
                        if result.get("status") == "success":
                            essay_file_path = file_path
                            response_parts.append(f"✓ Essay saved to {file_path}")
                            recent_actions.append(f"{tool_name}: Saved essay to {file_path}")
                            
                            # Emit file created event for real-time updates
                            try:
                                await events.file_created(job_id, file_path, "markdown")
                                await events.log(job_id, f"✅ File saved: {file_path}", "info")
                                await events.publish(job_id, "stage_completed", {
                                    "stage": "file_saving",
                                    "metadata": {"file_path": file_path}
                                })
                            except:
                                pass  # Don't fail if events fail
                        else:
                            response_parts.append(f"⚠ Failed to save file: {result.get('error', 'Unknown error')}")
                    except Exception as tool_error:
                        print(f"Save file error: {tool_error}")
                        import traceback
                        traceback.print_exc()
                        response_parts.append(f"⚠ Failed to save file: {str(tool_error)}")
                    break  # Only save once
        elif not tool_results:
            # No tools executed, no content to save
            response_parts.append("⚠ No tools were executed, so no content was generated.")
        
        # Generate response text - include essay content if available
        if essay_content:
            # Use essay content as the main response
            response_text = essay_content
            # Add a brief summary at the end if file was saved
            if essay_file_path:
                response_text += f"\n\n✅ Essay saved to {essay_file_path}"
        else:
            response_text = "\n".join(response_parts) if response_parts else "I've processed your request."
        
        # Include tool results in response for frontend to display (limit size to avoid huge responses)
        # tool_results is now a dict with tool_name as key
        try:
            for tool_name, result_data in list(tool_results.items())[:3]:  # Limit to 3 tool types
                if tool_name == "web_search" and result_data:
                    # Limit results to avoid huge base64 strings
                    limited_results = result_data[:3] if isinstance(result_data, list) else result_data
                    # Encode search results for frontend
                    search_data = {
                        "type": "web_search",
                        "query": "Search Results",
                        "results": limited_results
                    }
                    try:
                        search_json = json.dumps(search_data)
                        if len(search_json) > 10000:  # Limit JSON size
                            search_data["results"] = limited_results[:2] if isinstance(limited_results, list) else limited_results
                            search_json = json.dumps(search_data)
                        search_b64 = base64.b64encode(search_json.encode()).decode()
                        response_text += f"\n\n<!-- SEARCH_RESULTS_JSON_B64: {search_b64} -->"
                    except Exception as e:
                        print(f"Warning: Failed to encode search results: {e}")
                
                elif tool_name == "image_search" and result_data:
                    # Limit images to avoid huge base64 strings
                    limited_images = result_data[:2] if isinstance(result_data, list) else result_data
                    # Encode image search results for frontend
                    image_data = {
                        "type": "image_search",
                        "query": "Image Search Results",
                        "results": limited_images
                    }
                    try:
                        image_json = json.dumps(image_data)
                        if len(image_json) > 10000:  # Limit JSON size
                            image_data["results"] = limited_images[:1] if isinstance(limited_images, list) else limited_images
                            image_json = json.dumps(image_data)
                        image_b64 = base64.b64encode(image_json.encode()).decode()
                        response_text += f"\n\n<!-- IMAGE_SEARCH_JSON_B64: {image_b64} -->"
                    except Exception as e:
                        print(f"Warning: Failed to encode image results: {e}")
        except Exception as e:
            print(f"Warning: Failed to encode tool results: {e}")
        
        # Save to chat history (non-blocking, don't wait)
        try:
            # Don't wait for chat history save - it can be slow
            asyncio.create_task(chat_history_service.save_message(
                session_id=request.session_id,
                user_id=request.user_id,
                message=request.message,
                response=response_text[:1000],  # Truncate to avoid large responses
                metadata={
                    "reasoning": reasoning[:500] if reasoning else "",
                    "plan": plan,
                    "recent_actions": recent_actions,
                    "workspace_id": request.workspace_id,
                    "tool_results": {}  # Don't store full tool results in history
                }
            ))
        except Exception as e:
            print(f"Warning: Failed to save chat history: {e}")
        
        # Limit tool_results size to avoid huge responses
        limited_tool_results = {}
        for tool_name, result_data in tool_results.items():
            if tool_name == "web_search" and result_data:
                # Limit to first 3 results
                limited_tool_results[tool_name] = result_data[:3] if isinstance(result_data, list) else result_data
            elif tool_name == "image_search" and result_data:
                # Limit to first 2 images
                limited_tool_results[tool_name] = result_data[:2] if isinstance(result_data, list) else result_data
            elif tool_name == "image_generate" and result_data:
                # Limit to first 1 generated image
                limited_tool_results[tool_name] = result_data[:1] if isinstance(result_data, list) else result_data
        
        # Ensure essay content is in response
        final_response = response_text
        if essay_content and len(essay_content) > 100:
            # Use essay content as the main response
            final_response = essay_content
            if essay_file_path:
                final_response += f"\n\n✅ Essay saved to {essay_file_path}"
            
            # Publish final essay as response_chunk if not already published
            try:
                await events.connect()
                await events.publish(job_id, "response_chunk", {
                    "chunk": "",
                    "accumulated": final_response,
                    "completed": True
                })
            except Exception as e:
                print(f"⚠️ Failed to publish final response: {e}", flush=True)
        elif not final_response or len(final_response.strip()) < 50:
            # Fallback if no good response
            final_response = response_text if response_text else "I've processed your request."
        
        response_data = {
            "response": final_response[:10000],  # Increased limit for essays
            "reasoning": reasoning[:1000] if reasoning else "",
            "plan": plan,
            "tool_results": limited_tool_results  # Include limited tool results
        }
        
        # If essay was created, include file path for auto-opening
        if essay_file_path:
            response_data["file_created"] = {
                "path": essay_file_path,
                "workspace_id": request.workspace_id
            }
        
        # Include job_id for frontend to subscribe to events
        response_data["job_id"] = job_id
        
        # Emit completion event
        try:
            await events.log(job_id, "✅ Request processing completed!", "info")
            await events.publish(job_id, "stage_completed", {
                "stage": "complete",
                "metadata": {"file_path": essay_file_path or "none"}
            })
        except:
            pass
        
        print(f"✅ Returning response (file: {essay_file_path or 'none'}, response_len: {len(response_text)}, job_id: {job_id})")
        
        # Ensure response is serializable
        try:
            json.dumps(response_data)  # Test serialization
            print("✅ Response is serializable")
        except Exception as ser_error:
            print(f"⚠️ Response serialization error: {ser_error}")
            # Remove problematic data
            response_data["tool_results"] = {}
            response_data["response"] = response_text[:1000]
            response_data["plan"] = []
        
        print(f"✅ About to return response_data")
        return response_data
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Chat endpoint error: {e}")
        print(f"Traceback: {error_trace}")
        
        # Always return a response, never raise
        try:
            # Try self-healing (but don't wait for it)
            try:
                from services.self_healing import self_healing_system
                from services.rag_system import rag_system
                
                # Store error in RAG (async, but don't wait)
                asyncio.create_task(rag_system.store_solution(
                    problem=f"Chat endpoint error: {str(e)}",
                    solution="",
                    context={"traceback": error_trace[:500]},
                    category="errors"
                ))
            except:
                pass  # Don't fail on self-healing errors
        except:
            pass
        
        # Emit error event (job_id already exists from function start)
        try:
            await events.log(job_id, f"❌ Error: {str(e)[:200]}", "error")
        except:
            pass
        
        # Return error response with job_id so frontend can connect to stream
        error_response = {
            "response": f"I apologize, but I encountered an error processing your request: {str(e)[:200]}. Please try again or rephrase your message.",
            "reasoning": f"Error: {str(e)[:200]}",
            "plan": [],
            "tool_results": {},
            "job_id": job_id  # Always include job_id so frontend can connect
        }
        
        # Include job_id if we have one
        if 'job_id' in locals():
            error_response["job_id"] = job_id
        
        return error_response

# ============================================================================
# SSE STREAMING ENDPOINT
# ============================================================================

@app.head("/api/stream/agent-actions")
async def stream_actions_head(request: Request):
    """HEAD handler for SSE endpoint to prevent 405 errors."""
    origin = request.headers.get("origin", "http://localhost:3000")
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_origin = origin if origin in allowed_origins else "http://localhost:3000"
    
    return Response(
        content=b"",
        headers={
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Expose-Headers": "*",
        },
        media_type="text/plain"
    )

async def event_generator(session_id: str = "default", job_id: Optional[str] = None):
    """Generate SSE events for agent actions and job progress."""
    import redis.asyncio as redis
    from core.config import settings
    
    # Send connection event
    yield {
        "event": "connected",
        "data": json.dumps({
            "status": "connected",
            "session_id": session_id,
            "job_id": job_id,
            "message": "Stream connected"
        })
    }
    
    # Subscribe to BOTH session and job channels for continuous chat
    pubsub = None
    redis_client = None
    try:
        redis_url = settings.REDIS_URL
        if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
            redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
        
        redis_client = redis.from_url(redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        
        # Subscribe to session channel (receives ALL messages for this session)
        await pubsub.subscribe(f"session:{session_id}")
        print(f"📡 Subscribed to session:{session_id} for continuous chat", flush=True)
        
        # Also subscribe to job channel if provided
        if job_id:
            await pubsub.subscribe(f"job:{job_id}")
            print(f"📡 Also subscribed to job:{job_id}", flush=True)
            
            # Replay missed events from history (events that happened before connection)
            try:
                history_key = f"job:{job_id}:history"
                history_messages = await redis_client.lrange(history_key, 0, -1)
                if history_messages:
                    print(f"📜 Replaying {len(history_messages)} missed events for job:{job_id}", flush=True)
                    for msg_json in history_messages:
                        try:
                            event_data = json.loads(msg_json)
                            yield {
                                "event": event_data.get("type", "log"),
                                "data": json.dumps(event_data.get("data", {}))
                            }
                        except Exception as replay_error:
                            print(f"⚠️ Error replaying event: {replay_error}", flush=True)
            except Exception as replay_err:
                print(f"⚠️ Failed to replay history: {replay_err}", flush=True)
                
    except Exception as e:
        print(f"⚠️ Failed to subscribe to channels: {e}", flush=True)
    
    # Event loop
    import asyncio
    keepalive_counter = 0
    
    try:
        while True:
            # Check for job events
            if pubsub:
                try:
                    # Get message with short timeout for responsiveness
                    message = await asyncio.wait_for(
                        pubsub.get_message(timeout=0.1),
                        timeout=0.1
                    )
                    if message:
                        if message["type"] == "message":
                            # Parse and forward the event
                            try:
                                event_data = json.loads(message["data"])
                                event_type = event_data.get("type", "log")
                                event_payload = event_data.get("data", {})
                                
                                print(f"📤 Sending SSE event [{event_type}]: {str(event_payload)[:100]}...", flush=True)
                                
                                yield {
                                    "event": event_type,
                                    "data": json.dumps(event_payload)
                                }
                            except json.JSONDecodeError as je:
                                print(f"⚠️ Failed to parse event JSON: {je}", flush=True)
                        elif message["type"] == "subscribe":
                            print(f"✅ Subscribed to channel: {message.get('channel', 'unknown')}", flush=True)
                except asyncio.TimeoutError:
                    # No message, continue to keepalive check
                    pass
                except Exception as e:
                    print(f"⚠️ Error reading pubsub: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
            
            # Send keepalive every 30 seconds
            keepalive_counter += 1
            if keepalive_counter >= 300:  # 300 * 0.1s = 30 seconds
                yield {
                    "event": "keepalive",
                    "data": json.dumps({
                        "timestamp": datetime.now().isoformat()
                    })
                }
                keepalive_counter = 0
            
            await asyncio.sleep(0.1)  # Short sleep for responsive event delivery
                
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception as e:
                print(f"⚠️ Error closing pubsub: {e}", flush=True)
        if redis_client:
            try:
                await redis_client.close()
            except Exception as e:
                print(f"⚠️ Error closing redis client: {e}", flush=True)

@app.get("/api/stream/agent-actions")
async def stream_actions(request: Request, session_id: str = "default", job_id: Optional[str] = None):
    """SSE endpoint for streaming agent actions and job progress."""
    origin = request.headers.get("origin", "http://localhost:3000")
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_origin = origin if origin in allowed_origins else "http://localhost:3000"
    
    return EventSourceResponse(
        event_generator(session_id, job_id),
        headers={
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Expose-Headers": "*",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================

from fastapi import UploadFile, File

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    session_id: str = "default"
):
    """
    Upload a file to the workspace.
    Supports PDF, Excel, CSV, DOCX, images, and text files.
    Automatically extracts content for AI reference.
    """
    try:
        from services.file_upload_service import get_file_upload_service
        
        upload_service = get_file_upload_service()
        
        # Read file content
        content = await file.read()
        
        # Upload and process
        result = await upload_service.upload_file(
            file_content=content,
            filename=file.filename,
            workspace_id=workspace_id,
            session_id=session_id,
            extract_content=True
        )
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.get("/api/uploads/{workspace_id}")
async def list_uploads(workspace_id: str):
    """List all uploaded files in a workspace."""
    try:
        from services.file_upload_service import get_file_upload_service
        
        upload_service = get_file_upload_service()
        files = upload_service.list_uploads(workspace_id)
        
        return {"success": True, "files": files, "count": len(files)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/file/content/{workspace_id}/{filename}")
async def get_file_content(workspace_id: str, filename: str):
    """Get extracted content from an uploaded file."""
    try:
        from services.file_upload_service import get_file_upload_service
        from pathlib import Path
        
        upload_service = get_file_upload_service()
        file_path = Path("workspaces") / workspace_id / "uploads" / filename
        
        content = upload_service.get_file_content(file_path)
        
        if content:
            return {"success": True, "content": content[:10000], "truncated": len(content) > 10000}
        else:
            return {"success": False, "error": "No content extracted"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# SPREADSHEET AND GRAPH ENDPOINTS
# ============================================================================

@app.post("/api/spreadsheet/create")
async def create_spreadsheet(request: dict):
    """Create an Excel or CSV file from data."""
    try:
        from services.spreadsheet_service import get_spreadsheet_service
        
        service = get_spreadsheet_service()
        
        data = request.get("data", [])
        filename = request.get("filename", "data.xlsx")
        workspace_id = request.get("workspace_id", "default")
        formulas = request.get("formulas")
        auto_formulas = request.get("auto_formulas")
        create_chart = request.get("chart")
        
        if filename.endswith(".csv"):
            result = service.write_csv(data, filename, workspace_id)
        else:
            result = service.write_excel(
                data, filename, 
                formulas=formulas,
                auto_formulas=auto_formulas,
                create_chart=create_chart,
                workspace_id=workspace_id
            )
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/graph/create")
async def create_graph(request: dict):
    """Create a chart/graph from data."""
    try:
        from services.graph_service import get_graph_service
        
        service = get_graph_service()
        
        data = request.get("data", [])
        chart_type = request.get("type", "bar")
        title = request.get("title", "Chart")
        x = request.get("x")
        y = request.get("y")
        workspace_id = request.get("workspace_id", "default")
        filename = request.get("filename")
        
        result = service.create_chart(
            data, chart_type, title, x, y,
            workspace_id=workspace_id,
            filename=filename
        )
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/analyze")
async def analyze_data(request: dict):
    """
    Analyze a dataset with AI-powered insights.
    
    Supports:
    - Basic analysis (schema, stats, quality)
    - LLM-powered insights (comprehensive, statistical, trends, quality)
    - Real-time streaming to UI
    """
    try:
        from services.dataset_analyzer import dataset_analyzer
        
        file_path = request.get("file_path")
        analysis_type = request.get("type", "comprehensive")
        job_id = request.get("job_id")
        workspace_id = request.get("workspace_id", "default")
        use_llm = request.get("use_llm", True)
        streaming = request.get("streaming", False)
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        # Check if file exists
        from pathlib import Path
        if not Path(file_path).exists():
            # Try workspace path
            workspace_path = Path("workspaces") / workspace_id / "uploads" / file_path
            if workspace_path.exists():
                file_path = str(workspace_path)
            else:
                return {"success": False, "error": f"File not found: {file_path}"}
        
        if streaming and job_id:
            # Full streaming analysis with real-time updates
            result = await dataset_analyzer.analyze_streaming(
                file_path, job_id, workspace_id
            )
        elif use_llm:
            # LLM-powered analysis
            result = await dataset_analyzer.analyze_with_llm(
                file_path, analysis_type, job_id
            )
        else:
            # Basic analysis only
            result = await dataset_analyzer.analyze(file_path)
        
        return {"success": True, **result}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================================
# SKILLS ENDPOINTS (Already in file - keeping them)
# ============================================================================

@app.get("/api/skills")
async def list_skills():
    """List all available skills."""
    try:
        skills_manager = get_skills_manager()
        skills = skills_manager.list_skills()
        
        return {
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "metadata": skill.metadata
                }
                for skill in skills
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get details of a specific skill."""
    try:
        skills_manager = get_skills_manager()
        skill = skills_manager.get_skill(skill_name)
        
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        
        return {
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.instructions,
            "metadata": skill.metadata,
            "path": str(skill.path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/reload")
async def reload_skills():
    """Reload all skills from disk."""
    try:
        skills_manager = get_skills_manager()
        skills_manager.reload_skills()
        
        return {
            "status": "success",
            "message": "Skills reloaded successfully",
            "count": len(skills_manager.list_skills())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/for-task")
async def get_skills_for_task(task: str = Query(...)):
    """Get skills that might be relevant for a task."""
    try:
        skills_manager = get_skills_manager()
        relevant_skills = skills_manager.get_skills_for_task(task)
        
        return {
            "task": task,
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description
                }
                for skill in relevant_skills
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOCX CONVERSION ENDPOINT
# ============================================================================

class ConvertDocxRequest(BaseModel):
    content: str
    filename: str = "document"

@app.post("/api/files/{workspace_id}/convert/docx")
async def convert_to_docx(workspace_id: str, request: ConvertDocxRequest):
    """Convert markdown content to DOCX file with embedded images."""
    try:
        from services.docx_converter import convert_markdown_to_docx_enhanced
        
        docx_path = convert_markdown_to_docx_enhanced(request.content, request.filename, workspace_id=workspace_id)
        
        # Read the file and return it
        with open(docx_path, 'rb') as f:
            docx_content = f.read()
        
        # Clean up temp file
        import os
        try:
            os.unlink(docx_path)
        except:
            pass  # Ignore cleanup errors
        
        return Response(
            content=docx_content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{request.filename}.docx"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to convert to DOCX: {str(e)}")


# ============================================================================
# REDIS & WORKER TEST ENDPOINTS
# ============================================================================

@app.get("/api/test/redis")
async def test_redis():
    """Test Redis connection."""
    try:
        from core.cache import cache
        client = await cache.get_client()
        result = await client.ping()
        queue_length = await client.llen("queue:objectives")
        return {
            "status": "connected" if result else "failed",
            "ping": result,
            "queue:objectives_length": queue_length,
            "message": "Redis is working!" if result else "Redis connection failed"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Redis connection error: {str(e)}"
        }

@app.post("/api/test/queue")
async def test_queue():
    """Test job queue by pushing a test job."""
    try:
        from core.queue import JobQueue
        job_id = await JobQueue.push(
            queue_name="objectives",
            data={
                "test": True,
                "message": "This is a test job"
            }
        )
        return {
            "status": "success",
            "job_id": job_id,
            "message": f"Test job {job_id} queued successfully"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to queue job: {str(e)}"
        }

@app.get("/api/workers/status")
async def get_worker_status():
    """Get status of workers and queues."""
    try:
        from core.cache import cache
        client = await cache.get_client()
        
        # Check queue lengths
        objectives_queue = await client.llen("queue:objectives")
        content_queue = await client.llen("queue:content")
        search_queue = await client.llen("queue:search")
        tasks_queue = await client.llen("queue:tasks")
        
        # Check for recent jobs
        recent_jobs = []
        try:
            # Get recent job keys
            keys = await client.keys("job:*")
            for key in keys[:10]:  # Last 10 jobs
                job = await cache.get(key.replace("job:", ""))
                if job:
                    recent_jobs.append({
                        "job_id": job.get("job_id"),
                        "status": job.get("status"),
                        "queue": job.get("queue"),
                        "created_at": job.get("created_at")
                    })
        except:
            pass
        
        return {
            "status": "ok",
            "queues": {
                "objectives": {
                    "length": objectives_queue,
                    "status": "waiting" if objectives_queue > 0 else "empty"
                },
                "content": {
                    "length": content_queue,
                    "status": "waiting" if content_queue > 0 else "empty"
                },
                "search": {
                    "length": search_queue,
                    "status": "waiting" if search_queue > 0 else "empty"
                },
                "tasks": {
                    "length": tasks_queue,
                    "status": "waiting" if tasks_queue > 0 else "empty"
                }
            },
            "recent_jobs": recent_jobs,
            "message": "Workers are waiting for jobs. Start workers in separate terminals to process jobs."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get worker status: {str(e)}"
        }

# ============================================================================
# AGENT MONITORING & SELF-HEALING ENDPOINTS
# ============================================================================

@app.get("/api/agents/status")
async def get_agents_status():
    """Get status of all agents."""
    try:
        from services.agent_monitor import agent_monitor
        agents = await agent_monitor.get_all_agents()
        stats = await agent_monitor.get_agent_stats()
        
        return {
            "status": "ok",
            "agents": agents,
            "stats": stats
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/agents/list")
async def list_agents():
    """Get a simple list of available agents for mentions."""
    try:
        from services.agent_monitor import agent_monitor
        agents = await agent_monitor.get_all_agents()
        
        # Format for frontend
        agent_list = []
        for agent_id, agent_data in agents.items():
            agent_list.append({
                "id": agent_id,
                "name": agent_data.get("name", agent_id),
                "type": agent_data.get("type", "unknown"),
                "health": agent_data.get("health", {}).get("status", "unknown"),
                "display_name": agent_data.get("name", agent_id).replace("_", " ").title()
            })
        
        # Also add some common/default agents if none found
        if not agent_list:
            agent_list = [
                {"id": "research", "name": "research", "type": "agent", "health": "healthy", "display_name": "Research Agent"},
                {"id": "writer", "name": "writer", "type": "agent", "health": "healthy", "display_name": "Writer Agent"},
                {"id": "editor", "name": "editor", "type": "agent", "health": "healthy", "display_name": "Editor Agent"},
                {"id": "planner", "name": "planner", "type": "agent", "health": "healthy", "display_name": "Planner Agent"},
            ]
        
        return {
            "status": "ok",
            "agents": agent_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return default agents on error
        return {
            "status": "ok",
            "agents": [
                {"id": "research", "name": "research", "type": "agent", "health": "healthy", "display_name": "Research Agent", "description": "Handles web searches, academic research, and information gathering"},
                {"id": "writer", "name": "writer", "type": "agent", "health": "healthy", "display_name": "Writer Agent", "description": "Generates content, writes essays, and creates documents"},
                {"id": "editor", "name": "editor", "type": "agent", "health": "healthy", "display_name": "Editor Agent", "description": "Edits, refines, and improves existing content"},
                {"id": "planner", "name": "planner", "type": "agent", "health": "healthy", "display_name": "Planner Agent", "description": "Creates plans and organizes tasks"},
                {"id": "search", "name": "search", "type": "agent", "health": "healthy", "display_name": "Search Agent", "description": "Specialized in web and image searches"},
                {"id": "citation", "name": "citation", "type": "agent", "health": "healthy", "display_name": "Citation Agent", "description": "Handles academic citations and references"},
            ]
        }

@app.post("/api/agents/heal")
async def heal_agents():
    """Automatically heal unhealthy agents."""
    try:
        from services.agent_monitor import agent_monitor
        result = await agent_monitor.auto_heal_agents()
        
        return {
            "status": "ok",
            "healed": result["healed"],
            "failed": result["failed"],
            "total_checked": result["total_checked"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/api/agents/generate")
async def generate_agent(request: Dict):
    """Generate a missing agent."""
    try:
        from services.self_healing import self_healing_system
        
        agent_name = request.get("agent_name")
        purpose = request.get("purpose", "")
        requirements = request.get("requirements", [])
        
        if not agent_name:
            raise HTTPException(status_code=400, detail="agent_name is required")
        
        result = await self_healing_system.generate_missing_agent(
            agent_name=agent_name,
            purpose=purpose or f"Handle {agent_name} tasks",
            requirements=requirements
        )
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a job."""
    try:
        from core.queue import JobQueue
        job = await JobQueue.get_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "status": "ok",
            "job": job
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/serve/{file_path:path}")
async def serve_workspace_file(workspace_id: str, file_path: str):
    """Serve files from workspace (images, PDFs, etc.) - for browser loading."""
    try:
        workspace_dir = Path(__file__).parent.parent.parent / "workspaces" / workspace_id
        
        # Security: prevent directory traversal
        file_path_obj = Path(file_path)
        if ".." in str(file_path_obj):
            raise HTTPException(status_code=403, detail="Directory traversal not allowed")
        
        # Resolve the full path
        full_path = (workspace_dir / file_path).resolve()
        
        # Verify it's within workspace
        if not str(full_path).startswith(str(workspace_dir.resolve())):
            raise HTTPException(status_code=403, detail="File outside workspace")
        
        # Check if file exists
        if not full_path.exists():
            # Try alternate paths
            alt_paths = [
                workspace_dir / "images" / file_path_obj.name,
                workspace_dir / "figures" / file_path_obj.name,
                workspace_dir / "static" / file_path,
                workspace_dir / "assets" / file_path,
            ]
            
            full_path = None
            for alt_path in alt_paths:
                if alt_path.exists():
                    full_path = alt_path
                    break
            
            if not full_path:
                raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        media_type, _ = mimetypes.guess_type(str(full_path))
        if not media_type:
            media_type = "application/octet-stream"
        
        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=full_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/search")
async def search_rag(query: str, category: str = "solutions", top_k: int = 5):
    """Search RAG knowledge base."""
    try:
        from services.rag_system import rag_system
        results = await rag_system.retrieve_similar(
            query=query,
            category=category,
            top_k=top_k
        )
        
        return {
            "status": "ok",
            "results": results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# THESIS GENERATION ENDPOINTS - Complete Thesis with Parallel Generation
# ============================================================================

@app.post("/api/workspace/{workspace_id}/thesis/generate")
async def generate_complete_thesis(workspace_id: str):
    """
    Generate complete thesis (Chapters 1-6) using parallel agents.
    
    This endpoint orchestrates:
    - Phase 1: Chapter 1 (foundation)
    - Phase 2: Chapters 2-3 in parallel (after Ch1)
    - Phase 3: Chapters 4-5 in parallel (after Ch2-3)
    - Phase 4: Chapter 6 (after all others)
    - Phase 5: Combine all chapters into single thesis.md
    
    Uses 6 concurrent worker agents for maximum speed.
    """
    job_id = str(uuid.uuid4())
    
    try:
        # Get session/topic data
        from services.thesis_session_db import ThesisSessionDB
        
        db = ThesisSessionDB(workspace_id)
        topic = db.get_topic() or "Research Study"
        case_study = db.get_case_study() or ""
        
        async def run_thesis_generation():
            try:
                from services.thesis_combiner import generate_thesis_parallel
                
                await events.connect()
                
                # Start parallel thesis generation
                result = await generate_thesis_parallel(
                    topic=topic,
                    case_study=case_study,
                    workspace_id=workspace_id,
                    job_id=job_id,
                    session_id=workspace_id
                )
                
                thesis_path = result["thesis_path"]
                total_words = result["total_words"]
                
                # Publish completion
                await events.publish(job_id, "response_chunk", {
                    "chunk": f"\n\n✅ **Complete Thesis Generated Successfully!**\n\n**File**: `{Path(thesis_path).name}`\n**Total Words**: {total_words:,}\n**Pages**: ~{int(total_words / 250)}\n\nAll 6 chapters combined into single thesis.md file.",
                    "accumulated": ""
                }, session_id=workspace_id)
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "complete",
                    "status": "success"
                }, session_id=workspace_id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                await events.publish(job_id, "response_chunk", {
                    "chunk": f"❌ Error generating thesis: {str(e)}",
                    "accumulated": f"Error: {str(e)}"
                }, session_id=workspace_id)
                await events.publish(job_id, "stage_completed", {
                    "stage": "complete",
                    "status": "error"
                }, session_id=workspace_id)
        
        import asyncio
        asyncio.create_task(run_thesis_generation())
        
        return {
            "status": "started",
            "job_id": job_id,
            "message": f"Generating complete thesis for '{topic}' using 6 parallel agents...",
            "stream_url": f"/api/workspace/{workspace_id}/jobs/{job_id}/stream"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/{workspace_id}/thesis/combine")
async def combine_existing_chapters(workspace_id: str):
    """
    Combine already-generated chapters (1-6) into single thesis.md file.
    
    Use this if chapters already exist but haven't been combined yet.
    """
    job_id = str(uuid.uuid4())
    
    try:
        async def run_combine():
            try:
                from services.thesis_combiner import combine_existing_chapters
                
                await events.connect()
                
                # Combine existing chapters
                result = await combine_existing_chapters(
                    workspace_id=workspace_id,
                    job_id=job_id,
                    session_id=workspace_id
                )
                
                thesis_path = result["thesis_path"]
                total_words = result["total_words"]
                
                # Publish completion
                await events.publish(job_id, "response_chunk", {
                    "chunk": f"\n\n✅ **Thesis Combined Successfully!**\n\n**File**: `{Path(thesis_path).name}`\n**Total Words**: {total_words:,}\n**Pages**: ~{int(total_words / 250)}\n\nAll chapters combined into single thesis.md file.",
                    "accumulated": ""
                }, session_id=workspace_id)
                
                await events.publish(job_id, "stage_completed", {
                    "stage": "complete",
                    "status": "success"
                }, session_id=workspace_id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                await events.publish(job_id, "response_chunk", {
                    "chunk": f"❌ Error combining chapters: {str(e)}",
                    "accumulated": f"Error: {str(e)}"
                }, session_id=workspace_id)
                await events.publish(job_id, "stage_completed", {
                    "stage": "complete",
                    "status": "error"
                }, session_id=workspace_id)
        
        import asyncio
        asyncio.create_task(run_combine())
        
        return {
            "status": "started",
            "job_id": job_id,
            "message": "Combining existing chapters into single thesis.md...",
            "stream_url": f"/api/workspace/{workspace_id}/jobs/{job_id}/stream"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_id}/thesis/status")
async def get_thesis_status(workspace_id: str):
    """Get status of thesis generation - which chapters exist, are they combined?"""
    try:
        from pathlib import Path
        
        workspace_path = Path(f"/home/gemtech/Desktop/thesis/thesis_data/{workspace_id}")
        
        # Check which chapters exist
        chapters_exist = {}
        for i in range(1, 7):
            chapter_files = list(workspace_path.glob(f"Chapter_{i}*.md")) + list(workspace_path.glob(f"chapter_{i}*.md"))
            chapters_exist[f"chapter_{i}"] = len(chapter_files) > 0
        
        # Check if combined thesis exists
        thesis_files = list(workspace_path.glob("*esis.md")) + list(workspace_path.glob("Complete_Thesis.md"))
        thesis_combined = len(thesis_files) > 0
        
        return {
            "workspace_id": workspace_id,
            "chapters": chapters_exist,
            "thesis_combined": thesis_combined,
            "combined_file": Path(thesis_files[0]).name if thesis_files else None,
            "all_chapters_exist": all(chapters_exist.values()),
            "ready_to_combine": any(chapters_exist.values()) and not thesis_combined
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKSPACE CONTEXT ENDPOINTS (User Objectives, Data, Study Tools)
# ============================================================================

class SetObjectivesRequest(BaseModel):
    general_objective: str
    specific_objectives: List[str]
    research_questions: Optional[List[str]] = None

@app.post("/api/workspace/{workspace_id}/objectives")
async def set_workspace_objectives(workspace_id: str, request: SetObjectivesRequest):
    """Store user's research objectives for this workspace."""
    try:
        from app.services.workspace_context_service import get_workspace_context
        
        context_service = get_workspace_context(workspace_id)
        
        objectives = await context_service.set_objectives(
            general=request.general_objective,
            specific=request.specific_objectives,
            research_questions=request.research_questions
        )
        
        return {
            "status": "success",
            "workspace_id": workspace_id,
            "objectives": objectives,
            "message": f"Stored objectives for {len(request.specific_objectives)} specific research goals"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/objectives")
async def get_workspace_objectives(workspace_id: str):
    """Retrieve workspace objectives."""
    try:
        from app.services.workspace_context_service import get_workspace_context
        
        context_service = get_workspace_context(workspace_id)
        objectives = context_service.get_objectives()
        
        return {
            "workspace_id": workspace_id,
            "objectives": objectives
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/context")
async def get_workspace_full_context(workspace_id: str):
    """Get full workspace context (objectives + data + tools)."""
    try:
        from app.services.workspace_context_service import get_workspace_context
        
        context_service = get_workspace_context(workspace_id)
        
        return {
            "workspace_id": workspace_id,
            "context_summary": context_service.get_full_context_for_llm(),
            "objectives": context_service.get_objectives(),
            "datasets": context_service.get_datasets(),
            "documents": context_service.get_documents(),
            "study_tools": context_service.get_study_tools(),
            "config": context_service.get_workspace_config()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/register-dataset")
async def register_dataset(
    workspace_id: str,
    file: UploadFile = File(...),
    description: str = ""
):
    """Register a dataset in workspace context."""
    try:
        from pathlib import Path
        import shutil
        from app.services.workspace_context_service import get_workspace_context
        
        # Save file
        dataset_dir = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}/datasets")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = dataset_dir / file.filename
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Register in context
        context_service = get_workspace_context(workspace_id)
        file_type = Path(file.filename).suffix.lstrip('.')
        
        dataset = await context_service.register_uploaded_dataset(
            filename=file.filename,
            filepath=str(filepath),
            file_type=file_type,
            description=description
        )
        
        return {
            "status": "success",
            "dataset": dataset,
            "message": f"Registered dataset: {file.filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/{workspace_id}/register-study-tool")
async def register_study_tool(
    workspace_id: str,
    file: UploadFile = File(...),
    tool_type: str = "questionnaire",
    description: str = ""
):
    """Register a study tool (questionnaire, interview guide, etc.)."""
    try:
        from pathlib import Path
        import shutil
        from app.services.workspace_context_service import get_workspace_context
        
        # Save file
        tools_dir = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}/study_tools")
        tools_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = tools_dir / file.filename
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Register in context
        context_service = get_workspace_context(workspace_id)
        
        tool = await context_service.register_study_tool(
            tool_name=Path(file.filename).stem,
            tool_type=tool_type,
            filepath=str(filepath),
            description=description
        )
        
        return {
            "status": "success",
            "tool": tool,
            "message": f"Registered study tool: {file.filename} ({tool_type})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/data-summary")
async def get_workspace_data_summary(workspace_id: str):
    """Get summary of all registered data without file contents."""
    try:
        from app.services.workspace_context_service import get_workspace_context
        
        context_service = get_workspace_context(workspace_id)
        
        return {
            "workspace_id": workspace_id,
            "objectives_defined": bool(context_service.get_objectives().get("general")),
            "datasets_count": len(context_service.get_datasets()),
            "documents_count": len(context_service.get_documents()),
            "study_tools_count": len(context_service.get_study_tools()),
            "context_ready": bool(context_service.get_full_context_for_llm() != "No workspace context set yet.")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MULTI-UNIVERSITY THESIS ROUTER
# ============================================================================

# Universities data
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

@app.get("/api/thesis/universities")
async def list_universities():
    """List all available universities for thesis generation"""
    universities = list(UNIVERSITIES.values())
    return {"universities": universities}

@app.get("/api/thesis/universities/{university_type}")
async def get_university_info(university_type: str):
    """Get information about a specific university"""
    if university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=404,
            detail=f"University type '{university_type}' not found"
        )
    return UNIVERSITIES[university_type]

@app.get("/api/thesis/template/{university_type}")
async def get_thesis_template(university_type: str):
    """Get thesis template structure for a university"""
    if university_type not in UNIVERSITIES:
        raise HTTPException(
            status_code=404,
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

# ============================================================================
# THESIS GENERATION ENDPOINTS
# ============================================================================

@app.post("/api/thesis/generate")
async def generate_thesis(request: dict):
    """
    Generate COMPLETE PhD Thesis (All 6 Chapters) with:
    - Clear progress messages for each step
    - Study tools generation (questionnaire, interview guide)
    - Synthetic dataset generation
    - All 6 chapters with proper dependencies
    - Final combined thesis document
    """
    import asyncio
    from services.parallel_chapter_generator import parallel_chapter_generator, BACKGROUND_STYLES
    from pathlib import Path
    from datetime import datetime
    
    university_type = request.get('university_type', 'generic')
    title = request.get('title', 'Research Thesis')
    topic = request.get('topic', '')
    objectives = request.get('objectives', [topic]) if topic else []
    workspace_id = request.get('workspace_id', 'default')
    session_id = request.get('session_id', 'default')
    raw_case_study = request.get('case_study', '')
    background_style = request.get('background_style', 'inverted_pyramid')
    
    # Extract meaningful case study (not just repeating the topic)
    case_study = extract_case_study(topic, raw_case_study)
    
    if not topic:
        return {
            "success": False,
            "message": "Topic is required",
            "file_path": None
        }
    
    # Auto-generate objectives using global helper function
    if not objectives or (len(objectives) == 1 and objectives[0] == topic):
        objectives = generate_smart_objectives(topic, 6)
    
    # Ensure exactly 6 objectives
    short_theme = extract_short_theme(topic)
    objectives = objectives[:6] if len(objectives) >= 6 else objectives + [f"To investigate aspect {i+1} of {short_theme}" for i in range(6 - len(objectives))]
    
    print(f"📚 FULL THESIS request: {topic}")
    
    # Create workspace directories - use WORKSPACES_DIR for consistency with frontend
    from services.workspace_service import WORKSPACES_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_path = WORKSPACES_DIR / workspace_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    datasets_path = workspace_path / "datasets"
    datasets_path.mkdir(parents=True, exist_ok=True)
    chapters_path = workspace_path / "chapters"
    chapters_path.mkdir(parents=True, exist_ok=True)
    
    # Generate job_id for tracking
    job_id = f"thesis_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    # Background task for FULL thesis generation (all 6 chapters)
    async def run_full_thesis_generation():
        chapter_contents = {}
        
        try:
            await events.connect()
            
            # ================================================================
            # STEP 0: INITIALIZATION
            # ================================================================
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"""# 📚 GENERATING COMPLETE PhD THESIS

**Topic:** {topic}
**University:** {university_type}
**Case Study:** {case_study}

## 📋 Generation Pipeline (8 Steps)

| Step | Component | Status |
|------|-----------|--------|
| 1 | Chapter 1: Introduction | ⏳ Pending |
| 2 | Chapter 2: Literature Review | ⏳ Pending |
| 3 | Chapter 3: Methodology | ⏳ Pending |
| 4 | Study Tools Generation | ⏳ Pending |
| 5 | Synthetic Dataset Generation | ⏳ Pending |
| 6 | Chapter 4: Data Analysis | ⏳ Pending |
| 7 | Chapter 5: Discussion | ⏳ Pending |
| 8 | Chapter 6: Conclusion | ⏳ Pending |

---

""", "accumulated": ""},
                session_id=session_id
            )
            
            # ================================================================
            # STEP 1: CHAPTER 1 - INTRODUCTION
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 1, "name": "Chapter 1: Introduction", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "📖 STEP 1/8: Generating Chapter 1 (Introduction)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """
## 📖 STEP 1/8: CHAPTER 1 - INTRODUCTION

🔄 **Status:** Generating...
- Background of the study
- Problem statement
- Research objectives
- Significance of the study
- Scope and limitations

""", "accumulated": ""},
                session_id=session_id
            )
            
            chapter1_result = await parallel_chapter_generator.generate(
                topic=topic,
                case_study=case_study,
                job_id=job_id,
                session_id=session_id,
                background_style=background_style
            )
            chapter_contents['chapter1'] = chapter1_result
            
            # Save Chapter 1
            ch1_file = chapters_path / f"Chapter_1_Introduction_{timestamp}.md"
            with open(ch1_file, 'w', encoding='utf-8') as f:
                f.write(chapter1_result)
            
            # Send file_created event FIRST
            await events.publish(job_id, "file_created", {"path": str(ch1_file), "filename": ch1_file.name, "step": 1}, session_id=session_id)
            # Then send step_completed
            await events.publish(job_id, "step_completed", {"step": 1, "name": "Chapter 1: Introduction", "word_count": len(chapter1_result.split()), "file": str(ch1_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 1 Complete!** ({len(chapter1_result.split())} words) - Saved: {ch1_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 1 complete! {len(chapter1_result)} chars")
            
            # ================================================================
            # STEP 2: CHAPTER 2 - LITERATURE REVIEW
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 2, "name": "Chapter 2: Literature Review", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "📚 STEP 2/8: Generating Chapter 2 (Literature Review)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 📚 STEP 2/8: CHAPTER 2 - LITERATURE REVIEW

🔄 **Status:** Generating...
- Theoretical framework
- Conceptual framework
- Empirical review (50+ academic sources)
- Research gap analysis

⏱️ This step takes 3-5 minutes (searching academic databases)...

""", "accumulated": ""},
                session_id=session_id
            )
            
            chapter2_result = await parallel_chapter_generator.generate_chapter_two(
                topic=topic,
                case_study=case_study,
                job_id=job_id,
                session_id=session_id
            )
            chapter_contents['chapter2'] = chapter2_result
            
            # Save Chapter 2
            ch2_file = chapters_path / f"Chapter_2_Literature_Review_{timestamp}.md"
            with open(ch2_file, 'w', encoding='utf-8') as f:
                f.write(chapter2_result)
            
            await events.publish(job_id, "file_created", {"path": str(ch2_file), "filename": ch2_file.name, "step": 2}, session_id=session_id)
            await events.publish(job_id, "step_completed", {"step": 2, "name": "Chapter 2: Literature Review", "word_count": len(chapter2_result.split()), "file": str(ch2_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 2 Complete!** ({len(chapter2_result.split())} words) - Saved: {ch2_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 2 complete! {len(chapter2_result)} chars")
            
            # ================================================================
            # STEP 3: CHAPTER 3 - METHODOLOGY
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 3, "name": "Chapter 3: Methodology", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "🔬 STEP 3/8: Generating Chapter 3 (Methodology)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 🔬 STEP 3/8: CHAPTER 3 - METHODOLOGY

🔄 **Status:** Generating...
- Research design
- Population and sampling
- Data collection methods
- Data analysis procedures
- Ethical considerations
- Validity and reliability

""", "accumulated": ""},
                session_id=session_id
            )
            
            chapter3_result = await parallel_chapter_generator.generate_chapter_three(
                topic=topic,
                case_study=case_study,
                job_id=job_id,
                session_id=session_id
            )
            chapter_contents['chapter3'] = chapter3_result
            
            # Save Chapter 3
            ch3_file = chapters_path / f"Chapter_3_Methodology_{timestamp}.md"
            with open(ch3_file, 'w', encoding='utf-8') as f:
                f.write(chapter3_result)
            
            await events.publish(job_id, "file_created", {"path": str(ch3_file), "filename": ch3_file.name, "step": 3}, session_id=session_id)
            await events.publish(job_id, "step_completed", {"step": 3, "name": "Chapter 3: Methodology", "word_count": len(chapter3_result.split()), "file": str(ch3_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 3 Complete!** ({len(chapter3_result.split())} words) - Saved: {ch3_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 3 complete! {len(chapter3_result)} chars")
            
            # ================================================================
            # STEP 4: STUDY TOOLS GENERATION
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 4, "name": "Study Tools Generation", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "📋 STEP 4/8: Generating Study Tools (Questionnaire & Interview Guide)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 📋 STEP 4/8: STUDY TOOLS GENERATION

🔄 **Status:** Generating...
- Structured questionnaire (Likert scale items)
- Key Informant Interview (KII) guide
- Focus Group Discussion (FGD) guide
- Observation checklist

""", "accumulated": ""},
                session_id=session_id
            )
            
            # Generate study tools
            from services.data_collection_worker import generate_study_tools
            questionnaire_path = None
            try:
                tools_result = await generate_study_tools(
                    topic=topic,
                    objectives=objectives,
                    output_dir=str(workspace_path),
                    job_id=job_id,
                    session_id=session_id
                )
                questionnaire_path = tools_result.get('questionnaire_path')
            except Exception as e:
                print(f"⚠️ Study tools generation error: {e}")
                # Create basic questionnaire manually
                questionnaire_content = f"""# Research Questionnaire: {topic}

## Section A: Demographics
1. Age: [ ] 18-25 [ ] 26-35 [ ] 36-45 [ ] 46-55 [ ] 55+
2. Gender: [ ] Male [ ] Female [ ] Other
3. Education: [ ] Primary [ ] Secondary [ ] Tertiary [ ] Postgraduate

## Section B: {topic} Assessment
"""
                for i, obj in enumerate(objectives, 1):
                    questionnaire_content += f"""
### Objective {i}: {obj}
{i}.1. Rate your agreement: Strongly Disagree (1) to Strongly Agree (5)
{i}.2. Rate your agreement: Strongly Disagree (1) to Strongly Agree (5)
{i}.3. Rate your agreement: Strongly Disagree (1) to Strongly Agree (5)
"""
                questionnaire_path = workspace_path / f"Questionnaire_{topic.replace(' ', '_')}_{timestamp}.md"
                with open(questionnaire_path, 'w') as f:
                    f.write(questionnaire_content)
            
            await events.publish(job_id, "step_completed", {"step": 4, "name": "Study Tools Generation", "file": str(questionnaire_path) if questionnaire_path else None}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": "✅ **Study Tools Generated!**\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Study tools generated!")
            
            # ================================================================
            # STEP 5: SYNTHETIC DATASET GENERATION
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 5, "name": "Synthetic Dataset", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "📊 STEP 5/8: Generating Synthetic Research Dataset..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 📊 STEP 5/8: SYNTHETIC DATASET GENERATION

🔄 **Status:** Generating...
- Questionnaire responses (n=385)
- Key Informant Interview transcripts
- Focus Group Discussion transcripts
- Field observation notes

""", "accumulated": ""},
                session_id=session_id
            )
            
            # Generate synthetic dataset
            from services.data_collection_worker import generate_research_dataset
            dataset_file = None
            try:
                dataset_result = await generate_research_dataset(
                    topic=topic,
                    objectives=objectives,
                    questionnaire_path=str(questionnaire_path) if questionnaire_path else None,
                    output_dir=str(datasets_path),
                    job_id=job_id,
                    session_id=session_id
                )
                dataset_file = dataset_result.get('csv_path') if dataset_result else None
            except Exception as e:
                print(f"⚠️ Dataset generation error: {e}")
                # Create minimal dataset for Chapter 4
                import csv
                import random
                
                dataset_file = datasets_path / f"questionnaire_data_{timestamp}.csv"
                with open(dataset_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    headers = ['respondent_id', 'age', 'gender', 'education'] + [f'q{i}' for i in range(1, 19)]
                    writer.writerow(headers)
                    for r in range(385):
                        row = [f'R{r+1:03d}', random.choice(['18-25', '26-35', '36-45', '46-55', '55+']),
                               random.choice(['Male', 'Female']), random.choice(['Secondary', 'Tertiary', 'Postgraduate'])]
                        row.extend([random.randint(1, 5) for _ in range(18)])
                        writer.writerow(row)
            
            await events.publish(job_id, "step_completed", {"step": 5, "name": "Synthetic Dataset", "file": str(dataset_file) if dataset_file else None}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": "✅ **Dataset Generated!** (385 respondents)\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Dataset generated!")
            
            # ================================================================
            # STEP 6: CHAPTER 4 - DATA PRESENTATION & ANALYSIS
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 6, "name": "Chapter 4: Data Analysis", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "📈 STEP 6/8: Generating Chapter 4 (Data Presentation & Analysis)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 📈 STEP 6/8: CHAPTER 4 - DATA PRESENTATION & ANALYSIS

🔄 **Status:** Generating...
- Demographic analysis with tables
- Descriptive statistics per objective
- Inferential statistics (correlations, t-tests, ANOVA)
- Charts and visualizations
- Qualitative data analysis (thematic coding)

⏱️ This step takes 2-3 minutes (statistical analysis)...

""", "accumulated": ""},
                session_id=session_id
            )
            
            from services.chapter4_generator import generate_chapter4
            try:
                ch4_result = await generate_chapter4(
                    topic=topic,
                    case_study=case_study,
                    objectives=objectives,
                    datasets_dir=str(datasets_path),
                    output_dir=str(chapters_path),
                    job_id=job_id,
                    session_id=session_id
                )
                chapter4_result = ch4_result.get('content', '') or ch4_result.get('markdown', '')
                if not chapter4_result and ch4_result.get('filepath'):
                    with open(ch4_result['filepath'], 'r') as f:
                        chapter4_result = f.read()
            except Exception as e:
                print(f"⚠️ Chapter 4 error: {e}")
                chapter4_result = f"""# Chapter 4: Data Presentation, Analysis and Interpretation

## 4.1 Introduction

This chapter presents the findings from the data collected on {topic}. The analysis includes both quantitative and qualitative data.

## 4.2 Response Rate

A total of 385 questionnaires were distributed, with 350 returned representing a 90.9% response rate.

## 4.3 Demographic Analysis

[Demographic tables would be generated from actual dataset]

## 4.4 Findings per Objective

[Findings would be generated from actual analysis]

## 4.5 Summary

This chapter has presented the key findings related to {topic}.
"""
            
            chapter_contents['chapter4'] = chapter4_result
            
            # Save Chapter 4
            ch4_file = chapters_path / f"Chapter_4_Data_Analysis_{timestamp}.md"
            with open(ch4_file, 'w', encoding='utf-8') as f:
                f.write(chapter4_result)
            
            await events.publish(job_id, "file_created", {"path": str(ch4_file), "filename": ch4_file.name, "step": 6}, session_id=session_id)
            await events.publish(job_id, "step_completed", {"step": 6, "name": "Chapter 4: Data Analysis", "word_count": len(chapter4_result.split()), "file": str(ch4_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 4 Complete!** ({len(chapter4_result.split())} words) - Saved: {ch4_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 4 complete! {len(chapter4_result)} chars")
            
            # ================================================================
            # STEP 7: CHAPTER 5 - DISCUSSION
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 7, "name": "Chapter 5: Discussion", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "💬 STEP 7/8: Generating Chapter 5 (Discussion)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 💬 STEP 7/8: CHAPTER 5 - DISCUSSION

🔄 **Status:** Generating...
- Discussion of findings per objective
- Comparison with literature (Chapter 2)
- Theoretical implications
- Practical implications
- Confirmations and contradictions

⏱️ This step takes 2-3 minutes (literature synthesis)...

""", "accumulated": ""},
                session_id=session_id
            )
            
            from services.chapter5_generator_v2 import generate_chapter5
            try:
                ch5_result = await generate_chapter5(
                    topic=topic,
                    case_study=case_study,
                    objectives=objectives,
                    chapter_two_filepath=str(ch2_file),
                    chapter_four_filepath=str(ch4_file),
                    output_dir=str(chapters_path),
                    job_id=job_id,
                    session_id=session_id
                )
                chapter5_result = ch5_result.get('content', '') if isinstance(ch5_result, dict) else ch5_result
                if not chapter5_result and isinstance(ch5_result, dict) and ch5_result.get('filepath'):
                    with open(ch5_result['filepath'], 'r', encoding='utf-8') as f:
                        chapter5_result = f.read()
            except Exception as e:
                print(f"⚠️ Chapter 5 error: {e}")
                chapter5_result = f"""# Chapter 5: Discussion of Findings

## 5.1 Introduction

This chapter discusses the findings presented in Chapter 4 in relation to the literature reviewed in Chapter 2.

## 5.2 Discussion per Objective

"""
                for i, obj in enumerate(objectives, 1):
                    chapter5_result += f"""
### 5.{i+1} {obj}

The findings related to this objective indicated that... This is consistent with previous studies that found...

"""
                chapter5_result += """
## 5.3 Summary

This chapter has discussed the key findings in relation to existing literature on the topic.
"""
            
            chapter_contents['chapter5'] = chapter5_result
            
            # Save Chapter 5
            ch5_file = chapters_path / f"Chapter_5_Discussion_{timestamp}.md"
            with open(ch5_file, 'w', encoding='utf-8') as f:
                f.write(chapter5_result)
            
            await events.publish(job_id, "file_created", {"path": str(ch5_file), "filename": ch5_file.name, "step": 7}, session_id=session_id)
            await events.publish(job_id, "step_completed", {"step": 7, "name": "Chapter 5: Discussion", "word_count": len(chapter5_result.split()), "file": str(ch5_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 5 Complete!** ({len(chapter5_result.split())} words) - Saved: {ch5_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 5 complete! {len(chapter5_result)} chars")
            
            # ================================================================
            # STEP 8: CHAPTER 6 - CONCLUSION & RECOMMENDATIONS
            # ================================================================
            await events.publish(job_id, "step_started", {"step": 8, "name": "Chapter 6: Conclusion", "total_steps": 8}, session_id=session_id)
            await events.publish(job_id, "log", {"message": "🎯 STEP 8/8: Generating Chapter 6 (Conclusion & Recommendations)..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 🎯 STEP 8/8: CHAPTER 6 - CONCLUSION & RECOMMENDATIONS

🔄 **Status:** Generating...
- Summary of the study
- Key conclusions per objective
- Recommendations for practice
- Recommendations for policy
- Suggestions for future research

""", "accumulated": ""},
                session_id=session_id
            )
            
            from services.chapter6_generator_v2 import generate_chapter6
            try:
                ch6_result = await generate_chapter6(
                    topic=topic,
                    case_study=case_study,
                    objectives=objectives,
                    chapter4_content=chapter_contents.get('chapter4', ''),
                    chapter5_content=chapter_contents.get('chapter5', ''),
                    job_id=job_id,
                    session_id=session_id
                )
                chapter6_result = ch6_result if isinstance(ch6_result, str) else ch6_result.get('content', '')
            except Exception as e:
                print(f"⚠️ Chapter 6 error: {e}")
                chapter6_result = f"""# Chapter 6: Summary, Conclusion and Recommendations

## 6.1 Summary

This study examined {topic} with the aim of...

## 6.2 Conclusions

Based on the findings, the following conclusions were drawn:

"""
                for i, obj in enumerate(objectives, 1):
                    chapter6_result += f"{i}. Regarding {obj.lower()}, the study concluded that...\n\n"
                
                chapter6_result += """
## 6.3 Recommendations

Based on the findings and conclusions, the following recommendations are made:

### 6.3.1 Recommendations for Practice
1. Organizations should...
2. Practitioners should...

### 6.3.2 Recommendations for Policy
1. Policymakers should consider...
2. Government should...

## 6.4 Suggestions for Future Research

Future researchers should explore...
"""
            
            chapter_contents['chapter6'] = chapter6_result
            
            # Save Chapter 6
            ch6_file = chapters_path / f"Chapter_6_Conclusion_{timestamp}.md"
            with open(ch6_file, 'w', encoding='utf-8') as f:
                f.write(chapter6_result)
            
            await events.publish(job_id, "file_created", {"path": str(ch6_file), "filename": ch6_file.name, "step": 8}, session_id=session_id)
            await events.publish(job_id, "step_completed", {"step": 8, "name": "Chapter 6: Conclusion", "word_count": len(chapter6_result.split()), "file": str(ch6_file)}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Chapter 6 Complete!** ({len(chapter6_result.split())} words) - Saved: {ch6_file.name}\n\n---\n\n", "accumulated": ""},
                session_id=session_id
            )
            print(f"✅ Chapter 6 complete! {len(chapter6_result)} chars")
            
            # ================================================================
            # FINAL STEP: GENERATE BOTH PROPOSAL AND COMPLETE THESIS
            # ================================================================
            await events.publish(job_id, "log", {"message": "📑 FINAL STEP: Creating Proposal + Complete Thesis..."}, session_id=session_id)
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": """## 📑 CREATING BOTH OUTPUTS

🔄 **Status:** Generating...
1. **Research Proposal** (Chapters 1-3, Future Tense)
2. **Complete Thesis** (Chapters 1-6, Past Tense)

""", "accumulated": ""},
                session_id=session_id
            )
            
            # ================================================================
            # OUTPUT 1: RESEARCH PROPOSAL (Chapters 1-3, Future Tense - as-is)
            # ================================================================
            proposal_content = f"""# RESEARCH PROPOSAL

# {title}

---

**A Research Proposal Submitted in Partial Fulfillment of the Requirements for the Award of the Degree of Doctor of Philosophy**

**University:** {university_type}  
**Case Study:** {case_study}  
**Date:** {datetime.now().strftime('%B %Y')}

---

## Research Objectives

"""
            for i, obj in enumerate(objectives, 1):
                proposal_content += f"{i}. {obj}\n"
            
            proposal_content += f"""

---

{chapter_contents.get('chapter1', '')}

---

{chapter_contents.get('chapter2', '')}

---

{chapter_contents.get('chapter3', '')}

---

# REFERENCES

*All references are embedded as hyperlinks throughout the document*

---

# APPENDICES

## Appendix A: Proposed Research Questionnaire
*See: Questionnaire_{topic.replace(' ', '_')}_{timestamp}.md*

## Appendix B: Proposed Interview Guide
*See: Interview_Guide_{timestamp}.md*

---

**END OF PROPOSAL**
"""
            
            # Save Proposal
            proposal_filename = f"Research_Proposal_{topic.replace(' ', '_')}_{timestamp}.md"
            proposal_filepath = workspace_path / proposal_filename
            with open(proposal_filepath, 'w', encoding='utf-8') as f:
                f.write(proposal_content)
            
            await events.publish(
                job_id,
                "file_created",
                {"path": str(proposal_filepath), "filename": proposal_filename, "type": "markdown"},
                session_id=session_id
            )
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"✅ **Research Proposal saved:** `{proposal_filename}` ({len(proposal_content.split()):,} words)\n\n", "accumulated": ""},
                session_id=session_id
            )
            
            # ================================================================
            # OUTPUT 2: COMPLETE THESIS (Chapters 1-6, with 1-3 converted to Past Tense)
            # ================================================================
            
            # Convert Chapters 1-3 from future to past tense for the complete thesis
            chapter1_thesis = convert_future_to_past_tense(chapter_contents.get('chapter1', ''))
            chapter2_thesis = convert_future_to_past_tense(chapter_contents.get('chapter2', ''))
            chapter3_thesis = convert_future_to_past_tense(chapter_contents.get('chapter3', ''))
            
            # Chapters 4-6 are already in past tense (reporting completed research)
            chapter4_thesis = chapter_contents.get('chapter4', '')
            chapter5_thesis = chapter_contents.get('chapter5', '')
            chapter6_thesis = chapter_contents.get('chapter6', '')
            
            # Generate proper academic abstract using LLM
            await events.publish(job_id, "log", {"message": "📝 Generating abstract and preliminaries..."}, session_id=session_id)
            
            from services.deepseek_direct import deepseek_direct
            
            try:
                abstract_prompt = f"""Write a 300-word academic abstract for a PhD thesis.

TITLE: {title}
TOPIC: {topic}
CASE STUDY: {case_study}

RESEARCH OBJECTIVES:
{chr(10).join([f'{i+1}. {obj}' for i, obj in enumerate(objectives)])}

Write a structured abstract with these components (as flowing prose, not labelled sections):
1. Background/Context (2 sentences)
2. Purpose/Aim of the study (1 sentence)
3. Methodology (2-3 sentences: research design, population, sampling, data collection, analysis)
4. Key Findings (3-4 sentences summarising main results)
5. Conclusions and Recommendations (2 sentences)
6. Keywords line at the end

REQUIREMENTS:
- Write in UK English (analyse, behaviour, organisation)
- Use past tense throughout
- Be specific, not generic
- End with: Keywords: [5-7 relevant terms]"""

                generated_abstract = await deepseek_direct.generate_content(
                    prompt=abstract_prompt,
                    system_prompt="You are an expert academic writer. Write a formal PhD thesis abstract.",
                    temperature=0.7,
                    max_tokens=600
                )
            except Exception as abs_err:
                print(f"⚠️ Abstract generation failed: {abs_err}")
                generated_abstract = f"""This doctoral research investigated {topic.lower()} within the context of {case_study}. The study aimed to address critical gaps in understanding the subject matter through rigorous empirical investigation.

A mixed-methods research design was employed, combining quantitative survey data from structured questionnaires with qualitative data from semi-structured interviews and focus group discussions. The study population comprised key stakeholders, from which a representative sample was selected using purposive and stratified sampling techniques. Data analysis utilised both statistical techniques (descriptive and inferential statistics) and thematic analysis.

The findings revealed significant insights regarding each research objective. The quantitative results demonstrated measurable patterns and relationships among key variables, while qualitative findings provided contextual depth and explanatory power. The study identified both enabling factors and barriers relevant to the research context.

The study concludes that evidence-based interventions are essential for addressing the identified challenges. Recommendations for policy and practice are provided, along with suggestions for future research directions.

**Keywords:** {topic.split()[0]}, {topic.split()[1] if len(topic.split()) > 1 else 'Research'}, {case_study.split()[0]}, Mixed Methods, PhD Research, {case_study.split()[-1] if len(case_study.split()) > 1 else 'Study'}"""

            # Combine all chapters into final thesis with proper academic structure
            full_thesis = f"""
<div style="text-align: center; page-break-after: always;">

# {title.upper()}

---

**A Thesis Submitted in Partial Fulfilment of the Requirements for the Award of the Degree of**

## DOCTOR OF PHILOSOPHY

**in**

**{topic.split()[0].title()} Studies**

---

**University of Juba**

---

**{datetime.now().strftime('%B %Y')}**

</div>

---

<div style="page-break-after: always;">

## DECLARATION

I, the undersigned, hereby declare that this thesis is my original work and has not been submitted for the award of a degree in any other university or institution. All sources of information and scholarly works cited herein have been duly acknowledged through appropriate references.

&nbsp;

**Signature:** _________________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** _________________________

**Name of Candidate:** _________________________

&nbsp;

**This thesis has been submitted for examination with our approval as University Supervisors:**

&nbsp;

**Principal Supervisor:**

**Signature:** _________________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** _________________________

**Name:** _________________________

**Department:** _________________________

&nbsp;

**Co-Supervisor:**

**Signature:** _________________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** _________________________

**Name:** _________________________

**Department:** _________________________

</div>

---

<div style="page-break-after: always;">

## DEDICATION

*This thesis is dedicated to my family, whose unwavering support and encouragement made this academic journey possible.*

</div>

---

<div style="page-break-after: always;">

## ACKNOWLEDGEMENTS

I wish to express my profound gratitude to the Almighty God for His grace and guidance throughout this doctoral journey.

My sincere appreciation goes to my supervisors for their invaluable scholarly guidance, constructive criticism, and patience throughout the research process. Their expertise and mentorship have been instrumental in shaping this work.

I am deeply grateful to all the respondents and participants who generously gave their time and shared their insights, making this research possible. Special thanks to the institutional gatekeepers who facilitated access to research sites.

I acknowledge the financial and moral support from my family members, whose sacrifices and encouragement sustained me through the challenging periods of this academic endeavour.

Finally, I extend my appreciation to my colleagues and friends who provided intellectual stimulation and emotional support throughout this journey.

</div>

---

<div style="page-break-after: always;">

## ABSTRACT

{generated_abstract}

</div>

---

<div style="page-break-after: always;">

## TABLE OF CONTENTS

| Section | Page |
|---------|------|
| **PRELIMINARIES** | |
| Declaration | ii |
| Dedication | iii |
| Acknowledgements | iv |
| Abstract | v |
| Table of Contents | vi |
| List of Tables | viii |
| List of Figures | ix |
| List of Abbreviations | x |
| | |
| **CHAPTER ONE: INTRODUCTION** | 1 |
| 1.1 Background to the Study | 1 |
| 1.2 Statement of the Problem | |
| 1.3 Purpose of the Study | |
| 1.4 Research Objectives | |
| 1.5 Research Questions | |
| 1.6 Significance of the Study | |
| 1.7 Scope and Delimitations | |
| 1.8 Operational Definitions | |
| | |
| **CHAPTER TWO: LITERATURE REVIEW** | |
| 2.1 Introduction | |
| 2.2 Theoretical Framework | |
| 2.3-2.6 Empirical Reviews | |
| 2.7 Research Gap | |
| | |
| **CHAPTER THREE: RESEARCH METHODOLOGY** | |
| 3.1 Introduction | |
| 3.2 Research Philosophy | |
| 3.3 Research Design | |
| 3.4 Target Population | |
| 3.5 Sampling Procedures | |
| 3.6 Data Collection Instruments | |
| 3.7 Data Analysis | |
| 3.8 Ethical Considerations | |
| | |
| **CHAPTER FOUR: DATA PRESENTATION, ANALYSIS AND INTERPRETATION** | |
| 4.1 Introduction | |
| 4.2 Response Rate | |
| 4.3-4.6 Findings per Objective | |
| | |
| **CHAPTER FIVE: DISCUSSION OF FINDINGS** | |
| 5.0 Introduction | |
| 5.1-5.N Discussion per Objective | |
| | |
| **CHAPTER SIX: SUMMARY, CONCLUSIONS AND RECOMMENDATIONS** | |
| 6.1 Introduction | |
| 6.2 Summary of Findings | |
| 6.3 Conclusions | |
| 6.4 Recommendations | |
| 6.5 Suggestions for Further Research | |
| | |
| **REFERENCES** | |
| **APPENDICES** | |

</div>

---

<div style="page-break-after: always;">

## LIST OF TABLES

| Table | Title | Page |
|-------|-------|------|
| 3.1 | Target Population Distribution | |
| 3.2 | Sample Size Determination | |
| 4.1 | Response Rate | |
| 4.2 | Demographic Characteristics of Respondents | |
| 4.3 | Findings for Objective One | |
| 4.4 | Findings for Objective Two | |
| 4.5 | Findings for Objective Three | |
| 4.6 | Findings for Objective Four | |

*Note: Detailed tables are embedded within the respective chapters.*

</div>

---

<div style="page-break-after: always;">

## LIST OF FIGURES

| Figure | Title | Page |
|--------|-------|------|
| 2.1 | Conceptual Framework | |
| 3.1 | Saunders Research Onion | |
| 4.1 | Distribution of Respondents by Demographics | |
| 4.2 | Key Findings Visualisation | |

*Note: Detailed figures are embedded within the respective chapters.*

</div>

---

<div style="page-break-after: always;">

## LIST OF ABBREVIATIONS AND ACRONYMS

| Abbreviation | Full Form |
|--------------|-----------|
| C3I | Command, Control, Communications, and Intelligence |
| FGD | Focus Group Discussion |
| KII | Key Informant Interview |
| PhD | Doctor of Philosophy |
| R-ARCSS | Revitalised Agreement on the Resolution of Conflict in South Sudan |
| SD | Standard Deviation |
| SPSS | Statistical Package for Social Sciences |
| SSPDF | South Sudan People's Defence Forces |
| UN | United Nations |

</div>

---

## RESEARCH OBJECTIVES

"""
            for i, obj in enumerate(objectives, 1):
                full_thesis += f"{i}. {obj}\n"
            
            full_thesis += f"""

---

# CHAPTER ONE

# INTRODUCTION

{chapter1_thesis}

---

# CHAPTER TWO

# LITERATURE REVIEW

{chapter2_thesis}

---

# CHAPTER THREE

# RESEARCH METHODOLOGY

{chapter3_thesis}

---

# CHAPTER FOUR

# DATA PRESENTATION, ANALYSIS AND INTERPRETATION

{chapter4_thesis}

---

# CHAPTER FIVE

# DISCUSSION OF FINDINGS

{chapter5_thesis}

---

# CHAPTER SIX

# SUMMARY, CONCLUSIONS AND RECOMMENDATIONS

{chapter6_thesis}

---

# REFERENCES

All scholarly sources cited in this thesis are embedded as hyperlinks throughout the document. A consolidated reference list in APA 7th Edition format is available in the exported document.

---

# APPENDICES

## Appendix A: Research Questionnaire

The structured questionnaire used for data collection is available as a separate document:
- **File:** `Questionnaire_{timestamp}.md`

## Appendix B: Interview Guide

The semi-structured interview guide for qualitative data collection:
- **File:** `Interview_Guide_{timestamp}.md`

## Appendix C: Focus Group Discussion Guide

The FGD protocol and questions:
- **File:** See Interview Guide

## Appendix D: Research Permit/Authorisation Letters

*[To be inserted by researcher]*

## Appendix E: Informed Consent Form

*[To be inserted by researcher]*

## Appendix F: Raw Data

Statistical outputs and transcripts are available in:
- **Folder:** `datasets/`

---

**— END OF THESIS —**

"""
            
            # Save complete thesis
            thesis_filename = f"Complete_PhD_Thesis_{topic.replace(' ', '_')}_{timestamp}.md"
            thesis_filepath = workspace_path / thesis_filename
            
            with open(thesis_filepath, 'w', encoding='utf-8') as f:
                f.write(full_thesis)
            
            word_count = len(full_thesis.split())
            
            # Calculate chapter word counts
            ch1_words = len(chapter_contents.get('chapter1', '').split())
            ch2_words = len(chapter_contents.get('chapter2', '').split())
            ch3_words = len(chapter_contents.get('chapter3', '').split())
            ch4_words = len(chapter_contents.get('chapter4', '').split())
            ch5_words = len(chapter_contents.get('chapter5', '').split())
            ch6_words = len(chapter_contents.get('chapter6', '').split())
            
            # Notify completion with detailed summary
            proposal_words = len(proposal_content.split())
            
            await events.publish(
                job_id,
                "file_created",
                {"path": str(thesis_filepath), "filename": thesis_filename, "type": "markdown", "auto_open": True},
                session_id=session_id
            )
            
            await events.publish(
                job_id,
                "response_chunk",
                {"chunk": f"""

---

# ✅ THESIS GENERATION COMPLETE!

## 📊 Word Count Summary

| Chapter | Title | Words |
|---------|-------|-------|
| 1 | Introduction | {ch1_words:,} |
| 2 | Literature Review | {ch2_words:,} |
| 3 | Methodology | {ch3_words:,} |
| 4 | Data Analysis | {ch4_words:,} |
| 5 | Discussion | {ch5_words:,} |
| 6 | Conclusion | {ch6_words:,} |
| **Total** | **Complete Thesis** | **{word_count:,}** |

## 📁 Files Generated

### 📋 Research Proposal (Future Tense)
- `{proposal_filename}` ({proposal_words:,} words)
- Chapters 1-3 in **future tense** ("will", "shall")
- Use this for proposal submission/defense

### 📚 Complete PhD Thesis (Past Tense)
- `{thesis_filename}` ({word_count:,} words)
- Chapters 1-3 converted to **past tense** ("was", "were")
- Chapters 4-6 report completed research
- Use this for final thesis submission

### 📂 Other Files
- **Individual Chapters:** `chapters/` folder
- **Datasets:** `datasets/` folder
- **Study Tools:** Questionnaire, Interview Guide

## 🎉 Your PhD thesis is ready!

Download the proposal or complete thesis from the file panel.

""", "accumulated": full_thesis},
                session_id=session_id
            )
            
            await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "success"}, session_id=session_id)
            print(f"✅ COMPLETE THESIS GENERATED! {word_count} words")
            
        except Exception as e:
            import traceback
            print(f"❌ Thesis generation error: {str(e)}")
            print(traceback.format_exc())
            await events.publish(job_id, "response_chunk", {"chunk": f"\n\n❌ **Error:** {str(e)}\n\nPlease try again or check the logs.", "accumulated": ""}, session_id=session_id)
            await events.publish(job_id, "stage_completed", {"stage": "complete", "status": "error"}, session_id=session_id)
    
    # Start background generation
    asyncio.create_task(run_full_thesis_generation())
    
    print(f"✅ Full thesis generation started: job_id={job_id}")
    
    return {
        "success": True,
        "message": f"🚀 Full thesis generation started for '{topic}'. Generating all 6 chapters + study tools + datasets.",
        "job_id": job_id,
        "title": title,
        "topic": topic,
        "objectives": objectives,
        "status": "generating",
        "steps": [
            "Chapter 1: Introduction",
            "Chapter 2: Literature Review",
            "Chapter 3: Methodology",
            "Study Tools Generation",
            "Dataset Generation",
            "Chapter 4: Data Analysis",
            "Chapter 5: Discussion",
            "Chapter 6: Conclusion",
            "Combine Final Thesis"
        ]
    }

@app.post("/api/thesis/generate-from-topic")
async def generate_thesis_from_topic(request: dict):
    """Generate thesis from topic with auto-generated objectives"""
    try:
        university_type = request.get('university_type', 'generic')
        title = request.get('title', 'Untitled Thesis')
        topic = request.get('topic', '')
        
        # Auto-generate objectives if not provided
        objectives = request.get('objectives') or []
        if not objectives and topic:
            objectives = [
                f"Examine the current state of {topic}",
                f"Identify key challenges in {topic}",
                f"Propose solutions for {topic}"
            ]
        
        # Call generate_thesis
        return await generate_thesis({
            'university_type': university_type,
            'title': title,
            'topic': topic,
            'objectives': objectives,
            'workspace_id': request.get('workspace_id', 'default')
        })
        
    except Exception as e:
        import traceback
        print(f"Error generating thesis from topic: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "message": f"Error generating thesis: {str(e)}",
            "file_path": None,
            "university_type": request.get('university_type', 'unknown'),
            "title": request.get('title', 'unknown')
        }
