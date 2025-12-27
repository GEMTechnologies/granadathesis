"""
Search Worker - Wakes on-demand to process search requests.

Sleeps until work appears in Redis queue, then awakens and processes.
"""
import asyncio
import sys
import os
# Add parent directory to path to allow importing 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '..')

from core.queue import worker, JobQueue
from services.academic_search import academic_search_service
from core.database import db
import json
import hashlib
from pathlib import Path
from datetime import datetime

@worker("search")
async def process_search_job(data: dict):
    """
    Process academic search job.
    
    Agent awakens → Searches papers → Returns → Sleeps
    """
    print(f"   🔍 Searching papers: {data['query']}")
    
    search_type = data.get("type", "papers")
    thesis_id = data.get("thesis_id")
    
    if search_type == "papers":
        papers = await academic_search_service.search_academic_papers(
            query=data["query"],
            max_results=data.get("max_results", 20),
            job_id=data.get("job_id")  # Pass job_id for event emission
        )
        
        # Save to Database AND Files if thesis_id is present
        if thesis_id:
            print(f"   💾 Saving {len(papers)} papers to Sources Vault (DB + Files)...")
            saved_count = 0
            for paper in papers:
                try:
                    # Create hash for deduplication
                    content_str = f"{paper.get('title')}{paper.get('abstract', '')}"
                    source_hash = hashlib.sha256(content_str.encode()).hexdigest()
                    
                    # Check if exists in DB
                    existing = await db.fetchrow(
                        "SELECT id FROM sources WHERE thesis_id = $1 AND source_hash = $2",
                        thesis_id, source_hash
                    )
                    
                    if not existing:
                        # Save to database
                        await db.execute(
                            """
                            INSERT INTO sources (thesis_id, title, url, type, content, metadata, source_hash)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            thesis_id,
                            paper.get('title'),
                            paper.get('url'),
                            'academic_paper',
                            paper.get('abstract', ''),
                            json.dumps({
                                'authors': paper.get('authors', []),
                                'year': paper.get('year', ''),
                                'venue': paper.get('venue', ''),
                                'citationCount': paper.get('citationCount', 0)
                            }),
                            source_hash
                        )
                        saved_count += 1
                    
                    # ALWAYS save to file (even if exists in DB, file might be missing)
                    await save_paper_to_file(paper, thesis_id, source_hash)
                    
                    # Try to download PDF if URL is available (non-blocking background task)
                    if paper.get('url'):
                        url_lower = paper.get('url', '').lower()
                        if '.pdf' in url_lower or 'arxiv' in url_lower or 'openaccess' in url_lower:
                            # Download in background (don't block main flow)
                            asyncio.create_task(download_pdf_for_paper(paper, thesis_id))
                    
                except Exception as e:
                    print(f"   ⚠️ Failed to save source: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"   ✓ Saved {saved_count} new sources to DB and all to files")
        
        return {
            "papers": papers,
            "total": len(papers)
        }
    
    else:  # context
        context = await academic_search_service.get_research_context(
            topic=data["topic"],
            case_study=data["case_study"]
        )
        
        return context


async def save_paper_to_file(paper: dict, thesis_id: str, source_hash: str):
    """Save academic paper to JSON file in sources/ folder."""
    try:
        # Determine thesis data directory
        thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
        sources_dir = thesis_data_dir / "sources"
        
        # Ensure sources directory exists
        sources_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        title = paper.get('title', 'Unknown Paper')
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:50]
        safe_title = safe_title.strip().replace(' ', '_')
        
        # Use hash suffix for uniqueness
        hash_suffix = source_hash[:8]
        filename = f"{safe_title}_{hash_suffix}.json"
        filepath = sources_dir / filename
        
        # Check if file already exists
        if filepath.exists():
            return  # Already saved
        
        # Prepare paper data
        paper_data = {
            "title": title,
            "url": paper.get('url', ''),
            "type": "academic_paper",
            "content": paper.get('abstract', ''),
            "abstract": paper.get('abstract', ''),
            "authors": paper.get('authors', []),
            "year": paper.get('year', ''),
            "venue": paper.get('venue', ''),
            "citationCount": paper.get('citationCount', 0),
            "saved_at": datetime.now().isoformat(),
            "source_hash": source_hash,
            "metadata": {
                "authors": paper.get('authors', []),
                "year": paper.get('year', ''),
                "venue": paper.get('venue', ''),
                "citationCount": paper.get('citationCount', 0),
                "paperId": paper.get('paperId', ''),
                "externalIds": paper.get('externalIds', {})
            },
            "used_in": []  # Will be updated when content is generated
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 Saved paper file: {filename}")
        
    except Exception as e:
        print(f"   ⚠️ Failed to save paper to file: {e}")
        import traceback
        traceback.print_exc()


async def download_pdf_for_paper(paper: dict, thesis_id: str):
    """Download PDF for a paper and save to sources/ folder."""
    try:
        from pathlib import Path
        import httpx
        
        url = paper.get('url', '')
        if not url:
            return
        
        # Check if it's an arXiv paper - construct PDF URL
        if 'arxiv.org' in url and '/abs/' in url:
            # Convert abs URL to PDF URL
            pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
        elif url.endswith('.pdf'):
            pdf_url = url
        else:
            # Try to find PDF link in paper metadata
            pdf_url = paper.get('pdf_url') or paper.get('openAccessPdf', {}).get('url', '')
            if not pdf_url:
                return  # No PDF available
        
        # Determine save location
        thesis_data_dir = Path(__file__).parent.parent.parent.parent / "thesis_data" / thesis_id
        sources_dir = thesis_data_dir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        title = paper.get('title', 'unknown_paper')
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:50]
        safe_title = safe_title.strip().replace(' ', '_')
        year = paper.get('year', '')
        pdf_filename = f"{safe_title}_{year}.pdf" if year else f"{safe_title}.pdf"
        pdf_path = sources_dir / pdf_filename
        
        # Skip if already exists
        if pdf_path.exists():
            print(f"   📄 PDF already exists: {pdf_filename}")
            return pdf_path
        
        # Download PDF
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            
            # Verify it's a PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not pdf_url.endswith(".pdf"):
                print(f"   ⚠️ URL may not be a PDF: {pdf_url}")
                return None
            
            # Save PDF
            pdf_path.write_bytes(response.content)
            print(f"   📥 Downloaded PDF: {pdf_filename} ({len(response.content)} bytes)")
            
            return pdf_path
            
    except Exception as e:
        print(f"   ⚠️ PDF download failed: {e}")
        return None


if __name__ == "__main__":
    print("🔎 Search Worker - Starting...")
    asyncio.run(process_search_job())
