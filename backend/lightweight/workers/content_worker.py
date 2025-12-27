"""
Content Worker - Wakes on-demand to process content generation.

Sleeps until work appears in Redis queue, then awakens and processes.
"""
import asyncio
import sys
import os
# Add parent directory to path to allow importing 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '..')
import os
from pathlib import Path
from datetime import datetime

from core.queue import worker, JobQueue
from services.chapter_generator import chapter_generator


@worker("content")
async def process_content_job(data: dict):
    """
    Process content generation job.
    
    Agent awakens → Generates content → Saves to workspace → Returns → Sleeps
    """
    print(f"   ✍️ Generating content: {data.get('section_title', 'Chapter')}")
    
    job_type = data.get("type", "chapter")
    thesis_id = data.get("thesis_id")
    
    # Require thesis_id - should come from workspace creation
    if not thesis_id:
        print("⚠️ ERROR: No thesis_id provided in job data")
        return {
            "status": "error",
            "error": "No workspace ID provided. Please create a workspace first."
        }
    
    if job_type == "chapter":
        result = await chapter_generator.generate_chapter_one(
            topic=data["topic"],
            case_study=data["case_study"],
            objectives=data.get("objectives"),
            research_questions=data.get("research_questions")
        )
        
        # Save to workspace
        job_id = data.get("job_id")
        await save_to_workspace(thesis_id, "chapter_1", result["content"], result.get("references", []), None, job_id)
        
        # Return metadata (document handled separately)
        return {
            "metadata": result["metadata"],
            "references": result["references"],
            "status": "completed",
            "workspace_path": f"thesis_data/{thesis_id}/sections/chapter_1.md"
        }
    
    elif job_type == "revise":
        from services.simple_content_generator import simple_content_generator
        
        result = await simple_content_generator.revise_content(
            content=data["content"],
            instructions=data["instructions"],
            thesis_id=thesis_id,
            job_id=data.get("job_id")
        )
        
        # Save to workspace (overwrite existing or create new revision)
        section_name = sanitize_filename(data.get("section_title", "revised_section"))
        job_id = data.get("job_id")
        workspace_path = await save_to_workspace(
            thesis_id, 
            section_name, 
            result.get("content", ""), 
            [], # References are embedded in content for revision, or we'd need to parse them. 
               # For now, we assume they are in the text.
            None,
            job_id
        )
        
        result["workspace_path"] = workspace_path
        return result

    else:  # section
        from services.simple_content_generator import simple_content_generator
        
        result = await simple_content_generator.generate_cited_section(
            section_title=data["section_title"],
            topic=data["topic"],
            case_study=data.get("case_study", ""),
            word_count=data.get("word_count", 500),
            job_id=data.get("job_id"),
            thesis_id=thesis_id
        )
        
        # Save to workspace
        section_name = sanitize_filename(data.get("section_title", "section"))
        job_id = data.get("job_id")
        workspace_path = await save_to_workspace(
            thesis_id, 
            section_name, 
            result.get("content", ""), 
            result.get("references", []),
            result.get("cited_papers", []),
            job_id
        )
        
        # Add workspace path to result
        result["workspace_path"] = workspace_path
        result["status"] = "completed"
        
        return result


async def save_to_workspace(thesis_id: str, section_name: str, content: str, references: list, cited_papers: list = None, job_id: str = None) -> str:
    """
    Save generated content and references to thesis workspace.
    
    Args:
        thesis_id: Thesis identifier
        section_name: Name of the section
        content: Generated content
        references: List of references
        cited_papers: List of cited paper metadata
        
    Returns:
        Path to saved file
    """
    # Create workspace structure
    # Assuming running from backend/lightweight
    base_path = Path("../..") / "thesis_data" / thesis_id
    output_path = base_path / "sections"  # Use sections/ for generated content
    sources_path = base_path / "sources"  # Use sources/ for saved sources
    
    # Ensure directories exist
    output_path.mkdir(parents=True, exist_ok=True)
    sources_path.mkdir(parents=True, exist_ok=True)
    
    # Save content to output/ folder
    content_file = output_path / f"{section_name}.md"
    with open(content_file, 'w', encoding='utf-8') as f:
        f.write(f"# {section_name.replace('_', ' ').title()}\n\n")
        f.write(content)
        f.write("\n\n## References\n\n")
        for i, ref in enumerate(references, 1):
            f.write(f"{i}. {ref}\n")
    
    # Save sources to sources/ folder and update existing files
    if cited_papers:
        import json
        import hashlib
        for paper in cited_papers:
            # Create safe filename with hash to avoid duplicates
            title = paper.get('title', 'unknown_paper')
            safe_title = sanitize_filename(title)[:50]
            # Add hash to ensure uniqueness
            url = paper.get('url', '')
            content_str = f"{title}{paper.get('abstract', '')}"
            hash_suffix = hashlib.sha256(content_str.encode()).hexdigest()[:8] if content_str else ''
            source_file = sources_path / f"{safe_title}_{hash_suffix}.json"
            
            # Check if file already exists
            if source_file.exists():
                # Update existing file - add to used_in list
                try:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Update used_in list
                    used_in = existing_data.get('used_in', [])
                    if section_name not in used_in:
                        used_in.append(section_name)
                    
                    existing_data['used_in'] = used_in
                    existing_data.update({
                        **paper,  # Update with latest paper data
                        "type": paper.get('type', 'academic_paper')
                    })
                    
                    with open(source_file, 'w', encoding='utf-8') as f:
                        json.dump(existing_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"   ⚠️ Failed to update existing source file: {e}")
            else:
                # Create new file
                paper_metadata = {
                    **paper,
                    "saved_at": datetime.now().isoformat(),
                    "used_in": [section_name],
                    "type": paper.get('type', 'academic_paper')
                }
            
            # Save metadata
            with open(source_file, 'w', encoding='utf-8') as f:
                    json.dump(paper_metadata, f, indent=2, ensure_ascii=False)
                
    print(f"   💾 Saved to: {content_file}")
    print(f"   📚 Sources saved to: {sources_path}")
    
    # Emit file created event
    if job_id:
        from core.events import events
        await events.file_created(job_id, f"{thesis_id}/sections/{sectionName}.md", "markdown")
        print(f"   📢 Emitted file_created event for {section_name}.md")
    
    return str(content_file.relative_to(base_path))


def sanitize_filename(name: str) -> str:
    """Convert section title to valid filename."""
    import re
    # Remove special characters, replace spaces with underscores
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s]+', '_', name)
    return name.lower()


if __name__ == "__main__":
    with open("worker_debug.log", "a") as f:
        f.write("Starting worker...\n")
    print("📝 Content Worker - Starting...")
    try:
        asyncio.run(process_content_job())
    except Exception as e:
        with open("worker_debug.log", "a") as f:
            f.write(f"Worker crashed: {e}\n")
        raise

