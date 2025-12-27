"""
Academic Search Service - Semantic Scholar & Exa Integration

Enhances context research with academic paper search and neural search.
"""

import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings


class AcademicSearchService:
    """
    Search academic papers and research using Semantic Scholar and Exa.
    
    Provides:
    - Academic paper search
    - Citation analysis
    - Research trends
    - Neural semantic search
    """
    
    def __init__(self):
        self.semantic_scholar_key = settings.SEMANTIC_SCHOLAR_API_KEY
        self.exa_key = settings.EXA_API_KEY
        
        self.ss_base_url = "https://api.semanticscholar.org/graph/v1"
        self.exa_base_url = "https://api.exa.ai"
    
    async def search_academic_papers(
        self,
        query: str,
        max_results: int = 5,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search academic papers using Semantic Scholar with retry logic.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of papers with titles, abstracts, citations
        """
        if not self.semantic_scholar_key:
            print("   ⚠️  Semantic Scholar API key not configured")
            return []
        
        for attempt in range(max_retries):
            try:
                timeout = 30.0 + (attempt * 10)  # Increase timeout with each retry
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        f"{self.ss_base_url}/paper/search",
                        params={
                            "query": query,
                            "limit": max_results,
                            "fields": "title,abstract,year,citationCount,authors,venue"
                        },
                        headers={"x-api-key": self.semantic_scholar_key}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    papers = data.get("data", [])
                    print(f"   ✓ Found {len(papers)} academic papers")
                    return papers
                    
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"   ⏳ Timeout - retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    print(f"   ✗ Semantic Scholar search timed out after {max_retries} attempts")
                    return []
                    
            except httpx.HTTPStatusError as e:
                print(f"   ✗ Semantic Scholar API error: HTTP {e.response.status_code}")
                return []
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   ⚠️  Error: {str(e)[:50]} - retrying in {wait_time}s")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    print(f"   ✗ Semantic Scholar search failed: {str(e)[:50]}...")
                    return []
        
        return []
    
    async def search_with_exa(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "neural",
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Neural search using Exa with retry logic.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_type: "neural" or "keyword"
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of search results
        """
        if not self.exa_key:
            print("   ⚠️  Exa API key not configured")
            return []
        
        for attempt in range(max_retries):
            try:
                timeout = 30.0 + (attempt * 10)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.exa_base_url}/search",
                        headers={
                            "Content-Type": "application/json",
                            "x-api-key": self.exa_key
                        },
                        json={
                            "query": query,
                            "num_results": max_results,
                            "type": search_type,
                            "contents": {
                                "text": True
                            }
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    print(f"   ✓ Exa found {len(results)} results")
                    return results
                    
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   ⏳ Exa timeout - retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    print(f"   ✗ Exa search timed out after {max_retries} attempts")
                    return []
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   ⚠️  Exa error: {str(e)[:50]} - retrying in {wait_time}s")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    print(f"   ✗ Exa search failed: {str(e)[:50]}...")
                    return []
        
        return []
    
    async def get_research_context(
        self,
        topic: str,
        case_study: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive research context combining academic papers and web search.
        
        Args:
            topic: Research topic
            case_study: Case study
            
        Returns:
            Research context with papers, citations, and insights
        """
        print(f"\n📚 ACADEMIC SEARCH")
        print(f"   Searching for: {case_study} {topic}")
        
        # Search academic papers
        papers_query = f"{case_study} {topic}"
        papers = await self.search_academic_papers(papers_query, max_results=5)
        
        # Search with Exa for broader context
        exa_query = f"{case_study} {topic} research"
        exa_results = await self.search_with_exa(exa_query, max_results=5)
        
        # Extract insights
        context = {
            "academic_papers": [],
            "key_findings": [],
            "citation_trends": [],
            "research_gaps": []
        }
        
        # Process papers
        for paper in papers:
            context["academic_papers"].append({
                "title": paper.get("title", ""),
                "year": paper.get("year", ""),
                "citations": paper.get("citationCount", 0),
                "abstract": paper.get("abstract", "")[:200] + "..."
            })
            
            # Extract key findings from abstracts
            abstract = paper.get("abstract", "")
            if abstract:
                context["key_findings"].append(abstract[:150] + "...")
        
        # Process Exa results
        for result in exa_results:
            if result.get("text"):
                context["key_findings"].append(result["text"][:150] + "...")
        
        print(f"   ✓ Compiled {len(context['academic_papers'])} papers")
        print(f"   ✓ Extracted {len(context['key_findings'])} key findings\n")
        
        return context


# Singleton instance
academic_search_service = AcademicSearchService()
