#!/usr/bin/env python3
"""
Test Academic Search API Endpoints

Test all FastAPI endpoints to ensure they're working correctly.
"""

import asyncio
import httpx
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health check endpoint."""
    print("\n🔍 Testing Health Check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/search/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_search():
    """Test search endpoint."""
    print("\n🔍 Testing Search Endpoint...")
    
    payload = {
        "query": "machine learning",
        "limit_per_source": 2,
        "use_cache": True
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/api/search/search", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data['total_results']}")
            print(f"Search time: {data['search_time_ms']}ms")
            print(f"Cached: {data['cached']}")
            if data['papers']:
                print(f"\nFirst paper: {data['papers'][0]['title']}")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200


async def test_pubmed():
    """Test PubMed search endpoint."""
    print("\n🔍 Testing PubMed Endpoint...")
    
    params = {
        "query": "cancer immunotherapy",
        "limit": 3,
        "free_full_text": True
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/api/search/search/pubmed", params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total results: {data['total_results']}")
            if data['papers']:
                print(f"First paper: {data['papers'][0]['title']}")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200


async def test_cache_stats():
    """Test cache statistics endpoint."""
    print("\n🔍 Testing Cache Stats...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/search/cache/stats")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total entries: {data.get('total_entries', 0)}")
            print(f"Cache size: {data.get('total_size_mb', 0)} MB")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200


async def test_thesis_integration():
    """Test thesis integration endpoint."""
    print("\n🔍 Testing Thesis Integration...")
    
    payload = {
        "objective": "Develop a machine learning framework for predicting student performance",
        "limit": 3,
        "year_min": 2020
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{BASE_URL}/api/search/thesis/find-papers", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total papers: {data.get('total_papers', 0)}")
            print(f"Search query: {data.get('search_query', '')}")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200


async def run_all_tests():
    """Run all endpoint tests."""
    print("="*60)
    print("TESTING ACADEMIC SEARCH API ENDPOINTS")
    print("="*60)
    
    tests = [
        ("Health Check", test_health),
        ("Search", test_search),
        ("PubMed", test_pubmed),
        ("Cache Stats", test_cache_stats),
        ("Thesis Integration", test_thesis_integration)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = "✅ PASS" if result else "❌ FAIL"
        except Exception as e:
            results[name] = f"❌ ERROR: {str(e)}"
        
        await asyncio.sleep(1)  # Rate limiting
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    for name, result in results.items():
        print(f"{name}: {result}")
    
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")


if __name__ == "__main__":
    print("\n⚠️  Make sure the server is running:")
    print("   cd backend && uvicorn main:app --reload\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
