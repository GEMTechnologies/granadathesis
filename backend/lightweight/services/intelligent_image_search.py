"""
Intelligent Image Search Service

Uses LLM for query refinement, entity resolution, and relevance filtering.
Much smarter than simple keyword matching.

Features:
- Query refinement with LLM
- Entity resolution (e.g., "president of Uganda" → "Yoweri Museveni")
- Multi-step strategy (web search first, then image search)
- Relevance filtering with LLM
- Better image sources
"""

import httpx
from typing import Dict, List, Any, Optional
from core.config import settings
from services.deepseek_direct import deepseek_direct_service
from services.web_search import WebSearchService
from services.image_search import image_search_service


class IntelligentImageSearchService:
    """Intelligent image search with LLM-powered query refinement and filtering."""
    
    def __init__(self):
        self.web_search = WebSearchService()
        self.base_image_search = image_search_service
        
    async def search_intelligent(
        self,
        query: str,
        limit: int = 10,
        require_person: bool = False,
        require_official: bool = False
    ) -> Dict[str, Any]:
        """
        Intelligently search for images with query refinement and relevance filtering.
        
        Args:
            query: User's image search query
            limit: Number of results to return
            require_person: If True, expects person/portrait images
            require_official: If True, prefers official/professional images
            
        Returns:
            Dict with refined_query, entity_info, and filtered results
        """
        # Step 1: Analyze query and determine strategy
        analysis = await self._analyze_query(query, require_person, require_official)
        
        # Step 2: Entity resolution (if needed)
        entity_info = None
        if analysis.get("needs_entity_resolution"):
            entity_info = await self._resolve_entity(analysis["entity_query"])
            if entity_info:
                query = entity_info.get("refined_query", query)
        
        # Step 3: Query refinement with LLM
        refined_query = await self._refine_query(query, analysis)
        
        # Step 4: Search images with refined query
        image_results = await self.base_image_search.search(
            refined_query,
            limit=limit * 3,  # Get more for filtering
            deduplicate=True
        )
        
        # Step 5: Relevance filtering
        if entity_info or analysis.get("has_specific_requirements"):
            filtered_results = await self._filter_results(
                image_results,
                query,
                refined_query,
                entity_info
            )
        else:
            filtered_results = image_results[:limit]
        
        return {
            "original_query": query,
            "refined_query": refined_query,
            "entity_info": entity_info,
            "analysis": analysis,
            "results": filtered_results[:limit],
            "total_found": len(image_results),
            "total_filtered": len(filtered_results)
        }
    
    async def _analyze_query(
        self,
        query: str,
        require_person: bool,
        require_official: bool
    ) -> Dict[str, Any]:
        """Analyze query to determine search strategy."""
        prompt = f"""Analyze this image search query and determine the best search strategy:

Query: "{query}"

Determine:
1. What type of image is needed? (person/portrait, place/landscape, object, diagram, etc.)
2. Does this need entity resolution? (e.g., "president of Uganda" needs to find WHO is the president)
3. What keywords should be added for better results? (e.g., "portrait", "official", "photo")

Respond in JSON format:
{{
    "type": "person|place|object|other",
    "needs_entity_resolution": true/false,
    "entity_query": "query to search for entity info" (if needed),
    "suggested_keywords": ["keyword1", "keyword2"],
    "has_specific_requirements": true/false,
    "reasoning": "brief explanation"
}}"""

        try:
            response = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="deepseek",
                temperature=0.3
            )
            
            # Parse JSON
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"⚠️ Query analysis failed: {e}")
        
        # Fallback analysis
        query_lower = query.lower()
        needs_resolution = any(term in query_lower for term in [
            "president", "prime minister", "leader", "head of", "mayor of"
        ])
        
        return {
            "type": "person" if require_person or "president" in query_lower or "portrait" in query_lower else "other",
            "needs_entity_resolution": needs_resolution,
            "entity_query": query if needs_resolution else None,
            "suggested_keywords": ["portrait", "photo", "official"] if require_person else [],
            "has_specific_requirements": require_person or require_official,
            "reasoning": "Fallback analysis"
        }
    
    async def _resolve_entity(self, entity_query: str) -> Optional[Dict[str, Any]]:
        """Resolve entity (e.g., find who is the president of Uganda)."""
        try:
            # Use web search to find entity information
            search_query = f"who is {entity_query} name"
            search_result = await self.web_search._search(search_query, max_results=3)
            
            if not search_result or "results" not in search_result:
                return None
            
            # Extract entity name from search results
            results_text = "\n".join([
                r.get("content", "")[:200] for r in search_result.get("results", [])[:3]
            ])
            
            prompt = f"""Extract the specific entity name from this search result:

Search Query: "{entity_query}"
Search Results:
{results_text}

Extract:
1. The specific name of the entity (e.g., "Yoweri Museveni" for "president of Uganda")
2. A refined search query for images (e.g., "Yoweri Museveni president Uganda portrait")

Respond in JSON:
{{
    "entity_name": "extracted name",
    "refined_query": "refined query for image search",
    "confidence": "high|medium|low"
}}"""

            response = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="deepseek",
                temperature=0.2
            )
            
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                entity_data = json.loads(json_match.group())
                entity_data["original_query"] = entity_query
                return entity_data
        except Exception as e:
            print(f"⚠️ Entity resolution failed: {e}")
        
        return None
    
    async def _refine_query(
        self,
        query: str,
        analysis: Dict[str, Any]
    ) -> str:
        """Refine query with LLM for better search results."""
        suggested_keywords = analysis.get("suggested_keywords", [])
        query_type = analysis.get("type", "other")
        
        prompt = f"""Refine this image search query for better results:

Original Query: "{query}"
Query Type: {query_type}
Suggested Keywords: {suggested_keywords}

Create an optimized search query that will return the most relevant images.
Add relevant keywords like "portrait", "official", "photo", "professional" when appropriate.

Respond with ONLY the refined query, nothing else."""

        try:
            refined = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="deepseek",
                temperature=0.4
            )
            refined = refined.strip().strip('"').strip("'")
            if refined and len(refined) > 10:
                return refined
        except Exception as e:
            print(f"⚠️ Query refinement failed: {e}")
        
        # Fallback: Add keywords to original query
        if query_type == "person" and suggested_keywords:
            return f"{query} {' '.join(suggested_keywords[:2])}"
        
        return query
    
    async def _filter_results(
        self,
        results: List[Dict[str, Any]],
        original_query: str,
        refined_query: str,
        entity_info: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter results for relevance using LLM."""
        if not results:
            return []
        
        # Limit to first 20 for efficiency
        results_to_filter = results[:20]
        
        # Create prompt for relevance scoring
        entity_name = entity_info.get("entity_name", "") if entity_info else ""
        context = f"Searching for: {original_query}"
        if entity_name:
            context += f" (Entity: {entity_name})"
        
        # Prepare image metadata for filtering
        image_descriptions = []
        for i, img in enumerate(results_to_filter):
            title = img.get("title", "")
            source = img.get("source", "")
            desc = f"{i+1}. {title} (Source: {source})"
            image_descriptions.append(desc)
        
        prompt = f"""Rate the relevance of these image search results:

Context: {context}
Refined Query: {refined_query}

Image Results:
{chr(10).join(image_descriptions)}

For each image (1-{len(results_to_filter)}), determine if it's relevant to the search query.
Consider: Does this image match what was requested? Is it the right person/place/object?

Respond in JSON array format:
[
    {{"index": 1, "relevant": true, "score": 0.9, "reason": "brief reason"}},
    {{"index": 2, "relevant": false, "score": 0.2, "reason": "brief reason"}},
    ...
]

Only include images with score >= 0.7."""

        try:
            response = await openrouter_service.generate_content(
                prompt=prompt,
                model_key="deepseek",
                temperature=0.2
            )
            
            import json
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                scores = json.loads(json_match.group())
                
                # Filter results based on scores
                filtered = []
                for score_item in scores:
                    idx = score_item.get("index", 0) - 1  # Convert to 0-based
                    if 0 <= idx < len(results_to_filter) and score_item.get("score", 0) >= 0.7:
                        # Add score to result
                        result = results_to_filter[idx].copy()
                        result["relevance_score"] = score_item.get("score", 0.7)
                        result["relevance_reason"] = score_item.get("reason", "")
                        filtered.append(result)
                
                # Sort by relevance score
                filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                return filtered
        except Exception as e:
            print(f"⚠️ Relevance filtering failed: {e}")
        
        # Fallback: Return all results
        return results_to_filter
    
    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Simple search method that calls search_intelligent with defaults.
        Provides backward compatibility for API that expects .search().
        
        Args:
            query: Image search query
            limit: Number of results to return
            
        Returns:
            List of image results
        """
        result = await self.search_intelligent(query, limit=limit)
        return result.get("results", [])
    async def save_image_locally(
        self,
        image_url: str,
        workspace_id: str = "default",
        filename: str = None
    ) -> Dict[str, Any]:
        """
        Download an image and save it locally in the workspace.
        
        Args:
            image_url: URL of the image to download
            workspace_id: Workspace to save in
            filename: Optional filename (auto-generated if None)
            
        Returns:
            {"success": True, "local_path": "...", "relative_path": "..."}
        """
        try:
            import httpx
            import hashlib
            from pathlib import Path
            import time
            
            # Create images directory
            images_dir = Path("workspaces") / workspace_id / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Download image
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                
                content = response.content
                content_type = response.headers.get("content-type", "")
                
                # Determine extension
                if "png" in content_type:
                    ext = ".png"
                elif "gif" in content_type:
                    ext = ".gif"
                elif "webp" in content_type:
                    ext = ".webp"
                else:
                    ext = ".jpg"  # Default to jpg
                
                # Generate filename if not provided
                if not filename:
                    hash_str = hashlib.md5(content).hexdigest()[:8]
                    filename = f"img_{int(time.time())}_{hash_str}{ext}"
                elif not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    filename += ext
                
                # Save
                file_path = images_dir / filename
                file_path.write_bytes(content)
                
                return {
                    "success": True,
                    "local_path": str(file_path),
                    "relative_path": f"{workspace_id}/images/{filename}",
                    "filename": filename,
                    "size": len(content)
                }
                
        except Exception as e:
            print(f"⚠️ Image download failed: {e}")
            return {"success": False, "error": str(e), "url": image_url}
    
    async def search_and_save(
        self,
        query: str,
        workspace_id: str = "default",
        limit: int = 1,
        save_all: bool = False
    ) -> Dict[str, Any]:
        """
        Search for images and save them locally.
        
        Args:
            query: Image search query
            workspace_id: Workspace to save images in
            limit: Number of images to return (and save if save_all=True)
            save_all: If True, save all found images; if False, save only first
            
        Returns:
            {
                "success": True,
                "query": "...",
                "saved_images": [{"local_path": "...", ...}],
                "markdown": "![caption](local/path.jpg)"
            }
        """
        try:
            # Search for images
            results = await self.search(query, limit=limit)
            
            if not results:
                return {
                    "success": False,
                    "error": "No images found",
                    "query": query
                }
            
            saved_images = []
            
            # Determine how many to save
            images_to_save = results if save_all else [results[0]]
            
            for img in images_to_save:
                url = img.get("url") or img.get("full") or img.get("src")
                if url:
                    result = await self.save_image_locally(url, workspace_id)
                    if result.get("success"):
                        saved_images.append({
                            **result,
                            "original_url": url,
                            "title": img.get("title", ""),
                            "source": img.get("source", "")
                        })
            
            if not saved_images:
                return {
                    "success": False,
                    "error": "Failed to download any images",
                    "query": query
                }
            
            # Generate markdown for the first image
            first_img = saved_images[0]
            markdown = f"![{query}]({first_img['relative_path']})"
            
            return {
                "success": True,
                "query": query,
                "saved_images": saved_images,
                "markdown": markdown,
                "first_image": first_img
            }
            
        except Exception as e:
            print(f"⚠️ Search and save failed: {e}")
            return {"success": False, "error": str(e), "query": query}

# Singleton instance
intelligent_image_search_service = IntelligentImageSearchService()




