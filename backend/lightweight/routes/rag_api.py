"""
Fast RAG API Endpoints

High-performance REST APIs for document upload, semantic search, and workspace management.
Optimized for speed with async operations, streaming, and caching.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import aiofiles
import hashlib
from pathlib import Path
import json

# Create router
router = APIRouter(prefix="/api/rag", tags=["RAG"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    title: str
    chunks_indexed: int
    citations_found: int
    file_path: str
    processing_time: float

class SearchRequest(BaseModel):
    query: str
    workspace_id: str
    n_results: int = 5
    filter_source: Optional[str] = None  # 'user_upload', 'conversation', 'thesis'
    filter_date_from: Optional[str] = None
    filter_date_to: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    results: List[dict]
    count: int
    processing_time: float

class WorkspaceStatsResponse(BaseModel):
    workspace_id: str
    total_documents: int
    total_chunks: int
    storage_used_mb: float
    embedding_model: str

# ============================================================================
# FAST DOCUMENT UPLOAD WITH STREAMING
# ============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_fast(
    workspace_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    author: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Ultra-fast document upload with background indexing.
    
    Performance optimizations:
    - Async file I/O
    - Streaming file chunks
    - Background indexing (doesn't block response)
    - Progress updates via SSE
    
    Target: <2s for 10MB PDF
    """
    import time
    start_time = time.time()
    
    from services.document_upload_service import process_uploaded_pdf
    from services.workspace_service import WORKSPACES_DIR
    from core.events import events
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate job ID for progress tracking
    job_id = f"upload_{hashlib.md5(file.filename.encode()).hexdigest()[:12]}"
    
    # Save file with async I/O (fast!)
    workspace_uploads = WORKSPACES_DIR / workspace_id / "uploads"
    workspace_uploads.mkdir(parents=True, exist_ok=True)
    
    file_path = workspace_uploads / file.filename
    
    try:
        # Stream file to disk (async, non-blocking)
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
        
        # Publish upload complete event
        await events.connect()
        await events.publish(
            job_id,
            "log",
            {"message": f"📁 File uploaded: {file.filename}"},
            session_id=workspace_id
        )
        
        # Process and index in background (don't wait)
        if background_tasks:
            background_tasks.add_task(
                process_and_index_background,
                workspace_id=workspace_id,
                pdf_path=str(file_path),
                title=title,
                author=author,
                job_id=job_id
            )
        else:
            # Fallback: process synchronously if no background tasks
            result = await process_uploaded_pdf(
                workspace_id=workspace_id,
                pdf_path=str(file_path),
                title=title,
                author=author
            )
            
            processing_time = time.time() - start_time
            
            if result['success']:
                return DocumentUploadResponse(
                    success=True,
                    document_id=result['document_id'],
                    title=result['title'],
                    chunks_indexed=result['chunks_indexed'],
                    citations_found=result['citations_found'],
                    file_path=str(file_path),
                    processing_time=processing_time
                )
            else:
                raise HTTPException(status_code=500, detail=result.get('error', 'Processing failed'))
        
        # Return immediately with job ID (background processing continues)
        processing_time = time.time() - start_time
        
        return DocumentUploadResponse(
            success=True,
            document_id=job_id,
            title=title or file.filename,
            chunks_indexed=0,  # Background processing
            citations_found=0,  # Will be updated via SSE
            file_path=str(file_path),
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_and_index_background(
    workspace_id: str,
    pdf_path: str,
    title: Optional[str],
    author: Optional[str],
    job_id: str
):
    """Background task for processing and indexing PDF."""
    from services.document_upload_service import process_uploaded_pdf
    from core.events import events
    
    await events.connect()
    
    try:
        await events.publish(
            job_id,
            "log",
            {"message": "🔄 Processing PDF..."},
            session_id=workspace_id
        )
        
        result = await process_uploaded_pdf(
            workspace_id=workspace_id,
            pdf_path=pdf_path,
            title=title,
            author=author
        )
        
        if result['success']:
            await events.publish(
                job_id,
                "log",
                {"message": f"✅ Indexed {result['chunks_indexed']} chunks, found {result['citations_found']} citations"},
                session_id=workspace_id
            )
            
            # Publish completion event
            await events.publish(
                job_id,
                "stage_completed",
                {
                    "stage": "document_indexing",
                    "status": "success",
                    "chunks": result['chunks_indexed'],
                    "citations": result['citations_found']
                },
                session_id=workspace_id
            )
        else:
            await events.publish(
                job_id,
                "log",
                {"message": f"❌ Processing failed: {result.get('error')}"},
                session_id=workspace_id
            )
    
    except Exception as e:
        await events.publish(
            job_id,
            "log",
            {"message": f"❌ Error: {str(e)}"},
            session_id=workspace_id
        )


#============================================================================
# BATCH UPLOAD (Multiple Files)
# ============================================================================

@router.post("/upload/batch")
async def upload_documents_batch(
    workspace_id: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload multiple documents in parallel.
    
    Returns immediately with job IDs for tracking progress via SSE.
    """
    results = []
    
    for file in files:
        try:
            result = await upload_document_fast(
                workspace_id=workspace_id,
                file=file,
                background_tasks=background_tasks
            )
            results.append({"filename": file.filename, "status": "processing", "job_id": result.document_id})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "error": str(e)})
    
    return {"uploaded": len(results), "files": results}


# ============================================================================
# SEMANTIC SEARCH WITH STREAMING
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_documents_semantic(request: SearchRequest):
    """
    Blazing fast semantic search with caching.
    
    Performance optimizations:
    - Redis cache for repeated queries
    - Metadata filtering to reduce search space
    - Parallel vector similarity computation
    
    Target: <200ms response time
    """
    import time
    start_time = time.time()
    
    from services.vector_service import vector_service
    from core.cache import Cache
    
    # Check cache first (super fast!)
    cache_key = f"search:{request.workspace_id}:{request.query}:{request.n_results}"
    cached_result = await Cache.get(cache_key)
    
    if cached_result:
        processing_time = time.time() - start_time
        return SearchResponse(
            query=request.query,
            results=cached_result['results'],
            count=cached_result['count'],
            processing_time=processing_time
        )
    
    # Build metadata filter
    filter_metadata = {}
    if request.filter_source:
        filter_metadata['source'] = request.filter_source
    
    # Perform semantic search
    results = await vector_service.search(
        workspace_id=request.workspace_id,
        query=request.query,
        n_results=request.n_results,
        filter_metadata=filter_metadata if filter_metadata else None
    )
    
    processing_time = time.time() - start_time
    
    # Cache result for 5 minutes
    await Cache.set(cache_key, results, ttl=300)
    
    return SearchResponse(
        query=request.query,
        results=results.get('results', []),
        count=results.get('count', 0),
        processing_time=processing_time
    )


# ============================================================================
# WORKSPACE STATS (Cached)
# ============================================================================

@router.get("/workspace/{workspace_id}/stats", response_model=WorkspaceStatsResponse)
async def get_workspace_stats_cached(workspace_id: str):
    """
    Get workspace statistics with aggressive caching.
    
    Target: <100ms for cached queries
    """
    from services.vector_service import vector_service
    from core.cache import Cache
    
    # Check cache
    cache_key = f"workspace_stats:{workspace_id}"
    cached_stats = await Cache.get(cache_key)
    
    if cached_stats:
        return WorkspaceStatsResponse(**cached_stats)
    
    # Get fresh stats
    stats = await vector_service.get_workspace_stats(workspace_id)
    
    response = WorkspaceStatsResponse(
        workspace_id=workspace_id,
        total_documents=0,  # TODO: Add document count
        total_chunks=stats.get('total_chunks', 0),
        storage_used_mb=0.0,  # TODO: Calculate storage
        embedding_model=stats.get('embedding_model', 'default')
    )
    
    # Cache for 1 minute
    await Cache.set(cache_key, response.dict(), ttl=60)
    
    return response


# ============================================================================
# DELETE DOCUMENT (Async Cleanup)
# ============================================================================

@router.delete("/document/{workspace_id}/{document_id}")
async def delete_document_async(
    workspace_id: str,
    document_id: str,
    background_tasks: BackgroundTasks = None
):
    """
    Delete document with async cleanup.
    
    Returns immediately while deletion happens in background.
    """
    from services.vector_service import vector_service
    
    if background_tasks:
        background_tasks.add_task(
            vector_service.delete_document,
            workspace_id=workspace_id,
            document_id=document_id
        )
        return {"status": "deleting", "document_id": document_id}
    else:
        success = await vector_service.delete_document(workspace_id, document_id)
        return {"status": "deleted" if success else "failed", "document_id": document_id}


# ============================================================================
# LIST DOCUMENTS (Paginated)
# ============================================================================

@router.get("/workspace/{workspace_id}/documents")
async def list_workspace_documents(
    workspace_id: str,
    page: int = 1,
    page_size: int = 20,
    filter_source: Optional[str] = None
):
    """
    List documents with pagination for performance.
    
    Returns metadata only, not full content.
    """
    # TODO: Implement document listing from vector DB metadata
    # This will require storing document metadata separately
    
    return {
        "workspace_id": workspace_id,
        "page": page,
        "page_size": page_size,
        "documents": [],
        "total": 0
    }
