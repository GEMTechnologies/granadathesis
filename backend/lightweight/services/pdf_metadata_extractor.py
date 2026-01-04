"""
PDF Metadata Extractor - Extract metadata and content from PDFs

Extracts:
- Title (from metadata or first page)
- Authors (from metadata or parsing)
- Year (from filename or content)
- Abstract (first paragraphs)
- Full text content
- DOI (if present)
"""

import re
import PyPDF2
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class PDFMetadataExtractor:
    """Extract metadata and content from PDF files."""
    
    @staticmethod
    def extract_metadata(pdf_path: Path) -> Dict:
        """
        Extract comprehensive metadata from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with title, authors, year, abstract, content, etc.
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract PDF metadata
                pdf_info = pdf_reader.metadata or {}
                
                # Extract text from first few pages
                first_page_text = ""
                full_text = ""
                
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    full_text += page_text + "\n"
                    
                    if i == 0:
                        first_page_text = page_text
                
                # Extract components
                title = PDFMetadataExtractor._extract_title(pdf_info, first_page_text, pdf_path)
                authors = PDFMetadataExtractor._extract_authors(pdf_info, first_page_text)
                year = PDFMetadataExtractor._extract_year(pdf_path.name, first_page_text)
                abstract = PDFMetadataExtractor._extract_abstract(full_text)
                doi = PDFMetadataExtractor._extract_doi(full_text)
                
                return {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract,
                    "doi": doi,
                    "full_text": full_text,
                    "page_count": len(pdf_reader.pages),
                    "file_name": pdf_path.name,
                    "file_size": pdf_path.stat().st_size,
                    "extracted_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"⚠️ Error extracting metadata from {pdf_path.name}: {e}")
            return {
                "title": pdf_path.stem,
                "authors": [],
                "year": None,
                "abstract": "",
                "doi": None,
                "full_text": "",
                "error": str(e),
                "file_name": pdf_path.name
            }
    
    @staticmethod
    def _extract_title(pdf_info: Dict, first_page: str, pdf_path: Path) -> str:
        """Extract title from PDF metadata or first page."""
        
        # Try PDF metadata first
        if pdf_info.get('/Title'):
            return str(pdf_info['/Title']).strip()
        
        # Try to find title in first page (usually largest text at top)
        lines = first_page.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            # Title is usually longer than 10 chars and not all caps
            if len(line) > 10 and len(line) < 200:
                if not line.isupper() or len(line.split()) > 5:
                    return line
        
        # Fallback to filename
        return pdf_path.stem.replace('_', ' ').replace('-', ' ')
    
    @staticmethod
    def _extract_authors(pdf_info: Dict, first_page: str) -> List[str]:
        """Extract authors from PDF metadata or first page."""
        
        authors = []
        
        # Try PDF metadata
        if pdf_info.get('/Author'):
            author_str = str(pdf_info['/Author'])
            # Split by common separators
            authors = re.split(r'[,;]|\sand\s', author_str)
            authors = [a.strip() for a in authors if a.strip()]
        
        # Try to find authors in first page
        if not authors:
            # Common prefixes in theses/books
            prefix_patterns = [
                r'(?:By|by)\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?)',
                r'(?:Author|AUTHOR):\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?)',
                r'Submitted by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Candidate:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            ]
            
            for pattern in prefix_patterns:
                matches = re.findall(pattern, first_page[:1000])
                if matches:
                    authors.extend([m.strip() for m in matches if m.strip()])
            
            if not authors:
                # Fallback: Look for patterns like "John Smith" but be stricter
                # Avoid common non-names
                author_pattern = r'([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)'
                matches = re.findall(author_pattern, first_page[:800])
                
                # Filter bad matches
                bad_words = ["University", "College", "Department", "Faculty", "School", "Thesis", "Dissertation", "Degree", "Doctor", "Master", "Bachelor", "Science", "Arts", "Philosophy", "April", "June", "July", "September", "January", "December", "August", "February", "March", "October", "November", "Spring", "Summer", "Fall", "Winter"]
                
                filtered = []
                for m in matches:
                    if not any(bad in m for bad in bad_words) and len(m.split()) <= 4:
                        filtered.append(m)
                        
                if filtered:
                    authors = filtered[:3]  # Limit to 3 likely authors
        
        return authors if authors else ["Unknown Author"]
    
    @staticmethod
    def _extract_year(filename: str, content: str) -> Optional[int]:
        """Extract publication year from filename or content."""
        
        # Try filename first (e.g., Smith2020.pdf)
        year_match = re.search(r'(19|20)\d{2}', filename)
        if year_match:
            return int(year_match.group(0))
        
        # Try content (look for copyright, published, etc.)
        year_patterns = [
            r'©\s*(19|20)\d{2}',
            r'Copyright\s*(19|20)\d{2}',
            r'Published\s*(19|20)\d{2}',
            r'\((19|20)\d{2}\)',
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, content[:2000])
            if match:
                year_str = re.search(r'(19|20)\d{2}', match.group(0))
                if year_str:
                    return int(year_str.group(0))
        
        return None
    
    @staticmethod
    def _extract_abstract(full_text: str) -> str:
        """Extract abstract from PDF content."""
        
        # Look for "Abstract" section
        abstract_match = re.search(
            r'(?:ABSTRACT|Abstract)\s*[:\n]+(.*?)(?:\n\n|INTRODUCTION|Introduction|1\.|Keywords)',
            full_text,
            re.DOTALL | re.IGNORECASE
        )
        
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            # Limit to reasonable length
            return abstract[:1000] if len(abstract) > 1000 else abstract
        
        # Fallback: first few paragraphs
        paragraphs = full_text.split('\n\n')
        for para in paragraphs[:5]:
            if len(para) > 100 and len(para) < 1000:
                return para.strip()
        
        return ""
    
    @staticmethod
    def _extract_doi(content: str) -> Optional[str]:
        """Extract DOI if present."""
        
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        match = re.search(doi_pattern, content[:2000])
        
        return match.group(0) if match else None


# Singleton instance
pdf_metadata_extractor = PDFMetadataExtractor()
