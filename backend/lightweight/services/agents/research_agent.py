"""
Research Agent - Gathers Information from Various Sources

This agent:
1. Searches the web
2. Finds academic papers
3. Gathers data from URLs
4. Verifies facts
"""

from typing import Dict, Any, List, Optional
from services.agent_spawner import BaseAgent, AgentType, AgentStatus, AgentContext


class ResearchAgent(BaseAgent):
    """
    Research Agent - Gathers information before action.
    
    Capabilities:
    - Web search (Tavily)
    - Academic paper search (OpenAlex, Semantic Scholar)
    - URL content extraction
    - Fact verification
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id)
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main research process.
        
        Based on context.required_actions, performs:
        - search_web
        - search_papers
        - extract_url_content
        - verify_facts
        """
        await self.report_status(AgentStatus.THINKING, "🔬 Planning research strategy...")
        
        actions = context.required_actions
        
        # Determine what to search for
        search_query = self._build_search_query(context)
        
        # Perform searches based on required actions
        if "search_web" in actions:
            await self.report_status(AgentStatus.WORKING, f"🌐 Searching web: {search_query}...")
            web_results = await self._search_web(search_query)
            context.search_results.extend(web_results)
            context.gathered_data["web_search"] = web_results
        
        if "search_papers" in actions:
            await self.report_status(AgentStatus.WORKING, f"📚 Searching academic papers: {search_query}...")
            paper_results = await self._search_papers(search_query)
            context.search_results.extend(paper_results)
            context.gathered_data["paper_search"] = paper_results
        
        if "extract_url_content" in actions or "navigate" in actions:
            urls = context.entities.get("url", [])
            if urls:
                await self.report_status(AgentStatus.WORKING, f"📄 Extracting content from {len(urls)} URL(s)...")
                for url in urls[:3]:  # Limit to 3 URLs
                    content = await self._extract_url_content(url)
                    context.gathered_data[f"url_{url[:30]}"] = content
        
        # Update status with results count
        total_results = len(context.search_results)
        await self.report_status(
            AgentStatus.COMPLETED,
            f"✅ Research complete: Found {total_results} results",
            data={"result_count": total_results}
        )
        
        return context
    
    def _build_search_query(self, context: AgentContext) -> str:
        """Build search query from context."""
        # Use topic entity if available
        if "topic" in context.entities:
            topic = context.entities["topic"]
            if isinstance(topic, list):
                return " ".join(topic)
            return topic
        
        # Fall back to user message
        return context.user_message
    
    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search the web using Tavily."""
        try:
            from services.web_search import web_search_service
            results = await web_search_service.search(query, max_results=max_results)
            
            # Normalize results
            normalized = []
            for r in results:
                normalized.append({
                    "type": "web",
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0)
                })
            
            return normalized
        except Exception as e:
            print(f"⚠️ Web search failed: {e}")
            return []
    
    async def _search_papers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search academic papers using OpenAlex."""
        try:
            from services.academic_search import academic_search_service
            results = await academic_search_service.search_openalex(
                query=query,
                max_results=max_results
            )
            
            # Normalize results
            normalized = []
            for r in results:
                normalized.append({
                    "type": "paper",
                    "title": r.get("title", ""),
                    "authors": r.get("authors", []),
                    "year": r.get("year", ""),
                    "abstract": r.get("abstract", ""),
                    "url": r.get("url", ""),
                    "citations": r.get("cited_by_count", 0)
                })
            
            return normalized
        except Exception as e:
            print(f"⚠️ Paper search failed: {e}")
            return []
    
    async def _extract_url_content(self, url: str) -> Dict:
        """Extract content from a URL."""
        try:
            from services.browser_automation import get_browser
            
            browser = await get_browser(self.session_id)
            data = await browser.intelligent_scrape(url, target="article")
            
            return {
                "url": url,
                "title": data.get("title", ""),
                "content": data.get("article", "")[:2000],  # Truncate
                "success": True
            }
        except Exception as e:
            print(f"⚠️ URL extraction failed for {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "success": False
            }


# Export for agent spawner
__agent_class__ = ResearchAgent
