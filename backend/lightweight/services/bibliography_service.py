"""
Bibliography Service - Auto-generate and manage bibliographies

Features:
- Generate BibTeX entries from source metadata
- Support multiple citation styles (APA, Harvard, Chicago)
- Maintain references.bib file per workspace
- Auto-update when sources added
"""

import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class BibliographyService:
    """Manage bibliography generation and updates."""
    
    @staticmethod
    def generate_bibtex_entry(source: Dict) -> str:
        """
        Generate BibTeX entry from source metadata.
        
        Args:
            source: Source dict with title, authors, year, etc.
            
        Returns:
            BibTeX formatted entry
        """
        # Generate cite key (AuthorYear format)
        cite_key = BibliographyService._generate_cite_key(source)
        
        # Format authors
        authors = source.get("authors", ["Unknown"])
        if isinstance(authors, list):
            authors_str = " and ".join(authors)
        else:
            authors_str = str(authors)
        
        # Build BibTeX entry
        entry_type = source.get("type", "article")
        title = source.get("title", "Untitled")
        year = source.get("year", "n.d.")
        abstract = source.get("abstract", "")
        doi = source.get("doi", "")
        
        bibtex = f"""@{entry_type}{{{cite_key},
    title = {{{title}}},
    author = {{{authors_str}}},
    year = {{{year}}}"""
        
        if abstract:
            bibtex += f""",
    abstract = {{{abstract}}}"""
        
        if doi:
            bibtex += f""",
    doi = {{{doi}}}"""
        
        bibtex += "\n}\n"
        
        return bibtex
    
    @staticmethod
    def _generate_cite_key(source: Dict) -> str:
        """Generate citation key (e.g., Smith2020)."""
        
        authors = source.get("authors", ["Unknown"])
        year = source.get("year", "")
        
        # Get first author's last name
        if isinstance(authors, list) and authors:
            first_author = authors[0]
        else:
            first_author = str(authors)
        
        # Extract last name
        name_parts = first_author.split()
        last_name = name_parts[-1] if name_parts else "Unknown"
        
        # Clean last name (remove non-alphanumeric)
        last_name = re.sub(r'[^a-zA-Z]', '', last_name)
        
        return f"{last_name}{year}"
    
    @staticmethod
    async def update_bibliography(workspace_id: str, new_source: Dict):
        """
        Add source to workspace bibliography file.
        
        Args:
            workspace_id: Workspace ID
            new_source: Source metadata dict
        """
        from services.workspace_service import WORKSPACES_DIR
        
        workspace_path = WORKSPACES_DIR / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        bib_path = workspace_path / "references.bib"
        
        # Generate BibTeX entry
        entry = BibliographyService.generate_bibtex_entry(new_source)
        
        # Append to file (create if doesn't exist)
        with open(bib_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        
        print(f"✅ Added to bibliography: {BibliographyService._generate_cite_key(new_source)}")
    
    @staticmethod
    def generate_apa_citation(source: Dict) -> str:
        """Generate APA format citation."""
        
        authors = source.get("authors", ["Unknown"])
        year = source.get("year", "n.d.")
        title = source.get("title", "Untitled")
        
        # Format authors (APA style)
        if isinstance(authors, list):
            if len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} & {authors[1]}"
            else:
                author_str = f"{authors[0]} et al."
        else:
            author_str = str(authors)
        
        return f"{author_str} ({year}). {title}."
    
    @staticmethod
    def load_bibliography(workspace_id: str) -> List[str]:
        """Load all bibliography entries for workspace."""
        from services.workspace_service import WORKSPACES_DIR
        
        bib_path = WORKSPACES_DIR / workspace_id / "references.bib"
        
        if not bib_path.exists():
            return []
        
        with open(bib_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split into individual entries
        entries = re.split(r'@\w+\{', content)
        entries = [f"@{e}" for e in entries[1:] if e.strip()]
        
        return entries


# Singleton instance
bibliography_service = BibliographyService()
