"""
Browser Automation Service with Live Streaming

Agent can control a browser and user watches in real-time!
Uses Playwright for automation + screenshots for streaming.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import asyncio
import base64
import json


@dataclass
class BrowserAction:
    """Single browser action."""
    action_type: str  # navigate, click, type, scroll, screenshot
    params: Dict
    timestamp: str
    screenshot_path: Optional[str] = None


class BrowserAutomation:
    """
    Browser automation with LIVE STREAMING.
    
    User sees everything the agent does in real-time!
    
    Capabilities:
    - Navigate to URLs
    - Click elements
    - Type text
    - Scrape data
    - Take screenshots
    - Fill forms
    - Execute JavaScript
    - Stream browser screen to frontend
    """
    
    def __init__(self, workspace_id: str, headless: bool = False):
        self.workspace_id = workspace_id
        self.headless = headless
        self.browser = None
        self.page = None
        self.context = None
        
        # Screenshots directory for streaming
        from config import get_browser_dir
        self.screenshots_dir = get_browser_dir(workspace_id)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Action history
        self.actions: List[BrowserAction] = []
        
        # Stream callback (sends screenshots to frontend)
        self.stream_callback = None
    
    async def start(self, stream_callback=None):
        """Start browser instance with STEALTH MODE."""
        from playwright.async_api import async_playwright
        
        self.stream_callback = stream_callback
        
        self.playwright = await async_playwright().start()
        
        # Launch with anti-detection args
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',  # For testing
            ]
        )
        
        # Stealth context (looks like real browser!)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},  # Common resolution
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],  # Real browser permissions
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        )
        
        # Enable downloads
        await self.context.set_default_timeout(30000)
        
        self.page = await self.context.new_page()
        
        # Inject stealth scripts (hide webdriver)
        await self.page.add_init_script('''
            // Remove webdriver property
            Object.defineProperty(navigator, "webdriver", {get: () => false});
            
            // Mock plugins
            Object.defineProperty(navigator, "plugins", {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, "languages", {
                get: () => ["en-US", "en"]
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === "notifications" ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
        ''')
        
        print(f"✅ Stealth browser started for workspace {self.workspace_id}")
    
    async def navigate(self, url: str) -> str:
        """
        Navigate to URL and take screenshot.
        
        Returns: Screenshot base64 for streaming
        """
        if not self.page:
            await self.start()
        
        await self.page.goto(url, wait_until='networkidle')
        screenshot = await self._take_screenshot(f"navigate_{len(self.actions)}")
        
        action = BrowserAction(
            action_type='navigate',
            params={'url': url},
            timestamp=datetime.now().isoformat(),
            screenshot_path=screenshot
        )
        self.actions.append(action)
        
        # Stream to frontend
        if self.stream_callback:
            await self.stream_callback({
                'type': 'browser_action',
                'action': 'navigate',
                'url': url,
                'screenshot': screenshot
            })
        
        return screenshot
    
    async def click(self, selector: str) -> str:
        """Click element and take screenshot."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        await self.page.click(selector)
        await self.page.wait_for_timeout(500)  # Wait for animation
        
        screenshot = await self._take_screenshot(f"click_{len(self.actions)}")
        
        action = BrowserAction(
            action_type='click',
            params={'selector': selector},
            timestamp=datetime.now().isoformat(),
            screenshot_path=screenshot
        )
        self.actions.append(action)
        
        # Stream
        if self.stream_callback:
            await self.stream_callback({
                'type': 'browser_action',
                'action': 'click',
                'selector': selector,
                'screenshot': screenshot
            })
        
        return screenshot
    
    async def type_text(self, selector: str, text: str) -> str:
        """Type text into element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        await self.page.fill(selector, text)
        await self.page.wait_for_timeout(300)
        
        screenshot = await self._take_screenshot(f"type_{len(self.actions)}")
        
        action = BrowserAction(
            action_type='type',
            params={'selector': selector, 'text': text},
            timestamp=datetime.now().isoformat(),
            screenshot_path=screenshot
        )
        self.actions.append(action)
        
        # Stream
        if self.stream_callback:
            await self.stream_callback({
                'type': 'browser_action',
                'action': 'type',
                'selector': selector,
                'text': text,
                'screenshot': screenshot
            })
        
        return screenshot
    
    async def scroll(self, amount: int = 500) -> str:
        """Scroll page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        await self.page.evaluate(f"window.scrollBy(0, {amount})")
        await self.page.wait_for_timeout(300)
        
        screenshot = await self._take_screenshot(f"scroll_{len(self.actions)}")
        
        action = BrowserAction(
            action_type='scroll',
            params={'amount': amount},
            timestamp=datetime.now().isoformat(),
            screenshot_path=screenshot
        )
        self.actions.append(action)
        
        # Stream
        if self.stream_callback:
            await self.stream_callback({
                'type': 'browser_action',
                'action': 'scroll',
                'amount': amount,
                'screenshot': screenshot
            })
        
        return screenshot
    
    async def extract_text(self, selector: str) -> str:
        """Extract text from element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        text = await self.page.text_content(selector)
        
        action = BrowserAction(
            action_type='extract',
            params={'selector': selector, 'text': text},
            timestamp=datetime.now().isoformat()
        )
        self.actions.append(action)
        
        return text or ""
    
    async def execute_script(self, script: str) -> any:
        """Execute JavaScript in browser."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        result = await self.page.evaluate(script)
        
        action = BrowserAction(
            action_type='script',
            params={'script': script, 'result': str(result)},
            timestamp=datetime.now().isoformat()
        )
        self.actions.append(action)
        
        return result
    
    async def fill_form(self, form_data: Dict[str, str]) -> str:
        """Fill form fields."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        for selector, value in form_data.items():
            await self.page.fill(selector, value)
            await self.page.wait_for_timeout(200)
        
        screenshot = await self._take_screenshot(f"form_{len(self.actions)}")
        
        action = BrowserAction(
            action_type='fill_form',
            params={'form_data': form_data},
            timestamp=datetime.now().isoformat(),
            screenshot_path=screenshot
        )
        self.actions.append(action)
        
        # Stream
        if self.stream_callback:
            await self.stream_callback({
                'type': 'browser_action',
                'action': 'fill_form',
                'fields': len(form_data),
                'screenshot': screenshot
            })
        
        return screenshot
    
    async def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            return ""
        return self.page.url
    
    async def get_title(self) -> str:
        """Get page title."""
        if not self.page:
            return ""
        return await self.page.title()
    
    async def wait_for_selector(self, selector: str, timeout: int = 5000):
        """Wait for element to appear."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def download_pdf(self, url: str) -> Dict:
        """
        Download PDF and extract text.
        
        Returns: {
            'path': str,
            'text': str,
            'pages': int
        }
        """
        if not self.page:
            await self.start()
        
        # Set download path
        downloads_dir = self.screenshots_dir.parent / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        # Navigate and wait for download
        async with self.page.expect_download() as download_info:
            await self.page.goto(url)
        
        download = await download_info.value
        pdf_path = downloads_dir / download.suggested_filename
        await download.save_as(str(pdf_path))
        
        # Extract text using PyPDF2
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            return {
                'path': str(pdf_path),
                'text': text,
                'pages': len(pdf_reader.pages),
                'filename': download.suggested_filename
            }
        except Exception as e:
            return {
                'path': str(pdf_path),
                'text': f"Error extracting text: {e}",
                'pages': 0,
                'filename': download.suggested_filename
            }
    
    async def download_image(self, url: str) -> Dict:
        """
        Download image and get info.
        
        Returns: {
            'path': str,
            'size': tuple,
            'format': str
        }
        """
        if not self.page:
            await self.start()
        
        downloads_dir = self.screenshots_dir.parent / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        # Download image
        async with self.page.expect_download() as download_info:
            await self.page.goto(url)
        
        download = await download_info.value
        img_path = downloads_dir / download.suggested_filename
        await download.save_as(str(img_path))
        
        # Get image info
        try:
            from PIL import Image
            with Image.open(img_path) as img:
                return {
                    'path': str(img_path),
                    'size': img.size,
                    'format': img.format,
                    'filename': download.suggested_filename
                }
        except Exception as e:
            return {
                'path': str(img_path),
                'error': str(e),
                'filename': download.suggested_filename
            }
    
    async def intelligent_scrape(self, url: str, target: str = 'article') -> Dict:
        """
        Intelligently scrape content from webpage.
        
        Automatically finds:
        - Article text
        - Headlines
        - Images
        - Links
        - Tables
        
        Args:
            target: 'article', 'table', 'images', 'links', 'all'
        """
        if not self.page:
            await self.start()
        
        await self.page.goto(url, wait_until='networkidle')
        
        data = {}
        
        if target in ['article', 'all']:
            # Extract main article text (multiple strategies)
            selectors = [
                'article',
                '[role="article"]',
                '.article-content',
                '.post-content',
                'main',
                '#content'
            ]
            
            article_text = ""
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        article_text = await element.text_content()
                        if len(article_text) > 100:  # Found substantial content
                            break
                except:
                    continue
            
            data['article'] = article_text.strip() if article_text else ""
        
        if target in ['images', 'all']:
            # Extract all images
            images = await self.page.evaluate("""
                () => {
                    return Array.from(document.images).map(img => ({
                        src: img.src,
                        alt: img.alt,
                        width: img.width,
                        height: img.height
                    }));
                }
            """)
            data['images'] = images
        
        if target in ['links', 'all']:
            # Extract all links
            links = await self.page.evaluate("""
                () => {
                    return Array.from(document.links).map(link => ({
                        href: link.href,
                        text: link.textContent.trim()
                    }));
                }
            """)
            data['links'] = links
        
        if target in ['table', 'all']:
            # Extract tables
            tables = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('table')).map(table => {
                        const rows = Array.from(table.rows).map(row => 
                            Array.from(row.cells).map(cell => cell.textContent.trim())
                        );
                        return rows;
                    });
                }
            """)
            data['tables'] = tables
        
        # Always include title and metadata
        data['title'] = await self.page.title()
        data['url'] = self.page.url
        
        return data
    
    async def _take_screenshot(self, name: str) -> str:
        """
        Take screenshot and return path.
        
        Screenshots are used for:
        1. Streaming to frontend
        2. Debugging
        3. Action history
        """
        if not self.page:
            return ""
        
        screenshot_path = self.screenshots_dir / f"{name}.png"
        await self.page.screenshot(path=str(screenshot_path))
        
        # Also return base64 for streaming
        with open(screenshot_path, 'rb') as f:
            image_bytes = f.read()
            base64_img = base64.b64encode(image_bytes).decode()
        
        return base64_img
    
    async def close(self):
        """Close browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        print(f"✅ Browser closed for workspace {self.workspace_id}")
    
    def get_action_history(self) -> List[Dict]:
        """Get all browser actions (for context)."""
        return [
            {
                'action': action.action_type,
                'params': action.params,
                'timestamp': action.timestamp,
                'has_screenshot': action.screenshot_path is not None
            }
            for action in self.actions
        ]


# Global browser instances (one per workspace)
browser_instances: Dict[str, BrowserAutomation] = {}


async def get_browser(workspace_id: str, headless: bool = False) -> BrowserAutomation:
    """Get or create browser instance for workspace."""
    if workspace_id not in browser_instances:
        browser_instances[workspace_id] = BrowserAutomation(
            workspace_id=workspace_id,
            headless=headless
        )
        await browser_instances[workspace_id].start()
    
    return browser_instances[workspace_id]


async def close_browser(workspace_id: str):
    """Close browser for workspace."""
    if workspace_id in browser_instances:
        await browser_instances[workspace_id].close()
        del browser_instances[workspace_id]
