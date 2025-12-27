"""
Simple Content Generator for Lightweight System
Generates academic content with citations using DeepSeek API.
Refactored to generate coherent paragraphs via synthesis.
"""

import asyncio
from typing import Dict, List, Any, Optional
from core.events import events
from services.academic_search import academic_search_service
from services.deepseek_client import deepseek_client
from services.content_verifier import content_verifier
from services.web_search import web_search_service
from services.zotero_service import ZoteroService
from core.config import settings
import traceback
import os


class SimpleContentGenerator:
    """Lightweight content generator with DeepSeek API and streaming support."""
    
    def __init__(self):
        """Initialize the content generator."""
        self.deepseek = deepseek_client
        
        # Initialize Zotero Service if configured
        self.zotero = None
        if settings.ZOTERO_API_KEY and (settings.ZOTERO_USER_ID or settings.ZOTERO_GROUP_ID):
            try:
                self.zotero = ZoteroService(
                    api_key=settings.ZOTERO_API_KEY,
                    user_id=settings.ZOTERO_USER_ID,
                    group_id=settings.ZOTERO_GROUP_ID
                )
                print("   📚 Zotero Service initialized")
            except Exception as e:
                print(f"   ⚠️ Zotero initialization failed: {e}")
    
    async def generate_cited_section(
        self,
        section_title: str,
        topic: str,
        case_study: str = "",
        word_count: int = 500,
        job_id: Optional[str] = None,
        thesis_id: str = "default_thesis"
    ) -> Dict[str, Any]:
        """
        Generate a section with citations using DeepSeek API.
        Generates content paragraph-by-paragraph for better flow.
        """
        print(f"\n📝 GENERATING SECTION: {section_title}")
        print(f"   Topic: {topic}")
        print(f"   Target: {word_count} words\n")
        
        # Step 1: Search for papers
        if job_id:
            await events.log(job_id, f"📚 Searching for papers on {topic}...")
        
        papers = await academic_search_service.search_academic_papers(
            query=topic,
            max_results=20,
            job_id=job_id
        )
        
        if not papers:
            if job_id:
                await events.log(job_id, "⚠️ No papers found", "warning")
            return {
                "section_title": section_title,
                "content": "",
                "references": [],
                "error": "No papers found"
            }
        
        if job_id:
            await events.log(job_id, f"✓ Found {len(papers)} papers", "success")
            
        # Step 1.5: Perform Web Research (Pre-writing)
        web_context = ""
        if case_study:
            if job_id:
                await events.log(job_id, f"🌐 Researching current context for {case_study}...")
            
            try:
                from services.unified_research import unified_research_service
                research_result = await unified_research_service.collect_research(
                    topic, 
                    case_study,
                    thesis_id=thesis_id
                )
                
        # Format facts for prompt with metadata
                facts = research_result.get("facts", [])
                web_context = ""
                for i, fact in enumerate(facts):
                    meta = fact.get('raw_meta', {})
                    citation_str = fact.get('citation_meta', 'Unknown Source')
                    web_context += f"[{i+1}] {citation_str}\n    URL: {fact['source']}\n    Content: {fact['text']}\n\n"
                
                if job_id:
                    await events.log(job_id, f"✓ Gathered {len(facts)} verified fact blocks", "success")
            except Exception as e:
                print(f"   ⚠️ Web research failed: {e}")
                if job_id:
                    await events.log(job_id, f"⚠️ Web research failed: {e}", "warning")
        
        # Step 2: Generate content paragraph by paragraph
        if job_id:
            await events.log(job_id, f"✍️ Synthesizing content with DeepSeek...")
        
        # Calculate target paragraphs (approx 150 words per paragraph)
        target_paragraphs = max(2, int(word_count / 150))
        paragraphs = []
        cited_papers = []
        
        # Context for flow
        previous_context = ""
        
        for i in range(target_paragraphs):
            # CHECK JOB STATE
            if job_id:
                state = await self._check_job_state(job_id)
                if state == "stopped":
                    return self._create_stopped_result(section_title, paragraphs, cited_papers)
                elif state == "paused":
                    await self._wait_for_resume(job_id)
            
            # Select papers for this paragraph (3-5 papers)
            # Cycle through papers to ensure coverage
            start_idx = (i * 3) % len(papers)
            paragraph_papers = []
            for j in range(3):
                idx = (start_idx + j) % len(papers)
                paragraph_papers.append(papers[idx])
            
            # Generate paragraph
            try:
                paragraph = await self._generate_paragraph(
                    topic=topic,
                    section_title=section_title,
                    papers=paragraph_papers,
                    web_context=web_context,
                    context=previous_context,
                    is_intro=(i == 0),
                    is_conclusion=(i == target_paragraphs - 1)
                )
                
                paragraphs.append(paragraph)
                previous_context = paragraph[-200:] # Keep last 200 chars as context
                
                # Track cited papers
                for p in paragraph_papers:
                    if p not in cited_papers:
                        cited_papers.append(p)
                
                # EMIT STREAMING EVENT (Chunk is now a paragraph)
                if job_id:
                    await events.publish(job_id, "content_chunk", {
                        "sentence": paragraph + "\n\n", # Add spacing
                        "index": i,
                        "total": target_paragraphs
                    })
                    await events.log(job_id, f"✓ Generated paragraph {i + 1}/{target_paragraphs}")
                
                print(f"   ✓ Generated paragraph {i + 1}/{target_paragraphs}")
                
            except Exception as e:
                print(f"   ⚠️ Error generating paragraph {i}: {str(e)}")
                traceback.print_exc()
                if job_id:
                    await events.log(job_id, f"⚠️ Error in paragraph {i}: {str(e)}", "warning")
        
        content = "\n\n".join(paragraphs)
        
        # Step 3: Generate references
        if job_id:
            await events.log(job_id, f"📚 Formatting {len(cited_papers)} references...")
        
        references = self._format_references(cited_papers)
        
        # Update BibTeX file (and sync to Zotero)
        await self._update_bibtex(cited_papers, thesis_id)
        
        # Step 4: Verify and Correct Content
        # DISABLED: Verification step was destroying content and removing citations
        # TODO: Rebuild verification to preserve citations after sources work properly
        # if job_id:
        #     await events.log(job_id, f"🔍 Verifying content accuracy...")
        #     
        # verification_result = await content_verifier.verify_and_correct(
        #     content=content,
        #     topic=topic,
        #     job_id=job_id
        # )
        # 
        # # Emit correction event if changes were made
        # if verification_result.get("corrections") and job_id:
        #     await events.publish(job_id, "content_corrected", {
        #         "original": content,
        #         "corrected": verification_result["content"],
        #         "corrections": verification_result["corrections"]
        #     })
        # 
        # content = verification_result["content"]
        # verification_report = verification_result.get("verification_report", [])
        # corrections = verification_result.get("corrections", [])
        
        # Return content as-is without destructive verification
        verification_report = []
        corrections = []
        
        # Save section to workspace
        if thesis_id:
            section_path = await self._save_section_to_workspace(
                workspace_id=thesis_id,
                section_title=section_title,
                content=content,
                topic=topic
            )
            if job_id:
                await events.log(job_id, f"💾 Saved to: {section_path}", "success")
        
        if job_id:
            await events.log(job_id, f"✅ Section complete!", "success")
            
        return {
            "section_title": section_title,
            "content": content,
            "references": references,
            "cited_papers": cited_papers,
            "verification_report": verification_report,
            "metrics": {
                "word_count": len(content.split()),
                "paragraph_count": len(paragraphs),
                "citation_count": len(cited_papers),
                "verification_issues": len(corrections)
            }
        }

    async def revise_content(
        self,
        content: str,
        instructions: str,
        thesis_id: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revise existing content while preserving citations.
        """
        if job_id:
            await events.log(job_id, "✍️ Revising content...", "info")

        system_prompt = """You are an academic editor.
STRICT RULES:
1. PRESERVE ALL CITATIONS. Do not remove any (Author, Year) citations.
2. Improve flow, clarity, and academic tone.
3. Incorporate the user's instructions.
4. If you add new claims, you must mark them as [Needs Citation].
5. Output ONLY the revised text."""

        user_prompt = f"""Original Content:
{content}

Instructions:
{instructions}

Revise the content following the instructions. PRESERVE ALL CITATIONS."""

        revised_content = await self.deepseek.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3
        )

        if job_id:
            await events.log(job_id, "✅ Revision complete", "success")

        return {
            "content": revised_content.strip(),
            "status": "completed"
        }
    
    async def _save_section_to_workspace(
        self,
        workspace_id: str,
        section_title: str,
        content: str,
        topic: str
    ) -> str:
        """
        Save section to workspace/sections/ with sanitized filename.
        
        Args:
            workspace_id: Workspace ID
            section_title: Section title
            content: Markdown content
            topic: Research topic
            
        Returns:
            Path to saved file
        """
        from services.workspace_service import WORKSPACES_DIR
        import re
        
        # Sanitize filename components
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', section_title.lower())
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')  # Remove multiple underscores
        
        safe_topic = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower())[:30]
        safe_topic = re.sub(r'_+', '_', safe_topic).strip('_')
        
        # Create unique filename
        filename = f"{safe_title}_{safe_topic}.md"
        filepath = WORKSPACES_DIR / workspace_id / "sections" / filename
        
        # Ensure sections directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        filepath.write_text(content, encoding='utf-8')
        
        print(f"   💾 Saved section to: {filepath.relative_to(WORKSPACES_DIR)}")
        return str(filepath.relative_to(WORKSPACES_DIR))
    
    async def _generate_paragraph(
        self,
        topic: str,
        section_title: str,
        papers: List[Dict[str, Any]],
        web_context: str = "",
        context: str = "",
        is_intro: bool = False,
        is_conclusion: bool = False
    ) -> str:
        """
        Generate a coherent paragraph using verified facts.
        """
        # Build Prompt
        task_type = "Introduction" if is_intro else "Conclusion" if is_conclusion else "Body Paragraph"
        
        system_prompt = """You are generating academic text.

STRICT RULES:
1. SOURCE PRIORITY: 
   - Use ACADEMIC PAPERS for 80% of your claims and arguments.
   - Use VERIFIED FACTS (Web) ONLY for specific statistics, dates, or recent events.
2. CITE EVERY CLAIM using standard academic format: (Author, Year) or (Organization, Year).
3. SYNTHESIZE SOURCES: Whenever possible, cite 2-3 sources for key claims (e.g., "(Smith, 2023; Jones, 2024)").
4. DO NOT use [Source: URL]. Use the metadata provided in the fact block.
5. If the fact is not in the provided facts, respond: "No verified data available."
6. Write ONE sentence at a time. Synthesize facts into a coherent paragraph."""
        
        user_prompt = f"""Topic: {topic}
        Section: {section_title}
        Task: Write a {task_type} (approx 150 words).
        
        Context from previous paragraph: "{context}..."
        
        VERIFIED FACTS & SOURCES (Use ONLY for stats/dates):
        {web_context[:3000]}
        
        ACADEMIC PAPERS (PRIORITIZE THESE for arguments):
        {self._format_paper_summaries(papers)}
        
        Instructions:
        1. Synthesize these verified facts, prioritizing Academic Papers.
        2. Cite sources explicitly using (Author, Year) format.
           Example: "...economic impact (World Bank, 2024)."
           Example: "...according to Smith (2023)..."
        3. Aim for MULTI-CITATION where appropriate: "(Author A, Year; Author B, Year)".
        4. Ensure smooth flow from the previous context.
        5. Output ONLY the paragraph text.
        """
        
        response = await self.deepseek.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=400,
            temperature=0.5 # Lower temperature for fact-based generation
        )
        
        return response.strip()

    def _format_paper_summaries(self, papers: List[Dict]) -> str:
        text = ""
        for p in papers:
            authors = self._get_author_citation(p)
            year = p.get('year', 'n.d.')
            title = p.get('title', 'Unknown')
            abstract = (p.get('abstract') or '')[:300]
            text += f"- {title} ({authors}, {year}): {abstract}\n"
        return text

    def _get_author_citation(self, paper: Dict) -> str:
        """Get author string for citation (e.g., Smith et al.)."""
        authors = paper.get('authors', [])
        if not authors:
            return "Author"
        
        if isinstance(authors[0], dict):
            name = authors[0].get('name', 'Author').split()[-1]
        else:
            name = str(authors[0]).split()[-1]
            
        if len(authors) > 1:
            return f"{name} et al."
        return name

    def _format_references(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Format papers into APA-style references."""
        references = []
        for paper in papers:
            authors = paper.get('authors', [])
            year = paper.get('year', 'n.d.')
            title = paper.get('title', 'Unknown')
            venue = paper.get('venue', '')
            doi = paper.get('doi', '')
            
            author_str = "Author"
            if authors:
                if isinstance(authors[0], dict):
                    author_str = authors[0].get('name', 'Author')
                else:
                    author_str = str(authors[0])
            
            ref = f"{author_str}"
            if len(authors) > 1:
                ref += " et al."
            ref += f" ({year}). {title}."
            if venue:
                ref += f" {venue}."
            if doi:
                ref += f" https://doi.org/{doi}"
            
            references.append(ref)
        
        references.sort()
        return references

    async def _check_job_state(self, job_id: str) -> str:
        from core.cache import cache
        redis_client = await cache.get_client()
        state = await redis_client.get(f"job:{job_id}:state")
        return state.decode() if state else "running"
    
    async def _wait_for_resume(self, job_id: str):
        import asyncio
        from core.events import events
        await events.log(job_id, "⏸️ Paused - waiting for resume...", "warning")
        while True:
            state = await self._check_job_state(job_id)
            if state == "running":
                await events.log(job_id, "▶️ Resuming generation...", "success")
                break
            elif state == "stopped":
                break
            await asyncio.sleep(1)

    def _create_stopped_result(self, section_title, paragraphs, cited_papers):
        return {
            "section_title": section_title,
            "content": "\n\n".join(paragraphs),
            "references": self._format_references(cited_papers),
            "status": "stopped",
            "metrics": {"paragraph_count": len(paragraphs)}
        }

    async def _update_bibtex(self, papers: List[Dict[str, Any]], thesis_id: str = "default_thesis"):
        """Update references.bib and sync to Zotero."""
        try:
            # 1. Update local BibTeX
            # Define path relative to thesis workspace (assuming running from backend/lightweight)
            bib_path = f"../../thesis_data/{thesis_id}/references.bib"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(bib_path), exist_ok=True)
            
            existing_entries = set()
            if os.path.exists(bib_path):
                with open(bib_path, 'r') as f:
                    content = f.read()
                    # Simple check for existing IDs
                    for line in content.split('\n'):
                        if line.strip().startswith('@') and '{' in line:
                            entry_id = line.split('{')[1].split(',')[0].strip()
                            existing_entries.add(entry_id)
            
            new_entries = []
            for p in papers:
                # Generate ID: AuthorYearTitle
                authors = p.get('authors', [])
                year = p.get('year', 'n.d.')
                title = p.get('title', '')
                
                if not title:
                    continue
                
                title_word = title.split()[0] if title.split() else ''
                
                if authors and isinstance(authors[0], dict):
                    first_author = authors[0].get('name', '')
                    first_author = first_author.split()[-1] if first_author else ''
                elif authors:
                    first_author = str(authors[0]).split()[-1] if authors[0] else ''
                else:
                    first_author = ""
                
                # Skip entries without valid author
                if not first_author or first_author.lower() == 'unknown':
                    continue
                
                entry_id = f"{first_author}{year}{title_word}"
                entry_id = "".join(c for c in entry_id if c.isalnum())
                
                if entry_id in existing_entries:
                    continue
                
                existing_entries.add(entry_id)
                
                # Create BibTeX entry
                entry = f"@article{{{entry_id},\n"
                entry += f"  title = {{{p.get('title', '')}}},\n"
                entry += f"  author = {{{self._get_author_citation(p)}}},\n"
                entry += f"  year = {{{year}}},\n"
                if p.get('venue'):
                    entry += f"  journal = {{{p.get('venue')}}},\n"
                if p.get('url'):
                    entry += f"  url = {{{p.get('url')}}},\n"
                entry += "}\n\n"
                new_entries.append(entry)
            
            if new_entries:
                with open(bib_path, 'a') as f:
                    for entry in new_entries:
                        f.write(entry)
                print(f"   📚 Added {len(new_entries)} entries to references.bib")
            
            # 2. Sync to Zotero
            if self.zotero and papers:
                print(f"   🔄 Syncing {len(papers)} papers to Zotero...")
                # Run in background to not block
                asyncio.create_task(self.zotero.bulk_add_papers(papers, collection_name=f"Thesis: {thesis_id}"))
                
        except Exception as e:
            print(f"   ⚠️ Failed to update BibTeX: {e}")

# Singleton instance
simple_content_generator = SimpleContentGenerator()
