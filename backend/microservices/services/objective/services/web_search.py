"""
Web Search Service - Context Research for Objective Generation

Uses Tavily API to research context before generating objectives.
Extracts key periods, context-specific factors, and relevant variables.
"""

import httpx
from typing import Dict, List, Any
from app.core.config import settings


class WebSearchService:
    """
    Research context before objective generation using web search.
    
    Provides:
    - Key historical periods
    - Context-specific factors
    - Relevant variables
    - Data sources
    """
    
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
        
        if not self.api_key:
            print("⚠️  WARNING: TAVILY_API_KEY not configured. Context research will be limited.")
    
    async def research_topic_context(
        self,
        topic: str,
        case_study: str
    ) -> Dict[str, Any]:
        """
        Research context for a topic and case study.
        
        Args:
            topic: Research topic (e.g., "impact of wars on economic development")
            case_study: Case study context (e.g., "Nuba Mountains, Sudan")
            
        Returns:
            Context brief with key periods, factors, variables, and sources
        """
        print(f"\n🔍 CONTEXT RESEARCH")
        print(f"   Topic: {topic}")
        print(f"   Case Study: {case_study}")
        
        if not self.api_key:
            return self._fallback_context(topic, case_study)
        
        # Define search queries
        queries = [
            f"{case_study} {topic} recent developments timeline",
            f"{case_study} historical context key periods",
            f"{case_study} unique challenges factors",
            f"{case_study} research data sources"
        ]
        
        # Perform searches
        search_results = []
        for i, query in enumerate(queries):
            try:
                result = await self._search(query)
                search_results.append(result)
                print(f"   ✓ Searched: {query[:50]}...")
            except Exception as e:
                error_msg = str(e)
                print(f"   ✗ Search failed: {error_msg[:50]}...")
                
                # Fail fast on network/DNS errors
                if "name resolution" in error_msg or "ConnectError" in error_msg or "timeout" in error_msg.lower():
                    if i == 0: # If first query fails, assume network is down
                        print("   ⚠️  Network error detected. Skipping remaining searches.")
                        return self._fallback_context(topic, case_study)
        
        # Extract structured information
        context = self._extract_context(search_results, topic, case_study)
        
        print(f"   ✓ Found {len(context['key_periods'])} key periods")
        print(f"   ✓ Found {len(context['context_factors'])} context-specific factors")
        print(f"   ✓ Found {len(context['relevant_variables'])} relevant variables\n")
        
        return context
    
    async def _search(self, query: str) -> Dict[str, Any]:
        """Perform a single search query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5
                }
            )
            response.raise_for_status()
            return response.json()
    
    def _extract_context(
        self,
        search_results: List[Dict],
        topic: str,
        case_study: str
    ) -> Dict[str, Any]:
        """
        Extract structured context from search results.
        
        This is a simplified extraction. In production, you'd use
        an LLM to analyze search results and extract key information.
        """
        # Combine all search content
        all_content = []
        for result in search_results:
            if "results" in result:
                for item in result["results"]:
                    all_content.append(item.get("content", ""))
        
        combined_text = " ".join(all_content)
        
        # For now, return a structured template
        # In production, use LLM to extract from combined_text
        return {
            "key_periods": self._extract_periods(combined_text, case_study),
            "context_factors": self._extract_factors(combined_text, case_study),
            "relevant_variables": self._extract_variables(combined_text, topic),
            "data_sources": self._extract_sources(combined_text),
            "raw_content": combined_text[:500]  # First 500 chars for reference
        }
    
    def _extract_periods(self, text: str, case_study: str) -> List[str]:
        """Extract key historical periods from text."""
        # Simplified extraction - look for year patterns
        # In production, use LLM for better extraction
        periods = []
        
        # Common conflict period patterns
        if "2011" in text or "independence" in text.lower():
            periods.append("2011-present: Post-independence period")
        if "2002" in text or "CPA" in text or "peace" in text.lower():
            periods.append("2002-2011: CPA period")
        if "1983" in text or "civil war" in text.lower():
            periods.append("1983-2005: Second Sudanese Civil War")
        
        return periods if periods else ["Recent period (last 10-15 years)"]
    
    def _extract_factors(self, text: str, case_study: str) -> List[str]:
        """Extract context-specific factors."""
        factors = []
        
        # Look for conflict-related terms
        keywords = {
            "blockade": "Road blockades and isolation",
            "aerial": "Aerial bombardment",
            "displacement": "Forced displacement",
            "humanitarian": "Humanitarian access restrictions",
            "embargo": "Economic embargo",
            "isolation": "Geographic isolation"
        }
        
        text_lower = text.lower()
        for keyword, factor in keywords.items():
            if keyword in text_lower:
                factors.append(factor)
        
        return factors if factors else ["Conflict-related disruptions", "Economic instability"]
    
    def _extract_variables(self, text: str, topic: str) -> List[str]:
        """Extract relevant variables based on topic."""
        variables = []
        
        # Economic development variables
        if "economic" in topic.lower() or "development" in topic.lower():
            variables.extend([
                "Agricultural productivity (crop yields, livestock)",
                "Market prices and trade volumes",
                "Infrastructure availability",
                "Household income levels",
                "Employment rates"
            ])
        
        return variables if variables else ["Key outcome variables"]
    
    def _extract_sources(self, text: str) -> List[str]:
        """Extract potential data sources."""
        sources = []
        
        # Common humanitarian/research organizations
        orgs = ["OCHA", "WFP", "UNHCR", "FAO", "World Bank", "UNICEF", "WHO"]
        
        text_upper = text.upper()
        for org in orgs:
            if org in text_upper:
                sources.append(org)
        
        return sources if sources else ["Local surveys", "Government statistics", "NGO reports"]
    
    def _fallback_context(self, topic: str, case_study: str) -> Dict[str, Any]:
        """Fallback context when API is not available."""
        print("   ⚠️  Using fallback context (no API key)")
        
        return {
            "key_periods": ["Recent period (last 10-15 years)"],
            "context_factors": ["Conflict-related disruptions", "Economic instability"],
            "relevant_variables": [
                "Agricultural productivity",
                "Market functioning",
                "Infrastructure availability",
                "Household livelihoods"
            ],
            "data_sources": ["Local surveys", "Government statistics", "NGO reports"],
            "raw_content": "Fallback context - API key not configured"
        }


# Singleton instance
web_search_service = WebSearchService()
