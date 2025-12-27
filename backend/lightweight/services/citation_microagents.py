"""
Citation Microagents - Specialized agents for academic citation management

5 focused microagents for finding, validating, formatting, and managing citations
using MDAP voting for reliability.
"""

import json
import re
from typing import Any, Dict, List, Optional
from app.services.search_microagents import SearchMicroAgent


def extract_last_name(author: str) -> str:
    """Extract last name only from an author name for APA citations."""
    if not author:
        return ""
    author = str(author).strip()
    
    # Handle "Last, First" format
    if "," in author:
        return author.split(",")[0].strip()
    
    # Handle "First Last" format - get the last word
    parts = author.split()
    if parts:
        return parts[-1]
    return author


def format_apa_authors(authors: List[str], for_reference: bool = False) -> str:
    """
    Format authors for APA 7 citation.
    
    Args:
        authors: List of author names
        for_reference: If True, format for reference list (Last, F.); if False, for in-text (Last)
    """
    if not authors:
        return ""
    
    # Filter out empty/invalid authors
    valid_authors = [a for a in authors if a and str(a).lower() not in ['unknown', 'n/a', '']]
    if not valid_authors:
        return ""
    
    if for_reference:
        # Format for reference list: Last, F. M.
        formatted = []
        for author in valid_authors[:7]:
            last_name = extract_last_name(author)
            # Get initials from first name(s)
            if "," in author:
                # "Last, First Middle" format
                parts = author.split(",", 1)
                first_parts = parts[1].strip().split() if len(parts) > 1 else []
            else:
                # "First Middle Last" format
                parts = author.split()
                first_parts = parts[:-1] if len(parts) > 1 else []
            
            initials = ". ".join([p[0].upper() for p in first_parts if p]) + "." if first_parts else ""
            formatted.append(f"{last_name}, {initials}" if initials else last_name)
        
        if len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]}, & {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
    else:
        # Format for in-text citation: Last names only
        last_names = [extract_last_name(a) for a in valid_authors if extract_last_name(a)]
        if not last_names:
            return ""
        
        if len(last_names) == 1:
            return last_names[0]
        elif len(last_names) == 2:
            return f"{last_names[0]} & {last_names[1]}"
        else:
            return f"{last_names[0]} et al."


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

APA 7 format - CRITICAL: Use LAST NAMES ONLY:
- In-text single author: (Smith, 2020) or Smith (2020)
- In-text two authors: (Smith & Jones, 2020) or Smith & Jones (2020)
- In-text 3+ authors: (Smith et al., 2020) or Smith et al. (2020)
- Reference: Smith, J. A. (Year). Title of article. Journal Name, Volume(Issue), pages. https://doi.org/xxx

Harvard format:
- In-text: (Smith 2020) or Smith (2020)
- Reference: Smith, JA 2020, 'Title', Journal, vol. Volume, no. Issue, pp. pages.

CRITICAL RULES:
- NEVER use full first names in in-text citations
- Use LAST NAME ONLY for in-text citations
- Handle multiple authors: & for 2 authors, et al. for 3+
- Return ONLY valid JSON

Output format:
{"in_text": "(Smith, 2020)", "reference": "Smith, J. A. (2020). Title...", "style": "APA"}"""
    
    def get_user_prompt(
        self,
        paper: Dict[str, Any],
        style: str = "APA",
        **kwargs
    ) -> str:
        authors = paper.get('authors', [])
        
        # Use the helper function for proper APA formatting
        in_text_author = format_apa_authors(authors, for_reference=False)
        ref_author = format_apa_authors(authors, for_reference=True)
        
        # Skip papers without valid authors
        if not in_text_author:
            return ""
        
        return f"""Format this citation in {style} style:

Paper:
Authors (for reference): {ref_author}
Authors (for in-text - LAST NAMES ONLY): {in_text_author}
Year: {paper.get('year', 'n.d.')}
Title: {paper.get('title', 'Untitled')}
Journal: {paper.get('venue', '')}
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
        # Filter out papers without valid authors
        valid_papers = []
        for p in papers[:10]:
            authors = p.get('authors', [])
            author_list = [a for a in authors[:2] if a and str(a).lower() != 'unknown']
            if author_list:
                valid_papers.append(f"{len(valid_papers)+1}. {p.get('title', 'N/A')} by {', '.join(author_list)}")
        
        papers_text = "\n".join(valid_papers)
        
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
        authors = paper.get('authors', [])
        author_list = [a for a in authors[:2] if a and str(a).lower() != 'unknown']
        author_str = ', '.join(author_list) if author_list else ''
        
        # Skip if no valid authors
        if not author_str:
            return ""
        
        prompt = f"""Write ONE academic sentence about this topic using this paper:

Topic: {topic}

Paper to cite:
Title: {paper.get('title', 'N/A')}
Authors: {author_str}
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
