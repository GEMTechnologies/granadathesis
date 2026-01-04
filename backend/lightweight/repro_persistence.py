import asyncio
import sys
import os

# Add backend to path
sys.path.append("/home/gemtech/Desktop/thesis/backend/lightweight")

from services.conversation_memory import conversation_memory

async def test_persistence():
    print("--- Testing Chat Persistence ---")
    workspace_id = "default"
    
    # 1. Create Conversation
    conv = await conversation_memory.create_conversation(workspace_id, "Test Conv")
    cid = conv.conversation_id
    print(f"Created: {cid}")
    
    # 2. Add Message
    await conversation_memory.add_message(workspace_id, cid, "user", "Hello Persistence")
    print("Added message")
    
    # 3. List Conversations (Simulate Refresh)
    # Re-instantiate service (simulating restart if it wasn't singleton, but here we test file read)
    convs = conversation_memory.list_conversations(workspace_id)
    
    found = False
    for c in convs:
        if c['conversation_id'] == cid:
            found = True
            print(f"✅ Found conversation {cid} in list after listing.")
            break
            
    if not found:
        print("❌ Failed to find conversation in list!")
        
    # 4. Get Messages
    msgs = await conversation_memory.get_messages(workspace_id, cid)
    if msgs and msgs[0]['content'] == "Hello Persistence":
        print(f"✅ Found message content: {msgs[0]['content']}")
    else:
        print(f"❌ Message missing or wrong! {msgs}")

if __name__ == "__main__":
    asyncio.run(test_persistence())
