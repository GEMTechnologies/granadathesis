#!/usr/bin/env python3
"""
Zotero API Integration - Direct sync with Zotero library

Features:
- Add papers directly to Zotero library
- Create collections
- Sync with Zotero cloud
- Attach PDFs to items
"""

import httpx
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ZoteroService:
    """
    Zotero API integration.
    
    Requires:
    - Zotero API key (get from https://www.zotero.org/settings/keys)
    - User ID or Group ID
    """
    
    def __init__(self, api_key: str, user_id: Optional[str] = None, group_id: Optional[str] = None):
        """
        Initialize Zotero service.
        
        Args:
            api_key: Zotero API key
            user_id: Zotero user ID (for personal library)
            group_id: Zotero group ID (for group library)
        """
        self.api_key = api_key
        self.user_id = user_id
        self.group_id = group_id
        self.base_url = "https://api.zotero.org"
        
        if not user_id and not group_id:
            raise ValueError("Must provide either user_id or group_id")
        
        # Determine library path
        if user_id:
            self.library_path = f"/users/{user_id}"
        else:
            self.library_path = f"/groups/{group_id}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Zotero-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def paper_to_zotero_item(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert paper dict to Zotero item format.
        
        Args:
            paper: Paper dictionary
            
        Returns:
            Zotero item dictionary
        """
        # Map authors
        creators = []
        for author in paper.get("authors", []):
            # Try to split into first/last name
            parts = author.strip().split()
            if len(parts) >= 2:
                creators.append({
                    "creatorType": "author",
                    "firstName": " ".join(parts[:-1]),
                    "lastName": parts[-1]
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "name": author
                })
        
        # Build item
        item = {
            "itemType": "journalArticle",
            "title": paper.get("title", ""),
            "creators": creators,
            "abstractNote": paper.get("abstract", ""),
            "publicationTitle": paper.get("venue", ""),
            "date": str(paper.get("year", "")),
            "DOI": paper.get("doi", ""),
            "url": paper.get("url", ""),
            "extra": f"Source: {paper.get('source', '')}\nCitations: {paper.get('citations', 0)}"
        }
        
        return item
    
    async def create_item(self, paper: Dict[str, Any]) -> Optional[str]:
        """
        Create a new item in Zotero library.
        
        Args:
            paper: Paper dictionary
            
        Returns:
            Item key if successful, None otherwise
        """
        url = f"{self.base_url}{self.library_path}/items"
        item = self.paper_to_zotero_item(paper)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=[item]
                )
                response.raise_for_status()
                
                # Get item key from response
                result = response.json()
                if result.get("successful"):
                    item_key = list(result["successful"].values())[0]
                    logger.info(f"Created Zotero item: {item_key}")
                    return item_key
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to create Zotero item: {e}")
            return None
    
    async def create_collection(self, name: str, parent_key: Optional[str] = None) -> Optional[str]:
        """
        Create a new collection.
        
        Args:
            name: Collection name
            parent_key: Parent collection key (optional)
            
        Returns:
            Collection key if successful
        """
        url = f"{self.base_url}{self.library_path}/collections"
        
        collection = {
            "name": name,
            "parentCollection": parent_key if parent_key else False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=[collection]
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("successful"):
                    collection_key = list(result["successful"].values())[0]
                    logger.info(f"Created Zotero collection: {collection_key}")
                    return collection_key
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to create Zotero collection: {e}")
            return None
    
    async def add_to_collection(self, item_key: str, collection_key: str) -> bool:
        """
        Add item to collection.
        
        Args:
            item_key: Item key
            collection_key: Collection key
            
        Returns:
            True if successful
        """
        url = f"{self.base_url}{self.library_path}/items/{item_key}"
        
        try:
            async with httpx.AsyncClient() as client:
                # Get current item
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                item = response.json()
                
                # Add to collection
                if "collections" not in item:
                    item["collections"] = []
                if collection_key not in item["collections"]:
                    item["collections"].append(collection_key)
                
                # Update item
                response = await client.put(
                    url,
                    headers=self._get_headers(),
                    json=item
                )
                response.raise_for_status()
                
                logger.info(f"Added item {item_key} to collection {collection_key}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add item to collection: {e}")
            return False
    
    async def attach_pdf(self, item_key: str, pdf_path: str) -> bool:
        """
        Attach PDF to item.
        
        Args:
            item_key: Item key
            pdf_path: Path to PDF file
            
        Returns:
            True if successful
        """
        # Note: PDF upload requires multiple steps:
        # 1. Create attachment item
        # 2. Get upload authorization
        # 3. Upload file
        # 4. Register upload
        
        # This is a simplified version - full implementation would require
        # handling the multi-step upload process
        
        logger.warning("PDF attachment not fully implemented - requires multi-step upload")
        return False
    
    async def bulk_add_papers(self, papers: List[Dict[str, Any]], 
                             collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Add multiple papers to Zotero.
        
        Args:
            papers: List of paper dictionaries
            collection_name: Optional collection name to create
            
        Returns:
            Results dictionary
        """
        results = {
            "total": len(papers),
            "successful": 0,
            "failed": 0,
            "item_keys": []
        }
        
        # Create collection if specified
        collection_key = None
        if collection_name:
            collection_key = await self.create_collection(collection_name)
        
        # Add papers
        for paper in papers:
            item_key = await self.create_item(paper)
            
            if item_key:
                results["successful"] += 1
                results["item_keys"].append(item_key)
                
                # Add to collection
                if collection_key:
                    await self.add_to_collection(item_key, collection_key)
            else:
                results["failed"] += 1
        
        return results


# Example usage
async def example_usage():
    """Example of how to use Zotero service."""
    
    # Initialize (you need to get these from Zotero settings)
    zotero = ZoteroService(
        api_key="YOUR_API_KEY",
        user_id="YOUR_USER_ID"
    )
    
    # Sample paper
    paper = {
        "title": "Example Paper Title",
        "authors": ["John Doe", "Jane Smith"],
        "year": 2024,
        "abstract": "This is an example abstract...",
        "venue": "Example Journal",
        "doi": "10.1234/example",
        "url": "https://example.com/paper.pdf",
        "source": "OpenAlex",
        "citations": 42
    }
    
    # Add to Zotero
    item_key = await zotero.create_item(paper)
    print(f"Created item: {item_key}")
    
    # Create collection and add paper
    collection_key = await zotero.create_collection("My Research Papers")
    await zotero.add_to_collection(item_key, collection_key)
    
    # Bulk add multiple papers
    papers = [paper, paper, paper]  # Your list of papers
    results = await zotero.bulk_add_papers(papers, "Literature Review")
    print(f"Added {results['successful']}/{results['total']} papers")
