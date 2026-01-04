"""
Browser Automation API with Live Streaming

User can watch the browser in real-time!
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import json

router = APIRouter(prefix="/api/browser", tags=["Browser Automation"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class NavigateRequest(BaseModel):
    url: str
    workspace_id: str


class ClickRequest(BaseModel):
    selector: str
    workspace_id: str


class TypeRequest(BaseModel):
    selector: str
    text: str
    workspace_id: str


class FormFillRequest(BaseModel):
    form_data: Dict[str, str]
    workspace_id: str


class ScriptRequest(BaseModel):
    script: str
    workspace_id: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/start")
async def start_browser(workspace_id: str, headless: bool = False):
    """
    Start browser instance for workspace.
    
    headless=False shows browser (good for debugging)
    headless=True runs in background
    """
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(workspace_id, headless=headless)
        
        return {
            "status": "started",
            "workspace_id": workspace_id,
            "headless": headless
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/navigate")
async def navigate_to_url(request: NavigateRequest):
    """
    Navigate to URL.
    
    Returns screenshot immediately.
    """
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(request.workspace_id)
        screenshot = await browser.navigate(request.url)
        
        return {
            "status": "navigated",
            "url": request.url,
            "screenshot": screenshot,
            "current_url": await browser.get_current_url(),
            "title": await browser.get_title()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click")
async def click_element(request: ClickRequest):
    """Click element by selector."""
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(request.workspace_id)
        screenshot = await browser.click(request.selector)
        
        return {
            "status": "clicked",
            "selector": request.selector,
            "screenshot": screenshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/type")
async def type_text(request: TypeRequest):
    """Type text into element."""
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(request.workspace_id)
        screenshot = await browser.type_text(request.selector, request.text)
        
        return {
            "status": "typed",
            "selector": request.selector,
            "text": request.text,
            "screenshot": screenshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fill-form")
async def fill_form(request: FormFillRequest):
    """Fill multiple form fields."""
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(request.workspace_id)
        screenshot = await browser.fill_form(request.form_data)
        
        return {
            "status": "filled",
            "fields_count": len(request.form_data),
            "screenshot": screenshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/script")
async def execute_script(request: ScriptRequest):
    """Execute JavaScript in browser."""
    from services.browser_automation import get_browser
    
    try:
        browser = await get_browser(request.workspace_id)
        result = await browser.execute_script(request.script)
        
        return {
            "status": "executed",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{workspace_id}")
async def stream_browser(workspace_id: str):
    """
    LIVE STREAM browser screenshots.
    
    User watches everything the agent does in real-time!
    """
    from services.browser_automation import get_browser
    
    async def generate_stream():
        """Stream browser screenshots as they happen."""
        browser = await get_browser(workspace_id)
        queue = asyncio.Queue()
        
        # Stream callback - pushes to queue
        async def stream_callback(data):
            await queue.put(data)
        
        # Attach callback to browser
        browser.stream_callback = stream_callback
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        
        try:
            while True:
                # Wait for event or timeout (heartbeat)
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    
        except asyncio.CancelledError:
            # Clean up callback on disconnect
            print(f"👋 Browser stream client disconnected for {workspace_id}")
            browser.stream_callback = None
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )


@router.get("/history/{workspace_id}")
async def get_browser_history(workspace_id: str):
    """Get all browser actions (maintains context)."""
    from services.browser_automation import browser_instances
    
    if workspace_id not in browser_instances:
        return {"actions": [], "count": 0}
    
    browser = browser_instances[workspace_id]
    history = browser.get_action_history()
    
    return {
        "actions": history,
        "count": len(history),
        "current_url": await browser.get_current_url(),
        "title": await browser.get_title()
    }


@router.delete("/{workspace_id}")
async def close_browser(workspace_id: str):
    """Close browser instance."""
    from services.browser_automation import close_browser as close_browser_instance
    
    try:
        await close_browser_instance(workspace_id)
        
        return {"status": "closed", "workspace_id": workspace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
