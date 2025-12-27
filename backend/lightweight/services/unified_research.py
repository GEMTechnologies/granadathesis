import httpx
import asyncio
import os
import hashlib
import json
from typing import Dict, Any, List
from core.config import settings
from core.database import db

class UnifiedResearchService:
    """
    Unified Research Service that aggregates results from:
    - Serper (Google)
    - Tavily
    - Exa
    - Semantic Scholar
    - Firecrawl (Scraping)
    """
    
    def __init__(self):
        self.serper_key = settings.SERPER_API_KEY or os.getenv("SERPER_API_KEY")
        self.tavily_key = settings.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
        self.exa_key = settings.EXA_API_KEY or os.getenv("EXA_API_KEY")
        self.scholar_key = settings.SEMANTIC_SCHOLAR_API_KEY or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.firecrawl_key = settings.FIRECRAWL_API_KEY or os.getenv("FIRECRAWL_API_KEY")
        self.firecrawl_url = settings.FIRECRAWL_URL or os.getenv("FIRECRAWL_URL", "https://api.firecrawl.dev")

    async def collect_research(self, topic: str, case_study: str, thesis_id: str = "default") -> Dict[str, Any]:
        query = f"{topic} {case_study} economic impact analysis"
        print(f"\n🌐 UNIFIED RESEARCH: {query}")

        async with httpx.AsyncClient(timeout=30) as client:
            
            # Define search functions
            async def search_serper():
                if not self.serper_key: return {}
                try:
                    print("   🔍 Querying Serper...")
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                        json={"q": query}
                    )
                    return resp.json() if resp.status_code == 200 else {}
                except Exception as e:
                    print(f"   ⚠️ Serper failed: {e}")
                    return {}

            async def search_tavily():
                if not self.tavily_key: return {}
                try:
                    print("   🔍 Querying Tavily...")
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        headers={"Content-Type": "application/json"},
                        json={"api_key": self.tavily_key, "query": query, "search_depth": "basic", "max_results": 5}
                    )
                    return resp.json() if resp.status_code == 200 else {}
                except Exception as e:
                    print(f"   ⚠️ Tavily failed: {e}")
                    return {}

            async def search_exa():
                if not self.exa_key: return {}
                try:
                    print("   🔍 Querying Exa...")
                    resp = await client.post(
                        "https://api.exa.ai/search",
                        headers={"x-api-key": self.exa_key, "Content-Type": "application/json"},
                        json={"query": query, "type": "keyword", "numResults": 5}
                    )
                    return resp.json() if resp.status_code == 200 else {}
                except Exception as e:
                    print(f"   ⚠️ Exa failed: {e}")
                    return {}

            async def search_scholar():
                if not self.scholar_key: return {}
                try:
                    print("   🔍 Querying Semantic Scholar...")
                    resp = await client.get(
                        f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5&fields=title,year,abstract,url",
                        headers={"x-api-key": self.scholar_key}
                    )
                    return resp.json() if resp.status_code == 200 else {}
                except Exception as e:
                    print(f"   ⚠️ Semantic Scholar failed: {e}")
                    return {}

            # Run all searches in parallel
            responses = await asyncio.gather(
                search_serper(), 
                search_tavily(), 
                search_exa(), 
                search_scholar(),
                return_exceptions=True
            )

            serper_data = responses[0] if isinstance(responses[0], dict) else {}
            tavily_data = responses[1] if isinstance(responses[1], dict) else {}
            exa_data = responses[2] if isinstance(responses[2], dict) else {}
            scholar_data = responses[3] if isinstance(responses[3], dict) else {}

            # Collect URLs and Metadata
            # Structure: {url: {title, date, author, site_name}}
            url_metadata = {}

            # SERPER
            if "organic" in serper_data:
                for item in serper_data["organic"]:
                    if "link" in item:
                        url_metadata[item["link"]] = {
                            "title": item.get("title", ""),
                            "date": item.get("date", ""),
                            "site_name": item.get("source", ""),
                            "snippet": item.get("snippet", "")
                        }

            # TAVILY
            if "results" in tavily_data:
                for item in tavily_data["results"]:
                    if "url" in item:
                        url_metadata[item["url"]] = {
                            "title": item.get("title", ""),
                            "date": item.get("published_date", ""),
                            "site_name": "", # Tavily doesn't always provide site name explicitly
                            "snippet": item.get("content", "")
                        }

            # EXA
            if "results" in exa_data:
                for item in exa_data["results"]:
                    if "url" in item:
                        url_metadata[item["url"]] = {
                            "title": item.get("title", ""),
                            "date": item.get("publishedDate", ""),
                            "author": item.get("author", ""),
                            "snippet": item.get("text", "") # Exa might return text snippet
                        }
            
            urls = list(url_metadata.keys())
            print(f"   ✓ Found {len(urls)} unique URLs to scrape")

            # Scrape with Firecrawl
            pages = []
            if self.firecrawl_key:
                print(f"   🕷️ Scraping top 5 URLs with Firecrawl...")
                for url in urls[:5]:
                    try:
                        r = await client.post(
                            f"{self.firecrawl_url}/v1/scrape",
                            headers={"Authorization": f"Bearer {self.firecrawl_key}", "Content-Type": "application/json"},
                            json={"url": url, "formats": ["markdown"]}
                        )
                        if r.status_code == 200:
                            data = r.json()
                            text = data.get("data", {}).get("markdown", "")
                            if text:
                                pages.append({"url": url, "text": text})
                                # Save to database and file
                                await self._save_source_to_db(
                                    url=url,
                                    content=text,
                                    metadata=url_metadata.get(url, {}),
                                    thesis_id=thesis_id
                                )
                                
                                # Try to download PDF if URL is a PDF
                                if '.pdf' in url.lower():
                                    try:
                                        await self._download_pdf_to_sources(url, thesis_id, url_metadata.get(url, {}))
                                    except Exception as e:
                                        print(f"   ⚠️ PDF download failed (non-critical): {e}")
                    except Exception as e:
                        print(f"   ⚠️ Scrape failed for {url}: {e}")
            
            # Build Fact Blocks with Metadata
            fact_blocks = []
            for p in pages:
                if len(p["text"]) > 100:
                    meta = url_metadata.get(p["url"], {})
                    
                    # Format citation string
                    citation = f"{meta.get('title', 'Unknown Title')}"
                    if meta.get('author'):
                        citation += f", {meta.get('author')}"
                    if meta.get('date'):
                        citation += f" ({meta.get('date')})"
                    if meta.get('site_name'):
                        citation += f" - {meta.get('site_name')}"
                        
                    fact_blocks.append({
                        "source": p["url"],
                        "citation_meta": citation, # Pre-formatted citation string
                        "raw_meta": meta,          # Raw metadata for LLM
                        "text": p["text"][:2000]
                    })
            
            # Add academic papers
            if "data" in scholar_data:
                for paper in scholar_data["data"]:
                    title = paper.get("title", "Unknown")
                    year = paper.get("year", "n.d.")
                    abstract = paper.get("abstract") or ""
                    if abstract:
                        fact_blocks.append({
                            "source": f"Academic Paper: {title} ({year})",
                            "citation_meta": f"{title} ({year})",
                            "raw_meta": {"title": title, "year": year, "type": "academic"},
                            "text": abstract
                        })

            print(f"   ✓ Generated {len(fact_blocks)} fact blocks")

            return {
                "facts": fact_blocks,
                "academic": scholar_data,
                "raw": {
                    "serper": serper_data,
                    "exa": exa_data,
                    "tavily": tavily_data
                }
            }

    async def _save_source_to_db(self, url: str, content: str, metadata: dict, thesis_id: str = "default"):
        """Save scraped content to Supabase sources table AND to files in sources/ folder."""
        try:
            # Generate hash for deduplication
            source_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Check if already exists
            existing = await db.fetchrow(
                "SELECT id FROM sources WHERE thesis_id = $1 AND source_hash = $2",
                thesis_id, source_hash
            )
            
            if existing:
                print(f"   ℹ️ Source already exists: {metadata.get('title', url[:50])}")
                # Still save to file if it doesn't exist there
                await self._save_source_to_file(url, content, metadata, thesis_id, source_hash)
                return str(existing['id'])
            
            # Determine source type
            source_type = "web"
            if "semanticscholar" in url or "arxiv" in url:
                source_type = "academic_paper"
            elif ".pdf" in url:
                source_type = "pdf"
            elif any(news_domain in url for news_domain in ['reuters.com', 'bbc.com', 'cnn.com', 'nytimes.com']):
                source_type = "news"
            
            # Insert new source to database
            source_id = await db.fetchval(
                """
                INSERT INTO sources (thesis_id, title, url, type, content, metadata, source_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                thesis_id,
                metadata.get('title', 'Unknown Title')[:500],  # Limit title length
                url,
                source_type,
                content[:5000],  # Limit content size to first 5000 chars
                json.dumps(metadata),
                source_hash
            )
            
            # ALSO save to file in sources/ folder
            await self._save_source_to_file(url, content, metadata, thesis_id, source_hash, source_type)
            
            print(f"   ✅ Saved source to DB and file: {metadata.get('title', url[:50])}")
            return str(source_id)
            
        except Exception as e:
            print(f"   ⚠️ Failed to save source to DB {url[:50]}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _save_source_to_file(self, url: str, content: str, metadata: dict, thesis_id: str, source_hash: str, source_type: str = None):
        """Save source to JSON file in sources/ folder."""
        try:
            from pathlib import Path
            from datetime import datetime
            
            # Determine thesis data directory
            thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
            sources_dir = thesis_data_dir / "sources"
            
            # Ensure sources directory exists
            sources_dir.mkdir(parents=True, exist_ok=True)
            
            # Create safe filename
            title = metadata.get('title', 'Unknown Title')
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:50]
            safe_title = safe_title.strip().replace(' ', '_')
            
            # Use hash suffix for uniqueness
            hash_suffix = source_hash[:8]
            filename = f"{safe_title}_{hash_suffix}.json"
            filepath = sources_dir / filename
            
            # Prepare source data
            source_data = {
                "title": title,
                "url": url,
                "type": source_type or metadata.get('type', 'web'),
                "content": content,  # Full content, not truncated
                "abstract": content[:500] if len(content) > 500 else content,  # Preview
                "authors": metadata.get('authors', metadata.get('author', [])),
                "year": metadata.get('year', metadata.get('date', '')),
                "venue": metadata.get('venue', metadata.get('site_name', '')),
                "citationCount": metadata.get('citationCount', 0),
                "saved_at": datetime.now().isoformat(),
                "source_hash": source_hash,
                "metadata": metadata,
                "used_in": []  # Will be updated when content is generated
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(source_data, f, indent=2, ensure_ascii=False)
            
            print(f"   💾 Saved source file: {filename}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to save source to file: {e}")
            import traceback
            traceback.print_exc()
    
    async def _download_pdf_to_sources(self, url: str, thesis_id: str, metadata: dict):
        """Download PDF and save to sources/ folder."""
        try:
            from pathlib import Path
            import httpx
            
            # Determine thesis data directory
            thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
            sources_dir = thesis_data_dir / "sources"
            sources_dir.mkdir(parents=True, exist_ok=True)
            
            # Create safe filename
            title = metadata.get('title', 'Unknown')
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:50]
            safe_title = safe_title.strip().replace(' ', '_')
            pdf_filename = f"{safe_title}.pdf"
            pdf_path = sources_dir / pdf_filename
            
            # Skip if already exists
            if pdf_path.exists():
                print(f"   📄 PDF already exists: {pdf_filename}")
                return pdf_path
            
            # Download PDF
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
                    print(f"   ⚠️ URL may not be a PDF: {url}")
                    return None
                
                # Save PDF
                pdf_path.write_bytes(response.content)
                print(f"   📥 Downloaded PDF: {pdf_filename} ({len(response.content)} bytes)")
                
                return pdf_path
                
        except Exception as e:
            print(f"   ⚠️ Failed to download PDF: {e}")
            return None

unified_research_service = UnifiedResearchService()
