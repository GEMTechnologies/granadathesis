#!/usr/bin/env python3
"""
Scholarly Search Tool - Multi-API Academic Paper Search & Zotero Integration
"""

import os
import json
import asyncio
import httpx
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # API Keys
    DEEPSEEK_API_KEY = "sk-6f90c6f57da8440e878d8e3d0a70770d"
    
    # Gemini API Keys (backup)
    GEMINI_API_KEYS = [
        "AIzaSyBZidAshUk9cB3DuwY3kP2mPfnC4QXapj8",
        "AIzaSyCabO_o9ne78iKHS7M-rSpWcPlw7uBQuck",
        "AIzaSyANGk8pjA3XvMNU93MHlS6J8nf-bW7GeQM"
    ]
    
    SEMANTIC_SCHOLAR_API_KEY = "DWwu6SniKKaTS8b3TROzG2cu2vayfY4a2DEuuzT0"
    TAVILY_API_KEY = "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"
    CORE_API_KEY = "NrRbADwxfnBEGXZzFh9HoaOvQg4sLjm6"  # CORE API for open access papers
    
    # Unpaywall - FREE! Just needs email
    UNPAYWALL_EMAIL = "autogranada@thesis.edu"  # Required for Unpaywall API
    
    # OpenAlex - FREE! Just needs email (100k calls/day)
    OPENALEX_EMAIL = "autogranada@thesis.edu"  # Required for OpenAlex API
    
    # Zotero Integration
    ZOTERO_API_KEY = "INC1oHci992x3bsa8B8UThxw"
    ZOTERO_USER_ID = "18973079"  # Your Zotero User ID
    ZOTERO_GROUP_ID = None  # Optional - for group libraries

    
    # Model Settings
    PROVIDER = "deepseek"  # Using DeepSeek as primary
    MODEL_NAME = "deepseek-chat"
    
    # Generation Settings
    TARGET_WORD_COUNT_TOTAL = 150000
    
    # Paths
    OUTPUT_DIR = "thesis_data/research"
    
    @staticmethod
    def get_api_key(name):
        return getattr(Config, name, None)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Paper:
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    url: str
    source: str
    citations: int = 0
    venue: str = ""
    doi: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "url": self.url,
            "source": self.source,
            "citations": self.citations,
            "venue": self.venue,
            "doi": self.doi
        }

    def to_ris(self) -> str:
        """Convert to RIS format for Zotero import."""
        ris = ["TY  - JOUR"]
        ris.append(f"TI  - {self.title}")
        for author in self.authors:
            ris.append(f"AU  - {author}")
        if self.year:
            ris.append(f"PY  - {self.year}")
        if self.abstract:
            ris.append(f"AB  - {self.abstract}")
        if self.url:
            ris.append(f"UR  - {self.url}")
        if self.venue:
            ris.append(f"JO  - {self.venue}")
        if self.doi:
            ris.append(f"DO  - {self.doi}")
        ris.append("ER  - \n")
        return "\n".join(ris)

# ============================================================================
# SEARCH SERVICES
# ============================================================================

class ScholarlySearch:
    def __init__(self):
        self.output_dir = Config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Paper]:
        """Search Semantic Scholar API."""
        print(f"   🔍 Searching Semantic Scholar for: '{query}'...")
        if not Config.SEMANTIC_SCHOLAR_API_KEY:
            print("   ⚠️ Semantic Scholar API key missing")
            return []
            
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,year,citationCount,authors,venue,url,externalIds"
        }
        headers = {"x-api-key": Config.SEMANTIC_SCHOLAR_API_KEY}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("data", []):
                    authors = [a.get("name") for a in item.get("authors", [])]
                    external_ids = item.get("externalIds", {})
                    
                    papers.append(Paper(
                        title=item.get("title", ""),
                        authors=authors,
                        year=item.get("year"),
                        abstract=item.get("abstract", "") or "",
                        url=item.get("url", ""),
                        source="Semantic Scholar",
                        citations=item.get("citationCount", 0),
                        venue=item.get("venue", ""),
                        doi=external_ids.get("DOI", "")
                    ))
                print(f"   ✓ Found {len(papers)} papers from Semantic Scholar")
                return papers
        except Exception as e:
            print(f"   ✗ Semantic Scholar error: {e}")
            return []

    async def search_core(self, query: str, limit: int = 5) -> List[Paper]:
        """Search CORE API for open access papers."""
        print(f"   🔍 Searching CORE for: '{query}'...")
        if not Config.CORE_API_KEY:
            print("   ⚠️ CORE API key missing")
            return []
            
        url = "https://api.core.ac.uk/v3/search/works"
        headers = {"Authorization": f"Bearer {Config.CORE_API_KEY}"}
        payload = {
            "q": query,
            "limit": limit
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("results", []):
                    authors = [a.get("name") for a in item.get("authors", [])]
                    
                    papers.append(Paper(
                        title=item.get("title", ""),
                        authors=authors,
                        year=item.get("yearPublished"),
                        abstract=item.get("abstract", "") or "",
                        url=item.get("downloadUrl", "") or item.get("links", [{}])[0].get("url", ""),
                        source="CORE",
                        citations=item.get("citationCount", 0) if item.get("citationCount") else 0,
                        venue=item.get("publisher", ""),
                        doi=item.get("doi", "")
                    ))
                print(f"   ✓ Found {len(papers)} papers from CORE")
                return papers
        except Exception as e:
            print(f"   ✗ CORE error: {e}")
            return []

    async def search_crossref(self, query: str, limit: int = 5) -> List[Paper]:
        """Search CrossRef API for scholarly works (completely FREE, no API key needed!)."""
        print(f"   🔍 Searching CrossRef for: '{query}'...")
        
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": limit,
            "mailto": "autogranada@thesis.edu",  # Polite pool for better service
            "filter": "has-abstract:true"  # Only papers with abstracts
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("message", {}).get("items", []):
                    # Extract authors
                    authors = []
                    for author in item.get("author", []):
                        given = author.get("given", "")
                        family = author.get("family", "")
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                    
                    # Extract year
                    year = None
                    published = item.get("published") or item.get("published-print") or item.get("created")
                    if published and "date-parts" in published:
                        date_parts = published["date-parts"][0]
                        if date_parts:
                            year = date_parts[0]
                    
                    # Extract title
                    title_list = item.get("title", [])
                    title = title_list[0] if title_list else ""
                    
                    # Extract abstract (if available)
                    abstract = item.get("abstract", "")
                    if not abstract:
                        # Use subtitle or short-container-title as fallback
                        subtitle = item.get("subtitle", [])
                        abstract = subtitle[0] if subtitle else ""
                    
                    # Extract venue/journal
                    container_title = item.get("container-title", [])
                    venue = container_title[0] if container_title else ""
                    
                    # Get DOI and URL
                    doi = item.get("DOI", "")
                    url = item.get("URL", "") or (f"https://doi.org/{doi}" if doi else "")
                    
                    # Get citation count
                    citations = item.get("is-referenced-by-count", 0)
                    
                    papers.append(Paper(
                        title=title,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=url,
                        source="CrossRef",
                        citations=citations,
                        venue=venue,
                        doi=doi
                    ))
                
                print(f"   ✓ Found {len(papers)} papers from CrossRef")
                return papers
        except Exception as e:
            print(f"   ✗ CrossRef error: {e}")
            return []

    async def search_unpaywall(self, query: str, limit: int = 5) -> List[Paper]:
        """
        Search Unpaywall API for free, legal, full-text versions of papers.
        
        Note: Unpaywall works best with DOIs. For general queries, we first search
        CrossRef to get DOIs, then check Unpaywall for OA versions.
        """
        print(f"   🔍 Searching Unpaywall for: '{query}'...")
        
        # Strategy: First get DOIs from CrossRef, then check Unpaywall for OA versions
        # This is more efficient than the general search endpoint
        
        try:
            # Step 1: Get DOIs from CrossRef
            crossref_url = "https://api.crossref.org/works"
            crossref_params = {
                "query": query,
                "rows": limit * 2,  # Get more to filter for OA
                "mailto": Config.UNPAYWALL_EMAIL
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                crossref_response = await client.get(crossref_url, params=crossref_params)
                crossref_response.raise_for_status()
                crossref_data = crossref_response.json()
                
                papers = []
                items = crossref_data.get("message", {}).get("items", [])
                
                # Step 2: Check each DOI with Unpaywall
                for item in items[:limit * 2]:  # Check more than we need
                    doi = item.get("DOI")
                    if not doi:
                        continue
                    
                    # Query Unpaywall for this DOI
                    unpaywall_url = f"https://api.unpaywall.org/v2/{doi}"
                    unpaywall_params = {"email": Config.UNPAYWALL_EMAIL}
                    
                    try:
                        unpaywall_response = await client.get(unpaywall_url, params=unpaywall_params)
                        
                        if unpaywall_response.status_code == 404:
                            continue  # DOI not in Unpaywall
                        
                        unpaywall_response.raise_for_status()
                        unpaywall_data = unpaywall_response.json()
                        
                        # Only include if OA is available
                        if not unpaywall_data.get("is_oa", False):
                            continue
                        
                        # Extract best OA location
                        best_oa = unpaywall_data.get("best_oa_location")
                        if not best_oa:
                            continue
                        
                        # Extract metadata
                        authors = []
                        for author in unpaywall_data.get("z_authors", []) or []:
                            name = author.get("raw_author_name", "")
                            if name:
                                authors.append(name)
                        
                        # Get PDF URL (prefer PDF over landing page)
                        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
                        
                        # Get abstract from CrossRef data
                        abstract = item.get("abstract", "")
                        if not abstract:
                            subtitle = item.get("subtitle", [])
                            abstract = subtitle[0] if subtitle else ""
                        
                        # Get venue
                        container_title = item.get("container-title", [])
                        venue = container_title[0] if container_title else unpaywall_data.get("journal_name", "")
                        
                        # Get year
                        year = unpaywall_data.get("year") or unpaywall_data.get("published_date", "")[:4]
                        if year:
                            year = int(year) if str(year).isdigit() else None
                        
                        # Get OA status info
                        oa_status = unpaywall_data.get("oa_status", "unknown")
                        host_type = best_oa.get("host_type", "unknown")
                        version = best_oa.get("version", "unknown")
                        license_info = best_oa.get("license", "")
                        
                        # Create enriched title with OA info
                        title = unpaywall_data.get("title", "")
                        oa_badge = f"[{oa_status.upper()}]" if oa_status != "unknown" else ""
                        
                        papers.append(Paper(
                            title=f"{title} {oa_badge}".strip(),
                            authors=authors,
                            year=year,
                            abstract=abstract or f"Open Access: {oa_status} | Host: {host_type} | Version: {version} | License: {license_info or 'Not specified'}",
                            url=pdf_url or unpaywall_data.get("doi_url", ""),
                            source=f"Unpaywall ({oa_status})",
                            citations=item.get("is-referenced-by-count", 0),
                            venue=venue,
                            doi=doi
                        ))
                        
                        # Stop when we have enough OA papers
                        if len(papers) >= limit:
                            break
                            
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code != 404:
                            print(f"   ⚠️  Unpaywall error for DOI {doi}: {e}")
                        continue
                    except Exception as e:
                        print(f"   ⚠️  Error checking DOI {doi}: {e}")
                        continue
                
                print(f"   ✓ Found {len(papers)} OA papers from Unpaywall")
                return papers
                
        except Exception as e:
            print(f"   ✗ Unpaywall error: {e}")
            return []

    async def search_openalex(self, query: str, limit: int = 5) -> List[Paper]:
        """
        Search OpenAlex API - fully open catalog of global research.
        
        OpenAlex is the successor to Unpaywall and provides 2x coverage
        of paywalled services like Scopus and Web of Science.
        """
        print(f"   🔍 Searching OpenAlex for: '{query}'...")
        
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": limit,
            "mailto": Config.OPENALEX_EMAIL,  # Polite pool for better performance
            "filter": "is_oa:true"  # Only open access papers
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("results", []):
                    # Extract authors
                    authors = []
                    for authorship in item.get("authorships", []):
                        author = authorship.get("author", {})
                        display_name = author.get("display_name")
                        if display_name:
                            authors.append(display_name)
                    
                    # Extract year
                    year = item.get("publication_year")
                    
                    # Extract title
                    title = item.get("title", "")
                    
                    # Extract abstract (inverted index format)
                    abstract = ""
                    abstract_inverted = item.get("abstract_inverted_index")
                    if abstract_inverted:
                        # Reconstruct abstract from inverted index
                        words = {}
                        for word, positions in abstract_inverted.items():
                            for pos in positions:
                                words[pos] = word
                        abstract = " ".join([words[i] for i in sorted(words.keys())])
                    
                    # Get OA information
                    oa_info = item.get("open_access", {})
                    is_oa = oa_info.get("is_oa", False)
                    oa_status = oa_info.get("oa_status", "closed")
                    oa_url = oa_info.get("oa_url", "")
                    
                    # Get DOI
                    doi = item.get("doi", "")
                    if doi and doi.startswith("https://doi.org/"):
                        doi = doi.replace("https://doi.org/", "")
                    
                    # Get primary location (journal/venue)
                    primary_location = item.get("primary_location", {})
                    source = primary_location.get("source", {})
                    venue = source.get("display_name", "")
                    
                    # Get URL (prefer OA URL, fallback to DOI)
                    url = oa_url or item.get("doi", "")
                    
                    # Get citation count
                    citations = item.get("cited_by_count", 0)
                    
                    # Get topics (OpenAlex's new feature!)
                    topics = item.get("topics", [])
                    topic_names = [t.get("display_name", "") for t in topics[:3]]  # Top 3 topics
                    
                    # Get institutions
                    institutions = []
                    for authorship in item.get("authorships", [])[:3]:  # First 3 authors
                        for inst in authorship.get("institutions", []):
                            inst_name = inst.get("display_name")
                            if inst_name and inst_name not in institutions:
                                institutions.append(inst_name)
                    
                    # Create enriched title with OA badge and topics
                    oa_badge = f"[{oa_status.upper()}]" if is_oa else ""
                    topic_badge = f"({', '.join(topic_names[:2])})" if topic_names else ""
                    enriched_title = f"{title} {oa_badge}".strip()
                    
                    # Create enriched abstract with topics and institutions
                    if not abstract and topic_names:
                        abstract = f"Topics: {', '.join(topic_names)}"
                    if institutions:
                        abstract += f"\n\nInstitutions: {', '.join(institutions[:3])}"
                    
                    papers.append(Paper(
                        title=enriched_title,
                        authors=authors,
                        year=year,
                        abstract=abstract or "No abstract available",
                        url=url,
                        source=f"OpenAlex ({oa_status})",
                        citations=citations,
                        venue=venue,
                        doi=doi
                    ))
                
                print(f"   ✓ Found {len(papers)} OA papers from OpenAlex")
                return papers
                
        except Exception as e:
            print(f"   ✗ OpenAlex error: {e}")
            return []

    async def search_tavily(self, query: str, limit: int = 5) -> List[Paper]:
        """Search Tavily for general academic context."""
        print(f"   🔍 Searching Tavily for: '{query}'...")
        if not Config.TAVILY_API_KEY:
            print("   ⚠️ Tavily API key missing")
            return []
            
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": Config.TAVILY_API_KEY,
            "query": f"academic paper {query}",
            "search_depth": "advanced",
            "include_domains": ["scholar.google.com", "researchgate.net", "academia.edu", "arxiv.org"],
            "max_results": limit
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("results", []):
                    papers.append(Paper(
                        title=item.get("title", ""),
                        authors=[],  # Tavily often doesn't parse authors cleanly
                        year=None,
                        abstract=item.get("content", "")[:500] + "...",
                        url=item.get("url", ""),
                        source="Tavily",
                        citations=0,
                        venue="",
                        doi=""
                    ))
                print(f"   ✓ Found {len(papers)} results from Tavily")
                return papers
        except Exception as e:
            print(f"   ✗ Tavily error: {e}")
            return []

    async def run_search(self, query: str, limit_per_source: int = 5) -> List[Paper]:
        """Run search across all providers."""
        print(f"\n🚀 STARTING ACADEMIC SEARCH: '{query}'\n")
        
        tasks = [
            self.search_semantic_scholar(query, limit_per_source),
            self.search_core(query, limit_per_source),
            self.search_crossref(query, limit_per_source),
            self.search_unpaywall(query, limit_per_source),
            self.search_openalex(query, limit_per_source),
            self.search_tavily(query, limit_per_source)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_papers = []
        for source_results in results:
            all_papers.extend(source_results)
            
        # Deduplicate by title (simple fuzzy match could be better but keeping it light)
        seen_titles = set()
        unique_papers = []
        for paper in all_papers:
            # Normalize title for comparison
            normalized_title = "".join(c.lower() for c in paper.title if c.isalnum())
            if normalized_title and normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_papers.append(paper)
        
        print(f"\n✅ SEARCH COMPLETE")
        print(f"   Total unique papers found: {len(unique_papers)}")
        return unique_papers

    def save_results(self, papers: List[Paper], query: str):
        """Save results to JSON and RIS formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
        
        # Save JSON
        json_file = os.path.join(self.output_dir, f"search_{safe_query}_{timestamp}.json")
        with open(json_file, "w") as f:
            json.dump([p.to_dict() for p in papers], f, indent=2)
            
        # Save RIS (Zotero import)
        ris_file = os.path.join(self.output_dir, f"search_{safe_query}_{timestamp}.ris")
        with open(ris_file, "w") as f:
            for paper in papers:
                f.write(paper.to_ris())
                
        print(f"\n💾 RESULTS SAVED")
        print(f"   JSON: {json_file}")
        print(f"   RIS (Zotero): {ris_file}")
        print(f"   \n👉 To import into Zotero: File > Import > Select the .ris file")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Scholarly Search Tool")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Limit results per source")
    args = parser.parse_args()
    
    query = args.query
    if not query:
        print("\n🎓 SCHOLARLY SEARCH TOOL")
        print("========================")
        query = input("Enter search query: ").strip()
        
    if not query:
        print("❌ Query required")
        return

    searcher = ScholarlySearch()
    papers = await searcher.run_search(query, args.limit)
    
    if papers:
        searcher.save_results(papers, query)
        
        print("\n📋 TOP RESULTS:")
        for i, paper in enumerate(papers[:5], 1):
            print(f"\n{i}. {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:3])}")
            print(f"   Year: {paper.year or 'N/A'} | Source: {paper.source}")
            print(f"   URL: {paper.url}")

if __name__ == "__main__":
    asyncio.run(main())
