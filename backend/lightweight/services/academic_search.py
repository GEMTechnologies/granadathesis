"""
Academic Search Service - Multi-API Integration

Supports 8 academic search APIs:
- Semantic Scholar (primary, high-quality metadata)
- CrossRef (DOI registry, citations)
- Exa (neural semantic search)
- OpenAlex (free, comprehensive, ~250M works)
- PubMed/NCBI (biomedical literature)
- CORE (open access papers)
- arXiv (preprints in STEM)
- DBLP (computer science papers)
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional
from core.config import settings


class AcademicSearchService:
    """
    Multi-API academic paper search with fallback and aggregation.
    
    Provides:
    - Unified search across 8+ APIs
    - Citation analysis
    - Open access PDF detection
    - Research trends
    """
    
    def __init__(self):
        self.semantic_scholar_key = settings.SEMANTIC_SCHOLAR_API_KEY
        self.exa_key = settings.EXA_API_KEY
        self.core_key = getattr(settings, 'CORE_API_KEY', None)
        
        # API Base URLs
        self.ss_base_url = "https://api.semanticscholar.org/graph/v1"
        self.exa_base_url = "https://api.exa.ai"
        self.openalex_base_url = "https://api.openalex.org"
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.core_base_url = "https://api.core.ac.uk/v3"
        self.arxiv_base_url = "https://export.arxiv.org/api"
        self.dblp_base_url = "https://dblp.org/search/publ/api"
    
    async def search_academic_papers(
        self,
        query: str,
        max_results: int = 5,
        max_retries: int = 3,
        job_id: Optional[str] = None,
        sources: Optional[List[str]] = None,  # Allow filtering sources
        year_from: Optional[int] = None,  # Minimum publication year
        year_to: Optional[int] = None,  # Maximum publication year
        workspace_id: Optional[str] = None  # Get settings from workspace
    ) -> List[Dict[str, Any]]:
        """
        Search academic papers across multiple APIs with year filtering.
        
        Args:
            query: Search query
            max_results: Maximum results per source
            max_retries: Retry attempts per API
            job_id: For event emission
            sources: List of sources to use (default: all available)
            year_from: Minimum publication year (inclusive)
            year_to: Maximum publication year (inclusive)
            workspace_id: Workspace ID to load settings from
            
        Returns:
            Aggregated list of papers from all sources, filtered by year
        """
        # Load workspace settings if provided
        if workspace_id:
            from services.workspace_service import WorkspaceService
            filters = WorkspaceService.get_search_filters(workspace_id)
            year_from = year_from or filters.get('year_from')
            year_to = year_to or filters.get('year_to')
            sources = sources or filters.get('sources')
            max_results = filters.get('max_results', max_results)
            print(f"   📋 Workspace filters: {year_from}-{year_to}, sources: {sources}")
        
        all_results = []
        active_sources = sources or ['semantic_scholar', 'crossref', 'openalex', 'arxiv']
        
        # Emit search start
        if job_id:
            from core.events import events
            year_info = f" ({year_from}-{year_to})" if year_from or year_to else ""
            await events.log(job_id, f"🔍 Searching {len(active_sources)} databases for: '{query}'{year_info}...")
        
        # Run searches in parallel
        tasks = []
        
        if 'semantic_scholar' in active_sources and self.semantic_scholar_key:
            tasks.append(('Semantic Scholar', self._search_semantic_scholar(query, max_results, max_retries, job_id, year_from, year_to)))
        
        if 'crossref' in active_sources:
            tasks.append(('CrossRef', self.search_crossref(query, max_results, job_id, year_from, year_to)))
        
        if 'openalex' in active_sources:
            tasks.append(('OpenAlex', self.search_openalex(query, max_results, job_id, year_from, year_to)))
        
        if 'arxiv' in active_sources:
            tasks.append(('arXiv', self.search_arxiv(query, max_results, job_id, year_from, year_to)))
        
        if 'pubmed' in active_sources:
            tasks.append(('PubMed', self.search_pubmed(query, max_results, job_id, year_from, year_to)))
        
        if 'core' in active_sources and self.core_key:
            tasks.append(('CORE', self.search_core(query, max_results, job_id, year_from, year_to)))
        
        if 'dblp' in active_sources:
            tasks.append(('DBLP', self.search_dblp(query, max_results, job_id, year_from, year_to)))
        
        # Execute all searches concurrently
        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            
            for (source_name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    print(f"   ✗ {source_name} error: {str(result)[:50]}")
                elif result:
                    print(f"   ✓ {source_name}: {len(result)} results")
                    all_results.extend(result)
        
        # Apply post-filtering by year (as fallback for APIs that don't support year filter)
        if year_from or year_to:
            filtered_results = []
            for paper in all_results:
                year = paper.get('year')
                if year:
                    if year_from and year < year_from:
                        continue
                    if year_to and year > year_to:
                        continue
                filtered_results.append(paper)
            all_results = filtered_results
            print(f"   📅 Year filter ({year_from or 'any'}-{year_to or 'now'}): {len(all_results)} papers")
        
        # Deduplicate by title similarity
        seen_titles = set()
        unique_results = []
        for paper in all_results:
            title = paper.get('title', '').lower().strip()[:50]
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(paper)
        
        print(f"   📊 Total unique papers: {len(unique_results)}")
        
        if job_id:
            await events.log(job_id, f"✓ Found {len(unique_results)} unique papers from {len(tasks)} sources", "success")
        
        return unique_results[:max_results * 2]

    async def _search_semantic_scholar(
        self, query: str, max_results: int, max_retries: int, job_id: Optional[str],
        year_from: Optional[int] = None, year_to: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API."""
        for attempt in range(max_retries):
            try:
                timeout = 30.0 + (attempt * 10)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        f"{self.ss_base_url}/paper/search",
                        params={
                            "query": query,
                            "limit": max_results,
                            "fields": "title,abstract,year,citationCount,authors,venue,url,openAccessPdf,externalIds"
                        },
                        headers={"x-api-key": self.semantic_scholar_key}
                    )
                    response.raise_for_status()
                    data = response.json()
                    papers = data.get("data", [])
                    for p in papers:
                        p['source'] = 'Semantic Scholar'
                    return papers
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"   ✗ Semantic Scholar failed: {str(e)[:50]}")
        return []

    async def search_crossref(
        self, 
        query: str, 
        limit: int = 5, 
        job_id: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search CrossRef API (Free, DOI registry)."""
        try:
            # Build filter with year range if provided
            filters = ["has-abstract:true"]
            if year_from:
                filters.append(f"from-pub-date:{year_from}")
            if year_to:
                filters.append(f"until-pub-date:{year_to}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.crossref.org/works",
                    params={
                        "query": query,
                        "rows": limit,
                        "mailto": "research@thesis.edu",
                        "filter": ",".join(filters)
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("message", {}).get("items", []):
                    authors = []
                    for author in item.get("author", []):
                        if "given" in author and "family" in author:
                            authors.append(f"{author['given']} {author['family']}")
                        elif "family" in author:
                            authors.append(author["family"])
                    
                    abstract = item.get("abstract", "")
                    if not abstract:
                        subtitle = item.get("subtitle", [])
                        abstract = subtitle[0] if subtitle else ""
                    
                    year = None
                    published = item.get("published") or item.get("published-print") or item.get("created")
                    if published and "date-parts" in published:
                        parts = published["date-parts"][0]
                        if parts:
                            year = parts[0]

                    papers.append({
                        "title": item.get("title", [""])[0],
                        "authors": [{"name": a} for a in authors],
                        "year": year,
                        "abstract": abstract,
                        "citationCount": item.get("is-referenced-by-count", 0),
                        "venue": item.get("container-title", [""])[0],
                        "url": item.get("URL", ""),
                        "externalIds": {"DOI": item.get("DOI", "")},
                        "source": "CrossRef"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ CrossRef error: {e}")
            return []

    async def search_openalex(self, query: str, limit: int = 5, job_id: Optional[str] = None, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search OpenAlex API (Free, ~250M works).
        https://docs.openalex.org/
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.openalex_base_url}/works",
                    params={
                        "search": query,
                        "per_page": limit,
                        "mailto": "research@thesis.edu"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("results", []):
                    authors = []
                    for authorship in item.get("authorships", []):
                        author = authorship.get("author", {})
                        if author.get("display_name"):
                            authors.append({"name": author["display_name"]})
                    
                    # Get best open access URL
                    open_access = item.get("open_access", {})
                    pdf_url = open_access.get("oa_url")
                    
                    papers.append({
                        "title": item.get("title", ""),
                        "authors": authors,
                        "year": item.get("publication_year"),
                        "abstract": item.get("abstract", "") or "",
                        "citationCount": item.get("cited_by_count", 0),
                        "venue": item.get("primary_location", {}).get("source", {}).get("display_name", ""),
                        "url": item.get("doi") or item.get("id", ""),
                        "openAccessPdf": {"url": pdf_url} if pdf_url else None,
                        "externalIds": {"DOI": item.get("doi", "").replace("https://doi.org/", "")},
                        "source": "OpenAlex"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ OpenAlex error: {e}")
            return []

    async def search_arxiv(self, query: str, limit: int = 5, job_id: Optional[str] = None, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search arXiv API (Preprints in STEM).
        https://arxiv.org/help/api
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.arxiv_base_url}/query",
                    params={
                        "search_query": f"all:{query}",
                        "start": 0,
                        "max_results": limit,
                        "sortBy": "relevance",
                        "sortOrder": "descending"
                    }
                )
                response.raise_for_status()
                
                # Parse Atom XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                papers = []
                for entry in root.findall('atom:entry', ns):
                    # Extract authors
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name = author.find('atom:name', ns)
                        if name is not None and name.text:
                            authors.append({"name": name.text})
                    
                    # Extract year from published date
                    published = entry.find('atom:published', ns)
                    year = None
                    if published is not None and published.text:
                        year = int(published.text[:4])
                    
                    # Get PDF link
                    pdf_url = None
                    for link in entry.findall('atom:link', ns):
                        if link.get('title') == 'pdf':
                            pdf_url = link.get('href')
                            break
                    
                    title_elem = entry.find('atom:title', ns)
                    summary_elem = entry.find('atom:summary', ns)
                    id_elem = entry.find('atom:id', ns)
                    
                    papers.append({
                        "title": title_elem.text.strip() if title_elem is not None else "",
                        "authors": authors,
                        "year": year,
                        "abstract": summary_elem.text.strip() if summary_elem is not None else "",
                        "citationCount": 0,  # arXiv doesn't provide citation counts
                        "venue": "arXiv",
                        "url": id_elem.text if id_elem is not None else "",
                        "openAccessPdf": {"url": pdf_url} if pdf_url else None,
                        "source": "arXiv"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ arXiv error: {e}")
            return []

    async def search_pubmed(self, query: str, limit: int = 5, job_id: Optional[str] = None, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search PubMed/NCBI (Biomedical literature, ~35M citations).
        https://www.ncbi.nlm.nih.gov/books/NBK25497/
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Search for PMIDs
                search_response = await client.get(
                    f"{self.pubmed_base_url}/esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": limit,
                        "retmode": "json"
                    }
                )
                search_response.raise_for_status()
                search_data = search_response.json()
                pmids = search_data.get("esearchresult", {}).get("idlist", [])
                
                if not pmids:
                    return []
                
                # Step 2: Fetch details for PMIDs
                fetch_response = await client.get(
                    f"{self.pubmed_base_url}/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "json"
                    }
                )
                fetch_response.raise_for_status()
                fetch_data = fetch_response.json()
                
                papers = []
                result = fetch_data.get("result", {})
                for pmid in pmids:
                    item = result.get(pmid, {})
                    if not item or pmid == "uids":
                        continue
                    
                    authors = []
                    for author in item.get("authors", []):
                        authors.append({"name": author.get("name", "")})
                    
                    year = None
                    pubdate = item.get("pubdate", "")
                    if pubdate:
                        try:
                            year = int(pubdate.split()[0])
                        except:
                            pass
                    
                    papers.append({
                        "title": item.get("title", ""),
                        "authors": authors,
                        "year": year,
                        "abstract": "",  # Summary doesn't include abstract
                        "citationCount": 0,
                        "venue": item.get("fulljournalname", ""),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "externalIds": {"PMID": pmid, "DOI": item.get("elocationid", "").replace("doi: ", "")},
                        "source": "PubMed"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ PubMed error: {e}")
            return []

    async def search_core(self, query: str, limit: int = 5, job_id: Optional[str] = None, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search CORE API (Open access papers, ~200M papers).
        https://core.ac.uk/documentation/api
        """
        if not self.core_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.core_base_url}/search/works",
                    params={
                        "q": query,
                        "limit": limit
                    },
                    headers={"Authorization": f"Bearer {self.core_key}"}
                )
                response.raise_for_status()
                data = response.json()
                
                papers = []
                for item in data.get("results", []):
                    authors = [{"name": a} for a in item.get("authors", [])]
                    
                    papers.append({
                        "title": item.get("title", ""),
                        "authors": authors,
                        "year": item.get("yearPublished"),
                        "abstract": item.get("abstract", ""),
                        "citationCount": 0,
                        "venue": item.get("publisher", ""),
                        "url": item.get("downloadUrl") or item.get("sourceFulltextUrls", [""])[0],
                        "openAccessPdf": {"url": item.get("downloadUrl")} if item.get("downloadUrl") else None,
                        "externalIds": {"DOI": item.get("doi", "")},
                        "source": "CORE"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ CORE error: {e}")
            return []

    async def search_dblp(self, query: str, limit: int = 5, job_id: Optional[str] = None, year_from: Optional[int] = None, year_to: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search DBLP (Computer Science papers).
        https://dblp.org/faq/How+to+use+the+dblp+search+API.html
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.dblp_base_url}",
                    params={
                        "q": query,
                        "h": limit,
                        "format": "json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                papers = []
                hits = data.get("result", {}).get("hits", {}).get("hit", [])
                
                for item in hits:
                    info = item.get("info", {})
                    
                    # Handle authors (can be string or list)
                    authors_data = info.get("authors", {}).get("author", [])
                    if isinstance(authors_data, str):
                        authors = [{"name": authors_data}]
                    elif isinstance(authors_data, dict):
                        authors = [{"name": authors_data.get("text", "")}]
                    else:
                        authors = []
                        for a in authors_data:
                            if isinstance(a, dict):
                                authors.append({"name": a.get("text", "")})
                            else:
                                authors.append({"name": str(a)})
                    
                    papers.append({
                        "title": info.get("title", ""),
                        "authors": authors,
                        "year": int(info.get("year", 0)) if info.get("year") else None,
                        "abstract": "",  # DBLP doesn't provide abstracts
                        "citationCount": 0,
                        "venue": info.get("venue", ""),
                        "url": info.get("url", ""),
                        "externalIds": {"DOI": info.get("doi", "")},
                        "source": "DBLP"
                    })
                
                return papers
        except Exception as e:
            print(f"   ✗ DBLP error: {e}")
            return []
    
    async def search_with_exa(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "neural",
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """Neural search using Exa."""
        if not self.exa_key:
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
                            "contents": {"text": True}
                        }
                    )
                    response.raise_for_status()
                    return response.json().get("results", [])
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"   ✗ Exa search failed: {str(e)[:50]}")
        return []
    
    async def get_research_context(self, topic: str, case_study: str) -> Dict[str, Any]:
        """Get comprehensive research context combining all sources."""
        print(f"\n📚 MULTI-API ACADEMIC SEARCH")
        print(f"   Searching for: {case_study} {topic}")
        
        # Search all academic APIs
        papers_query = f"{case_study} {topic}"
        papers = await self.search_academic_papers(papers_query, max_results=5)
        
        # Search with Exa for broader context
        exa_results = await self.search_with_exa(f"{papers_query} research", max_results=5)
        
        context = {
            "academic_papers": [],
            "key_findings": [],
            "sources_used": [],
        }
        
        # Track which sources we got results from
        sources_used = set()
        
        for paper in papers:
            sources_used.add(paper.get("source", "Unknown"))
            context["academic_papers"].append({
                "title": paper.get("title", ""),
                "year": paper.get("year", ""),
                "citations": paper.get("citationCount", 0),
                "abstract": (paper.get("abstract", "") or "")[:200] + "...",
                "source": paper.get("source", "")
            })
            
            abstract = paper.get("abstract", "")
            if abstract:
                context["key_findings"].append(abstract[:150] + "...")
        
        for result in exa_results:
            if result.get("text"):
                context["key_findings"].append(result["text"][:150] + "...")
        
        context["sources_used"] = list(sources_used)
        
        print(f"   ✓ Compiled {len(context['academic_papers'])} papers from {len(sources_used)} sources")
        print(f"   Sources: {', '.join(sources_used)}\n")
        
        return context


# Singleton instance
academic_search_service = AcademicSearchService()

