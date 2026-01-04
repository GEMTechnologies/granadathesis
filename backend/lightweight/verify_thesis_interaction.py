import asyncio
import redis.asyncio as redis
import json
import uuid
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append("/home/gemtech/Desktop/thesis/backend/lightweight")

from services.central_brain import central_brain
from core.config import settings

async def verify_interaction():
    session_id = f"test_doc_{uuid.uuid4().hex[:6]}"
    workspace_id = "ux_test_ws"
    
    # Setup Redis URL (Local vs Docker)
    redis_url = settings.REDIS_URL
    if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
        redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
    
    # 1. Setup Redis listener
    redis_client = redis.from_url(redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"session:{session_id}")
    
    async def listen():
        print("📡 Listening for stage events...")
        events = []
        try:
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 20:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = json.loads(message['data'])
                    msg_type = data.get('type')
                    if msg_type in ['stage_started', 'stage_completed']:
                        print(f"✅ EVENT: {msg_type} -> {data['data'].get('stage')}: {data['data'].get('message')}")
                        events.append(data)
        except Exception as e:
            print(f"Error: {e}")
        return events

    # 2. Prepare context (ensure a file exists for interaction)
    from services.workspace_service import WORKSPACES_DIR
    ws_dir = WORKSPACES_DIR / workspace_id
    ws_dir.mkdir(parents=True, exist_ok=True)
    test_file = ws_dir / "my_thesis.md"
    test_file.write_text("# My Thesis\n\nThis is a test thesis draft about technology in South Sudan.")
    
    # Start listener
    listener_task = asyncio.create_task(listen())
    
    # 3. Trigger Interaction
    print("\n[Step 1] Triggering Chat with Thesis...")
    await central_brain.run_agent_workflow(
        "ask my thesis: what is the main topic?", 
        session_id, 
        workspace_id,
        job_id=f"job_{uuid.uuid4().hex[:4]}"
    )
    
    events = await listener_task
    
    # 4. Success Check
    starts = [e for e in events if e.get('type') == 'stage_started']
    completes = [e for e in events if e.get('type') == 'stage_completed']
    
    print(f"\n📊 Summary: {len(starts)} started, {len(completes)} completed.")
    if len(starts) > 0 and len(completes) > 0:
        print("🏆 SUCCESS: Task tracking events correctly emitted!")
    else:
        print("❌ FAILED: Missing stage events.")

if __name__ == "__main__":
    asyncio.run(verify_interaction())
