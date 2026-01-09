"""
Vector Database Service using ChromaDB

Provides document embedding, storage, and semantic search capabilities.
Workspace-scoped collections for multi-tenancy.
"""

import chromadb
import os
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import json

# Storage directory for ChromaDB
VECTOR_DB_DIR = Path(__file__).parent.parent.parent / "chroma_data"
VECTOR_DB_DIR.mkdir(exist_ok=True)


class VectorService:
    """
    Vector database service for semantic search and RAG.
    
    Features:
    - Workspace-scoped collections
    - Automatic embeddings via OpenAI
    - Metadata filtering
    - Semantic similarity search
    """
    
    def __init__(self):
        """Initialize ChromaDB client with persistent storage."""
        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DB_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Use OpenAI embeddings if key is available, else default embeddings.
        openai_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
            try:
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    model_name="text-embedding-3-small"
                )
                print("✓ Vector service using OpenAI embeddings")
            except Exception as e:
                print(f"⚠️ OpenAI embeddings unavailable, using default: {e}")
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        else:
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    def _get_collection_name(self, workspace_id: str) -> str:
        """Get collection name for workspace."""
        # Sanitize workspace_id for collection name
        return f"workspace_{workspace_id.replace('-', '_')}"
    
    def _get_collection(self, workspace_id: str):
        """Get or create collection for workspace."""
        collection_name = self._get_collection_name(workspace_id)
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"workspace_id": workspace_id}
        )
    
    async def add_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: List[str],
        metadata: Dict[str, Any],
        source: str = "user_upload"
    ) -> Dict[str, Any]:
        """
        Add document chunks to vector database.
        
        Args:
            workspace_id: Workspace ID
            document_id: Unique document identifier
            chunks: List of text chunks
            metadata: Document metadata (title, author, etc.)
            source: Source type (user_upload, conversation, thesis, etc.)
        
        Returns:
            Dict with indexed count and document ID
        """
        if not chunks:
            return {"indexed": 0, "document_id": document_id}
        
        collection = self._get_collection(workspace_id)
        
        # Generate unique IDs for each chunk
        chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Prepare metadata for each chunk
        chunk_metadata = [
            {
                **metadata,
                "document_id": document_id,
                "chunk_index": i,
                "source": source,
                "workspace_id": workspace_id
            }
            for i in range(len(chunks))
        ]
        
        # Add to collection (automatic embedding)
        collection.add(
            documents=chunks,
            metadatas=chunk_metadata,
            ids=chunk_ids
        )
        
        print(f"✓ Indexed {len(chunks)} chunks for document {document_id}")
        
        return {
            "indexed": len(chunks),
            "document_id": document_id,
            "chunk_ids": chunk_ids
        }
    
    async def search(
        self,
        workspace_id: str,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Semantic search for relevant document chunks.
        
        Args:
            workspace_id: Workspace ID to search within
            query: Search query (semantic)
            n_results: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"source": "user_upload"})
        
        Returns:
            Dict with documents, metadatas, distances
        """
        try:
            collection = self._get_collection(workspace_id)
            
            # Query collection
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_metadata if filter_metadata else None
            )
            
            # Format results
            formatted_results = {
                "query": query,
                "results": [],
                "count": len(results['documents'][0]) if results['documents'] else 0
            }
            
            # Combine results into structured format
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results['results'].append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0,
                        "id": results['ids'][0][i] if results['ids'] else None
                    })
            
            return formatted_results
        
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return {"query": query, "results": [], "count": 0, "error": str(e)}
    
    async def delete_document(self, workspace_id: str, document_id: str) -> bool:
        """
        Delete all chunks of a document.
        
        Args:
            workspace_id: Workspace ID
            document_id: Document ID to delete
        
        Returns:
            True if successful
        """
        try:
            collection = self._get_collection(workspace_id)
            
            # Delete all chunks with matching document_id metadata
            collection.delete(
                where={"document_id": document_id}
            )
            
            print(f"✓ Deleted document {document_id} from vector DB")
            return True
        
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
    
    async def get_workspace_stats(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get statistics for workspace collection.
        
        Returns:
            Dict with count and metadata
        """
        try:
            collection = self._get_collection(workspace_id)
            count = collection.count()
            
            return {
                "workspace_id": workspace_id,
                "collection_name": self._get_collection_name(workspace_id),
                "total_chunks": count,
                "embedding_model": "text-embedding-3-small" if hasattr(self.embedding_function, 'model_name') else "default"
            }
        
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {"workspace_id": workspace_id, "total_chunks": 0, "error": str(e)}
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Chunk text into overlapping segments.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in tokens (approx)
            overlap: Overlap between chunks in tokens
        
        Returns:
            List of text chunks
        """
        # Simple word-based chunking (TODO: use tiktoken for exact token count)
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += chunk_size - overlap
        
        return chunks


# Singleton instance
vector_service = VectorService()
