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
from datetime import datetime
import json
import base64
import asyncio


class ResearchAgent(BaseAgent):
    """
    Research Agent - Gathers information before action.
    
    Capabilities:
    - Web search (Tavily)
    - Academic paper search (OpenAlex, Semantic Scholar)
    - URL content extraction
    - Fact verification
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id, job_id)
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main research process with PARALLEL execution.
        
        Executes Web Search, Academic Search, and Browser Automation concurrently
        to maximize information gathering as requested by user.
        """
        await self.report_status(AgentStatus.THINKING, "🔬 Planning comprehensive research strategy...")
        
        actions = context.required_actions
        search_query = self._build_search_query(context)
        
        tasks = []
        
        # 1. Web Search Task
        if "search_web" in actions or "search" in str(actions):
            tasks.append(self._run_web_search(context, search_query))
            
        # 2. Academic Search Task (Always run if we have a query, as requested)
        if search_query and len(search_query) > 3:
             tasks.append(self._run_academic_search(context, search_query))
             
        # 3. Browser/URL Extraction Task
        if "extract_url_content" in actions or "navigate" in actions:
            tasks.append(self._run_url_extraction(context))
            
        # Execute all tasks in parallel
        if tasks:
            await self.report_status(AgentStatus.WORKING, f"🚀 Launching parallel search agents for: '{search_query}'...")
            await asyncio.gather(*tasks)
            
        # AUTO-BROWSE: If we found results but didn't browse, pick "best" result to browse
        # This ensures the user sees browser activity ("Full Power" mode)
        if context.search_results and "extract_url_content" not in actions:
            best_url = context.search_results[0].get("url")
            if best_url:
                await self.report_status(AgentStatus.WORKING, f"🌍 Auto-browsing top result: {best_url}...")
                context.entities["url"] = [best_url]
                await self._run_url_extraction(context)
            
        # Update status with results count
        total_results = len(context.search_results)
        
        # PERSISTENCE: Save high-quality results to Sources Service
        if total_results > 0:
            await self.report_status(AgentStatus.WORKING, f"💾 Persisting {total_results} results to thesis sources...")
            try:
                from services.sources_service import sources_service
                for res in context.search_results:
                    source_data = {
                        "title": res.get("title", "Unknown"),
                        "url": res.get("url", ""),
                        "abstract": res.get("abstract") or res.get("content", "")[:500],
                        "type": res.get("type", "web"),
                        "authors": res.get("authors", ["Online Source"]),
                        "year": res.get("year", "2024")
                    }
                    await sources_service.add_source(
                        context.workspace_id, 
                        source_data, 
                        download_pdf=True,
                        extract_text=True
                    )
            except Exception as e:
                print(f"⚠️ Failed to persist sources: {e}")
                
        await self.report_status(
            AgentStatus.COMPLETED,
            f"✅ Research complete: Found {total_results} results",
            data={"result_count": total_results}
        )

        return context

    async def _run_web_search(self, context: AgentContext, query: str):
        """Execute web search with UI updates."""
        try:
            await self.report_status(AgentStatus.WORKING, f"🌐 Searching web: {query}...")
            
            # VISUAL FEEDBACK SPEED BOOST: 
            # Launch browser to Google immediately so user sees results in preview FAST
            # This runs in background while we wait for API data
            asyncio.create_task(self._visual_search_feedback(context, query))
            
            # Live Preview status
            await self._publish_browser_event(context.workspace_id, "loading", {"loading": True, "action": f"Searching web for '{query}'..."})
            
            web_results = await self._search_web(query)
            
            # Live Preview update
            await self._publish_browser_event(context.workspace_id, "action", {"action": f"Found {len(web_results)} web results"})
            await self._publish_browser_event(context.workspace_id, "loading", {"loading": False})
            
            context.search_results.extend(web_results)
            context.gathered_data["web_search"] = web_results
            
            if self.events:
                await self.events.publish(self.job_id, "stage_completed", {
                    "stage": "web_search",
                    "message": f"✅ Found {len(web_results)} web results."
                }, session_id=self.session_id)
        except Exception as e:
            print(f"Web search error: {e}")

    async def _visual_search_feedback(self, context: AgentContext, query: str):
        """
        Show visual search results in browser preview IMMEDIATELY.
        Does not affect data gathering, just satisfies user need for visual confirmation.
        """
        try:
            from services.browser_automation import get_browser
            import urllib.parse
            
            browser = await get_browser(context.workspace_id, headless=True)
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            await self._publish_browser_event(context.workspace_id, "action", {"action": f"Visualizing search for: {query}"})
            await browser.navigate(search_url)
        except Exception as e:
            print(f"Visual search feedback failed (non-critical): {e}")

    async def _run_academic_search(self, context: AgentContext, query: str):
        """Execute academic search with UI updates."""
        try:
            await self.report_status(AgentStatus.WORKING, f"📚 Searching academic sources: {query}...")
            
            # Live Preview
            await self._publish_browser_event(context.workspace_id, "loading", {"loading": True, "action": f"Querying academic databases..."})
            
            paper_results = await self._search_papers(query)
            
            # Live Preview update
            await self._publish_browser_event(context.workspace_id, "action", {"action": f"Found {len(paper_results)} academic papers"})
            
            context.search_results.extend(paper_results)
            context.gathered_data["paper_search"] = paper_results
            
            if self.events:
                await self.events.publish(self.job_id, "stage_completed", {
                    "stage": "academic_search",
                    "message": f"✅ Found {len(paper_results)} papers."
                }, session_id=self.session_id)
        except Exception as e:
            print(f"Academic search error: {e}")

    async def _run_url_extraction(self, context: AgentContext):
        """Execute URL extraction using Playwright."""
        try:
            urls = context.entities.get("url", [])
            if urls:
                await self.report_status(AgentStatus.WORKING, f"📄 Extracting content from {len(urls)} URLs...")
                for url in urls[:3]:
                    # Live Preview
                    await self._publish_browser_event(context.workspace_id, "loading", {"loading": True, "action": f"Browsing: {url}..."})
                    
                    content = await self._extract_url_content(url)
                    context.gathered_data[f"url_{url[:30]}"] = content
                    
                    # Live Preview
                    await self._publish_browser_event(context.workspace_id, "action", {"action": f"Extracted content from {url}"})
        except Exception as e:
            print(f"URL extraction error: {e}")


    
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


    async def _publish_browser_event(self, workspace_id: str, event_type: str, data: Dict):
        """Publish an event to the browser preview stream using workspace_id."""
        await self._ensure_connections()
        if self.redis:
            payload = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                **data
            }
            try:
                # Use workspace_id for the channel to match frontend subscription
                await self.redis.publish(f"browser:{workspace_id}", json.dumps(payload))
            except Exception as e:
                print(f"⚠️ Failed to publish browser event: {e}")


# Export for agent spawner
__agent_class__ = ResearchAgent
