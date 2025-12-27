#!/usr/bin/env python3
"""
PubMed/PubMed Central API Integration

PubMed provides access to:
- 35M+ biomedical citations
- Free full-text via PubMed Central (PMC)
- MeSH term classification
- Clinical trials data
- Completely FREE - No API key required!
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PubMedPaper:
    """PubMed paper data structure."""
    pmid: str
    pmcid: Optional[str]
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    journal: str
    doi: Optional[str]
    pmc_url: Optional[str]
    mesh_terms: List[str]
    publication_types: List[str]


class PubMedAPI:
    """
    PubMed/PMC API client.
    
    With API key: 10 requests/second
    Without API key: 3 requests/second
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: str = "researchwriting32@gmail.com", 
                 tool: str = "AutoGranada",
                 api_key: Optional[str] = "f92ab0c933df1ca9187698ad55f42cb79c08"):
        """
        Initialize PubMed API client.
        
        Args:
            email: Your email (for NCBI tracking)
            tool: Tool name (for NCBI tracking)
            api_key: Optional API key (increases rate limit to 10 req/sec)
        """
        self.email = email
        self.tool = tool
        self.api_key = api_key
        self.rate_limit_delay = 0.1 if api_key else 0.34  # 10/sec with key, 3/sec without
    
    async def search(self, query: str, max_results: int = 10, 
                    filters: Optional[Dict[str, str]] = None) -> List[str]:
        """
        Search PubMed and return PMIDs.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            filters: Optional filters (e.g., {"ffrft": "free full text"})
            
        Returns:
            List of PMIDs
        """
        url = f"{self.BASE_URL}/esearch.fcgi"
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "tool": self.tool,
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        # Add filters
        if filters:
            for key, value in filters.items():
                params[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                pmids = data.get("esearchresult", {}).get("idlist", [])
                logger.info(f"Found {len(pmids)} PubMed results for: {query}")
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                return pmids
                
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []
    
    async def fetch_details(self, pmids: List[str]) -> List[PubMedPaper]:
        """
        Fetch detailed information for PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of PubMedPaper objects
        """
        if not pmids:
            return []
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": self.tool,
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                papers = []
                
                for article in root.findall(".//PubmedArticle"):
                    paper = self._parse_article(article)
                    if paper:
                        papers.append(paper)
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                return papers
                
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return []
    
    def _parse_article(self, article: ET.Element) -> Optional[PubMedPaper]:
        """Parse PubMed article XML."""
        try:
            # PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # Title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                if last_name is not None:
                    name = last_name.text
                    if first_name is not None:
                        name = f"{first_name.text} {name}"
                    authors.append(name)
            
            # Abstract
            abstract_parts = []
            for abstract_text in article.findall(".//AbstractText"):
                label = abstract_text.get("Label", "")
                text = abstract_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)
            
            # Year
            year = None
            pub_date = article.find(".//PubDate/Year")
            if pub_date is not None:
                try:
                    year = int(pub_date.text)
                except:
                    pass
            
            # Journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # DOI
            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            # PMCID (for free full-text)
            pmcid = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "pmc":
                    pmcid = article_id.text
                    break
            
            # PMC URL
            pmc_url = None
            if pmcid:
                pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            
            # MeSH terms
            mesh_terms = []
            for mesh in article.findall(".//MeshHeading/DescriptorName"):
                if mesh.text:
                    mesh_terms.append(mesh.text)
            
            # Publication types
            pub_types = []
            for pub_type in article.findall(".//PublicationType"):
                if pub_type.text:
                    pub_types.append(pub_type.text)
            
            return PubMedPaper(
                pmid=pmid,
                pmcid=pmcid,
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                journal=journal,
                doi=doi,
                pmc_url=pmc_url,
                mesh_terms=mesh_terms,
                publication_types=pub_types
            )
            
        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None
    
    async def search_and_fetch(self, query: str, max_results: int = 10,
                               free_full_text: bool = False) -> List[PubMedPaper]:
        """
        Search and fetch in one call.
        
        Args:
            query: Search query
            max_results: Maximum results
            free_full_text: Only return papers with free full-text
            
        Returns:
            List of PubMedPaper objects
        """
        # Add free full-text filter if requested
        filters = {}
        if free_full_text:
            filters["ffrft"] = "free full text"
        
        # Search
        pmids = await self.search(query, max_results, filters)
        
        if not pmids:
            return []
        
        # Fetch details
        papers = await self.fetch_details(pmids)
        
        return papers


# Integration with existing Paper dataclass
def pubmed_to_paper_dict(pubmed_paper: PubMedPaper) -> Dict[str, Any]:
    """Convert PubMedPaper to standard Paper dictionary."""
    return {
        "title": pubmed_paper.title,
        "authors": pubmed_paper.authors,
        "year": pubmed_paper.year,
        "abstract": pubmed_paper.abstract,
        "url": pubmed_paper.pmc_url or f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_paper.pmid}/",
        "source": "PubMed" + (" (PMC)" if pubmed_paper.pmcid else ""),
        "citations": 0,  # PubMed doesn't provide citation counts directly
        "venue": pubmed_paper.journal,
        "doi": pubmed_paper.doi or "",
        "extra": {
            "pmid": pubmed_paper.pmid,
            "pmcid": pubmed_paper.pmcid,
            "mesh_terms": pubmed_paper.mesh_terms,
            "publication_types": pubmed_paper.publication_types
        }
    }


# Example usage
async def example_search():
    """Example PubMed search."""
    pubmed = PubMedAPI()
    
    # Search for papers
    papers = await pubmed.search_and_fetch(
        "machine learning healthcare",
        max_results=5,
        free_full_text=True  # Only free full-text
    )
    
    print(f"Found {len(papers)} papers:\n")
    for paper in papers:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(paper.authors[:3])}")
        print(f"Year: {paper.year}")
        print(f"PMID: {paper.pmid}")
        if paper.pmcid:
            print(f"PMC: {paper.pmcid} (Free full-text!)")
        if paper.mesh_terms:
            print(f"MeSH: {', '.join(paper.mesh_terms[:3])}")
        print()


if __name__ == "__main__":
    asyncio.run(example_search())
