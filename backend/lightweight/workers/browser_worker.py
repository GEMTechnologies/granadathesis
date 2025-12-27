"""
Browser Worker - Background Web Scraping

Handles long-running browser automation tasks.
"""

from celery_config import celery_app
from typing import List, Dict
import asyncio


@celery_app.task(bind=True, name='browser.scrape_urls')
def scrape_multiple_urls(self, urls: List[str], workspace_id: str, target='all'):
    """
    Scrape multiple URLs in sequence.
    
    Args:
        urls: List of URLs to scrape
        workspace_id: Workspace ID
        target: What to extract ('article', 'images', 'links', 'tables', 'all')
    """
    
    self.update_state(
        state='STARTED',
        meta={'total': len(urls), 'completed': 0}
    )
    
    from services.browser_automation import get_browser
    
    results = []
    
    async def scrape_all():
        browser = await get_browser(workspace_id, headless=True)
        
        for i, url in enumerate(urls):
            self.update_state(
                state='PROGRESS',
                meta={
                    'total': len(urls),
                    'completed': i,
                    'current_url': url
                }
            )
            
            data = await browser.intelligent_scrape(url, target=target)
            results.append({'url': url, 'data': data})
        
        await browser.close()
        return results
    
    return asyncio.run(scrape_all())


@celery_app.task(name='browser.download_resources')
def download_resources(self, urls: List[str], workspace_id: str, resource_type='pdf'):
    """
    Download PDFs or images from multiple URLs.
    
    Args:
        urls: List of resource URLs
        workspace_id: Workspace ID
        resource_type: 'pdf' or 'image'
    """
    
    from services.browser_automation import get_browser
    
    async def download_all():
        browser = await get_browser(workspace_id, headless=True)
        
        downloads = []
        for i, url in enumerate(urls):
            self.update_state(
                state='PROGRESS',
                meta={'completed': i + 1, 'total': len(urls)}
            )
            
            if resource_type == 'pdf':
                result = await browser.download_pdf(url)
            else:
                result = await browser.download_image(url)
            
            downloads.append(result)
        
        await browser.close()
        return downloads
    
    return asyncio.run(download_all())


@celery_app.task(bind=True, name='browser.web_search')
def web_search_browser(self, query: str, session_id: str = 'default'):
    """
    Search the web using Playwright browser.
    
    Navigates to DuckDuckGo, takes screenshots, streams to browser panel.
    
    Args:
        query: Search query
        session_id: Session ID for Redis streaming
    """
    import redis
    import json
    import os
    from services.browser_automation import BrowserAutomation
    
    # Setup Redis for streaming
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    if redis_url.startswith("redis://redis:") and not os.path.exists("/.dockerenv"):
        redis_url = redis_url.replace("redis://redis:", "redis://localhost:")
    r = redis.from_url(redis_url)
    
    def stream_to_browser(data):
        """Stream to browser preview panel."""
        r.publish(f"browser:{session_id}", json.dumps(data))
    
    self.update_state(state='STARTED', meta={'query': query})
    
    async def do_search():
        browser = BrowserAutomation(workspace_id=session_id, headless=False)
        await browser.start()
        
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        
        stream_to_browser({"type": "action", "action": f"Navigating to search: {query}"})
        screenshot = await browser.navigate(search_url)
        
        stream_to_browser({
            "type": "screenshot",
            "image": screenshot,
            "url": search_url
        })
        
        # Wait for results
        await browser.page.wait_for_timeout(2000)
        
        # Take another screenshot
        screenshot2 = await browser._take_screenshot("search_results")
        stream_to_browser({
            "type": "screenshot",
            "image": screenshot2,
            "url": browser.page.url
        })
        
        # Extract results
        results = await browser.page.evaluate("""
            () => {
                const results = [];
                const els = document.querySelectorAll('[data-result="web"]') || 
                           document.querySelectorAll('.result');
                els.forEach((el, i) => {
                    if (i < 5) {
                        const a = el.querySelector('a');
                        if (a) results.push({title: a.textContent, url: a.href});
                    }
                });
                return results;
            }
        """)
        
        stream_to_browser({"type": "action", "action": f"Found {len(results)} results"})
        
        # Don't close browser - keep it alive for user interaction
        return {"results": results, "query": query}
    
    return asyncio.run(do_search())

