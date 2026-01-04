
import sys
import os
from pathlib import Path

# Add project root to path
project_root = "/home/gemtech/Desktop/thesis/backend/lightweight"
sys.path.append(project_root)

from services.agent_spawner import AgentContext

def test_workspace_coupling():
    session_id = "test-session-1234567890"
    # Case 1: Default workspace
    ctx1 = AgentContext(user_message="test", session_id=session_id, workspace_id="default")
    print(f"Case 1 (default): {ctx1.workspace_id}")
    assert ctx1.workspace_id == f"ws_{session_id[:12]}", f"Expected ws_{session_id[:12]}, got {ctx1.workspace_id}"
    
    # Case 2: Specified workspace (should keep it)
    ctx2 = AgentContext(user_message="test", session_id=session_id, workspace_id="other_ws")
    print(f"Case 2 (specified): {ctx2.workspace_id}")
    assert ctx2.workspace_id == "other_ws", f"Expected other_ws, got {ctx2.workspace_id}"
    
    print("✅ Workspace coupling test passed!")

if __name__ == "__main__":
    try:
        test_workspace_coupling()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
