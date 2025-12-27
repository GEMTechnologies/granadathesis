#!/usr/bin/env python3
"""
Thesis System Integration - Auto-find Relevant Papers

Integrate scholarly search with thesis objective generation:
- Auto-find papers for objectives
- Suggest citations for literature review
- Provide context for research gaps
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from scholarly_search_v2 which has SearchFilters
try:
    from scholarly_search_v2 import ScholarlySearch, SearchFilters
except ImportError:
    # Fallback to basic scholarly_search
    from scholarly_search import ScholarlySearch
    SearchFilters = None

from app.services.cache_service import get_cache
try:
    from app.services.fulltext_search import get_search_index
except ImportError:
    get_search_index = None



class ThesisResearchAssistant:
    """Integrate paper search with thesis generation."""
    
    def __init__(self):
        """Initialize research assistant."""
        self.searcher = ScholarlySearch()
        self.cache = get_cache()
        try:
            self.search_index = get_search_index()
        except:
            self.search_index = None
    
    async def find_papers_for_objective(self, objective: str, 
                                       limit: int = 10,
                                       year_min: int = 2018) -> Dict[str, Any]:
        """
        Find relevant papers for a thesis objective.
        
        Args:
            objective: Thesis objective text
            limit: Number of papers per source
            year_min: Minimum publication year
            
        Returns:
            Dictionary with papers and analysis
        """
        # Extract key terms from objective
        key_terms = self._extract_key_terms(objective)
        
        # Build search query
        query = " ".join(key_terms[:5])  # Use top 5 terms
        
        # Set filters for recent, high-quality papers
        filters = None
        if SearchFilters:
            filters = SearchFilters(
                year_min=year_min,
                citations_min=5,  # At least 5 citations
                oa_only=True  # Prefer open access
            )

        
        # Search
        papers = await self.searcher.run_search(query, limit, filters)
        
        # Analyze results
        analysis = {
            "objective": objective,
            "search_query": query,
            "key_terms": key_terms,
            "total_papers": len(papers),
            "papers": [p.to_dict() for p in papers],
            "recommendations": self._generate_recommendations(papers, objective)
        }
        
        return analysis
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from objective text."""
        # Simple keyword extraction (can be improved with NLP)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Tokenize and filter
        words = text.lower().split()
        keywords = [w.strip('.,!?;:()[]{}') for w in words 
                   if w.lower() not in stopwords and len(w) > 3]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    def _generate_recommendations(self, papers: List[Any], 
                                 objective: str) -> Dict[str, Any]:
        """Generate recommendations based on found papers."""
        if not papers:
            return {
                "status": "no_papers_found",
                "suggestion": "Try broadening search terms or reducing filters"
            }
        
        # Sort by citations
        sorted_papers = sorted(papers, key=lambda p: p.citations, reverse=True)
        
        recommendations = {
            "highly_cited": [
                {
                    "title": p.title,
                    "citations": p.citations,
                    "year": p.year,
                    "url": p.url
                }
                for p in sorted_papers[:3]
            ],
            "recent_papers": [
                {
                    "title": p.title,
                    "year": p.year,
                    "url": p.url
                }
                for p in sorted(papers, key=lambda p: p.year or 0, reverse=True)[:3]
            ],
            "open_access": [
                {
                    "title": p.title,
                    "source": p.source,
                    "url": p.url
                }
                for p in papers if "unpaywall" in p.source.lower() or "openalex" in p.source.lower()
            ][:3]
        }
        
        return recommendations
    
    async def generate_literature_review_outline(self, 
                                                topic: str,
                                                num_papers: int = 20) -> Dict[str, Any]:
        """
        Generate literature review outline with papers.
        
        Args:
            topic: Research topic
            num_papers: Number of papers to find
            
        Returns:
            Structured outline with papers
        """
        # Search for papers
        papers = await self.searcher.run_search(topic, limit_per_source=num_papers // 6)
        
        if not papers:
            return {"error": "No papers found"}
        
        # Group by year
        by_year = {}
        for paper in papers:
            year = paper.year or "Unknown"
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(paper)
        
        # Create outline
        outline = {
            "topic": topic,
            "total_papers": len(papers),
            "sections": {
                "foundational_works": {
                    "description": "Seminal papers and early research",
                    "papers": sorted(papers, key=lambda p: p.citations, reverse=True)[:5]
                },
                "recent_advances": {
                    "description": "Latest developments (last 3 years)",
                    "papers": [p for p in papers if p.year and p.year >= 2022][:5]
                },
                "methodologies": {
                    "description": "Key methodological approaches",
                    "papers": [p for p in papers if any(term in p.title.lower() 
                              for term in ['method', 'approach', 'framework', 'model'])][:5]
                },
                "applications": {
                    "description": "Practical applications and case studies",
                    "papers": [p for p in papers if any(term in p.title.lower()
                              for term in ['application', 'case study', 'implementation'])][:5]
                }
            },
            "timeline": {str(year): len(papers_list) 
                        for year, papers_list in sorted(by_year.items())}
        }
        
        return outline
    
    async def suggest_research_gap(self, topic: str) -> Dict[str, Any]:
        """
        Analyze papers to suggest research gaps.
        
        Args:
            topic: Research topic
            
        Returns:
            Analysis of potential research gaps
        """
        # Search for papers
        papers = await self.searcher.run_search(topic, limit_per_source=10)
        
        if not papers:
            return {"error": "No papers found"}
        
        # Analyze coverage
        all_keywords = []
        for paper in papers:
            title_keywords = self._extract_key_terms(paper.title)
            abstract_keywords = self._extract_key_terms(paper.abstract)
            all_keywords.extend(title_keywords + abstract_keywords)
        
        # Find common themes
        from collections import Counter
        keyword_freq = Counter(all_keywords)
        common_themes = [kw for kw, count in keyword_freq.most_common(10)]
        
        # Identify potential gaps (keywords in topic but not in papers)
        topic_keywords = self._extract_key_terms(topic)
        potential_gaps = [kw for kw in topic_keywords if kw not in common_themes]
        
        analysis = {
            "topic": topic,
            "papers_analyzed": len(papers),
            "common_themes": common_themes,
            "potential_gaps": potential_gaps,
            "suggestions": [
                f"Limited research on: {gap}" for gap in potential_gaps[:3]
            ],
            "year_range": {
                "oldest": min(p.year for p in papers if p.year),
                "newest": max(p.year for p in papers if p.year)
            }
        }
        
        return analysis


# Example usage
async def example_usage():
    """Example of thesis integration."""
    assistant = ThesisResearchAssistant()
    
    # Example objective
    objective = "Develop a machine learning framework for predicting student performance in online learning environments"
    
    print("Finding papers for objective...")
    result = await assistant.find_papers_for_objective(objective, limit=5)
    
    print(f"\nFound {result['total_papers']} papers")
    print(f"Search query: {result['search_query']}")
    print(f"\nTop 3 highly cited papers:")
    for paper in result['recommendations']['highly_cited']:
        print(f"  - {paper['title']} ({paper['citations']} citations)")


if __name__ == "__main__":
    asyncio.run(example_usage())
