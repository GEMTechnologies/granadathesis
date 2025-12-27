#!/usr/bin/env python3
"""
Full-Text Search Index

Index extracted PDF text for fast searching within paper content.
Uses Whoosh for lightweight full-text search.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID, DATETIME, KEYWORD
    from whoosh.qparser import QueryParser, MultifieldParser
    from whoosh.query import And, Or, Term
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False
    print("⚠️  Whoosh not installed - full-text search unavailable")


class FullTextSearchIndex:
    """Full-text search index for papers."""
    
    def __init__(self, index_dir: str = "thesis_data/search_index"):
        """
        Initialize search index.
        
        Args:
            index_dir: Directory to store index
        """
        if not WHOOSH_AVAILABLE:
            raise ImportError("Whoosh not installed. Run: pip install whoosh")
        
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Define schema
        self.schema = Schema(
            paper_id=ID(stored=True, unique=True),
            title=TEXT(stored=True),
            authors=TEXT(stored=True),
            abstract=TEXT(stored=True),
            fulltext=TEXT,  # Not stored to save space
            year=KEYWORD(stored=True),
            venue=TEXT(stored=True),
            doi=ID(stored=True),
            url=ID(stored=True),
            source=KEYWORD(stored=True),
            indexed_at=DATETIME(stored=True)
        )
        
        # Create or open index
        if index.exists_in(str(self.index_dir)):
            self.ix = index.open_dir(str(self.index_dir))
        else:
            self.ix = index.create_in(str(self.index_dir), self.schema)
    
    def add_paper(self, paper_id: str, paper: Dict[str, Any], fulltext: Optional[str] = None):
        """
        Add paper to index.
        
        Args:
            paper_id: Unique paper identifier (DOI or title hash)
            paper: Paper metadata dictionary
            fulltext: Optional full-text content from PDF
        """
        writer = self.ix.writer()
        
        try:
            writer.add_document(
                paper_id=paper_id,
                title=paper.get("title", ""),
                authors=", ".join(paper.get("authors", [])),
                abstract=paper.get("abstract", ""),
                fulltext=fulltext or "",
                year=str(paper.get("year", "")),
                venue=paper.get("venue", ""),
                doi=paper.get("doi", ""),
                url=paper.get("url", ""),
                source=paper.get("source", ""),
                indexed_at=datetime.now()
            )
            writer.commit()
        except Exception as e:
            writer.cancel()
            raise e
    
    def search(self, query: str, fields: Optional[List[str]] = None, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the index.
        
        Args:
            query: Search query
            fields: Fields to search (default: title, abstract, fulltext)
            limit: Maximum results
            
        Returns:
            List of matching papers
        """
        if fields is None:
            fields = ["title", "abstract", "fulltext"]
        
        with self.ix.searcher() as searcher:
            # Multi-field query parser
            parser = MultifieldParser(fields, schema=self.ix.schema)
            q = parser.parse(query)
            
            # Search
            results = searcher.search(q, limit=limit)
            
            # Convert to list of dicts
            papers = []
            for hit in results:
                papers.append({
                    "paper_id": hit["paper_id"],
                    "title": hit["title"],
                    "authors": hit["authors"],
                    "year": hit["year"],
                    "venue": hit["venue"],
                    "doi": hit["doi"],
                    "url": hit["url"],
                    "source": hit["source"],
                    "score": hit.score,
                    "highlights": hit.highlights("fulltext", top=3) if "fulltext" in fields else None
                })
            
            return papers
    
    def search_within_papers(self, paper_ids: List[str], query: str, 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search within specific papers only.
        
        Args:
            paper_ids: List of paper IDs to search within
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching papers
        """
        with self.ix.searcher() as searcher:
            # Create query for specific papers
            paper_filter = Or([Term("paper_id", pid) for pid in paper_ids])
            
            # Parse search query
            parser = MultifieldParser(["title", "abstract", "fulltext"], schema=self.ix.schema)
            text_query = parser.parse(query)
            
            # Combine filters
            combined_query = And([paper_filter, text_query])
            
            # Search
            results = searcher.search(combined_query, limit=limit)
            
            papers = []
            for hit in results:
                papers.append({
                    "paper_id": hit["paper_id"],
                    "title": hit["title"],
                    "score": hit.score,
                    "highlights": hit.highlights("fulltext", top=3)
                })
            
            return papers
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self.ix.searcher() as searcher:
            return {
                "total_documents": searcher.doc_count_all(),
                "indexed_fields": list(self.schema.names()),
                "index_size_mb": sum(
                    f.stat().st_size for f in self.index_dir.glob("*")
                ) / 1024 / 1024
            }
    
    def clear(self):
        """Clear the entire index."""
        writer = self.ix.writer()
        writer.commit(mergetype=index.CLEAR)


# Global index instance
_search_index = None


def get_search_index() -> FullTextSearchIndex:
    """Get global search index instance."""
    global _search_index
    if _search_index is None:
        _search_index = FullTextSearchIndex()
    return _search_index
