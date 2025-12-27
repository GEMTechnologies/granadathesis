"""
Search Microagents - Specialized agents for academic search tasks

15 focused microagents following MAKER's extreme decomposition principle:
- Query Processing (3): Decompose, Refine, Select Sources
- Result Processing (7): Extract, Validate, Score, Deduplicate, Citations, Summarize, Enrich
- Synthesis (5): Aggregate, Insights, Gaps, Trends, Recommendations
"""

import json
import re
from typing import Any, Dict, List, Optional
from app.services.maker_framework import MicroAgent, AgentResponse


class SearchMicroAgent(MicroAgent):
    """Base class for search microagents with LLM call implementation."""
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM using the provided client."""
        return await self.llm_client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )


class QueryDecomposerAgent(SearchMicroAgent):
    """Breaks complex queries into focused sub-queries."""
    
    def get_system_prompt(self) -> str:
        return """You are a query decomposition specialist. Your ONLY job is to break a complex research query into 2-4 focused sub-queries.

Rules:
- Each sub-query must be specific and searchable
- Sub-queries should cover different aspects of the topic
- Keep each sub-query under 10 words
- Return ONLY valid JSON

Output format:
{"sub_queries": ["query1", "query2", "query3"]}"""
    
    def get_user_prompt(self, query: str, **kwargs) -> str:
        return f"""Decompose this research query into sub-queries:

Query: {query}

Return JSON with sub_queries list."""
    
    def parse_response(self, raw_response: str) -> Any:
        # Extract JSON from response
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"sub_queries": []}


class QueryRefinerAgent(SearchMicroAgent):
    """Improves query quality and specificity."""
    
    def get_system_prompt(self) -> str:
        return """You are a query refinement specialist. Your ONLY job is to improve a research query for academic search.

Rules:
- Add relevant academic keywords
- Make it more specific and searchable
- Keep it concise (under 15 words)
- Return ONLY valid JSON

Output format:
{"refined_query": "improved query here"}"""
    
    def get_user_prompt(self, query: str, context: Optional[str] = None, **kwargs) -> str:
        prompt = f"""Refine this research query for academic search:

Original: {query}"""
        
        if context:
            prompt += f"\nContext: {context}"
        
        prompt += "\n\nReturn JSON with refined_query."
        return prompt
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"refined_query": ""}


class SourceSelectorAgent(SearchMicroAgent):
    """Chooses optimal APIs to query."""
    
    def get_system_prompt(self) -> str:
        return """You are a source selection specialist. Your ONLY job is to choose which academic APIs to query.

Available sources:
- semantic_scholar: General academic papers, citations
- pubmed: Medical/biomedical research
- exa: Neural semantic search, broader context

Rules:
- Select 1-3 sources based on query topic
- Return ONLY valid JSON

Output format:
{"sources": ["semantic_scholar", "pubmed"]}"""
    
    def get_user_prompt(self, query: str, **kwargs) -> str:
        return f"""Select the best sources for this query:

Query: {query}

Return JSON with sources list."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"sources": ["semantic_scholar"]}


class ResultExtractorAgent(SearchMicroAgent):
    """Parses API responses into structured format."""
    
    def get_system_prompt(self) -> str:
        return """You are a result extraction specialist. Your ONLY job is to extract key fields from API responses.

Extract:
- title
- authors
- year
- abstract
- citations

Rules:
- Extract exactly what's present, no hallucination
- Return ONLY valid JSON
- If field missing, use empty string/0

Output format:
{"title": "...", "authors": ["..."], "year": 2024, "abstract": "...", "citations": 0}"""
    
    def get_user_prompt(self, api_response: Dict[str, Any], **kwargs) -> str:
        return f"""Extract structured data from this API response:

{json.dumps(api_response, indent=2)[:500]}

Return JSON with title, authors, year, abstract, citations."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"title": "", "authors": [], "year": 0, "abstract": "", "citations": 0}


class ResultValidatorAgent(SearchMicroAgent):
    """Checks result completeness and quality."""
    
    def get_system_prompt(self) -> str:
        return """You are a result validation specialist. Your ONLY job is to check if a paper result is complete and valid.

Check:
- Has title
- Has at least one author
- Has year (reasonable range)
- Has abstract (at least 50 chars)

Rules:
- Return ONLY valid JSON
- is_valid: true/false
- missing_fields: list of what's missing

Output format:
{"is_valid": true, "missing_fields": [], "quality_score": 0.9}"""
    
    def get_user_prompt(self, paper: Dict[str, Any], **kwargs) -> str:
        return f"""Validate this paper result:

{json.dumps(paper, indent=2)}

Return JSON with is_valid, missing_fields, quality_score (0-1)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"is_valid": False, "missing_fields": ["unknown"], "quality_score": 0.0}


class RelevanceScorerAgent(SearchMicroAgent):
    """Ranks results by relevance to query."""
    
    def get_system_prompt(self) -> str:
        return """You are a relevance scoring specialist. Your ONLY job is to score how relevant a paper is to a query.

Consider:
- Title match to query
- Abstract relevance
- Recency (newer = better)
- Citation count (higher = more influential)

Rules:
- Score from 0.0 to 1.0
- Return ONLY valid JSON

Output format:
{"relevance_score": 0.85, "reasoning": "brief explanation"}"""
    
    def get_user_prompt(self, query: str, paper: Dict[str, Any], **kwargs) -> str:
        return f"""Score relevance of this paper to the query:

Query: {query}

Paper:
Title: {paper.get('title', '')}
Abstract: {paper.get('abstract', '')[:200]}...
Year: {paper.get('year', 0)}
Citations: {paper.get('citations', 0)}

Return JSON with relevance_score (0-1) and brief reasoning."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"relevance_score": 0.5, "reasoning": ""}


class DeduplicationAgent(SearchMicroAgent):
    """Identifies duplicate papers."""
    
    def get_system_prompt(self) -> str:
        return """You are a deduplication specialist. Your ONLY job is to determine if two papers are duplicates.

Consider:
- Title similarity (exact or very close)
- Same authors
- Same year
- Same venue

Rules:
- Return ONLY valid JSON
- is_duplicate: true if same paper

Output format:
{"is_duplicate": false, "confidence": 0.95}"""
    
    def get_user_prompt(self, paper1: Dict[str, Any], paper2: Dict[str, Any], **kwargs) -> str:
        return f"""Are these two papers duplicates?

Paper 1:
Title: {paper1.get('title', '')}
Authors: {', '.join(paper1.get('authors', [])[:3])}
Year: {paper1.get('year', 0)}

Paper 2:
Title: {paper2.get('title', '')}
Authors: {', '.join(paper2.get('authors', [])[:3])}
Year: {paper2.get('year', 0)}

Return JSON with is_duplicate (boolean) and confidence (0-1)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"is_duplicate": False, "confidence": 0.5}


class CitationExtractorAgent(SearchMicroAgent):
    """Extracts citation metadata."""
    
    def get_system_prompt(self) -> str:
        return """You are a citation extraction specialist. Your ONLY job is to extract citation information.

Extract:
- citation_count: number of citations
- influential_citations: highly cited papers citing this
- citation_velocity: recent citation trend

Rules:
- Return ONLY valid JSON
- Use 0 if data missing

Output format:
{"citation_count": 42, "influential_citations": 5, "citation_velocity": "increasing"}"""
    
    def get_user_prompt(self, paper: Dict[str, Any], **kwargs) -> str:
        return f"""Extract citation metadata:

Paper: {paper.get('title', '')}
Citations: {paper.get('citations', 0)}
Year: {paper.get('year', 0)}

Return JSON with citation_count, influential_citations, citation_velocity."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"citation_count": 0, "influential_citations": 0, "citation_velocity": "stable"}


class AbstractSummarizerAgent(SearchMicroAgent):
    """Summarizes paper abstracts."""
    
    def get_system_prompt(self) -> str:
        return """You are an abstract summarization specialist. Your ONLY job is to create a 1-sentence summary of a paper abstract.

Rules:
- One sentence, under 30 words
- Focus on main contribution
- Return ONLY valid JSON

Output format:
{"summary": "One sentence summary here"}"""
    
    def get_user_prompt(self, abstract: str, **kwargs) -> str:
        return f"""Summarize this abstract in one sentence:

{abstract[:500]}

Return JSON with summary (one sentence, under 30 words)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"summary": ""}


class MetadataEnricherAgent(SearchMicroAgent):
    """Adds contextual metadata."""
    
    def get_system_prompt(self) -> str:
        return """You are a metadata enrichment specialist. Your ONLY job is to add context about a paper.

Add:
- research_area: field/subfield
- methodology: experimental/theoretical/review
- impact_level: high/medium/low (based on citations & year)

Rules:
- Return ONLY valid JSON
- Be concise

Output format:
{"research_area": "...", "methodology": "...", "impact_level": "..."}"""
    
    def get_user_prompt(self, paper: Dict[str, Any], **kwargs) -> str:
        return f"""Add metadata for this paper:

Title: {paper.get('title', '')}
Abstract: {paper.get('abstract', '')[:200]}...
Year: {paper.get('year', 0)}
Citations: {paper.get('citations', 0)}

Return JSON with research_area, methodology, impact_level."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"research_area": "", "methodology": "", "impact_level": "medium"}


class ResultAggregatorAgent(SearchMicroAgent):
    """Combines results from multiple sources."""
    
    def get_system_prompt(self) -> str:
        return """You are a result aggregation specialist. Your ONLY job is to combine papers from multiple sources.

Rules:
- Merge duplicates
- Rank by relevance
- Return top N papers
- Return ONLY valid JSON

Output format:
{"aggregated_papers": [{"title": "...", "score": 0.9}, ...]}"""
    
    def get_user_prompt(self, papers_by_source: Dict[str, List[Dict]], top_n: int = 10, **kwargs) -> str:
        return f"""Aggregate papers from multiple sources:

{json.dumps(papers_by_source, indent=2)[:800]}

Return JSON with aggregated_papers (top {top_n}, ranked by relevance)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"aggregated_papers": []}


class InsightExtractorAgent(SearchMicroAgent):
    """Identifies key findings from papers."""
    
    def get_system_prompt(self) -> str:
        return """You are an insight extraction specialist. Your ONLY job is to extract 3-5 key insights from a set of papers.

Rules:
- Each insight: one sentence
- Focus on novel findings
- Return ONLY valid JSON

Output format:
{"insights": ["insight 1", "insight 2", ...]}"""
    
    def get_user_prompt(self, papers: List[Dict[str, Any]], **kwargs) -> str:
        summaries = "\n".join([
            f"- {p.get('title', '')}: {p.get('abstract', '')[:100]}..."
            for p in papers[:5]
        ])
        
        return f"""Extract key insights from these papers:

{summaries}

Return JSON with insights (3-5 sentences)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"insights": []}


class GapAnalysisAgent(SearchMicroAgent):
    """Identifies research gaps."""
    
    def get_system_prompt(self) -> str:
        return """You are a gap analysis specialist. Your ONLY job is to identify 2-3 research gaps from a literature review.

Rules:
- Each gap: one sentence
- Focus on understudied areas
- Return ONLY valid JSON

Output format:
{"research_gaps": ["gap 1", "gap 2", ...]}"""
    
    def get_user_prompt(self, papers: List[Dict[str, Any]], query: str, **kwargs) -> str:
        summaries = "\n".join([
            f"- {p.get('title', '')} ({p.get('year', 0)})"
            for p in papers[:5]
        ])
        
        return f"""Identify research gaps for: {query}

Existing research:
{summaries}

Return JSON with research_gaps (2-3 sentences)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"research_gaps": []}


class TrendDetectorAgent(SearchMicroAgent):
    """Identifies research trends."""
    
    def get_system_prompt(self) -> str:
        return """You are a trend detection specialist. Your ONLY job is to identify 2-3 research trends from papers.

Consider:
- Publication years
- Citation patterns
- Emerging topics

Rules:
- Each trend: one sentence
- Return ONLY valid JSON

Output format:
{"trends": ["trend 1", "trend 2", ...]}"""
    
    def get_user_prompt(self, papers: List[Dict[str, Any]], **kwargs) -> str:
        summaries = "\n".join([
            f"- {p.get('title', '')} ({p.get('year', 0)}, {p.get('citations', 0)} cites)"
            for p in papers[:5]
        ])
        
        return f"""Identify research trends:

{summaries}

Return JSON with trends (2-3 sentences)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"trends": []}


class RecommendationAgent(SearchMicroAgent):
    """Suggests next research steps."""
    
    def get_system_prompt(self) -> str:
        return """You are a recommendation specialist. Your ONLY job is to suggest 2-3 next research steps.

Based on:
- Current findings
- Research gaps
- Trends

Rules:
- Each recommendation: one sentence
- Actionable and specific
- Return ONLY valid JSON

Output format:
{"recommendations": ["rec 1", "rec 2", ...]}"""
    
    def get_user_prompt(
        self,
        insights: List[str],
        gaps: List[str],
        trends: List[str],
        **kwargs
    ) -> str:
        return f"""Suggest next research steps:

Key Insights:
{chr(10).join(f'- {i}' for i in insights[:3])}

Research Gaps:
{chr(10).join(f'- {g}' for g in gaps[:3])}

Trends:
{chr(10).join(f'- {t}' for t in trends[:3])}

Return JSON with recommendations (2-3 actionable steps)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"recommendations": []}
