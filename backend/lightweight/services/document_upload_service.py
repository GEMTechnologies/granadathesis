"""
Document Upload and RAG Integration Service

Handles PDF uploads, processes documents, and indexes them in vector DB
for retrieval-augmented generation.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
from services.pdf_service import extract_text_from_pdf
from services.vector_service import vector_service


async def process_uploaded_pdf(
    workspace_id: str,
    pdf_path: str,
    title: Optional[str] = None,
    author: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process uploaded PDF and index in vector database.
    
    Args:
        workspace_id: Workspace ID
        pdf_path: Path to PDF file
        title: Document title (optional, extracted from filename if not provided)
        author: Document author (optional)
    
    Returns:
        Dict with processing status, chunk count, citations
    """
    pdf_path_obj = Path(pdf_path)
    
    # Generate document ID
    document_id = hashlib.md5(pdf_path.encode()).hexdigest()[:12]
    
    # Extract title from filename if not provided
    if not title:
        title = pdf_path_obj.stem.replace('_', ' ').replace('-', ' ').title()
    
    try:
        # Step 1: Extract text from PDF
        text = await extract_text_from_pdf(pdf_path)
        
        if not text or len(text) < 100:
            return {
                "success": False,
                "error": "Could not extract text from PDF or text too short",
                "document_id": document_id
            }
        
        # Step 2: Chunk text for embedding
        chunks = vector_service.chunk_text(
            text,
            chunk_size=500,  # ~500 words per chunk
            overlap=50       # 50 word overlap between chunks
        )
        
        # Step 3: Extract citations (simple regex-based)
        citations = extract_citations_from_text(text)
        
        # Step 4: Index in vector database
        result = await vector_service.add_document(
            workspace_id=workspace_id,
            document_id=document_id,
            chunks=chunks,
            metadata={
                "title": title,
                "author": author or "Unknown",
                "filename": pdf_path_obj.name,
                "type": "pdf",
                "citation_count": len(citations)
            },
            source="user_upload"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "title": title,
            "chunks_indexed": result['indexed'],
            "citations_found": len(citations),
            "citations": citations[:10],  # Return first 10 citations
            "file_path": str(pdf_path)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id
        }


def extract_citations_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract citations from text using regex patterns.
    
    Returns:
        List of citation dicts with author, year, title
    """
    import re
    
    citations = []
    
    # Pattern for common citation formats
    # e.g., "Smith, J. (2023). Paper title."
    # e.g., "Smith, J., & Jones, A. (2024)"
    citation_pattern = r'([A-Z][a-z]+(?:,?\s+(?:[A-Z]\.|[A-Z][a-z]+))*)\s*\((\d{4})\)'
    
    matches = re.findall(citation_pattern, text)
    
    for author, year in matches:
        citations.append({
            "author": author.strip(),
            "year": year,
            "format": "apa"
        })
    
    # Deduplicate
    unique_citations = []
    seen = set()
    for cit in citations:
        key = (cit['author'], cit['year'])
        if key not in seen:
            seen.add(key)
            unique_citations.append(cit)
    
    return unique_citations


async def search_user_documents(
    workspace_id: str,
    query: str,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Search uploaded documents for relevant content.
    
    Args:
        workspace_id: Workspace ID
        query: Search query
        n_results: Number of results to return
    
    Returns:
        Search results with document chunks and metadata
    """
    results = await vector_service.search(
        workspace_id=workspace_id,
        query=query,
        n_results=n_results,
        filter_metadata={"source": "user_upload"}
    )
    
    return results
