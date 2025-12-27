#!/usr/bin/env python3
"""
PDF Service - Download, Store, and Extract Text from Academic Papers

Features:
- Download PDFs from OA sources
- Organize by year/author/topic
- Extract text (regular + OCR for scanned)
- Extract images and figures
- Track download status
"""

import os
import hashlib
import asyncio
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging

# PDF processing
try:
    from PyPDF2 import PdfReader
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# OCR for scanned PDFs
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Image extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFService:
    """Manage PDF downloads and text extraction."""
    
    def __init__(self, base_dir: str = "thesis_data/pdfs"):
        """
        Initialize PDF service.
        
        Args:
            base_dir: Base directory for storing PDFs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.base_dir / "by_year").mkdir(exist_ok=True)
        (self.base_dir / "by_author").mkdir(exist_ok=True)
        (self.base_dir / "by_topic").mkdir(exist_ok=True)
        (self.base_dir / "images").mkdir(exist_ok=True)
        (self.base_dir / "fulltext").mkdir(exist_ok=True)
    
    def _sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """
        Create safe filename from text.
        
        Args:
            text: Input text
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        # Remove special characters
        safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
        # Remove extra spaces/underscores
        safe = "_".join(safe.split())
        # Truncate
        return safe[:max_length]
    
    def _get_pdf_path(self, paper: Dict[str, Any], organization: str = "year") -> Path:
        """
        Get storage path for PDF.
        
        Args:
            paper: Paper metadata
            organization: How to organize ('year', 'author', 'topic')
            
        Returns:
            Path to store PDF
        """
        title = paper.get("title", "unknown")
        year = paper.get("year", "unknown")
        authors = paper.get("authors", [])
        
        # Create filename
        safe_title = self._sanitize_filename(title, 80)
        filename = f"{safe_title}_{year}.pdf"
        
        # Organize by preference
        if organization == "year" and year != "unknown":
            subdir = self.base_dir / "by_year" / str(year)
        elif organization == "author" and authors:
            first_author = self._sanitize_filename(authors[0], 30)
            subdir = self.base_dir / "by_author" / first_author
        else:
            subdir = self.base_dir / "by_topic" / "general"
        
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir / filename
    
    async def download_pdf(self, url: str, paper: Dict[str, Any], 
                          organization: str = "year") -> Optional[Path]:
        """
        Download PDF from URL.
        
        Args:
            url: PDF URL
            paper: Paper metadata
            organization: How to organize files
            
        Returns:
            Path to downloaded PDF or None if failed
        """
        try:
            pdf_path = self._get_pdf_path(paper, organization)
            
            # Skip if already exists
            if pdf_path.exists():
                logger.info(f"PDF already exists: {pdf_path.name}")
                return pdf_path
            
            # Download
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
                    logger.warning(f"URL may not be a PDF: {url}")
                
                # Save
                pdf_path.write_bytes(response.content)
                logger.info(f"Downloaded PDF: {pdf_path.name} ({len(response.content)} bytes)")
                
                return pdf_path
                
        except Exception as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            return None
    
    def extract_text_simple(self, pdf_path: Path) -> str:
        """
        Extract text using PyPDF2 (fast, basic).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            reader = PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""
    
    def extract_text_advanced(self, pdf_path: Path) -> Tuple[str, List[List]]:
        """
        Extract text and tables using pdfplumber (slower, better quality).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (text, tables)
        """
        if not PDFPLUMBER_AVAILABLE:
            return self.extract_text_simple(pdf_path), []
        
        try:
            text = ""
            all_tables = []
            
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)
            
            return text.strip(), all_tables
            
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return self.extract_text_simple(pdf_path), []
    
    def extract_text_ocr(self, pdf_path: Path) -> str:
        """
        Extract text using OCR (for scanned PDFs).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR not available - install pdf2image and pytesseract")
            return self.extract_text_simple(pdf_path)
        
        try:
            # Convert PDF to images
            images = convert_from_path(str(pdf_path))
            
            # OCR each page
            text = ""
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                text += f"--- Page {i+1} ---\n{page_text}\n\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return self.extract_text_simple(pdf_path)
    
    def extract_images(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract images from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of image metadata
        """
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available - cannot extract images")
            return []
        
        try:
            doc = fitz.open(str(pdf_path))
            images = []
            
            for page_num, page in enumerate(doc):
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    # Save image
                    image_filename = f"{pdf_path.stem}_page{page_num+1}_img{img_index+1}.{base_image['ext']}"
                    image_path = self.base_dir / "images" / image_filename
                    image_path.write_bytes(base_image["image"])
                    
                    images.append({
                        "page": page_num + 1,
                        "index": img_index + 1,
                        "path": str(image_path),
                        "width": base_image["width"],
                        "height": base_image["height"],
                        "format": base_image["ext"]
                    })
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            return []
    
    def process_pdf(self, pdf_path: Path, extract_images: bool = False, 
                   use_ocr: bool = False) -> Dict[str, Any]:
        """
        Fully process a PDF.
        
        Args:
            pdf_path: Path to PDF file
            extract_images: Whether to extract images
            use_ocr: Whether to use OCR
            
        Returns:
            Processing results
        """
        results = {
            "pdf_path": str(pdf_path),
            "file_size": pdf_path.stat().st_size,
            "processed_at": datetime.now().isoformat()
        }
        
        # Extract text
        if use_ocr:
            results["text"] = self.extract_text_ocr(pdf_path)
            results["extraction_method"] = "ocr"
        else:
            text, tables = self.extract_text_advanced(pdf_path)
            results["text"] = text
            results["tables"] = tables
            results["extraction_method"] = "pdfplumber" if PDFPLUMBER_AVAILABLE else "pypdf2"
        
        # Save full text
        text_path = self.base_dir / "fulltext" / f"{pdf_path.stem}.txt"
        text_path.write_text(results["text"])
        results["text_path"] = str(text_path)
        
        # Extract images
        if extract_images:
            results["images"] = self.extract_images(pdf_path)
        
        return results
    
    async def download_and_process(self, paper: Dict[str, Any], 
                                  extract_images: bool = False,
                                  use_ocr: bool = False) -> Optional[Dict[str, Any]]:
        """
        Download PDF and process it.
        
        Args:
            paper: Paper metadata with URL
            extract_images: Whether to extract images
            use_ocr: Whether to use OCR
            
        Returns:
            Processing results or None if failed
        """
        # Get PDF URL
        url = paper.get("url", "")
        if not url or not (".pdf" in url.lower() or "download" in url.lower()):
            logger.warning(f"No PDF URL found for: {paper.get('title', 'unknown')}")
            return None
        
        # Download
        pdf_path = await self.download_pdf(url, paper)
        if not pdf_path:
            return None
        
        # Process
        results = self.process_pdf(pdf_path, extract_images, use_ocr)
        results["paper"] = paper
        
        return results


# Global PDF service instance
_pdf_service = None


def get_pdf_service() -> PDFService:
    """Get global PDF service instance."""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
