"""
Citation Management System for Thesis Chapters
Handles APA 7 format citations, references, and in-text citations
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class CitationStyle(Enum):
    """Supported citation styles."""
    APA_7 = "APA 7"
    APA_6 = "APA 6"
    HARVARD = "Harvard"
    CHICAGO = "Chicago"
    MLA = "MLA"


@dataclass
class Author:
    """Represents an author with various name formats."""
    first_name: str
    last_name: str
    middle_initials: Optional[str] = None
    
    def apa_format(self) -> str:
        """Return author in APA format: Last, F. M."""
        if self.middle_initials:
            return f"{self.last_name}, {self.first_name[0]}. {self.middle_initials}."
        return f"{self.last_name}, {self.first_name[0]}."
    
    def full_name(self) -> str:
        """Return full name."""
        if self.middle_initials:
            return f"{self.first_name} {self.middle_initials} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


@dataclass
class Citation:
    """Represents a complete citation with all metadata."""
    
    # Basic info
    citation_id: str  # Unique identifier (e.g., "Grabowski2018")
    authors: List[Author]
    year: int
    title: str
    source_type: str  # "journal", "book", "website", "report", etc.
    
    # Publication details
    publication_name: Optional[str] = None  # Journal/Book name
    volume: Optional[int] = None
    issue: Optional[int] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    
    # Publisher info
    publisher: Optional[str] = None
    publication_city: Optional[str] = None
    
    # Additional metadata
    retrieved_date: Optional[str] = None
    number_of_pages: Optional[int] = None
    edition: Optional[str] = None
    
    def apa_reference(self) -> str:
        """Generate APA 7 format reference."""
        
        # Author names
        if len(self.authors) == 1:
            authors_str = self.authors[0].apa_format()
        elif len(self.authors) == 2:
            authors_str = f"{self.authors[0].apa_format()}, & {self.authors[1].apa_format()}"
        elif len(self.authors) > 2:
            authors_str = ", ".join([a.apa_format() for a in self.authors[:-1]])
            authors_str += f", & {self.authors[-1].apa_format()}"
        else:
            authors_str = "Anonymous"
        
        # Base reference
        base = f"{authors_str} ({self.year}). {self.title}."
        
        # Source-specific formatting
        if self.source_type == "journal":
            ref = f"{base} *{self.publication_name}*"
            if self.volume:
                ref += f", {self.volume}"
                if self.issue:
                    ref += f"({self.issue})"
            if self.pages:
                ref += f", {self.pages}"
            if self.doi:
                ref += f". https://doi.org/{self.doi}"
            elif self.url:
                ref += f". Retrieved from {self.url}"
            ref += "."
            
        elif self.source_type == "book":
            ref = f"{base} "
            if self.publication_city:
                ref += f"{self.publication_city}: "
            ref += f"{self.publisher}."
            if self.doi:
                ref += f" https://doi.org/{self.doi}"
            elif self.url:
                ref += f" Retrieved from {self.url}"
            
        elif self.source_type == "chapter":
            ref = f"{base} In {self.publication_name} (pp. {self.pages})."
            if self.publication_city:
                ref += f" {self.publication_city}: "
            ref += f"{self.publisher}."
            
        elif self.source_type == "website":
            ref = f"{base} Retrieved from {self.url}"
            if self.retrieved_date:
                ref += f", {self.retrieved_date}"
            
        else:  # Generic source
            ref = base
            if self.publication_name:
                ref += f" {self.publication_name}."
            if self.doi:
                ref += f" https://doi.org/{self.doi}"
            elif self.url:
                ref += f" Retrieved from {self.url}"
        
        return ref
    
    def in_text_citation(self, page: Optional[int] = None) -> str:
        """Generate in-text citation in APA 7 format."""
        if len(self.authors) == 1:
            authors_str = self.authors[0].last_name
        elif len(self.authors) == 2:
            authors_str = f"{self.authors[0].last_name} & {self.authors[1].last_name}"
        else:
            authors_str = f"{self.authors[0].last_name} et al."
        
        citation = f"{authors_str} ({self.year})"
        if page:
            citation += f", p. {page}"
        
        return citation
    
    def in_text_narrative(self, page: Optional[int] = None) -> str:
        """Generate narrative in-text citation."""
        if len(self.authors) == 1:
            authors_str = self.authors[0].full_name()
        elif len(self.authors) == 2:
            authors_str = f"{self.authors[0].full_name()} and {self.authors[1].full_name()}"
        else:
            authors_str = f"{self.authors[0].full_name()} et al."
        
        citation = f"{authors_str} ({self.year})"
        if page:
            citation += f", p. {page}"
        
        return citation


class CitationManager:
    """Manages citations for thesis chapters."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.workspace_path = Path(f"/home/gemtech/Desktop/thesis/workspaces/{workspace_id}")
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.citations_dir = self.workspace_path / ".citations"
        self.citations_dir.mkdir(exist_ok=True)
        self.citations: Dict[str, Citation] = {}
        self.load_citations()
    
    def add_citation(self, citation: Citation):
        """Add citation to manager."""
        self.citations[citation.citation_id] = citation
        self.save_citations()
    
    def add_journal_article(
        self,
        citation_id: str,
        authors: List[Author],
        year: int,
        title: str,
        journal: str,
        volume: int,
        issue: Optional[int] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None
    ) -> Citation:
        """Convenience method for adding journal articles."""
        citation = Citation(
            citation_id=citation_id,
            authors=authors,
            year=year,
            title=title,
            source_type="journal",
            publication_name=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi
        )
        self.add_citation(citation)
        return citation
    
    def add_book(
        self,
        citation_id: str,
        authors: List[Author],
        year: int,
        title: str,
        publisher: str,
        publication_city: str,
        doi: Optional[str] = None,
        pages: Optional[int] = None
    ) -> Citation:
        """Convenience method for adding books."""
        citation = Citation(
            citation_id=citation_id,
            authors=authors,
            year=year,
            title=title,
            source_type="book",
            publisher=publisher,
            publication_city=publication_city,
            doi=doi,
            number_of_pages=pages
        )
        self.add_citation(citation)
        return citation
    
    def get_citation(self, citation_id: str) -> Optional[Citation]:
        """Get citation by ID."""
        return self.citations.get(citation_id)
    
    def get_reference(self, citation_id: str) -> str:
        """Get full reference for a citation."""
        citation = self.get_citation(citation_id)
        if citation:
            return citation.apa_reference()
        return ""
    
    def get_in_text(self, citation_id: str, page: Optional[int] = None) -> str:
        """Get in-text citation."""
        citation = self.get_citation(citation_id)
        if citation:
            return citation.in_text_citation(page)
        return ""
    
    def get_narrative(self, citation_id: str, page: Optional[int] = None) -> str:
        """Get narrative in-text citation."""
        citation = self.get_citation(citation_id)
        if citation:
            return citation.in_text_narrative(page)
        return ""
    
    def generate_bibliography(self, citation_ids: List[str]) -> str:
        """Generate complete bibliography in APA 7 format."""
        references = []
        
        for cid in citation_ids:
            citation = self.get_citation(cid)
            if citation:
                references.append(citation.apa_reference())
        
        # Sort alphabetically by first author
        references.sort()
        
        bibliography = "References\n\n"
        for ref in references:
            bibliography += ref + "\n\n"
        
        return bibliography
    
    def save_citations(self):
        """Save citations to JSON file."""
        citations_file = self.citations_dir / "citations.json"
        
        citations_data = {}
        for cid, citation in self.citations.items():
            citations_data[cid] = {
                "citation_id": citation.citation_id,
                "authors": [
                    {
                        "first_name": a.first_name,
                        "last_name": a.last_name,
                        "middle_initials": a.middle_initials
                    }
                    for a in citation.authors
                ],
                "year": citation.year,
                "title": citation.title,
                "source_type": citation.source_type,
                "publication_name": citation.publication_name,
                "volume": citation.volume,
                "issue": citation.issue,
                "pages": citation.pages,
                "doi": citation.doi,
                "url": citation.url,
                "publisher": citation.publisher,
                "publication_city": citation.publication_city,
                "retrieved_date": citation.retrieved_date,
                "number_of_pages": citation.number_of_pages,
                "edition": citation.edition
            }
        
        with open(citations_file, 'w') as f:
            json.dump(citations_data, f, indent=2)
    
    def load_citations(self):
        """Load citations from JSON file."""
        citations_file = self.citations_dir / "citations.json"
        
        if citations_file.exists():
            with open(citations_file, 'r') as f:
                citations_data = json.load(f)
            
            for cid, data in citations_data.items():
                authors = [
                    Author(
                        first_name=a["first_name"],
                        last_name=a["last_name"],
                        middle_initials=a.get("middle_initials")
                    )
                    for a in data["authors"]
                ]
                
                citation = Citation(
                    citation_id=data["citation_id"],
                    authors=authors,
                    year=data["year"],
                    title=data["title"],
                    source_type=data["source_type"],
                    publication_name=data.get("publication_name"),
                    volume=data.get("volume"),
                    issue=data.get("issue"),
                    pages=data.get("pages"),
                    doi=data.get("doi"),
                    url=data.get("url"),
                    publisher=data.get("publisher"),
                    publication_city=data.get("publication_city"),
                    retrieved_date=data.get("retrieved_date"),
                    number_of_pages=data.get("number_of_pages"),
                    edition=data.get("edition")
                )
                
                self.citations[cid] = citation
    
    def export_citations_for_chapter(
        self,
        chapter_num: int,
        citation_ids: List[str]
    ) -> str:
        """Export formatted citations for a specific chapter."""
        output = f"Chapter {chapter_num} - References\n"
        output += "=" * 50 + "\n\n"
        output += self.generate_bibliography(citation_ids)
        
        return output
