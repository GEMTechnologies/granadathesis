
import asyncio
import json
import redis.asyncio as aioredis
from pathlib import Path
from services.central_brain import central_brain
from services.workspace_service import WORKSPACES_DIR

async def verify_research_ux():
    print("\n--- Verification: Research UX & Persistence ---")
    session_id = "ux_test_session"
    workspace_id = "ux_test_ws"
    
    # 1. Listen to Redis in background
    redis_url = "redis://localhost:6379"
    redis = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"browser:{session_id}")
    
    async def listen_redis():
        print("📡 Listening for browser & agent events...")
        events_found = []
        try:
            # Subscribe to both browser and agent channels
            await pubsub.subscribe(f"agents:{session_id}")
            
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 15:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = json.loads(message['data'])
                    msg_type = data.get('type', data.get('status', 'unknown'))
                    print(f"🔥 Event: {msg_type} - {data.get('message', '')}")
                    if "results" in data.get('data', {}):
                        print(f"✅ Found rich results: {len(data['data']['results'])} items")
                    events_found.append(data)
        except Exception as e:
            print(f"Error: {e}")
        return events_found

    # Start listener
    listener_task = asyncio.create_task(listen_redis())
    
    # 2. Trigger Research
    print("\n[Step 1] Triggering search for GDP of South Sudan...")
    message = "search for the latest GDP statistics of South Sudan"
    await central_brain.run_agent_workflow(message, session_id, workspace_id)
    
    # Wait for listener to finish
    events = await listener_task
    
    # Check for stage_started
    stage_events = [e for e in events if e.get('type') == 'agent_activity' and e.get('message', '').startswith('🌐 Searching')]
    if stage_events:
        print("✅ SUCCESS: Found activity event that triggers UI auto-opening.")
    else:
        print("❌ FAILED: No activity event found with the correct prefix.")
    
    # 3. Verify Persistence in Project Root
    print(f"\n[Step 2] Checking persistence in: {WORKSPACES_DIR}")
    sources_index = WORKSPACES_DIR / workspace_id / "sources" / "index.json"
    if sources_index.exists():
        with open(sources_index, 'r') as f:
            data = json.load(f)
            count = len(data.get('sources', []))
            print(f"✅ Sources found in {sources_index}: {count} entries.")
            if count > 0:
                print("🏆 SUCCESS: Research is persistent and project-aligned.")
            else:
                print("⚠️ Index found but EMPTY.")
    else:
        print(f"❌ Sources index NOT found at: {sources_index}")
        # List actual dirs to see where it went
        print(f"Actual workspace contents: {[f.name for f in (WORKSPACES_DIR / workspace_id).glob('*')] if (WORKSPACES_DIR / workspace_id).exists() else 'Workspace dir missing'}")

if __name__ == "__main__":
    asyncio.run(verify_research_ux())
