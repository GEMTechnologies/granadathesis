"""
GraphQL Schema for Sources - Fast Academic Reference Queries

Features:
- Query sources by ID, title, author, year, citation key
- Full-text search across sources
- Citation graph traversal
- Filter and sort capabilities
"""
import strawberry
from strawberry.types import Info
from typing import List, Optional
from datetime import datetime


@strawberry.type
class Author:
    """Author of an academic source."""
    name: str
    
@strawberry.type 
class Source:
    """Academic source (paper, article, dataset, etc.)."""
    id: str
    title: str
    authors: List[str]
    year: int
    type: str
    doi: Optional[str]
    url: Optional[str]
    abstract: Optional[str]
    venue: Optional[str]
    citation_count: int
    citation_key: str
    added_at: str
    file_path: Optional[str]
    text_extracted: bool
    
    @strawberry.field
    def authors_formatted(self) -> str:
        """Get formatted author string."""
        if len(self.authors) == 0:
            return "Unknown"
        elif len(self.authors) == 1:
            return self.authors[0]
        elif len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        else:
            return f"{self.authors[0]} et al."
    
    @strawberry.field
    def apa_citation(self) -> str:
        """Get APA format citation."""
        author_str = self.authors_formatted
        return f"{author_str} ({self.year}). {self.title}."


@strawberry.type
class SourcesIndex:
    """Index of all sources in a workspace."""
    total: int
    sources: List[Source]
    

@strawberry.type
class SearchResult:
    """Search result with relevance score."""
    source: Source
    relevance: float
    matched_fields: List[str]


@strawberry.input
class SourceFilter:
    """Filter options for sources."""
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    type: Optional[str] = None
    has_pdf: Optional[bool] = None
    has_text: Optional[bool] = None
    min_citations: Optional[int] = None


@strawberry.enum
class SortField:
    YEAR = "year"
    CITATIONS = "citation_count"
    TITLE = "title"
    ADDED = "added_at"


@strawberry.enum
class SortOrder:
    ASC = "asc"
    DESC = "desc"


def get_sources_service():
    """Lazy import to avoid circular deps."""
    from services.sources_service import sources_service
    return sources_service


@strawberry.type
class Query:
    """GraphQL queries for sources."""
    
    @strawberry.field
    def sources(
        self,
        workspace_id: str,
        filter: Optional[SourceFilter] = None,
        sort_by: SortField = SortField.ADDED,
        sort_order: SortOrder = SortOrder.DESC,
        limit: int = 50,
        offset: int = 0
    ) -> SourcesIndex:
        """Get all sources with optional filtering and sorting."""
        service = get_sources_service()
        all_sources = service.list_sources(workspace_id)
        
        # Apply filters
        filtered = all_sources
        if filter:
            if filter.year_min:
                filtered = [s for s in filtered if s.get("year", 0) >= filter.year_min]
            if filter.year_max:
                filtered = [s for s in filtered if s.get("year", 9999) <= filter.year_max]
            if filter.type:
                filtered = [s for s in filtered if s.get("type") == filter.type]
            if filter.has_pdf:
                filtered = [s for s in filtered if bool(s.get("file_path")) == filter.has_pdf]
            if filter.has_text:
                filtered = [s for s in filtered if s.get("text_extracted") == filter.has_text]
            if filter.min_citations:
                filtered = [s for s in filtered if s.get("citation_count", 0) >= filter.min_citations]
        
        # Sort
        sort_key = sort_by.value
        reverse = sort_order == SortOrder.DESC
        sorted_sources = sorted(filtered, key=lambda x: x.get(sort_key, ""), reverse=reverse)
        
        # Paginate
        paginated = sorted_sources[offset:offset + limit]
        
        # Convert to Source objects
        source_objects = [
            Source(
                id=s.get("id", ""),
                title=s.get("title", ""),
                authors=s.get("authors", []) if isinstance(s.get("authors", []), list) else [],
                year=s.get("year", 0),
                type=s.get("type", ""),
                doi=s.get("doi"),
                url=s.get("url"),
                abstract=s.get("abstract"),
                venue=s.get("venue"),
                citation_count=s.get("citation_count", 0),
                citation_key=s.get("citation_key", ""),
                added_at=s.get("added_at", ""),
                file_path=s.get("file_path"),
                text_extracted=s.get("text_extracted", False)
            )
            for s in paginated
        ]
        
        return SourcesIndex(total=len(filtered), sources=source_objects)
    
    @strawberry.field
    def source(self, workspace_id: str, source_id: str) -> Optional[Source]:
        """Get a specific source by ID."""
        service = get_sources_service()
        s = service.get_source(workspace_id, source_id)
        
        if not s:
            return None
        
        return Source(
            id=s.get("id", ""),
            title=s.get("title", ""),
            authors=s.get("authors", []) if isinstance(s.get("authors", []), list) else [],
            year=s.get("year", 0),
            type=s.get("type", ""),
            doi=s.get("doi"),
            url=s.get("url"),
            abstract=s.get("abstract"),
            venue=s.get("venue"),
            citation_count=s.get("citation_count", 0),
            citation_key=s.get("citation_key", ""),
            added_at=s.get("added_at", ""),
            file_path=s.get("file_path"),
            text_extracted=s.get("text_extracted", False)
        )
    
    @strawberry.field
    def source_by_citation_key(self, workspace_id: str, citation_key: str) -> Optional[Source]:
        """Get source by its citation key (e.g., 'smith2024machine')."""
        service = get_sources_service()
        all_sources = service.list_sources(workspace_id)
        
        for s in all_sources:
            if s.get("citation_key") == citation_key:
                return Source(
                    id=s.get("id", ""),
                    title=s.get("title", ""),
                    authors=s.get("authors", []) if isinstance(s.get("authors", []), list) else [],
                    year=s.get("year", 0),
                    type=s.get("type", ""),
                    doi=s.get("doi"),
                    url=s.get("url"),
                    abstract=s.get("abstract"),
                    venue=s.get("venue"),
                    citation_count=s.get("citation_count", 0),
                    citation_key=s.get("citation_key", ""),
                    added_at=s.get("added_at", ""),
                    file_path=s.get("file_path"),
                    text_extracted=s.get("text_extracted", False)
                )
        return None
    
    @strawberry.field
    def search_sources(
        self,
        workspace_id: str,
        query: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Full-text search across sources."""
        service = get_sources_service()
        all_sources = service.list_sources(workspace_id)
        
        query_lower = query.lower()
        results = []
        
        for s in all_sources:
            score = 0.0
            matched = []
            
            # Title match (highest weight)
            if query_lower in s.get("title", "").lower():
                score += 10.0
                matched.append("title")
            
            # Abstract match
            if query_lower in s.get("abstract", "").lower():
                score += 5.0
                matched.append("abstract")
            
            # Author match
            for author in s.get("authors", []):
                if query_lower in str(author).lower():
                    score += 3.0
                    matched.append("authors")
                    break
            
            # Venue match
            if query_lower in s.get("venue", "").lower():
                score += 2.0
                matched.append("venue")
            
            # Citation key match
            if query_lower in s.get("citation_key", "").lower():
                score += 8.0
                matched.append("citation_key")
            
            if score > 0:
                results.append({
                    "source": s,
                    "score": score,
                    "matched": matched
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Convert to SearchResult objects
        return [
            SearchResult(
                source=Source(
                    id=r["source"].get("id", ""),
                    title=r["source"].get("title", ""),
                    authors=r["source"].get("authors", []),
                    year=r["source"].get("year", 0),
                    type=r["source"].get("type", ""),
                    doi=r["source"].get("doi"),
                    url=r["source"].get("url"),
                    abstract=r["source"].get("abstract"),
                    venue=r["source"].get("venue"),
                    citation_count=r["source"].get("citation_count", 0),
                    citation_key=r["source"].get("citation_key", ""),
                    added_at=r["source"].get("added_at", ""),
                    file_path=r["source"].get("file_path"),
                    text_extracted=r["source"].get("text_extracted", False)
                ),
                relevance=r["score"],
                matched_fields=r["matched"]
            )
            for r in results[:limit]
        ]
    
    @strawberry.field
    def source_text(self, workspace_id: str, source_id: str) -> Optional[str]:
        """Get extracted text content of a source (for LLM context)."""
        service = get_sources_service()
        return service.get_source_text(workspace_id, source_id)
    
    @strawberry.field
    def sources_context(self, workspace_id: str, max_sources: int = 5) -> str:
        """Get formatted sources context for LLM."""
        service = get_sources_service()
        return service.get_sources_context(workspace_id, max_sources)


@strawberry.type
class Mutation:
    """GraphQL mutations for sources."""
    
    @strawberry.mutation
    async def add_source(
        self,
        workspace_id: str,
        title: str,
        authors: List[str],
        year: int,
        type: str = "paper",
        doi: Optional[str] = None,
        url: Optional[str] = None,
        abstract: Optional[str] = None,
        pdf_url: Optional[str] = None
    ) -> Source:
        """Add a new source manually."""
        service = get_sources_service()
        
        source_data = {
            "title": title,
            "authors": authors,
            "year": year,
            "type": type,
            "doi": doi or "",
            "url": url or "",
            "abstract": abstract or "",
            "pdf_url": pdf_url
        }
        
        result = await service.add_source(workspace_id, source_data)
        
        return Source(
            id=result.get("id", ""),
            title=result.get("title", ""),
            authors=result.get("authors", []),
            year=result.get("year", 0),
            type=result.get("type", ""),
            doi=result.get("doi"),
            url=result.get("url"),
            abstract=result.get("abstract"),
            venue=result.get("venue"),
            citation_count=result.get("citation_count", 0),
            citation_key=result.get("citation_key", ""),
            added_at=result.get("added_at", ""),
            file_path=result.get("file_path"),
            text_extracted=result.get("text_extracted", False)
        )
    
    @strawberry.mutation
    def delete_source(self, workspace_id: str, source_id: str) -> bool:
        """Delete a source."""
        service = get_sources_service()
        return service.delete_source(workspace_id, source_id)


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
