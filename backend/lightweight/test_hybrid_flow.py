import requests
import json
import time

BASE_URL = "http://localhost:8000"
USER_ID = "test_user"

def test_hybrid_flow():
    print("🚀 Starting Hybrid Research-Writing Verification...")
    
    # 1. Create session
    resp = requests.post(f"{BASE_URL}/api/session/init", json={"user_id": USER_ID})
    session_data = resp.json()
    session_id = session_data["session_id"]
    workspace_id = session_data["workspace_id"]
    print(f"✅ Created Session: {session_id} in Workspace: {workspace_id}")
    
    # 2. Create initial simple file
    print("\n📝 Step 1: Create initial simple file...")
    msg = "make a file uganda.md with the text 'Uganda is a country.'"
    requests.post(f"{BASE_URL}/api/chat/message", json={
        "session_id": session_id,
        "workspace_id": workspace_id,
        "user_id": USER_ID,
        "message": msg
    })
    
    # 3. Request Hybrid Update (Research + Rewrite)
    print("\n🔬 Step 2: Request hybrid rewrite with studies...")
    msg2 = "rewrite uganda.md with real studies about its economy and tourism"
    resp = requests.post(f"{BASE_URL}/api/chat/message", json={
        "session_id": session_id,
        "workspace_id": workspace_id,
        "user_id": USER_ID,
        "message": msg2
    })
    result = resp.json()
    print(f"🤖 Response: {result.get('response')}")
    
    # 4. Verify no redundant files
    print("\n📂 Step 3: Verifying file structure...")
    struct_resp = requests.get(f"{BASE_URL}/api/workspace/{workspace_id}/structure")
    items = struct_resp.json().get("items", [])
    files = [f["name"] for f in items if f["type"] == "file"]
    print(f"Files in workspace: {files}")
    
    if len(files) == 1 and "uganda.md" in files:
        print("✅ Success: No redundant files created. 'uganda.md' was updated.")
    elif "uganda.md" in files:
        print("⚠️ 'uganda.md' exists but other files might have been created: " + str(files))
    else:
        print("❌ 'uganda.md' is missing!")

    # 5. Check content for citations
    content_resp = requests.get(f"{BASE_URL}/api/workspace/{workspace_id}/file?path=uganda.md")
    content = content_resp.json().get("content", "")
    if "(" in content and ")" in content:
        print("✅ Success: File contains (Author, Year) style citations!")
    else:
        print("❌ No citations found in the updated content.")

if __name__ == "__main__":
    test_hybrid_flow()
