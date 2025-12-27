#!/usr/bin/env python3
"""
Advanced Deduplication Utilities

Provides sophisticated deduplication for academic papers using:
- DOI-based (primary)
- Fuzzy title matching
- Author + year matching
"""

from typing import List, Dict, Any, Set
from dataclasses import dataclass
from fuzzywuzzy import fuzz
import re


@dataclass
class Paper:
    """Paper data structure (matches scholarly_search.py)."""
    title: str
    authors: List[str]
    year: int
    abstract: str
    url: str
    source: str
    citations: int = 0
    venue: str = ""
    doi: str = ""


class Deduplicator:
    """Advanced paper deduplication."""
    
    def __init__(self, title_threshold: int = 85, author_threshold: int = 80):
        """
        Initialize deduplicator.
        
        Args:
            title_threshold: Minimum fuzzy match score for titles (0-100)
            author_threshold: Minimum fuzzy match score for authors (0-100)
        """
        self.title_threshold = title_threshold
        self.author_threshold = author_threshold
    
    def normalize_title(self, title: str) -> str:
        """
        Normalize title for comparison.
        
        Args:
            title: Original title
            
        Returns:
            Normalized title
        """
        # Convert to lowercase
        title = title.lower()
        
        # Remove special characters
        title = re.sub(r'[^\w\s]', ' ', title)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        return title
    
    def normalize_author(self, author: str) -> str:
        """
        Normalize author name.
        
        Args:
            author: Original author name
            
        Returns:
            Normalized author name
        """
        # Convert to lowercase
        author = author.lower()
        
        # Remove special characters
        author = re.sub(r'[^\w\s]', ' ', author)
        
        # Remove extra whitespace
        author = ' '.join(author.split())
        
        return author
    
    def titles_match(self, title1: str, title2: str) -> bool:
        """
        Check if two titles match using fuzzy matching.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            True if titles match
        """
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Fuzzy match
        score = fuzz.ratio(norm1, norm2)
        return score >= self.title_threshold
    
    def authors_match(self, authors1: List[str], authors2: List[str]) -> bool:
        """
        Check if author lists match.
        
        Args:
            authors1: First author list
            authors2: Second author list
            
        Returns:
            True if authors match
        """
        if not authors1 or not authors2:
            return False
        
        # Normalize all authors
        norm1 = [self.normalize_author(a) for a in authors1]
        norm2 = [self.normalize_author(a) for a in authors2]
        
        # Check first author match (most important)
        if norm1[0] == norm2[0]:
            return True
        
        # Fuzzy match on first author
        score = fuzz.ratio(norm1[0], norm2[0])
        if score >= self.author_threshold:
            return True
        
        # Check if any authors overlap
        set1 = set(norm1)
        set2 = set(norm2)
        overlap = len(set1 & set2)
        
        # If >50% overlap, consider match
        min_len = min(len(set1), len(set2))
        if min_len > 0 and overlap / min_len >= 0.5:
            return True
        
        return False
    
    def papers_match(self, paper1: Dict[str, Any], paper2: Dict[str, Any]) -> bool:
        """
        Check if two papers are duplicates.
        
        Priority:
        1. DOI match (if both have DOIs)
        2. Title + Year match
        3. Title + First Author match
        
        Args:
            paper1: First paper
            paper2: Second paper
            
        Returns:
            True if papers are duplicates
        """
        # DOI match (highest priority)
        doi1 = paper1.get("doi", "").strip()
        doi2 = paper2.get("doi", "").strip()
        if doi1 and doi2 and doi1.lower() == doi2.lower():
            return True
        
        # Title match
        title1 = paper1.get("title", "")
        title2 = paper2.get("title", "")
        
        if not title1 or not title2:
            return False
        
        titles_similar = self.titles_match(title1, title2)
        
        if not titles_similar:
            return False
        
        # If titles match, check year
        year1 = paper1.get("year")
        year2 = paper2.get("year")
        
        if year1 and year2 and year1 == year2:
            return True
        
        # If titles match, check authors
        authors1 = paper1.get("authors", [])
        authors2 = paper2.get("authors", [])
        
        if self.authors_match(authors1, authors2):
            return True
        
        return False
    
    def deduplicate(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate papers from list.
        
        Strategy:
        1. Group by DOI (if available)
        2. For papers without DOI, use fuzzy matching
        3. Keep paper with most citations when duplicates found
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            Deduplicated list of papers
        """
        if not papers:
            return []
        
        # Track seen DOIs
        seen_dois: Set[str] = set()
        
        # Track unique papers
        unique_papers: List[Dict[str, Any]] = []
        
        for paper in papers:
            # Check DOI first
            doi = paper.get("doi", "").strip().lower()
            
            if doi and doi in seen_dois:
                # Duplicate DOI - skip
                continue
            
            # Check against existing unique papers
            is_duplicate = False
            duplicate_index = -1
            
            for i, existing_paper in enumerate(unique_papers):
                if self.papers_match(paper, existing_paper):
                    is_duplicate = True
                    duplicate_index = i
                    break
            
            if is_duplicate:
                # Keep paper with more citations
                existing_citations = unique_papers[duplicate_index].get("citations", 0)
                new_citations = paper.get("citations", 0)
                
                if new_citations > existing_citations:
                    # Replace with higher-cited version
                    unique_papers[duplicate_index] = paper
                    
                    # Update DOI tracking
                    if doi:
                        seen_dois.add(doi)
            else:
                # New unique paper
                unique_papers.append(paper)
                
                if doi:
                    seen_dois.add(doi)
        
        return unique_papers
    
    def get_duplicate_groups(self, papers: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group duplicate papers together.
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            List of duplicate groups
        """
        groups: List[List[Dict[str, Any]]] = []
        processed: Set[int] = set()
        
        for i, paper1 in enumerate(papers):
            if i in processed:
                continue
            
            group = [paper1]
            processed.add(i)
            
            for j, paper2 in enumerate(papers[i+1:], start=i+1):
                if j in processed:
                    continue
                
                if self.papers_match(paper1, paper2):
                    group.append(paper2)
                    processed.add(j)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups


# Global deduplicator instance
_deduplicator = None


def get_deduplicator() -> Deduplicator:
    """Get global deduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = Deduplicator()
    return _deduplicator
