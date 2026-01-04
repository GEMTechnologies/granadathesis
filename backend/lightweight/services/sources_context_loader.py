"""
Sources Context Loader - Integrate uploaded PDFs into LLM context

This helper loads uploaded PDF sources and formats them for LLM consumption,
enabling the AI to use uploaded literature when generating chapters.
"""

from typing import Dict, List, Optional
from pathlib import Path


def load_sources_for_llm(workspace_id: str, max_sources: int = 10) -> str:
    """
    Load sources from workspace and format for LLM context.
    
    Args:
        workspace_id: Workspace ID
        max_sources: Maximum number of sources to include
        
    Returns:
        Formatted string with source content for LLM
    """
    try:
        from services.sources_service import sources_service
        
        sources = sources_service.list_sources(workspace_id)
        
        if not sources:
            return ""
        
        # Sort by relevance (citation count, recency)
        sorted_sources = sorted(
            sources,
            key=lambda x: (x.get("citation_count", 0), x.get("year", 0)),
            reverse=True
        )
        
        context_parts = ["## 📚 Available Literature Sources\n"]
        context_parts.append("Use these sources to support your writing. Cite them using (Author, Year) format.\n")
        
        for i, source in enumerate(sorted_sources[:max_sources]):
            authors = source.get("authors", [])
            if not authors:
                continue
            
            # Format authors
            if isinstance(authors, list):
                if len(authors) == 1:
                    author_str = authors[0]
                elif len(authors) == 2:
                    author_str = f"{authors[0]} and {authors[1]}"
                else:
                    author_str = f"{authors[0]} et al."
            else:
                author_str = str(authors)
            
            year = source.get("year", "n.d.")
            title = source.get("title", "Untitled")
            abstract = source.get("abstract", "")
            
            # Get full text if available
            full_text = source.get("full_text", "")
            text_preview = full_text[:2000] if full_text else abstract[:500]
            
            context_parts.append(f"""
### Source {i+1}: {author_str} ({year})
**Title**: {title}
**Citation Key**: ({author_str.split()[0]}, {year})
**Content Preview**:
{text_preview}
{'...' if len(text_preview) >= 500 else ''}
---
""")
        
        context_parts.append(f"\n**Total sources available**: {len(sources)}")
        context_parts.append("\n**Instructions**: When citing, use format: (Author, Year). Example: 'Research shows that... (Smith, 2020).'")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        print(f"⚠️ Error loading sources for LLM: {e}")
        return ""


def get_citation_instructions() -> str:
    """Get citation instructions for LLM."""
    return """
## Citation Guidelines
- Use in-text citations: (Author, Year)
- For multiple authors: (Smith et al., 2020)
- For multiple citations: (Smith, 2020; Jones, 2021)
- Cite after statements, before period: "...conclusion (Author, Year)."
- All cited sources are available in the literature sources above
"""


# Add this function to chapter generator prompts
def enhance_prompt_with_sources(base_prompt: str, workspace_id: str, max_sources: int = 10) -> str:
    """
    Enhance a chapter generation prompt with source context.
    
    Args:
        base_prompt: Original prompt
        workspace_id: Workspace ID
        max_sources: Max sources to include
        
    Returns:
        Enhanced prompt with sources
    """
    sources_context = load_sources_for_llm(workspace_id, max_sources)
    
    if not sources_context:
        return base_prompt
    
    enhanced = f"""{base_prompt}

{sources_context}

{get_citation_instructions()}
"""
    
    return enhanced
