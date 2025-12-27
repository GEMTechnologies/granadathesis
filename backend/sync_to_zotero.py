#!/usr/bin/env python3
"""
Sync Search Results to Zotero

Quick script to search for papers and sync them to your Zotero library.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from scholarly_search import ScholarlySearch, Config
from app.services.zotero_service import ZoteroService


async def sync_to_zotero(query: str, limit: int = 10, collection_name: str = None):
    """
    Search for papers and sync to Zotero.
    
    Args:
        query: Search query
        limit: Number of papers per source
        collection_name: Optional collection name
    """
    print(f"\n🔍 Searching for: '{query}'")
    print(f"   Limit: {limit} papers per source\n")
    
    # 1. Search for papers
    searcher = ScholarlySearch()
    papers = await searcher.run_search(query, limit_per_source=limit)
    
    if not papers:
        print("❌ No papers found")
        return
    
    print(f"\n✅ Found {len(papers)} unique papers")
    
    # 2. Check Zotero configuration
    if not Config.ZOTERO_API_KEY:
        print("\n⚠️  Zotero API key not configured")
        print("   Using RIS export instead...")
        searcher.save_results(papers, query)
        print("\n💡 To use direct Zotero sync:")
        print("   1. Get API key from https://www.zotero.org/settings/keys")
        print("   2. Add to .env file: ZOTERO_API_KEY=your_key")
        print("   3. Add User ID: ZOTERO_USER_ID=your_id")
        return
    
    if not Config.ZOTERO_USER_ID:
        print("\n⚠️  Zotero User ID not configured")
        print("   Using RIS export instead...")
        searcher.save_results(papers, query)
        print("\n💡 Get your User ID:")
        print("   1. Go to https://www.zotero.org/settings/keys")
        print("   2. Find 'Your userID for use in API calls is XXXXXX'")
        print("   3. Add to .env file: ZOTERO_USER_ID=XXXXXX")
        return
    
    # 3. Sync to Zotero
    print(f"\n📚 Syncing to Zotero...")
    
    try:
        zotero = ZoteroService(
            api_key=Config.ZOTERO_API_KEY,
            user_id=Config.ZOTERO_USER_ID
        )
        
        # Use query as collection name if not specified
        if not collection_name:
            collection_name = f"Search: {query}"
        
        # Bulk add papers
        results = await zotero.bulk_add_papers(
            [p.to_dict() for p in papers],
            collection_name=collection_name
        )
        
        print(f"\n✅ Zotero Sync Complete!")
        print(f"   Successfully added: {results['successful']}/{results['total']} papers")
        print(f"   Failed: {results['failed']}")
        print(f"   Collection: '{collection_name}'")
        
        if results['failed'] > 0:
            print(f"\n💡 Some papers may already exist in your library")
        
    except Exception as e:
        print(f"\n❌ Zotero sync failed: {e}")
        print("   Falling back to RIS export...")
        searcher.save_results(papers, query)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Search and sync papers to Zotero")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Papers per source (default: 5)")
    parser.add_argument("--collection", help="Zotero collection name")
    args = parser.parse_args()
    
    await sync_to_zotero(args.query, args.limit, args.collection)


if __name__ == "__main__":
    asyncio.run(main())
