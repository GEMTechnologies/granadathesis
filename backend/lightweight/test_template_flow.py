
import asyncio
import json
from pathlib import Path
from services.central_brain import central_brain
from services.agent_spawner import AgentContext, AgentType

async def test_proactive_greeting():
    print("\n--- Test 1: Proactive Greeting (No Outline) ---")
    session_id = "test_template_session"
    workspace_id = "test_template_ws"
    
    # Ensure clean workspace
    from services.workspace_service import WORKSPACES_DIR
    ws_path = WORKSPACES_DIR / workspace_id
    if ws_path.exists():
        import shutil
        shutil.rmtree(ws_path)
    ws_path.mkdir(parents=True)

    # Simulate first message "hi"
    message = "hi"
    result = await central_brain.run_agent_workflow(message, session_id, workspace_id)
    
    print(f"Intent: {result.get('intent')}")
    print(f"Goals: {result.get('goals')}")
    
    # In a real environment, the final_response from api.py would contain the question.
    # Here we check if UnderstandingAgent spotted the 'missing_info'.
    # Note: central_brain doesn't return the full LLM intent reasoning directly in 'result' 
    # but we can check if it completed successfully.

async def test_chapter_with_outline():
    print("\n--- Test 2: Chapter Generation with Existing Outline ---")
    session_id = "test_outline_session"
    workspace_id = "test_outline_ws"
    
    from services.workspace_service import WORKSPACES_DIR
    ws_path = WORKSPACES_DIR / workspace_id
    ws_path.mkdir(parents=True, exist_ok=True)
    
    # Create custom outline
    outline = {
        "chapters": [
            {
                "number": 1,
                "title": "My Custom Introduction Title",
                "sections": ["Section A", "Section B"]
            }
        ]
    }
    with open(ws_path / "outline.json", "w") as f:
        json.dump(outline, f)
        
    # Simulate chapter 1 request
    message = "make chapter 1"
    result = await central_brain.run_agent_workflow(message, session_id, workspace_id)
    
    print(f"Intent: {result.get('intent')}")
    
    # Check if file was created with custom title
    found_files = list(ws_path.glob("chapter_01_my_custom_introduction_title.md"))
    if found_files:
        print(f"✅ Created file with custom title: {found_files[0].name}")
    else:
        print("❌ Failed to use custom outline title")
        # List all files for debugging
        print(f"Actual files: {[f.name for f in ws_path.glob('*')]}")

if __name__ == "__main__":
    asyncio.run(test_proactive_greeting())
    asyncio.run(test_chapter_with_outline())
