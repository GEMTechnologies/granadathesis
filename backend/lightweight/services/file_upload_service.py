"""
File Upload Service - Handle file uploads and reference management

Features:
- Accept any file type (PDF, Excel, CSV, images, DOCX)
- Store in workspace/uploads/
- Extract text/content for AI reference
- Track uploaded files per session

Dependencies: python-magic (optional), pandas, PyPDF2
"""

import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

# PDF handling
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Spreadsheet handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

# DOCX handling
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class FileUploadService:
    """Service for handling file uploads and content extraction."""
    
    SUPPORTED_EXTENSIONS = {
        'documents': ['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'],
        'spreadsheets': ['.xlsx', '.xls', '.csv', '.tsv'],
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
        'data': ['.json', '.xml', '.yaml', '.yml'],
        'code': ['.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c']
    }
    
    def __init__(self, workspace_dir: str = "workspaces"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Track uploaded files per session
        self._session_files: Dict[str, List[Dict]] = {}
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type category."""
        ext = Path(filename).suffix.lower()
        for category, extensions in self.SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return category
        return "other"
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute file hash for deduplication."""
        return hashlib.md5(content).hexdigest()[:12]
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        workspace_id: str = "default",
        session_id: str = "default",
        extract_content: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a file to the workspace.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            workspace_id: Workspace to store in
            session_id: Session ID for tracking
            extract_content: Whether to extract text content
            
        Returns:
            {
                "success": True,
                "path": "workspace/uploads/filename.pdf",
                "file_type": "documents",
                "content_extracted": True,
                "content_preview": "First 500 chars...",
                "metadata": {...}
            }
        """
        try:
            # Create upload directory
            upload_dir = self.workspace_dir / workspace_id / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename if exists
            file_path = upload_dir / filename
            if file_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while file_path.exists():
                    file_path = upload_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            # Save file
            file_path.write_bytes(file_content)
            
            # Determine file type
            file_type = self._get_file_type(filename)
            
            # Extract content if requested
            content = ""
            content_preview = ""
            if extract_content:
                content = await self._extract_content(file_path, file_type)
                if content:
                    content_preview = content[:500] + "..." if len(content) > 500 else content
            
            # Build metadata
            metadata = {
                "original_filename": filename,
                "saved_filename": file_path.name,
                "file_size": len(file_content),
                "file_type": file_type,
                "extension": file_path.suffix.lower(),
                "uploaded_at": datetime.now().isoformat(),
                "file_hash": self._compute_hash(file_content),
                "workspace_id": workspace_id,
                "session_id": session_id
            }
            
            # Track in session
            if session_id not in self._session_files:
                self._session_files[session_id] = []
            self._session_files[session_id].append({
                "path": str(file_path),
                "filename": filename,
                "type": file_type,
                "content_length": len(content)
            })
            
            # Save content for AI reference
            if content:
                content_path = file_path.with_suffix('.extracted.txt')
                content_path.write_text(content)
                metadata["content_path"] = str(content_path)
                metadata["content_length"] = len(content)
            
            return {
                "success": True,
                "path": str(file_path),
                "relative_path": f"{workspace_id}/uploads/{file_path.name}",
                "file_type": file_type,
                "content_extracted": bool(content),
                "content_preview": content_preview,
                "metadata": metadata
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def _extract_content(self, file_path: Path, file_type: str) -> str:
        """Extract text content from file."""
        try:
            suffix = file_path.suffix.lower()
            
            # PDF
            if suffix == '.pdf' and PYPDF2_AVAILABLE:
                reader = PdfReader(str(file_path))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
                return text.strip()
            
            # Plain text
            elif suffix in ['.txt', '.md', '.rtf', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
                return file_path.read_text(errors='ignore')
            
            # DOCX
            elif suffix == '.docx' and DOCX_AVAILABLE:
                doc = DocxDocument(str(file_path))
                return "\n".join([para.text for para in doc.paragraphs])
            
            # Spreadsheets
            elif suffix in ['.xlsx', '.xls', '.csv'] and PANDAS_AVAILABLE:
                if suffix == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                return f"Columns: {list(df.columns)}\n\nFirst 10 rows:\n{df.head(10).to_string()}"
            
            return ""
            
        except Exception as e:
            print(f"Content extraction error: {e}")
            return ""
    
    def get_session_files(self, session_id: str) -> List[Dict]:
        """Get all files uploaded in a session."""
        return self._session_files.get(session_id, [])
    
    def get_file_content(self, file_path: Union[str, Path]) -> Optional[str]:
        """Get extracted content for a file."""
        file_path = Path(file_path)
        content_path = file_path.with_suffix('.extracted.txt')
        if content_path.exists():
            return content_path.read_text()
        return None
    
    def list_uploads(self, workspace_id: str) -> List[Dict]:
        """List all uploaded files in a workspace."""
        upload_dir = self.workspace_dir / workspace_id / "uploads"
        if not upload_dir.exists():
            return []
        
        files = []
        for file_path in upload_dir.iterdir():
            if file_path.suffix == '.extracted.txt':
                continue  # Skip extracted content files
            files.append({
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "type": self._get_file_type(file_path.name),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        return files
    
    async def chat_with_file(
        self,
        file_path: Union[str, Path],
        question: str
    ) -> Dict[str, Any]:
        """
        Answer a question based on file content.
        Uses the extracted content for context.
        
        Args:
            file_path: Path to uploaded file
            question: User's question
            
        Returns:
            {"success": True, "answer": "...", "context": "..."}
        """
        content = self.get_file_content(file_path)
        if not content:
            return {"success": False, "error": "No extracted content available"}
        
        # This would integrate with LLM for actual Q&A
        # For now, return context for external processing
        return {
            "success": True,
            "content": content,
            "content_length": len(content),
            "file_path": str(file_path),
            "question": question
        }
    
    def rename_file(self, workspace_id: str, old_path: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file in the workspace.
        
        Args:
            workspace_id: Workspace ID
            old_path: Current relative path (e.g., "uploads/old_name.pdf")
            new_name: New filename (just the name, not path)
            
        Returns:
            {"success": True, "old_path": "...", "new_path": "..."}
        """
        try:
            file_path = self.workspace_dir / workspace_id / old_path
            
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            new_path = file_path.parent / new_name
            
            if new_path.exists():
                return {"success": False, "error": "File with that name already exists"}
            
            # Rename the file
            file_path.rename(new_path)
            
            # Rename extracted content file if exists
            old_content = file_path.with_suffix('.extracted.txt')
            if old_content.exists():
                new_content = new_path.with_suffix('.extracted.txt')
                old_content.rename(new_content)
            
            return {
                "success": True,
                "old_path": str(file_path),
                "new_path": str(new_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_file(self, workspace_id: str, file_path: str) -> Dict[str, Any]:
        """
        Delete a file from the workspace.
        
        Args:
            workspace_id: Workspace ID
            file_path: Relative path to file (e.g., "uploads/file.pdf")
            
        Returns:
            {"success": True, "deleted": "..."}
        """
        try:
            full_path = self.workspace_dir / workspace_id / file_path
            
            if not full_path.exists():
                return {"success": False, "error": "File not found"}
            
            # Delete the file
            full_path.unlink()
            
            # Delete extracted content file if exists
            content_path = full_path.with_suffix('.extracted.txt')
            if content_path.exists():
                content_path.unlink()
            
            return {
                "success": True,
                "deleted": str(file_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_file(self, workspace_id: str, source_path: str, dest_folder: str) -> Dict[str, Any]:
        """
        Move a file to a different folder in the workspace.
        
        Args:
            workspace_id: Workspace ID
            source_path: Current relative path (e.g., "uploads/file.pdf")
            dest_folder: Destination folder (e.g., "sources/pdfs")
            
        Returns:
            {"success": True, "old_path": "...", "new_path": "..."}
        """
        try:
            source = self.workspace_dir / workspace_id / source_path
            
            if not source.exists():
                return {"success": False, "error": "Source file not found"}
            
            # Create destination folder if needed
            dest_dir = self.workspace_dir / workspace_id / dest_folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest = dest_dir / source.name
            
            # Move file
            shutil.move(str(source), str(dest))
            
            # Move extracted content if exists
            source_content = source.with_suffix('.extracted.txt')
            if source_content.exists():
                dest_content = dest.with_suffix('.extracted.txt')
                shutil.move(str(source_content), str(dest_content))
            
            return {
                "success": True,
                "old_path": str(source_path),
                "new_path": f"{dest_folder}/{source.name}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_file(self, workspace_id: str, file_path: str) -> Dict[str, Any]:
        """
        Read file content (extracted text or raw for text files).
        
        Args:
            workspace_id: Workspace ID
            file_path: Relative path to file
            
        Returns:
            {"success": True, "content": "...", "filename": "..."}
        """
        try:
            full_path = self.workspace_dir / workspace_id / file_path
            
            if not full_path.exists():
                return {"success": False, "error": "File not found"}
            
            # Try extracted content first
            content = self.get_file_content(full_path)
            
            # Fall back to raw read for text files
            if not content:
                suffix = full_path.suffix.lower()
                if suffix in ['.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.py', '.js', '.html', '.css']:
                    content = full_path.read_text(errors='ignore')
            
            if content:
                return {
                    "success": True,
                    "content": content,
                    "filename": full_path.name,
                    "size": full_path.stat().st_size
                }
            else:
                return {
                    "success": False,
                    "error": "Cannot read content from this file type",
                    "filename": full_path.name
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_file_upload_service = None

def get_file_upload_service() -> FileUploadService:
    """Get global file upload service instance."""
    global _file_upload_service
    if _file_upload_service is None:
        _file_upload_service = FileUploadService()
    return _file_upload_service
