
import asyncio
import os
import json
import redis.asyncio as aioredis
from services.browser_automation import get_browser

async def test_browser_stream():
    workspace_id = "test_browser_preview"
    
    # 1. Start listener
    print(f"👂 Listening for events on browser:{workspace_id}")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
        redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
    
    redis = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"browser:{workspace_id}")
    
    # 2. Trigger browser action
    print("🚀 Triggering browser action...")
    try:
        browser = await get_browser(workspace_id, headless=True)
        await browser.navigate("http://example.com")
        
        # 3. Check for events
        print("⏳ Waiting for events...")
        async with asyncio.timeout(5):
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    # detailed data is inside 'data' field again as json string
                    inner_data = json.loads(data["data"])
                    
                    print(f"✅ Received event: {inner_data.get('type')} - {inner_data.get('action', 'no-action')}")
                    
                    if inner_data.get('type') == 'browser_action' and inner_data.get('action') == 'navigate':
                        print("🎉 SUCCESS! Browser navigation event received via Redis!")
                        return
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await browser.close()
        await redis.close()

if __name__ == "__main__":
    # Ensure we can import services
    import sys
    sys.path.append("/home/gemtech/Desktop/thesis/backend/lightweight")
    
    asyncio.run(test_browser_stream())
