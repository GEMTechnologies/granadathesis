"""
Document Service - Upload, parse, and manage documents for RAG chat.

Supports:
- PDF (with page numbers)
- DOCX (with page numbers)
- Images (OCR via vision models)
- Text files
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

# PDF processing
try:
    import pdfplumber
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# DOCX processing
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Image processing
try:
    from PIL import Image
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

from services.workspace_service import WORKSPACES_DIR
from services.vision_service import vision_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing uploaded documents with RAG support."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.documents_dir = WORKSPACES_DIR / workspace_id / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.documents_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load document metadata."""
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text())
            except:
                return {}
        return {}
    
    def _save_metadata(self):
        """Save document metadata."""
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2))
    
    async def upload_document(
        self,
        file_path: Path,
        filename: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        Upload and parse a document.
        
        Returns document metadata with chunks and page numbers.
        """
        doc_id = hashlib.md5(f"{filename}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Save file
        saved_path = self.documents_dir / f"{doc_id}_{filename}"
        if file_path != saved_path:
            import shutil
            shutil.copy2(file_path, saved_path)
        
        # Parse based on type
        if file_type == "pdf":
            chunks = await self._parse_pdf(saved_path)
        elif file_type == "docx":
            chunks = await self._parse_docx(saved_path)
        elif file_type in ["png", "jpg", "jpeg", "gif", "webp"]:
            chunks = await self._parse_image(saved_path)
        elif file_type == "txt":
            chunks = await self._parse_text(saved_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Store metadata
        doc_metadata = {
            "id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "file_path": str(saved_path),
            "uploaded_at": datetime.now().isoformat(),
            "chunks": chunks,
            "total_chunks": len(chunks),
            "total_pages": max([c.get("page", 0) for c in chunks], default=0)
        }
        
        self.metadata[doc_id] = doc_metadata
        self._save_metadata()
        
        logger.info(f"Uploaded document {filename} with {len(chunks)} chunks")

        # BRIDGE TO SOURCES SERVICE:
        # Automatically add PDFs to Sources for Thesis RAG context
        if file_type == "pdf":
            try:
                from services.sources_service import sources_service
                # Use add_pdf_source to extract metadata and add to sources/ index
                # We pass the saved path. add_pdf_source will make its own copy in sources/pdfs
                await sources_service.add_pdf_source(
                    workspace_id=self.workspace_id,
                    pdf_path=saved_path,
                    original_filename=filename
                )
                logger.info(f"✅ Automatically added {filename} to Sources index for Thesis RAG")
            except Exception as bridge_error:
                logger.warning(f"⚠️ Failed to auto-add to Sources: {bridge_error}")
        
        return doc_metadata
    
    async def _parse_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Parse PDF with page numbers."""
        chunks = []
        
        if not PDF_AVAILABLE:
            raise ImportError("PDF libraries not available. Install: pip install pdfplumber PyPDF2")
        
        try:
            # Use pdfplumber for better text extraction
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        chunks.append({
                            "page": page_num,
                            "text": text.strip(),
                            "chunk_index": len(chunks),
                            "type": "text"
                        })
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            # Fallback to PyPDF2
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    chunks.append({
                        "page": page_num,
                        "text": text.strip(),
                        "chunk_index": len(chunks),
                        "type": "text"
                    })
        
        return chunks
    
    async def _parse_docx(self, docx_path: Path) -> List[Dict[str, Any]]:
        """Parse DOCX with page estimation."""
        chunks = []
        
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not available. Install: pip install python-docx")
        
        doc = Document(docx_path)
        
        # Estimate pages (rough: ~500 words per page)
        current_page = 1
        word_count = 0
        current_text = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            word_count += len(text.split())
            current_text.append(text)
            
            # Approximate page breaks (500 words per page)
            if word_count >= 500:
                chunks.append({
                    "page": current_page,
                    "text": "\n".join(current_text),
                    "chunk_index": len(chunks),
                    "type": "text"
                })
                current_text = []
                word_count = 0
                current_page += 1
        
        # Add remaining text
        if current_text:
            chunks.append({
                "page": current_page,
                "text": "\n".join(current_text),
                "chunk_index": len(chunks),
                "type": "text"
            })
        
        return chunks
    
    async def _parse_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """Parse image using vision service (OCR)."""
        chunks = []
        
        try:
            # Use vision service for OCR
            result = await vision_service.analyze_image(
                image_path=str(image_path),
                prompt="Extract all text from this image. Include any visible text, numbers, labels, and captions."
            )
            
            if result and result.get("text"):
                chunks.append({
                    "page": 1,
                    "text": result["text"],
                    "chunk_index": 0,
                    "type": "image_ocr"
                })
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            chunks.append({
                "page": 1,
                "text": f"[Image file: {image_path.name}. OCR not available.]",
                "chunk_index": 0,
                "type": "image"
            })
        
        return chunks
    
    async def _parse_text(self, text_path: Path) -> List[Dict[str, Any]]:
        """Parse plain text file."""
        text = text_path.read_text(encoding='utf-8', errors='ignore')
        
        # Split into chunks (roughly 500 words per chunk/page)
        words = text.split()
        chunks = []
        chunk_size = 500
        current_page = 1
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i+chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunks.append({
                "page": current_page,
                "text": chunk_text,
                "chunk_index": len(chunks),
                "type": "text"
            })
            current_page += 1
        
        return chunks
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata."""
        return self.metadata.get(doc_id)
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all uploaded documents."""
        return list(self.metadata.values())
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id not in self.metadata:
            return False
        
        doc = self.metadata[doc_id]
        file_path = Path(doc["file_path"])
        
        # Delete file
        if file_path.exists():
            file_path.unlink()
        
        # Remove from metadata
        del self.metadata[doc_id]
        self._save_metadata()
        
        return True
    
    def search_chunks(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search in document chunks.
        Returns chunks with document info and page numbers.
        """
        results = []
        
        for doc_id, doc_meta in self.metadata.items():
            if doc_ids and doc_id not in doc_ids:
                continue
            
            query_lower = query.lower()
            for chunk in doc_meta.get("chunks", []):
                text = chunk.get("text", "").lower()
                if query_lower in text:
                    results.append({
                        "doc_id": doc_id,
                        "doc_name": doc_meta["filename"],
                        "page": chunk.get("page", 0),
                        "text": chunk["text"],
                        "chunk_index": chunk.get("chunk_index", 0),
                        "relevance_score": text.count(query_lower) / max(len(text.split()), 1)
                    })
        
        # Sort by relevance and return top_k
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

