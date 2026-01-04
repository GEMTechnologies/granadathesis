
import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from services.central_brain import central_brain
from services.agent_spawner import AgentType, AgentContext
from core.config import settings

async def test_gdp_analysis():
    print("🚀 Starting GDP Analysis Verification...")
    
    session_id = "test_analysis_session"
    workspace_id = "ws_test_analysis"
    message = "search current trends of gdp of south sudan for past 5 years and make aalysis generate chats for it"
    
    # 1. Run workflow
    print(f"🧠 Running workflow for: {message}")
    result = await central_brain.run_agent_workflow(
        message=message,
        session_id=session_id,
        workspace_id=workspace_id,
        conversation_history=[]
    )
    
    print("\n✅ Workflow Complete!")
    print(f"Intent: {result.get('intent')}")
    print(f"Goals: {len(result.get('goals', []))}")
    print(f"Completed Actions: {len(result.get('completed_actions', []))}")
    
    # 2. Check for figures
    from services.workspace_service import WORKSPACES_DIR
    figures_dir = WORKSPACES_DIR / workspace_id / "figures"
    
    if figures_dir.exists():
        charts = list(figures_dir.glob("*.png"))
        print(f"📊 Found {len(charts)} charts in {figures_dir}")
        for chart in charts:
            print(f"  - {chart.name}")
        
        if len(charts) > 0:
            print("\n✨ SUCCESS: Charts were generated!")
        else:
            print("\n❌ FAILURE: No charts found in figures directory.")
    else:
        print(f"\n❌ FAILURE: Figures directory {figures_dir} does not exist.")

    # 3. Check for analysis output
    action_plan = result.get("action_plan", [])
    analysis_actions = [a for a in action_plan if a.get("action") == "data_analysis"]
    if analysis_actions:
        print(f"✅ Analysis action status: {analysis_actions[0].get('status')}")
    else:
        print("❌ FAILURE: No data_analysis action found in result.")

if __name__ == "__main__":
    asyncio.run(test_gdp_analysis())
