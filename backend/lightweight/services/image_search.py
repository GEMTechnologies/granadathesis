"""
Image Search Service - Multiple APIs

Supports:
- Unsplash (free, high quality)
- Pexels (free, diverse)
- Pixabay (free, large collection)
- Tavily (from web search)
"""

import httpx
from typing import Dict, List, Any, Optional
from core.config import settings


class ImageSearchService:
    """Search for images across multiple APIs."""
    
    def __init__(self):
        self.unsplash_key = getattr(settings, 'UNSPLASH_API_KEY', None)
        self.pexels_key = getattr(settings, 'PEXELS_API_KEY', None)
        self.pixabay_key = getattr(settings, 'PIXABAY_API_KEY', None)
        
    async def search(self, query: str, limit: int = 10, source: str = "all", deduplicate: bool = True) -> List[Dict[str, Any]]:
        """
        Search for images across multiple APIs with deduplication and ranking.
        
        Args:
            query: Search query
            limit: Number of results to return (after deduplication)
            source: 'all', 'unsplash', 'pexels', 'pixabay'
            deduplicate: Whether to deduplicate results
            
        Returns:
            List of deduplicated and ranked image results
        """
        results = []
        
        # Fetch more results per source to account for deduplication
        fetch_limit = limit * 2 if deduplicate else limit
        
        if source in ["all", "unsplash"] and self.unsplash_key:
            try:
                unsplash_results = await self._search_unsplash(query, fetch_limit)
                results.extend(unsplash_results)
            except Exception as e:
                print(f"⚠️ Unsplash search failed: {e}")
        
        if source in ["all", "pexels"] and self.pexels_key:
            try:
                pexels_results = await self._search_pexels(query, fetch_limit)
                results.extend(pexels_results)
            except Exception as e:
                print(f"⚠️ Pexels search failed: {e}")
        
        if source in ["all", "pixabay"] and self.pixabay_key:
            try:
                pixabay_results = await self._search_pixabay(query, fetch_limit)
                results.extend(pixabay_results)
            except Exception as e:
                print(f"⚠️ Pixabay search failed: {e}")
        
        # If no API keys, fall back to generic image URLs
        if not results:
            results = self._fallback_image_results(query, limit)
            return results
        
        # Deduplicate and rank if requested
        if deduplicate and results:
            from services.search_utils import deduplicate_image_results, rank_image_results, ensure_diversity
            results = deduplicate_image_results(results)
            results = rank_image_results(results, query)
            results = ensure_diversity(results, max_per_source=3)
        
        # Limit to requested number
        return results[:limit]
    
    async def _search_unsplash(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Unsplash for images using Access Key (Client-ID header)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "per_page": min(limit, 30),  # Unsplash allows up to 30 per page
                },
                headers={
                    "Authorization": f"Client-ID {self.unsplash_key}",
                    "Accept-Version": "v1"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("description") or item.get("alt_description") or query,
                    "url": item["urls"].get("regular") or item["urls"].get("small"),  # Regular size
                    "thumbnail": item["urls"].get("thumb") or item["urls"].get("small"),
                    "full": item["urls"].get("full") or item["urls"].get("regular"),
                    "author": item["user"].get("name", "Unknown"),
                    "author_url": item["user"]["links"].get("html", ""),
                    "source": "Unsplash",
                    "source_url": item["links"].get("html", ""),
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "color": item.get("color")
                })
            return results
    
    async def _search_pexels(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Pexels for images."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": limit},
                headers={"Authorization": self.pexels_key}
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("photos", []):
                results.append({
                    "title": item.get("alt") or query,
                    "url": item["src"]["large"],  # Large size
                    "thumbnail": item["src"]["medium"],
                    "full": item["src"]["original"],
                    "author": item["photographer"],
                    "author_url": item["photographer_url"],
                    "source": "Pexels",
                    "source_url": item["url"],
                    "width": item.get("width"),
                    "height": item.get("height")
                })
            return results
    
    async def _search_pixabay(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Pixabay for images - matches official API documentation."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Pixabay API expects URL-encoded query, max 100 characters
            import urllib.parse
            encoded_query = urllib.parse.quote(query[:100])
            
            response = await client.get(
                "https://pixabay.com/api/",
                params={
                    "key": self.pixabay_key,
                    "q": encoded_query,
                    "image_type": "photo",
                    "per_page": min(limit, 200),  # Pixabay allows 3-200 per page
                    "safesearch": "true",
                    "order": "popular"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("hits", []):
                # Use webformatURL (640px) as default, with fallbacks
                image_url = item.get("webformatURL") or item.get("largeImageURL") or item.get("previewURL", "")
                full_url = item.get("largeImageURL") or item.get("fullHDURL") or item.get("imageURL") or image_url
                
                results.append({
                    "title": item.get("tags") or query,
                    "url": image_url,
                    "thumbnail": item.get("previewURL", image_url),
                    "full": full_url,
                    "author": item.get("user", "Unknown"),
                    "author_url": f"https://pixabay.com/users/{item.get('user', '')}-{item.get('user_id', '')}/" if item.get('user_id') else "",
                    "source": "Pixabay",
                    "source_url": item.get("pageURL", ""),
                    "width": item.get("imageWidth") or item.get("webformatWidth"),
                    "height": item.get("imageHeight") or item.get("webformatHeight"),
                    "likes": item.get("likes", 0),
                    "views": item.get("views", 0),
                    "downloads": item.get("downloads", 0)
                })
            return results
    
    def _fallback_image_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback results when APIs are not configured."""
        return [
            {
                "title": f"Image related to: {query}",
                "url": f"https://source.unsplash.com/800x600/?{query.replace(' ', ',')}",
                "thumbnail": f"https://source.unsplash.com/300x200/?{query.replace(' ', ',')}",
                "source": "Unsplash (fallback)",
                "note": "Configure API keys for better results"
            }
        ] * min(limit, 5)


# Singleton instance
image_search_service = ImageSearchService()

