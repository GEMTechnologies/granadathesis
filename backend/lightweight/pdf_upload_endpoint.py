"""
PDF Upload Endpoint - Add to api.py

Insert this after the existing sources endpoints (around line 1312)
"""

@app.post("/api/workspace/{workspace_id}/upload-pdfs")
async def upload_pdfs(
    workspace_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple PDFs and extract metadata.
    Supports bulk upload of 100+ PDFs.
    """
    try:
        from services.sources_service import sources_service
        from services.pdf_metadata_extractor import pdf_metadata_extractor
        import tempfile
        import shutil
        
        results = []
        errors = []
        
        print(f"📚 Uploading {len(files)} PDFs to workspace {workspace_id}")
        
        for i, file in enumerate(files):
            try:
                # Validate file type
                if not file.filename.lower().endswith('.pdf'):
                    errors.append({
                        "filename": file.filename,
                        "error": "Not a PDF file"
                    })
                    continue
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    shutil.copyfileobj(file.file, temp_file)
                    temp_path = Path(temp_file.name)
                
                # Extract metadata
                print(f"  [{i+1}/{len(files)}] Extracting: {file.filename}")
                metadata = pdf_metadata_extractor.extract_metadata(temp_path)
                
                # Add to sources
                source = await sources_service.add_pdf_source(
                    workspace_id=workspace_id,
                    pdf_path=temp_path,
                    metadata=metadata
                )
                
                # Clean up temp file
                temp_path.unlink()
                
                results.append({
                    "filename": file.filename,
                    "source_id": source["id"],
                    "title": source["title"],
                    "authors": source["authors"],
                    "year": source["year"],
                    "citation_key": source["citation_key"],
                    "status": "success"
                })
                
                print(f"    ✓ {source['title'][:50]}")
                
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return {
            "workspace_id": workspace_id,
            "total_uploaded": len(files),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
