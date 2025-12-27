"""
Sources Service - Unified Academic Sources Management

Features:
- Index and track all sources in workspace
- Download and store PDFs
- Extract text for LLM access
- Generate BibTeX citations
- Provide context for AI writing/research
"""
import uuid
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from services.workspace_service import WORKSPACES_DIR
from services.pdf_service import get_pdf_service


class SourcesService:
    """Manage academic sources within workspaces."""
    
    def __init__(self):
        self.pdf_service = get_pdf_service()
    
    def _get_sources_dir(self, workspace_id: str) -> Path:
        """Get the sources directory for a workspace."""
        sources_dir = WORKSPACES_DIR / workspace_id / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        return sources_dir
    
    def _get_index_path(self, workspace_id: str) -> Path:
        """Get the path to the sources index file."""
        return self._get_sources_dir(workspace_id) / "index.json"
    
    def _load_index(self, workspace_id: str) -> Dict:
        """Load the sources index, creating if needed."""
        index_path = self._get_index_path(workspace_id)
        
        if index_path.exists():
            try:
                return json.loads(index_path.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"⚠️ Error loading sources index: {e}")
        
        # Create new index
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sources": []
        }
    
    def _save_index(self, workspace_id: str, index: Dict):
        """Save the sources index."""
        index["updated_at"] = datetime.now().isoformat()
        index_path = self._get_index_path(workspace_id)
        index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def _generate_citation_key(self, source: Dict) -> str:
        """Generate a BibTeX citation key."""
        authors = source.get("authors", [])
        year = source.get("year", datetime.now().year)
        title = source.get("title", "unknown")
        
        # Get first author's last name
        first_author = "unknown"
        if authors:
            first_author_full = authors[0] if isinstance(authors[0], str) else authors[0].get("name", "unknown")
            # Extract last name
            parts = first_author_full.split()
            first_author = parts[-1] if parts else "unknown"
        
        # First significant word from title
        title_word = ""
        for word in title.split():
            if len(word) > 3 and word.lower() not in ["the", "and", "for", "with", "from"]:
                title_word = word.lower()[:10]
                break
        
        return f"{first_author.lower()}{year}{title_word}"
    
    async def add_source(
        self,
        workspace_id: str,
        source_data: Dict,
        download_pdf: bool = True,
        extract_text: bool = True
    ) -> Dict:
        """
        Add a source to the workspace.
        
        Args:
            workspace_id: Workspace ID
            source_data: Source metadata (title, authors, year, url, doi, etc.)
            download_pdf: Whether to download PDF if available
            extract_text: Whether to extract text from PDF
            
        Returns:
            Added source with generated fields
        """
        sources_dir = self._get_sources_dir(workspace_id)
        index = self._load_index(workspace_id)
        
        # Check for duplicates by DOI or title
        doi = source_data.get("doi", "")
        title = source_data.get("title", "")
        
        for existing in index["sources"]:
            if doi and existing.get("doi") == doi:
                print(f"⚠️ Source already exists (DOI match): {title[:50]}")
                return existing
            if title and existing.get("title", "").lower() == title.lower():
                print(f"⚠️ Source already exists (title match): {title[:50]}")
                return existing
        
        # Create source entry
        source_id = str(uuid.uuid4())[:8]
        source = {
            "id": source_id,
            "title": source_data.get("title", "Unknown Title"),
            "authors": source_data.get("authors", []),
            "year": source_data.get("year", datetime.now().year),
            "type": source_data.get("type", "paper"),
            "doi": doi,
            "url": source_data.get("url", ""),
            "abstract": source_data.get("abstract", ""),
            "venue": source_data.get("venue", ""),
            "citation_count": source_data.get("citation_count", 0),
            "added_at": datetime.now().isoformat(),
            "file_path": None,
            "text_extracted": False,
            "text_file": None,
        }
        
        # Generate citation key
        source["citation_key"] = self._generate_citation_key(source)
        
        # Download PDF if available
        pdf_url = source_data.get("pdf_url") or source_data.get("openAccessPdf", {}).get("url")
        if download_pdf and pdf_url:
            try:
                print(f"📥 Downloading PDF: {source['title'][:50]}...")
                
                # Create pdfs subdirectory
                pdfs_dir = sources_dir / "pdfs"
                pdfs_dir.mkdir(exist_ok=True)
                
                # Download
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(pdf_url, follow_redirects=True)
                    if response.status_code == 200 and 'pdf' in response.headers.get('content-type', '').lower():
                        # Save PDF
                        safe_filename = "".join(c for c in source['title'][:50] if c.isalnum() or c in ' -_').strip()
                        pdf_path = pdfs_dir / f"{safe_filename}.pdf"
                        pdf_path.write_bytes(response.content)
                        source["file_path"] = f"pdfs/{safe_filename}.pdf"
                        print(f"   ✓ PDF saved: {source['file_path']}")
                        
                        # Extract text
                        if extract_text:
                            try:
                                text = self.pdf_service.extract_text_simple(pdf_path)
                                if text and len(text) > 100:
                                    # Save extracted text
                                    extracted_dir = sources_dir / "extracted"
                                    extracted_dir.mkdir(exist_ok=True)
                                    text_path = extracted_dir / f"{safe_filename}.txt"
                                    text_path.write_text(text, encoding='utf-8')
                                    source["text_extracted"] = True
                                    source["text_file"] = f"extracted/{safe_filename}.txt"
                                    print(f"   ✓ Text extracted: {len(text)} chars")
                            except Exception as e:
                                print(f"   ⚠️ Text extraction failed: {e}")
            except Exception as e:
                print(f"   ⚠️ PDF download failed: {e}")
        
        # Add to index
        index["sources"].append(source)
        self._save_index(workspace_id, index)
        
        # Update BibTeX
        await self._update_bibtex(workspace_id, source)
        
        print(f"✅ Added source: {source['title'][:50]}")
        return source
    
    async def _update_bibtex(self, workspace_id: str, source: Dict):
        """Add source to references.bib file."""
        bib_path = WORKSPACES_DIR / workspace_id / "references.bib"
        
        # Format authors for BibTeX
        authors = source.get("authors", [])
        if authors:
            if isinstance(authors[0], dict):
                author_str = " and ".join([a.get("name", "") for a in authors if a.get("name")])
            else:
                author_str = " and ".join([a for a in authors if a])
        else:
            author_str = ""
        
        # Skip if no valid author
        if not author_str or author_str.lower() == "unknown":
            return
        
        # Create BibTeX entry
        entry_type = "article" if source.get("type") == "paper" else "misc"
        bib_entry = f"""
@{entry_type}{{{source['citation_key']},
  author = {{{author_str}}},
  title = {{{source['title']}}},
  year = {{{source['year']}}},
  doi = {{{source.get('doi', '')}}},
  url = {{{source.get('url', '')}}},
}}

"""
        
        # Append to bib file
        with open(bib_path, 'a', encoding='utf-8') as f:
            f.write(bib_entry)
    
    def list_sources(self, workspace_id: str) -> List[Dict]:
        """List all sources in a workspace."""
        index = self._load_index(workspace_id)
        return index.get("sources", [])
    
    def get_source(self, workspace_id: str, source_id: str) -> Optional[Dict]:
        """Get a specific source by ID."""
        sources = self.list_sources(workspace_id)
        for source in sources:
            if source.get("id") == source_id:
                return source
        return None
    
    def get_source_text(self, workspace_id: str, source_id: str) -> Optional[str]:
        """Get extracted text content from a source."""
        source = self.get_source(workspace_id, source_id)
        if not source:
            return None
        
        text_file = source.get("text_file")
        if not text_file:
            return None
        
        text_path = self._get_sources_dir(workspace_id) / text_file
        if text_path.exists():
            return text_path.read_text(encoding='utf-8')
        
        return None
    
    def get_sources_context(self, workspace_id: str, max_sources: int = 5) -> str:
        """
        Get sources as context for LLM.
        
        Returns a formatted string with source summaries for AI context.
        """
        sources = self.list_sources(workspace_id)
        
        if not sources:
            return "No sources available in this workspace."
        
        # Sort by citation count (most cited first)
        sorted_sources = sorted(sources, key=lambda x: x.get("citation_count", 0), reverse=True)
        
        context_parts = ["## Available Sources\n"]
        
        for i, source in enumerate(sorted_sources[:max_sources]):
            authors = source.get("authors", [])
            if authors:
                if isinstance(authors[0], dict):
                    author_str = ", ".join([a.get("name", "")[:20] for a in authors[:3] if a.get("name")])
                else:
                    author_str = ", ".join([a[:20] for a in authors[:3] if a])
                if len(authors) > 3:
                    author_str += " et al."
            else:
                author_str = ""
            
            # Skip sources without valid authors
            if not author_str:
                continue
            
            context_parts.append(f"""
### [{source['citation_key']}] {source['title'][:80]}
- **Authors**: {author_str}
- **Year**: {source.get('year', 'N/A')}
- **Venue**: {source.get('venue', 'N/A')}
- **Citations**: {source.get('citation_count', 0)}
- **Abstract**: {source.get('abstract', 'N/A')[:300]}...
""")
        
        if len(sources) > max_sources:
            context_parts.append(f"\n*...and {len(sources) - max_sources} more sources*")
        
        return "\n".join(context_parts)
    
    async def search_and_save(
        self,
        workspace_id: str,
        query: str,
        max_results: int = 5,
        auto_save: bool = True  # Default to auto-save, user can set to False for manual
    ) -> Dict:
        """
        Search for academic sources and optionally save them.
        
        Args:
            workspace_id: Workspace ID
            query: Search query
            max_results: Max results to return
            auto_save: If True, automatically save all results
            
        Returns:
            Dict with search results and saved sources
        """
        from services.academic_search import academic_search_service
        
        print(f"🔍 Searching: {query}")
        
        # Search academic papers
        papers = await academic_search_service.search_academic_papers(
            query=query,
            max_results=max_results
        )
        
        saved = []
        results = []
        
        for paper in papers:
            # Format paper data
            open_access_pdf = paper.get("openAccessPdf") or {}
            external_ids = paper.get("externalIds") or {}
            source_data = {
                "title": paper.get("title", "Unknown"),
                "authors": paper.get("authors", []),
                "year": paper.get("year", datetime.now().year),
                "type": "paper",
                "doi": external_ids.get("DOI", ""),
                "url": paper.get("url", ""),
                "abstract": paper.get("abstract", ""),
                "venue": paper.get("venue", ""),
                "citation_count": paper.get("citationCount", 0),
                "pdf_url": open_access_pdf.get("url", ""),
            }
            
            results.append(source_data)
            
            if auto_save:
                saved_source = await self.add_source(workspace_id, source_data)
                saved.append(saved_source)
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results,
            "saved": saved,
            "saved_count": len(saved)
        }
    
    def delete_source(self, workspace_id: str, source_id: str) -> bool:
        """Delete a source from the workspace."""
        index = self._load_index(workspace_id)
        sources_dir = self._get_sources_dir(workspace_id)
        
        for i, source in enumerate(index["sources"]):
            if source.get("id") == source_id:
                # Delete files
                if source.get("file_path"):
                    pdf_path = sources_dir / source["file_path"]
                    if pdf_path.exists():
                        pdf_path.unlink()
                
                if source.get("text_file"):
                    text_path = sources_dir / source["text_file"]
                    if text_path.exists():
                        text_path.unlink()
                
                # Remove from index
                del index["sources"][i]
                self._save_index(workspace_id, index)
                print(f"🗑️ Deleted source: {source.get('title', source_id)[:50]}")
                return True
        
        return False


# Singleton instance
sources_service = SourcesService()
