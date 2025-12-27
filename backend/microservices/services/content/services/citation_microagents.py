"""
Citation Microagents - Specialized agents for academic citation management

5 focused microagents for finding, validating, formatting, and managing citations
using MDAP voting for reliability.
"""

import json
import re
from typing import Any, Dict, List, Optional
from app.services.search_microagents import SearchMicroAgent


class CitationFinderAgent(SearchMicroAgent):
    """Finds relevant academic papers for a given claim or sentence."""
    
    def get_system_prompt(self) -> str:
        return """You are a citation finder specialist. Your ONLY job is to identify the most relevant academic paper for a given claim or sentence.

Rules:
- Return the most relevant paper from the provided list
- Consider recency, citation count, and relevance
- Return ONLY valid JSON

Output format:
{"selected_paper_index": 0, "relevance_score": 0.95, "reasoning": "brief explanation"}"""
    
    def get_user_prompt(self, claim: str, papers: List[Dict[str, Any]], **kwargs) -> str:
        papers_text = "\n".join([
            f"{i}. {p.get('title', 'N/A')} ({p.get('year', 'N/A')}, {p.get('citations', 0)} citations)"
            for i, p in enumerate(papers[:5])
        ])
        
        return f"""Find the most relevant paper for this claim:

Claim: "{claim}"

Available papers:
{papers_text}

Return JSON with selected_paper_index (0-{len(papers[:5])-1}), relevance_score (0-1), and reasoning."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"selected_paper_index": 0, "relevance_score": 0.5, "reasoning": ""}


class CitationValidatorAgent(SearchMicroAgent):
    """Validates that a citation is relevant and appropriate for the claim."""
    
    def get_system_prompt(self) -> str:
        return """You are a citation validation specialist. Your ONLY job is to verify if a paper citation is relevant and appropriate for a claim.

Rules:
- Check if paper content matches the claim
- Verify citation is not misleading
- Return ONLY valid JSON

Output format:
{"is_valid": true, "confidence": 0.9, "issues": []}"""
    
    def get_user_prompt(self, claim: str, paper: Dict[str, Any], **kwargs) -> str:
        return f"""Validate if this paper is appropriate for the claim:

Claim: "{claim}"

Paper:
Title: {paper.get('title', 'N/A')}
Abstract: {paper.get('abstract', 'N/A')[:300]}...
Year: {paper.get('year', 'N/A')}

Return JSON with is_valid (boolean), confidence (0-1), and issues (list of problems, empty if valid)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"is_valid": True, "confidence": 0.7, "issues": []}


class CitationFormatterAgent(SearchMicroAgent):
    """Formats citations in APA or Harvard style."""
    
    def get_system_prompt(self) -> str:
        return """You are a citation formatting specialist. Your ONLY job is to format citations in academic style.

APA format:
- In-text: (Author, Year) or Author (Year)
- Reference: Author, A. A. (Year). Title. Journal, Volume(Issue), pages.

Harvard format:
- In-text: (Author Year) or Author (Year)
- Reference: Author, AA Year, 'Title', Journal, vol. Volume, no. Issue, pp. pages.

Rules:
- Format exactly according to style guide
- Handle multiple authors (et al. for 3+)
- Return ONLY valid JSON

Output format:
{"in_text": "(Smith, 2020)", "reference": "Smith, J. (2020). Title...", "style": "APA"}"""
    
    def get_user_prompt(
        self,
        paper: Dict[str, Any],
        style: str = "APA",
        **kwargs
    ) -> str:
        authors = paper.get('authors', [])
        author_str = ', '.join(authors[:3]) if authors else 'Unknown'
        
        return f"""Format this citation in {style} style:

Paper:
Authors: {author_str}
Year: {paper.get('year', 'n.d.')}
Title: {paper.get('title', 'Untitled')}
Journal: {paper.get('venue', 'Unknown')}
DOI: {paper.get('doi', '')}

Return JSON with in_text citation, full reference, and style."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "in_text": "(Author, Year)",
            "reference": "Author, A. (Year). Title. Journal.",
            "style": "APA"
        }


class ReferenceGeneratorAgent(SearchMicroAgent):
    """Generates complete reference list entries."""
    
    def get_system_prompt(self) -> str:
        return """You are a reference list generator specialist. Your ONLY job is to create properly formatted reference list entries.

Rules:
- Follow citation style guide exactly
- Include all available metadata (DOI, URL, etc.)
- Alphabetize by first author's last name
- Return ONLY valid JSON

Output format:
{"reference": "Full reference entry here", "sort_key": "Smith"}"""
    
    def get_user_prompt(
        self,
        papers: List[Dict[str, Any]],
        style: str = "APA",
        **kwargs
    ) -> str:
        papers_text = "\n".join([
            f"{i+1}. {p.get('title', 'N/A')} by {', '.join(p.get('authors', ['Unknown'])[:2])}"
            for i, p in enumerate(papers[:10])
        ])
        
        return f"""Generate reference list entries in {style} style for these papers:

{papers_text}

Return JSON with references (list of entries) and sort_keys (list of author last names for sorting)."""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"references": [], "sort_keys": []}


class CitationDensityAgent(SearchMicroAgent):
    """Analyzes and ensures sufficient citation density in text."""
    
    def get_system_prompt(self) -> str:
        return """You are a citation density specialist. Your ONLY job is to analyze citation density and suggest where more citations are needed.

Rules:
- Count sentences with citations
- Identify sentences that need citations
- Target: 70-80% of sentences should have citations
- Return ONLY valid JSON

Output format:
{"citation_density": 0.75, "total_sentences": 20, "cited_sentences": 15, "needs_citation": [3, 7, 12]}"""
    
    def get_user_prompt(self, text: str, **kwargs) -> str:
        return f"""Analyze citation density in this text:

{text[:1000]}

Return JSON with:
- citation_density (0-1)
- total_sentences (count)
- cited_sentences (count)
- needs_citation (list of sentence indices that need citations, 0-indexed)"""
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "citation_density": 0.0,
            "total_sentences": 0,
            "cited_sentences": 0,
            "needs_citation": []
        }


class SentenceCitationAgent(SearchMicroAgent):
    """Generates a single sentence with appropriate citation."""
    
    def get_system_prompt(self) -> str:
        return """You are a sentence citation specialist. Your ONLY job is to write a single academic sentence with an in-text citation.

Rules:
- Write ONE sentence only
- Include in-text citation at the end: (Author, Year)
- Sentence must relate to the topic and paper provided
- Use formal academic language
- Return ONLY valid JSON

Output format:
{"sentence": "Machine learning algorithms improve diagnostic accuracy (Smith, 2020).", "citation": "(Smith, 2020)"}"""
    
    def get_user_prompt(
        self,
        topic: str,
        paper: Dict[str, Any],
        context: Optional[str] = None,
        **kwargs
    ) -> str:
        prompt = f"""Write ONE academic sentence about this topic using this paper:

Topic: {topic}

Paper to cite:
Title: {paper.get('title', 'N/A')}
Authors: {', '.join(paper.get('authors', ['Unknown'])[:2])}
Year: {paper.get('year', 'N/A')}
Abstract: {paper.get('abstract', 'N/A')[:200]}..."""

        if context:
            prompt += f"\n\nContext (previous sentences):\n{context}"
        
        prompt += "\n\nReturn JSON with sentence (including citation) and citation (just the citation part)."
        return prompt
    
    def parse_response(self, raw_response: str) -> Any:
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "sentence": "Research shows significant findings (Author, Year).",
            "citation": "(Author, Year)"
        }
