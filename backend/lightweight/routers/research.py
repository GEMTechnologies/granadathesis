from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import asyncio
from core.config import settings

router = APIRouter()

# Use settings or fallback to os.getenv
SERPER_API_KEY = settings.SERPER_API_KEY or os.getenv("SERPER_API_KEY")
TAVILY_API_KEY = settings.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
EXA_API_KEY = settings.EXA_API_KEY or os.getenv("EXA_API_KEY")
FIRECRAWL_API_KEY = settings.FIRECRAWL_API_KEY or os.getenv("FIRECRAWL_API_KEY")
SEMANTIC_SCHOLAR_API_KEY = settings.SEMANTIC_SCHOLAR_API_KEY or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
FIRECRAWL_URL = settings.FIRECRAWL_URL or os.getenv("FIRECRAWL_URL", "https://api.firecrawl.dev")

class ResearchRequest(BaseModel):
    topic: str
    caseStudy: str


@router.post("/collect")
async def collect_research(req: ResearchRequest):
    query = f"{req.topic} {req.caseStudy} economic impact analysis"
    print(f"\n🌐 UNIFIED RESEARCH: {query}")

    async with httpx.AsyncClient(timeout=30) as client:

        # --- GOOGLE SEARCH (Serper) ---
        async def search_serper():
            if not SERPER_API_KEY: return {}
            try:
                print("   🔍 Querying Serper...")
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": query}
                )
                return resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                print(f"   ⚠️ Serper failed: {e}")
                return {}

        # --- TAVILY AGGREGATED RESEARCH ---
        async def search_tavily():
            if not TAVILY_API_KEY: return {}
            try:
                print("   🔍 Querying Tavily...")
                resp = await client.post(
                    "https://api.tavily.com/search",
                    headers={"Content-Type": "application/json"},
                    json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "max_results": 5}
                )
                return resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                print(f"   ⚠️ Tavily failed: {e}")
                return {}

        # --- EXA SEMANTIC SEARCH ---
        async def search_exa():
            if not EXA_API_KEY: return {}
            try:
                print("   🔍 Querying Exa...")
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
                    json={"query": query, "type": "keyword", "numResults": 5}
                )
                return resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                print(f"   ⚠️ Exa failed: {e}")
                return {}

        # --- SEMANTIC SCHOLAR (ACADEMIC) ---
        async def search_scholar():
            if not SEMANTIC_SCHOLAR_API_KEY: return {}
            try:
                print("   🔍 Querying Semantic Scholar...")
                resp = await client.get(
                    f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5&fields=title,year,abstract,url",
                    headers={"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
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

        # Collect all URLs
        urls = []

        # SERPER
        if "organic" in serper_data:
            urls += [item["link"] for item in serper_data["organic"] if "link" in item]

        # TAVILY
        if "results" in tavily_data:
            urls += [item["url"] for item in tavily_data["results"] if "url" in item]

        # EXA
        if "results" in exa_data:
            urls += [item["url"] for item in exa_data["results"] if "url" in item]

        # DEDUP
        urls = list(set(urls))
        print(f"   ✓ Found {len(urls)} unique URLs to scrape")

        # === FULL PAGE SCRAPE USING FIRECRAWL ===
        pages = []
        if FIRECRAWL_API_KEY:
            print(f"   🕷️ Scraping top 5 URLs with Firecrawl...")
            for url in urls[:5]:  # limit to first 5 to save time/credits
                try:
                    r = await client.post(
                        f"{FIRECRAWL_URL}/v1/scrape",
                        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"},
                        json={"url": url, "formats": ["markdown"]}
                    )
                    if r.status_code == 200:
                        data = r.json()
                        text = data.get("data", {}).get("markdown", "")
                        if text:
                            pages.append({"url": url, "text": text})
                except Exception as e:
                    print(f"   ⚠️ Scrape failed for {url}: {e}")
        else:
            print("   ⚠️ Firecrawl API key missing, skipping scrape.")

        # === BUILD FACT BLOCKS ===
        fact_blocks = []
        for p in pages:
            if len(p["text"]) > 100:
                fact_blocks.append(
                    {
                        "source": p["url"],
                        "text": p["text"][:2000]  # crop safely
                    }
                )
        
        # Add academic papers as fact blocks too
        if "data" in scholar_data:
            for paper in scholar_data["data"]:
                title = paper.get("title", "Unknown")
                year = paper.get("year", "n.d.")
                abstract = paper.get("abstract") or ""
                if abstract:
                    fact_blocks.append({
                        "source": f"Academic Paper: {title} ({year})",
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
