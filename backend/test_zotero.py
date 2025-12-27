#!/usr/bin/env python3
"""
Test Zotero Connection

Simple script to test if Zotero API is working correctly.
"""

import asyncio
import httpx


async def test_zotero_connection():
    """Test Zotero API connection."""
    
    API_KEY = "INC1oHci992x3bsa8B8UThxw"
    USER_ID = "18973079"
    
    print("🔍 Testing Zotero API Connection\n")
    print(f"API Key: {API_KEY[:20]}...")
    print(f"User ID: {USER_ID}\n")
    
    # Test 1: Get library info
    print("Test 1: Fetching library info...")
    url = f"https://api.zotero.org/users/{USER_ID}/items"
    headers = {
        "Zotero-API-Key": API_KEY,
        "Zotero-API-Version": "3"
    }
    params = {"limit": 1}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Connection successful!")
                data = response.json()
                print(f"Library has items: {len(data) > 0}")
            elif response.status_code == 403:
                print("❌ Authentication failed - check API key")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 2: Create a test item
    print("\nTest 2: Creating test item...")
    create_url = f"https://api.zotero.org/users/{USER_ID}/items"
    
    test_item = {
        "itemType": "journalArticle",
        "title": "Test Paper from AutoGranada",
        "creators": [
            {
                "creatorType": "author",
                "firstName": "Test",
                "lastName": "Author"
            }
        ],
        "date": "2024",
        "abstractNote": "This is a test item created by AutoGranada to verify Zotero API integration."
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                create_url,
                headers=headers,
                json=[test_item]
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Item created successfully!")
                if result.get("successful"):
                    item_keys = list(result["successful"].values())
                    print(f"Item key: {item_keys[0] if item_keys else 'unknown'}")
                print("\n💡 Check your Zotero library - you should see the test item!")
            else:
                print(f"❌ Failed to create item")
                print(f"Response: {response.text[:500]}")
                
    except Exception as e:
        print(f"❌ Error creating item: {e}")
    
    print("\n" + "="*50)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_zotero_connection())
