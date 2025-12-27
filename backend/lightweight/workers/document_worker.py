"""
Document Worker - Background Document Processing

Handles RAG document processing and indexing.
"""

from celery_config import celery_app
from typing import List
import asyncio


@celery_app.task(bind=True, name='document.process_batch')
def process_documents_batch(self, file_paths: List[str], workspace_id: str):
    """
    Process and index multiple documents.
    
    Args:
        file_paths: List of document paths
        workspace_id: Workspace ID
    """
    
    self.update_state(
        state='STARTED',
        meta={'total': len(file_paths), 'completed': 0}
    )
    
    from services.document_upload_service import document_upload_service
    from services.vector_service import vector_service
    
    results = []
    
    for i, file_path in enumerate(file_paths):
        self.update_state(
            state='PROGRESS',
            meta={
                'total': len(file_paths),
                'completed': i,
                'current': file_path
            }
        )
        
        # Extract text
        text = document_upload_service.extract_text(file_path)
        
        # Index in vector DB
        vector_service.add_documents(
            workspace_id=workspace_id,
            documents=[{
                'text': text,
                'metadata': {'source': file_path}
            }]
        )
        
        results.append({'file': file_path, 'indexed': True})
    
    return results
