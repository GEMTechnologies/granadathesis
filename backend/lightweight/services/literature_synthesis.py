"""
Literature Synthesis Service

Reads all collected sources (PDFs, abstracts, texts, JSONs) and generates
a well-cited synthesized report using chunked LLM processing.

Features:
- Gathers all workspace sources
- Extracts and chunks text content
- Synthesizes across sources with citations
- Streams output in real-time
- Generates BibTeX references
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from services.sources_service import sources_service
from services.pdf_service import PDFService
from services.deepseek_direct import deepseek_direct_service


class LiteratureSynthesisService:
    """
    Synthesize literature from collected sources into a well-cited report.
    """
    
    def __init__(self):
        self.llm = deepseek_direct_service
        self.pdf_service = PDFService()
        self.max_chunk_size = 12000  # chars per chunk for LLM context
        self.max_sources_per_synthesis = 20  # Max sources to process at once
    
    async def stream_generate(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        """Wrapper to stream LLM generation as async generator."""
        import httpx
        from core.config import settings
        
        if not self.llm.api_key:
            yield "Error: DeepSeek API key not configured"
            return
        
        headers = {
            "Authorization": f"Bearer {self.llm.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system or "You are a helpful academic assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 16000,
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.llm.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if line.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(line)
                            if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"\n\nError during generation: {e}"
    
    async def gather_source_content(
        self,
        workspace_id: str,
        source_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Gather all source content from workspace.
        
        Args:
            workspace_id: Workspace ID
            source_types: Filter by types ['pdf', 'abstract', 'text', 'json']
        
        Returns:
            List of source objects with extracted content
        """
        from services.workspace_service import WORKSPACES_DIR
        
        sources = []
        sources_dir = WORKSPACES_DIR / workspace_id / "sources"
        
        # 1. Load indexed sources from sources_service
        indexed_sources = sources_service.list_sources(workspace_id)
        print(f"📚 Found {len(indexed_sources)} indexed sources")
        
        for source in indexed_sources[:self.max_sources_per_synthesis]:
            content = ""
            source_type = "unknown"
            
            # Get abstract if available
            if source.get('abstract'):
                content = source['abstract']
                source_type = "abstract"
            
            # Try to get full text if PDF exists
            # Note: sources_service saves path as 'file_path', not 'pdf_path'
            pdf_file = source.get('file_path') or source.get('pdf_path')
            if pdf_file:
                from services.workspace_service import WORKSPACES_DIR
                pdf_path = sources_dir / pdf_file
                if pdf_path.exists():
                    try:
                        text = await self.pdf_service.extract_text(str(pdf_path))
                        if text and len(text) > len(content):
                            content = text
                            source_type = "pdf"
                    except Exception as e:
                        print(f"  ⚠️ Could not extract PDF: {e}")
            
            # Try text file
            text_path = sources_dir / f"{source.get('id', '')}.txt"
            if text_path.exists():
                try:
                    text = text_path.read_text(encoding='utf-8')
                    if len(text) > len(content):
                        content = text
                        source_type = "text"
                except:
                    pass
            
            if content:
                sources.append({
                    "id": source.get('id', ''),
                    "title": source.get('title', 'Untitled'),
                    "authors": source.get('authors', []),
                    "year": source.get('year'),
                    "citation_key": source.get('citation_key', f"source_{len(sources)+1}"),
                    "content": content,
                    "source_type": source_type,
                    "doi": source.get('doi'),
                    "url": source.get('url'),
                    "pdf_path": source.get('file_path'),  # Keep for reference linking
                })
        
        # 2. Also check for standalone PDFs
        if sources_dir.exists():
            for pdf_file in sources_dir.glob("*.pdf"):
                # Skip if already indexed
                if any(s.get('pdf_path', '').endswith(pdf_file.name) for s in sources):
                    continue
                
                try:
                    text = await self.pdf_service.extract_text(str(pdf_file))
                    if text:
                        sources.append({
                            "id": pdf_file.stem,
                            "title": pdf_file.stem.replace('_', ' ').title(),
                            "authors": [],
                            "year": None,
                            "citation_key": f"pdf_{len(sources)+1}",
                            "content": text,
                            "source_type": "pdf",
                        })
                except:
                    pass
        
        # 3. Check for JSON data files
        data_dir = WORKSPACES_DIR / workspace_id / "data"
        if data_dir.exists():
            for json_file in data_dir.glob("*.json"):
                if json_file.name.startswith('job'):  # Skip job files
                    continue
                try:
                    data = json.loads(json_file.read_text(encoding='utf-8'))
                    # Convert JSON to readable text
                    content = json.dumps(data, indent=2)
                    sources.append({
                        "id": json_file.stem,
                        "title": f"Data: {json_file.stem}",
                        "authors": [],
                        "year": None,
                        "citation_key": f"data_{len(sources)+1}",
                        "content": content[:self.max_chunk_size],
                        "source_type": "json",
                    })
                except:
                    pass
        
        print(f"📖 Gathered {len(sources)} sources with content")
        return sources
    
    def chunk_sources(
        self,
        sources: List[Dict[str, Any]],
        max_chunk_size: int = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Group sources into chunks that fit within LLM context.
        """
        max_chunk_size = max_chunk_size or self.max_chunk_size
        chunks = []
        current_chunk = []
        current_size = 0
        
        for source in sources:
            content_size = len(source.get('content', ''))
            
            # If single source exceeds limit, truncate it
            if content_size > max_chunk_size:
                source = source.copy()
                source['content'] = source['content'][:max_chunk_size]
                content_size = max_chunk_size
            
            # Start new chunk if needed
            if current_size + content_size > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            
            current_chunk.append(source)
            current_size += content_size
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def format_sources_for_llm(self, sources: List[Dict[str, Any]]) -> str:
        """Format sources for LLM consumption."""
        formatted = []
        
        for source in sources:
            authors = source.get('authors', [])
            if authors:
                if isinstance(authors[0], dict):
                    author_str = ", ".join([a.get('name', '') for a in authors[:3] if a.get('name')])
                else:
                    author_str = ", ".join([a for a in authors[:3] if a])
                if len(authors) > 3:
                    author_str += " et al."
            else:
                author_str = ""
            
            # Skip sources without valid authors
            if not author_str or author_str.lower() == 'unknown':
                continue
            
            year = source.get('year', 'n.d.')
            citation_key = source.get('citation_key', '')
            
            formatted.append(f"""
### [{citation_key}] {source.get('title', 'Untitled')}
**Authors:** {author_str} ({year})
**Type:** {source.get('source_type', 'unknown')}

{source.get('content', '')[:8000]}

---""")
        
        return "\n".join(formatted)
    
    async def synthesize_chunk(
        self,
        sources: List[Dict[str, Any]],
        topic: str,
        synthesis_type: str = "comprehensive"
    ) -> AsyncGenerator[str, None]:
        """
        Synthesize a chunk of sources into a coherent narrative.
        
        Yields chunks of generated text for streaming.
        """
        sources_text = self.format_sources_for_llm(sources)
        
        # Create citation reference for prompt with proper author-year format
        # Include DOI/URL so LLM can create hyperlinked citations
        citation_refs = []
        for s in sources:
            key = s.get('citation_key', 'unknown')
            authors = s.get('authors', [])
            if authors:
                first_author = authors[0].get('name', authors[0]) if isinstance(authors[0], dict) else authors[0]
                # Get last name only - skip if no valid author
                first_author = first_author.split()[-1] if first_author else ''
                if not first_author:
                    continue
                # Handle multiple authors
                if len(authors) == 2:
                    second = authors[1].get('name', authors[1]) if isinstance(authors[1], dict) else authors[1]
                    second = second.split()[-1] if second else ''
                    author_cite = f"{first_author} & {second}" if second else first_author
                elif len(authors) > 2:
                    author_cite = f"{first_author} et al."
                else:
                    author_cite = first_author
            else:
                author_cite = ''
            
            # Skip sources without valid authors
            if not author_cite or author_cite.lower() == 'unknown':
                continue
                
            year = s.get('year', 'n.d.')
            
            # Build citation with link info for proper hyperlinking
            doi = s.get('doi', '')
            url = s.get('url', '')
            link_url = f"https://doi.org/{doi}" if doi else (url or f"#ref-{key}")
            
            citation_refs.append(f"- **{author_cite} ({year})** [cite: [{author_cite}, {year}]({link_url})]: {s.get('title', '')[:60]}")
        
        citation_guide = "\n".join(citation_refs)
        
        prompt = f"""You are writing a LITERATURE SYNTHESIS (not a summary) on the topic: "{topic}"

## Available Sources - Citation key and DOI/URL link provided:
{citation_guide}

## Source Content:
{sources_text}

## CRITICAL INSTRUCTIONS:

### Citation Format (REQUIRED - USE HYPERLINKS):
- Use markdown links for citations: [Author, Year](https://doi.org/DOI) or [Author, Year](#ref-key)
- Single author: [Smith, 2020](link) or Smith ([2020](link)) found that...
- Two authors: [Smith & Jones, 2020](link)
- Three+ authors: [Smith et al., 2020](link)
- Multiple citations: ([Smith, 2020](link); [Jones, 2021](link))

The citation guide above shows the exact link to use for each author - USE THOSE LINKS!

### Synthesis Writing Style:
1. **SYNTHESIZE, don't summarize** - Compare/contrast findings ACROSS sources
2. **Every claim needs a citation with hyperlink** - No unsupported statements
3. Use phrases like:
   - "Several studies have found that... ([Author1, Year](link); [Author2, Year](link))"
   - "While [Author1 (Year)](link) argues X, [Author2 (Year)](link) contends Y"
4. **Organize thematically** - Group by concepts, not by individual papers
5. **Identify patterns** - Where do researchers agree/disagree?

### Structure:
- Use clear headings for themes
- Flow logically from one idea to the next
- Build coherent arguments supported by multiple sources

Write 1000-1500 words of scholarly synthesis with HYPERLINKED citations."""

        system = """You are an expert academic writer specializing in systematic literature reviews. 

CRITICAL RULES:
1. ALWAYS use in-text citations in format: (LastName, Year) or (Author1 & Author2, Year) or (Author1 et al., Year)
2. NEVER summarize sources one-by-one - SYNTHESIZE across sources
3. Group related findings from different authors together
4. Every factual claim must have a citation
5. Use academic language and formal tone
6. Identify themes, patterns, agreements and disagreements in the literature"""

        async for chunk in self.stream_generate(prompt, system=system):
            yield chunk
    
    async def synthesize_literature(
        self,
        workspace_id: str,
        topic: str,
        output_format: str = "markdown",
        job_manager: Optional[Any] = None,
        job_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Main synthesis pipeline - gathers sources, chunks, and synthesizes.
        
        Args:
            workspace_id: Workspace to read sources from
            topic: Research topic/focus for synthesis
            output_format: 'markdown' or 'docx'
            job_manager: Optional job manager for progress updates
            job_id: Optional job ID for progress tracking
        
        Yields:
            Chunks of synthesized text
        """
        # Log progress
        async def log(msg: str):
            print(f"  {msg}")
            if job_manager and job_id:
                await job_manager.emit_log(job_id, msg)
        
        async def update_progress(progress: float, step: str):
            if job_manager and job_id:
                await job_manager.update_progress(
                    job_manager.get_job(workspace_id, job_id),
                    progress,
                    step
                )
        
        # Step 1: Gather sources
        await log("📚 Gathering sources from workspace...")
        await update_progress(0.1, "Gathering sources...")
        
        sources = await self.gather_source_content(workspace_id)
        
        if not sources:
            yield "## No Sources Found\n\nNo sources were found in this workspace. Please add some papers or documents first using the search feature.\n"
            return
        
        await log(f"📖 Found {len(sources)} sources")
        
        # Step 2: Chunk sources
        chunks = self.chunk_sources(sources)
        await log(f"📦 Organized into {len(chunks)} chunks for processing")
        
        # Step 3: Generate header
        yield f"""# Literature Synthesis: {topic}

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Based on {len(sources)} sources*

---

"""
        
        # Step 4: Process each chunk
        chunk_syntheses = []
        
        for i, chunk in enumerate(chunks):
            chunk_num = i + 1
            progress = 0.2 + (0.6 * (i / len(chunks)))
            
            await log(f"🔍 Processing chunk {chunk_num}/{len(chunks)} ({len(chunk)} sources)...")
            await update_progress(progress, f"Synthesizing chunk {chunk_num}/{len(chunks)}...")
            
            if len(chunks) > 1:
                yield f"\n## Section {chunk_num}\n\n"
            
            synthesis = ""
            async for text in self.synthesize_chunk(chunk, topic):
                synthesis += text
                yield text
            
            chunk_syntheses.append(synthesis)
            yield "\n\n"
        
        # Step 5: Generate conclusion if multiple chunks
        if len(chunks) > 1:
            await log("📝 Generating synthesis conclusion...")
            await update_progress(0.85, "Generating conclusion...")
            
            yield "\n## Conclusion\n\n"
            
            conclusion_prompt = f"""Based on the following section syntheses about "{topic}", write a brief conclusion that:
1. Summarizes the key findings across all sections
2. Identifies the main gaps in the literature
3. Suggests directions for future research

Sections:
{chr(10).join([f'Section {i+1}: {s[:500]}...' for i, s in enumerate(chunk_syntheses)])}

Keep the conclusion to 200-300 words."""

            async for chunk in self.stream_generate(conclusion_prompt):
                yield chunk
        
        # Step 6: Generate references with hyperlinks
        await log("📋 Generating references with hyperlinks...")
        await update_progress(0.95, "Generating references...")
        
        yield "\n\n---\n\n## References\n\n"
        
        for source in sorted(sources, key=lambda x: x.get('citation_key', '')):
            citation_key = source.get('citation_key', '')
            authors = source.get('authors', [])
            if authors:
                if isinstance(authors[0], dict):
                    author_str = ", ".join([a.get('name', '') for a in authors if a.get('name')])
                else:
                    author_str = ", ".join([a for a in authors if a])
            else:
                author_str = ""
            
            # Skip sources without valid authors
            if not author_str or author_str.lower() == 'unknown':
                continue
            
            year = source.get('year', 'n.d.')
            title = source.get('title', 'Untitled')
            doi = source.get('doi', '')
            url = source.get('url', '')
            pdf_path = source.get('pdf_path', '')
            
            # Create anchor ID for this reference (for internal linking)
            anchor_id = f"ref-{citation_key}"
            
            # Build reference with anchor and hyperlinks
            ref = f'<a id="{anchor_id}"></a>\n'
            ref += f"**[{citation_key}]** {author_str} ({year}). "
            
            # Make title a clickable link if we have DOI or URL
            if doi:
                ref += f"[*{title}*](https://doi.org/{doi})"
            elif url:
                ref += f"[*{title}*]({url})"
            elif pdf_path:
                ref += f"*{title}* [📄 PDF]({pdf_path})"
            else:
                ref += f"*{title}*"
            
            ref += "."
            
            yield f"{ref}\n\n"
        
        await log("✅ Synthesis complete!")
        await update_progress(1.0, "Complete")
    
    def post_process_citations(self, content: str, sources: List[Dict]) -> str:
        """
        Post-process synthesis content to add hyperlinks to citations.
        
        Converts (Author, Year) citations to clickable links that jump to references.
        """
        import re
        
        # Build mapping of author patterns to citation keys
        author_patterns = {}
        for source in sources:
            citation_key = source.get('citation_key', 'unknown')
            authors = source.get('authors', [])
            year = source.get('year', '')
            
            if authors and year:
                first_author = authors[0].get('name', authors[0]) if isinstance(authors[0], dict) else authors[0]
                last_name = first_author.split()[-1] if first_author else ''
                
                if len(authors) == 1:
                    pattern = f"{last_name}, {year}"
                    author_patterns[pattern] = citation_key
                elif len(authors) == 2:
                    second = authors[1].get('name', authors[1]) if isinstance(authors[1], dict) else authors[1]
                    second_last = second.split()[-1] if second else ''
                    pattern = f"{last_name} & {second_last}, {year}"
                    author_patterns[pattern] = citation_key
                    pattern = f"{last_name} and {second_last}, {year}"
                    author_patterns[pattern] = citation_key
                else:
                    pattern = f"{last_name} et al., {year}"
                    author_patterns[pattern] = citation_key
        
        # Replace citations with hyperlinks
        for pattern, key in author_patterns.items():
            # Match (Author, Year) or (Author et al., Year)
            content = content.replace(
                f"({pattern})",
                f"([{pattern}](#ref-{key}))"
            )
            # Match Author (Year) format
            parts = pattern.rsplit(", ", 1)
            if len(parts) == 2:
                auth, yr = parts
                content = content.replace(
                    f"{auth} ({yr})",
                    f"[{auth}](#ref-{key}) ({yr})"
                )
        
        return content


# Singleton instance
literature_synthesis_service = LiteratureSynthesisService()
