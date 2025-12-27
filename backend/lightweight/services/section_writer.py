"""
Section Writer - Writes individual essay sections in parallel.

Each section writer runs independently, allowing 4-5 sections
to be written simultaneously for faster essay generation.
"""
import asyncio
from typing import Dict, Any, Optional, Callable
from services.deepseek_direct import deepseek_direct_service
from core.events import events


async def write_section(
    section: Dict[str, Any],
    topic: str,
    context: str = "",
    job_id: str = None,
    workspace_id: str = "default",
    stream_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Write a single section of an essay.
    
    Args:
        section: {id, heading, word_target, key_points, needs_image, image_prompt}
        topic: Overall essay topic
        context: Research context/sources
        job_id: For event streaming
        stream_callback: For real-time streaming
        
    Returns:
        {
            "section_id": 1,
            "heading": "Introduction",
            "content": "Written content...",
            "word_count": 150,
            "image_url": "..." or None
        }
    """
    section_id = section.get("id", 0)
    heading = section.get("heading", "Section")
    word_target = section.get("word_target", 200)
    key_points = section.get("key_points", [])
    
    if job_id:
        await events.log(job_id, f"✍️ Writing section {section_id}: {heading} ({word_target} words)")
    
    # Build section prompt
    key_points_text = "\n".join([f"- {point}" for point in key_points]) if key_points else ""
    
    prompt = f"""Write approximately {word_target} words for the "{heading}" section of an essay about "{topic}".

Key points to cover:
{key_points_text}

Context/Sources:
{context[:1500] if context else "Use your knowledge."}

Requirements:
- Write exactly this section, not the whole essay
- Target {word_target} words (±20%)
- Write in academic style
- Include citations where appropriate [Author, Year]
- Be specific and informative

Output ONLY the section content (no heading, no meta-commentary):"""

    try:
        content = await deepseek_direct_service.generate_content(
            prompt=prompt,
            max_tokens=max(word_target * 4, 2000),  # ~4 tokens per word, min 2000
            stream=bool(stream_callback),
            stream_callback=stream_callback
        )
        
        # Get image if needed
        image_url = None
        if section.get("needs_image") and section.get("image_prompt"):
            try:
                from services.intelligent_image_search import intelligent_image_search_service
                images = await intelligent_image_search_service.search(
                    section["image_prompt"], limit=1
                )
                if images:
                    image_url = images[0].get("url") or images[0].get("full")
            except Exception as img_err:
                print(f"⚠️ Image search error for section {section_id}: {img_err}")
        
        result = {
            "section_id": section_id,
            "heading": heading,
            "content": content.strip(),
            "word_count": len(content.split()),
            "image_url": image_url
        }
        
        if job_id:
            await events.log(job_id, f"✅ Section {section_id} done: {result['word_count']} words")
        
        return result
        
    except Exception as e:
        print(f"⚠️ Section {section_id} error: {e}")
        return {
            "section_id": section_id,
            "heading": heading,
            "content": f"[Error writing section: {e}]",
            "word_count": 0,
            "image_url": None
        }


async def write_section_with_tab(
    section: Dict[str, Any],
    topic: str,
    context: str,
    job_id: str,
    workspace_id: str,
    on_complete: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Write a section with its own dedicated tab showing real-time progress.
    Uses events.publish for streaming.
    """
    section_id = section.get("id", 0)
    heading = section.get("heading", "Section")
    word_target = section.get("word_target", 200)
    key_points = section.get("key_points", [])
    
    # Create a unique agent name for this section's tab
    tab_name = f"section_{section_id}"
    display_name = heading  # e.g., "Introduction", "Background"
    
    # Open a new tab for this section
    await events.publish(job_id, "agent_stream", {
        "agent": tab_name,
        "display_name": f"✍️ {display_name}",
        "event_type": "start",
        "content": f"# {heading}\n_Writing {word_target} words..._\n\n",
        "completed": False,
        "workspace_id": workspace_id
    })
    
    # Build prompt
    key_points_text = "\n".join([f"- {point}" for point in key_points]) if key_points else ""
    
    prompt = f"""Write approximately {word_target} words for the "{heading}" section of an essay about "{topic}".

Key points to cover:
{key_points_text}

Context/Sources:
{context[:1500] if context else "Use your knowledge."}

Requirements:
- Write exactly this section, not the whole essay
- Target {word_target} words (±20%)
- Write in academic style
- Include citations where appropriate [Author, Year]
- Be specific and informative

Output ONLY the section content (no heading, no meta-commentary):"""

    content_chunks = []
    
    try:
        # Stream callback to send chunks to the section's tab
        async def stream_to_tab(chunk: str):
            content_chunks.append(chunk)
            await events.publish(job_id, "agent_stream", {
                "agent": tab_name,
                "event_type": "chunk",
                "content": chunk,
                "workspace_id": workspace_id
            })
        
        # Generate with streaming
        await deepseek_direct_service.generate_content(
            prompt=prompt,
            max_tokens=word_target * 3,
            stream=True,
            stream_callback=stream_to_tab
        )
        
        content = "".join(content_chunks)
        word_count = len(content.split())
        
        # Get image if needed
        image_url = None
        if section.get("needs_image") and section.get("image_prompt"):
            try:
                from services.intelligent_image_search import intelligent_image_search_service
                await events.publish(job_id, "agent_stream", {
                    "agent": tab_name,
                    "event_type": "chunk",
                    "content": "\n\n_🖼️ Finding relevant image..._",
                    "workspace_id": workspace_id
                })
                images = await intelligent_image_search_service.search(
                    section["image_prompt"], limit=1
                )
                if images:
                    image_url = images[0].get("url") or images[0].get("full")
                    await events.publish(job_id, "agent_stream", {
                        "agent": tab_name,
                        "event_type": "chunk",
                        "content": f"\n\n![{heading}]({image_url})",
                        "workspace_id": workspace_id
                    })
            except Exception as img_err:
                print(f"⚠️ Image error for section {section_id}: {img_err}")
        
        # Mark section complete
        await events.publish(job_id, "agent_stream", {
            "agent": tab_name,
            "display_name": f"✅ {display_name}",
            "event_type": "complete",
            "content": f"\n\n---\n_✅ {word_count} words complete_",
            "completed": True,
            "workspace_id": workspace_id
        })
        
        # Notify parent that this section is done (for Planner update)
        if on_complete:
            await on_complete(section_id, heading, word_count)
        
        return {
            "section_id": section_id,
            "heading": heading,
            "content": content.strip(),
            "word_count": word_count,
            "image_url": image_url
        }
        
    except Exception as e:
        print(f"⚠️ Section {section_id} error: {e}")
        await events.publish(job_id, "agent_stream", {
            "agent": tab_name,
            "display_name": f"❌ {display_name}",
            "event_type": "error",
            "content": f"\n\n_Error: {e}_",
            "completed": True,
            "workspace_id": workspace_id
        })
        return {
            "section_id": section_id,
            "heading": heading,
            "content": f"[Error writing section: {e}]",
            "word_count": 0,
            "image_url": None
        }


async def write_all_sections_parallel(
    outline: Dict[str, Any],
    topic: str,
    context: str = "",
    job_id: str = None,
    workspace_id: str = "default",
    planner_update_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Write ALL sections in parallel, each in its own tab.
    Updates Planner in real-time as sections complete.
    
    Args:
        outline: Output from planner.generate_outline()
        topic: Essay topic
        context: Research context
        planner_update_callback: Called when each section completes to update Planner
        
    Returns:
        {
            "title": "Essay Title",
            "sections": [completed sections...],
            "total_words": 1000,
            "images": [...]
        }
    """
    sections = outline.get("sections", [])
    title = outline.get("title", f"Essay on {topic}")
    
    if job_id:
        await events.log(job_id, f"🚀 Opening {len(sections)} section tabs for PARALLEL writing")
    
    # Track completion status for Planner updates
    completed_count = [0]  # Use list to allow mutation in closure
    
    async def on_section_complete(section_id: int, heading: str, word_count: int):
        completed_count[0] += 1
        if planner_update_callback:
            await planner_update_callback(section_id, heading, word_count, completed_count[0], len(sections))
    
    # Create tasks for ALL sections - each gets its own tab!
    tasks = [
        write_section_with_tab(
            section=section,
            topic=topic,
            context=context,
            job_id=job_id,
            workspace_id=workspace_id,
            on_complete=on_section_complete
        )
        for section in sections
    ]
    
    # Execute ALL in parallel - user sees 5 tabs updating simultaneously!
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    completed_sections = []
    total_words = 0
    images = []
    
    for result in results:
        if isinstance(result, Exception):
            print(f"⚠️ Section failed: {result}")
            continue
        completed_sections.append(result)
        total_words += result.get("word_count", 0)
        if result.get("image_url"):
            images.append({
                "section_id": result["section_id"],
                "url": result["image_url"]
            })
    
    # Sort by section_id
    completed_sections.sort(key=lambda x: x.get("section_id", 0))
    
    if job_id:
        await events.log(job_id, f"✅ All {len(completed_sections)} sections complete: {total_words} total words")
    
    return {
        "title": title,
        "sections": completed_sections,
        "total_words": total_words,
        "images": images
    }



def combine_sections_to_markdown(
    essay_data: Dict[str, Any],
    include_images: bool = True
) -> str:
    """
    Combine all sections into final markdown document.
    """
    title = essay_data.get("title", "Essay")
    sections = essay_data.get("sections", [])
    
    lines = [f"# {title}\n"]
    
    for section in sections:
        heading = section.get("heading", "Section")
        content = section.get("content", "")
        image_url = section.get("image_url")
        
        lines.append(f"\n## {heading}\n")
        
        # Insert image at start of section if available
        if include_images and image_url:
            lines.append(f"\n![{heading}]({image_url})\n")
        
        lines.append(content)
    
    return "\n".join(lines)
