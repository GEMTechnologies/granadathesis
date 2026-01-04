
import asyncio
import json
from pathlib import Path
from services.central_brain import central_brain
from services.agent_spawner import AgentContext, AgentType

async def test_persistent_research_and_uoj():
    print("\n--- Test: Persistent Research & UoJ Flow ---")
    session_id = "test_uoj_session"
    workspace_id = "test_uoj_ws"
    
    from services.workspace_service import WORKSPACES_DIR
    ws_path = WORKSPACES_DIR / workspace_id
    if ws_path.exists():
        import shutil
        shutil.rmtree(ws_path)
    ws_path.mkdir(parents=True)

    # 1. Ask for statistics (Should trigger Research + Persistence)
    print("\n[Step 1] Requesting statistics for South Sudan climate...")
    message = "give me the latest statistics on flooding in South Sudan for my UoJ PhD"
    result = await central_brain.run_agent_workflow(message, session_id, workspace_id)
    
    # Check if sources were saved
    sources_index = ws_path / "sources" / "index.json"
    if sources_index.exists():
        with open(sources_index, 'r') as f:
            data = json.load(f)
            print(f"✅ Sources persisted: {len(data.get('sources', []))} entries found.")
    else:
        print("❌ Sources index NOT found!")

    # 2. Write Chapter (Should pull from saved sources)
    print("\n[Step 2] Writing Chapter 1 (UoJ Style)...")
    message = "write chapter 1 for my thesis"
    result = await central_brain.run_agent_workflow(message, session_id, workspace_id)
    
    # Check for UoJ Style markers or persistence usage
    found_files = list(ws_path.glob("chapter_01_introduction.md"))
    if found_files:
        content = found_files[0].read_text()
        print(f"✅ Chapter created: {found_files[0].name}")
        # Check if synthesized content contains citations or indicators of RAG
        if "(" in content and ")" in content:
            print("✅ Synthesis contains potential citations.")
        if "South Sudan" in content:
            print("✅ Content contains contextually relevant info.")
    else:
        print("❌ Chapter file NOT found!")
        print(f"Actual files: {[f.name for f in ws_path.glob('*')]}")

if __name__ == "__main__":
    asyncio.run(test_persistent_research_and_uoj())
