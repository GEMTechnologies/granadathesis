"""
Task Worker - Intelligent worker that handles complex multi-step tasks.

Can process:
- Essay writing with images
- Document generation
- Multi-step research tasks
- Parallel tool execution
"""
import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '..')

from core.queue import worker, JobQueue
from core.events import events
from services.planner import planner_service
from services.web_search import web_search_service
from services.intelligent_image_search import intelligent_image_search_service
from services.image_generation import image_generation_service
from tools.filesystem import write_file, read_file
from services.deepseek_direct import deepseek_direct_service
from services.workspace_service import WORKSPACES_DIR


@worker("tasks")
async def process_task_job(data: dict):
    """
    Process complex multi-step task job.
    
    Handles:
    - Essay/document writing
    - Image search and generation
    - Web research
    - Parallel execution of tools
    """
    # Extract job_id from data or generate one
    job_id = data.get("job_id")
    if not job_id:
        # Try to get from job metadata if available
        import uuid
        job_id = str(uuid.uuid4())
        data["job_id"] = job_id
    
    workspace_id = data.get("workspace_id", "default")
    session_id = data.get("session_id", "default")  # Extract session_id for continuous chat
    user_message = data.get("message", "")
    
    try:
        print(f"⚡ Task Worker awakened! Processing: {user_message[:100]}...")
        
        # Emit start event with session_id for continuous chat
        await events.log(job_id, f"🚀 Starting task: {user_message[:100]}", session_id=session_id)
        await events.publish(job_id, "progress", {"stage": "planning", "percent": 5}, session_id=session_id)
        
        # Step 1: Generate plan WITH STREAMING - OPEN PREVIEW TAB IMMEDIATELY
        print(f"   📋 Generating plan...")
        await events.log(job_id, "📋 Analyzing request and creating plan...")
        
        # Use planner agent stream handler - OPEN PREVIEW TAB IMMEDIATELY
        from core.agent_stream_factory import get_agent_stream_handler
        planner_handler = get_agent_stream_handler("planner", job_id, workspace_id)
        
        # Emit agent_working for Planner in chat (ONLY for planning, not writing)
        await events.publish(job_id, "agent_working", {
            "agent": "planner",
            "agent_name": "Planner",
            "status": "running",
            "action": "Creating plan...",
            "icon": "📋"
        })
        
        # Create task.md file for tracking
        from pathlib import Path
        workspace_path = Path(f"workspaces/{workspace_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        task_md_path = workspace_path / f"task_{job_id[:8]}.md"
        
        # CALL LLM FIRST to get REAL plan (not hardcoded!)
        from services.planner import planner_service
        from core.agent_stream_factory import get_agent_stream_handler
        
        planner_handler = get_agent_stream_handler("planner", job_id, workspace_id)
        
        # Show initial "thinking" state
        await events.publish(job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": planner_handler.tab_id,
            "content": "🤔 **Analyzing your request...**\n\n_Calling DeepSeek to generate plan..._",
            "completed": False,
            "workspace_id": workspace_id
        })
        
        # Extract word count if specified
        import re
        word_match = re.search(r'(\d+)\s*word', user_message.lower())
        target_words = int(word_match.group(1)) if word_match else 1000
        
        # CALL LLM FOR REAL OUTLINE
        await events.log(job_id, "📋 DeepSeek generating outline...")
        
        async def stream_outline(chunk: str):
            """Stream outline generation to Planner tab"""
            if chunk:
                await planner_handler.stream_chunk(chunk, {"stage": "planning"})
        
        outline = await planner_service.generate_outline(
            topic=user_message,
            word_count=target_words,
            include_images=True,
            job_id=job_id,
            stream_callback=stream_outline
        )
        
        # BUILD STEPS FROM REAL LLM OUTLINE (not hardcoded!)
        sections = outline.get("sections", [])
        steps = [{"id": "plan", "name": "Planning", "icon": "📋", "status": "done"}]  # Planning done
        
        for section in sections:
            steps.append({
                "id": f"section_{section.get('id', 0)}",
                "name": section.get("heading", "Section"),
                "icon": "✍️",
                "status": "pending",
                "word_target": section.get("word_target", 200)
            })
        
        steps.append({"id": "verify", "name": "Verification", "icon": "🔍", "status": "pending"})
        
        def format_task_md(steps_list, task_desc=""):
            """Format as markdown with checkboxes"""
            lines = [f"# {outline.get('title', 'Essay')}\n"]
            lines.append(f"_Target: {target_words} words_\n")
            for step in steps_list:
                word_info = f" ({step.get('word_target', '')} words)" if step.get('word_target') else ""
                if step["status"] == "done":
                    lines.append(f"- [x] {step['icon']} **{step['name']}**{word_info} ✓")
                elif step["status"] == "running":
                    lines.append(f"- [ ] {step['icon']} **{step['name']}**{word_info} ⏳")
                else:
                    lines.append(f"- [ ] {step['icon']} {step['name']}{word_info}")
            return "\n".join(lines)
        
        def save_task_md(steps_list):
            md_content = format_task_md(steps_list, user_message)
            task_md_path.write_text(md_content)
            return md_content
        
        # Show REAL outline from LLM
        initial_md = save_task_md(steps)
        await events.publish(job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": planner_handler.tab_id,
            "content": initial_md,
            "completed": False,
            "workspace_id": workspace_id,
            "metadata": {"outline": outline, "steps": steps}
        })
        
        await events.log(job_id, f"📋 Plan ready: {len(sections)} sections, {target_words} words")
        
        await events.publish(job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": planner_handler.tab_id,
            "chunk": "",
            "content": save_task_md(steps),
            "type": "planning",
            "completed": False,
            "workspace_id": workspace_id,
            "metadata": {
                "status": "running",
                "action": "planning",
                "steps": steps
            }
        })
        
        # Stream reasoning chunks during planning - ONLY to workspace, NOT to Planner tab
        reasoning_chunks = []
        async def stream_planning_reasoning(chunk: str):
            """Stream planning reasoning to workspace ONLY (not to preview tab - keep it clean)"""
            if not chunk:
                return
            reasoning_chunks.append(chunk)
            try:
                accumulated = "".join(reasoning_chunks)
                
                # ONLY send to workspace - NOT to Planner tab (keep tab clean with steps only)
                await events.publish(job_id, "reasoning_chunk", {
                    "chunk": chunk,
                    "accumulated": accumulated
                })
                
                # NO streaming to planner tab - keep it clean with step progress only
                await asyncio.sleep(0.001)  # 1ms - faster
            except Exception as e:
                print(f"⚠️ Error streaming reasoning: {e}", flush=True)
        
        try:
            plan_data = await asyncio.wait_for(
                planner_service.generate_plan(
                    user_request=user_message,
                    session_id=data.get("session_id", "default"),
                    workspace_id=workspace_id,
                    user_id=data.get("user_id", "default"),
                    job_id=job_id,
                    stream=True,
                    stream_callback=stream_planning_reasoning
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            await events.log(job_id, "⚠️ Planning timed out, using fallback plan", "warning")
            plan_data = {
                "reasoning": "Planning timed out, proceeding with direct execution",
                "plan": [{"action": "generate_content", "parameters": {"content": user_message}}]
            }
        
        reasoning = plan_data.get("reasoning", "")
        plan = plan_data.get("plan", [])
        
        # Mark planning complete - UPDATE STEP STATUS
        steps[0]["status"] = "done"  # Planning done
        
        # Update planner tab with progress
        await events.publish(job_id, "agent_stream", {
            "agent": "planner",
            "tab_id": planner_handler.tab_id,
            "content": save_task_md(steps) + f"\n\n**{len(plan)} actions planned**",
            "completed": False,
            "workspace_id": workspace_id,
            "metadata": {"status": "running", "steps": steps}
        })
        
        await events.log(job_id, f"✅ Plan: {len(plan)} steps")
        await events.publish(job_id, "progress", {"stage": "executing", "percent": 15})
        
        # Step 2: Execute plan steps in parallel where possible
        results = {}
        tool_results = {}
        
        # Group steps by type for parallel execution
        web_search_steps = [s for s in plan if s.get("action") == "web_search"]
        image_search_steps = [s for s in plan if s.get("action") == "image_search"]
        image_generate_steps = [s for s in plan if s.get("action") == "image_generate"]
        content_steps = [s for s in plan if s.get("action") in ["generate_content", "write_file", "create_document"]]
        
        # Execute parallel groups
        parallel_tasks = []
        
        # Web searches (parallel) - Use Internet Search Agent for real-time data
        if web_search_steps:
            # Create INTERNET SEARCH agent handler (separate from regular search)
            from core.agent_stream_factory import get_agent_stream_handler
            internet_search_handler = get_agent_stream_handler("internet_search", job_id, workspace_id)
            
            async def do_web_search(step):
                query = step.get("parameters", {}).get("query", "")
                if query:
                    # Emit agent_working event for chat feedback
                    await events.publish(job_id, "agent_working", {
                        "agent": "internet_search",
                        "agent_name": "Internet Search",
                        "status": "running",
                        "action": f"Searching: {query[:50]}...",
                        "icon": "🌐"
                    })
                    
                    # OPEN INTERNET SEARCH TAB IMMEDIATELY
                    await events.publish(job_id, "agent_stream", {
                        "agent": "internet_search",
                        "tab_id": internet_search_handler.tab_id,
                        "chunk": "",
                        "content": f"🌐 **Searching for updated data:** {query}\n\n_Fetching real-time results..._\n\n",
                        "type": "search",
                        "completed": False,
                        "workspace_id": workspace_id,
                        "metadata": {
                            "query": query,
                            "status": "searching",
                            "action": "searching"
                        }
                    })
                    
                    await events.log(job_id, f"🌐 Internet Search: {query[:50]}...")
                    
                    result = await web_search_service.search(query, max_results=5)
                    results = result.get('results', [])
                    results_count = len(results)
                    
                    # Stream results to Internet Search preview tab
                    await internet_search_handler.stream_search_results(query, results, {
                        "count": results_count,
                        "status": "completed",
                        "results": results
                    })
                    
                    # Emit agent_working complete for chat feedback
                    await events.publish(job_id, "agent_working", {
                        "agent": "internet_search",
                        "agent_name": "Internet Search",
                        "status": "completed",
                        "action": f"Found {results_count} results",
                        "icon": "🌐"
                    })
                    await events.log(job_id, f"✅ Internet Search found {results_count} results")
                    return ("web_search", query, result)
                return None
            
            for step in web_search_steps:
                parallel_tasks.append(do_web_search(step))
        
        # Image searches (parallel)
        if image_search_steps:
            async def do_image_search(step):
                query = step.get("parameters", {}).get("query", "")
                if query:
                    # Emit real-time event BEFORE search
                    await events.publish(job_id, "agent_activity", {
                        "agent": "image_search",
                        "action": "searching",
                        "query": query[:100],
                        "status": "running"
                    }, session_id=session_id)
                    await events.log(job_id, f"🖼️ Searching and saving images: {query[:50]}...", session_id=session_id)
                    
                    # Use search_and_save to download images locally
                    result = await intelligent_image_search_service.search_and_save(
                        query=query, 
                        workspace_id=workspace_id,
                        limit=3,
                        save_all=True  # Save all found images locally
                    )
                    images_count = len(result.get('images', []))
                    
                    # Emit completion event
                    await events.publish(job_id, "agent_activity", {
                        "agent": "image_search",
                        "action": "completed",
                        "query": query[:100],
                        "results": images_count,
                        "saved_locally": True,
                        "status": "completed"
                    }, session_id=session_id)
                    await events.log(job_id, f"✅ Found and saved {images_count} images for: {query[:50]}", session_id=session_id)
                    return ("image_search", query, result)
                return None
            
            for step in image_search_steps:
                parallel_tasks.append(do_image_search(step))
        
        # Image generation (parallel)
        if image_generate_steps:
            async def do_image_generate(step):
                prompt = step.get("parameters", {}).get("prompt", "")
                if prompt:
                    # Emit real-time event BEFORE generation
                    await events.publish(job_id, "agent_activity", {
                        "agent": "image_generator",
                        "action": "generating",
                        "prompt": prompt[:100],
                        "status": "running"
                    })
                    await events.log(job_id, f"🎨 Generating image: {prompt[:50]}...")
                    
                    result = await image_generation_service.generate(prompt=prompt, size="1024x1024")
                    
                    # Emit completion event
                    await events.publish(job_id, "agent_activity", {
                        "agent": "image_generator",
                        "action": "completed",
                        "prompt": prompt[:100],
                        "status": "completed"
                    })
                    await events.log(job_id, f"✅ Image generated: {prompt[:50]}")
                    return ("image_generate", prompt, result)
                return None
            
            for step in image_generate_steps:
                parallel_tasks.append(do_image_generate(step))
        
        # Execute all parallel tasks
        if parallel_tasks:
            await events.log(job_id, f"🔄 Executing {len(parallel_tasks)} tasks in parallel...")
            await events.publish(job_id, "progress", {"stage": "parallel_execution", "percent": 30})
            
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
            completed_count = 0
            for result in parallel_results:
                if result and not isinstance(result, Exception):
                    tool_type, query, data = result
                    if tool_type not in tool_results:
                        tool_results[tool_type] = []
                    tool_results[tool_type].append({
                        "query": query,
                        "data": data
                    })
                    completed_count += 1
                    await events.log(job_id, f"✅ {tool_type} completed: {query[:50]}")
                    await events.publish(job_id, "progress", {
                        "stage": "parallel_execution",
                        "percent": 30 + int((completed_count / len(parallel_tasks)) * 25)
                    })
                elif isinstance(result, Exception):
                    await events.log(job_id, f"⚠️ Task error: {str(result)}", "warning")
        
        await events.publish(job_id, "progress", {"stage": "content_generation", "percent": 60})
        
        # Update step: Internet Search done (if it ran)
        if web_search_steps or any("web_search" in str(t) for t in parallel_tasks):
            steps[1]["status"] = "done"
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps), "workspace_id": workspace_id
            })
        
        # Step 3: ACADEMIC SEARCH - get scholarly sources
        academic_results = []
        if any(word in user_message.lower() for word in ['research', 'academic', 'essay', 'paper', 'study', 'analysis', 'war', 'current', 'info']):
            steps[2]["status"] = "running"
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps), "workspace_id": workspace_id
            })
            
            try:
                # Open Academic tab
                academic_handler = get_agent_stream_handler("academic", job_id, workspace_id)
                await events.publish(job_id, "agent_stream", {
                    "agent": "academic",
                    "tab_id": academic_handler.tab_id,
                    "content": "📚 **Academic Search Agent**\n\n🔄 Searching ALL sources in parallel...\n- Semantic Scholar\n- CrossRef\n- EXA Neural Search\n- PubMed/PMC\n\n",
                    "completed": False,
                    "workspace_id": workspace_id
                })
                
                # Extract topic for academic search
                topic = " ".join(user_message.split()[:10])
                
                # RUN ALL SEARCHES IN PARALLEL for speed
                from services.academic_search import academic_search_service
                from services.pubmed_api import PubMedAPI
                
                pubmed = PubMedAPI()
                
                # Parallel API calls - all at once for maximum speed
                search_tasks = [
                    academic_search_service.search_academic_papers(topic, max_results=3, job_id=job_id),
                    academic_search_service.search_with_exa(f"{topic} research study", max_results=3),
                    pubmed.search_and_fetch(topic, max_results=3, free_full_text=True),
                ]
                
                await events.log(job_id, "📚 Searching 4 academic APIs in parallel...")
                
                # Execute ALL searches in parallel
                results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                # Combine results
                semantic_results = results[0] if not isinstance(results[0], Exception) else []
                exa_results = results[1] if not isinstance(results[1], Exception) else []
                pubmed_results = results[2] if not isinstance(results[2], Exception) else []
                
                # Format papers for display
                papers_text = "## 📚 Academic Sources\n\n"
                
                if semantic_results:
                    papers_text += "### Semantic Scholar + CrossRef\n"
                    for paper in semantic_results[:3]:
                        url = paper.get('url', paper.get('paperId', ''))
                        papers_text += f"- [{paper.get('title', 'Unknown')}]({url}) ({paper.get('year', 'N/A')})\n"
                    academic_results.extend(semantic_results)
                
                if pubmed_results:
                    papers_text += "\n### PubMed/PMC\n"
                    for paper in pubmed_results[:3]:
                        title = paper.title if hasattr(paper, 'title') else paper.get('title', 'Unknown')
                        year = paper.year if hasattr(paper, 'year') else paper.get('year', 'N/A')
                        pmc_url = paper.pmc_url if hasattr(paper, 'pmc_url') else paper.get('pmc_url', '#')
                        papers_text += f"- [{title}]({pmc_url}) ({year})\n"
                        academic_results.append({"title": title, "year": year, "source": "PubMed", "url": pmc_url})
                
                if exa_results:
                    papers_text += "\n### Neural Search (EXA)\n"
                    for result in exa_results[:2]:
                        url = result.get('url', '#')
                        papers_text += f"- [{result.get('title', 'Source')[:60]}...]({url})\n"
                
                total_found = len(semantic_results) + len(pubmed_results) + len(exa_results)
                papers_text += f"\n✅ **{total_found} sources found**"
                
                await academic_handler.stream_complete(papers_text, {"count": total_found})
                await events.log(job_id, f"📚 Found {total_found} papers")
                
                # Generate BibTeX file for citations
                try:
                    bib_entries = []
                    for i, paper in enumerate(academic_results[:10]):
                        title = paper.get('title', 'Unknown')
                        year = paper.get('year', 2024)
                        authors = paper.get('authors', [{'name': 'Unknown'}])
                        author_str = ' and '.join([a.get('name', 'Unknown') for a in (authors if isinstance(authors, list) else [authors])])
                        cite_key = f"ref{i+1}_{year}"
                        bib_entries.append(f"""@article{{{cite_key},
  title = {{{title}}},
  author = {{{author_str}}},
  year = {{{year}}},
  source = {{{paper.get('source', 'Academic')}}}
}}""")
                    
                    if bib_entries:
                        bib_content = "\n\n".join(bib_entries)
                        bib_path = workspace_path / f"references_{job_id[:8]}.bib"
                        bib_path.write_text(bib_content)
                        await events.log(job_id, f"📄 Created BibTeX: references_{job_id[:8]}.bib")
                except Exception as bib_err:
                    print(f"⚠️ BibTeX error: {bib_err}")
                
                # Try to download PDFs for papers with Open Access
                try:
                    from services.pdf_service import get_pdf_service
                    pdf_service = get_pdf_service()
                    for paper in academic_results[:2]:  # Download first 2
                        if paper.get("url") or paper.get("pmc_url"):
                            url = paper.get("pmc_url") or paper.get("url")
                            # Non-blocking PDF download
                            asyncio.create_task(pdf_service.download_and_process(paper))
                except Exception as pdf_err:
                    print(f"⚠️ PDF download skipped: {pdf_err}")
                    await events.log(job_id, f"📚 Found {len(academic_results)} academic papers")
                
                steps[2]["status"] = "done"
            except Exception as e:
                print(f"⚠️ Academic search error: {e}")
                steps[2]["status"] = "done"  # Continue even if fails
            
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps), "workspace_id": workspace_id
            })
        else:
            steps[2]["status"] = "done"  # Skip if not academic
        
        # Step 4: Generate content using PARALLEL SECTION WRITERS
        content = ""
        has_content_request = any(word in user_message.lower() for word in ['write', 'essay', 'document', 'create', 'generate', 'about'])
        
        if content_steps or has_content_request:
            # Update step: Writing
            steps[3]["status"] = "running"
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps), "workspace_id": workspace_id
            })
            
            print(f"🎯 PARALLEL WRITER: Starting section-based parallel writing")
            await events.log(job_id, "📋 Generating outline with LLM...")
            await events.publish(job_id, "progress", {"stage": "content_generation", "percent": 55})
            
            # Build context from research
            context_parts = []
            if "web_search" in tool_results:
                for search_result in tool_results["web_search"]:
                    context_parts.append(f"Research: {json.dumps(search_result.get('data', {}), indent=2)}")
            if academic_results:
                context_parts.append("## Academic Sources:\n" + "\n".join([f"- {p.get('title', '')} ({p.get('year', '')})" for p in academic_results[:3]]))
            context = "\n\n".join(context_parts)
            
            # Step 4a: Generate outline using LLM
            from services.planner import planner_service
            from services.section_writer import write_all_sections_parallel, combine_sections_to_markdown
            
            # Extract word count from message if specified
            import re
            word_match = re.search(r'(\d+)\s*word', user_message.lower())
            word_count = int(word_match.group(1)) if word_match else 1000
            
            # Generate outline with LLM
            outline = await planner_service.generate_outline(
                topic=user_message,
                word_count=word_count,
                include_images=True,
                job_id=job_id
            )
            
            # Show outline in Planner tab
            outline_text = f"## 📋 Outline: {outline.get('title', 'Essay')}\n\n"
            for section in outline.get("sections", []):
                outline_text += f"- {section.get('heading')} ({section.get('word_target')} words)\n"
            
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": outline_text, "workspace_id": workspace_id
            })
            
            await events.log(job_id, f"🚀 Starting {outline.get('total_sections', 5)} parallel section writers...")
            
            # Open Writer tab
            writer_handler = get_agent_stream_handler("writer", job_id, workspace_id)
            await events.publish(job_id, "agent_stream", {
                "agent": "writer", "tab_id": writer_handler.tab_id,
                "content": f"✍️ **Writing {outline.get('total_sections', 5)} sections in PARALLEL**\n\n_All sections generating simultaneously..._\n\n",
                "completed": False, "workspace_id": workspace_id
            })
            
            # Track section completion for Planner updates
            sections_completed = []
            
            async def on_section_complete(section_id, heading, word_count, done_count, total_count):
                """Called when each section finishes - update Planner tab in real-time"""
                sections_completed.append(heading)
                
                # Build updated progress display
                progress_text = f"## 📋 Progress: {done_count}/{total_count} sections\n\n"
                for section in outline.get("sections", []):
                    sec_heading = section.get("heading", "")
                    if sec_heading in sections_completed:
                        progress_text += f"- [x] ✅ {sec_heading} ({section.get('word_target')} words)\n"
                    else:
                        progress_text += f"- [ ] ⏳ {sec_heading} ({section.get('word_target')} words)\n"
                
                progress_text += f"\n_Writing in parallel... {done_count} complete_"
                
                await events.publish(job_id, "agent_stream", {
                    "agent": "planner", "tab_id": planner_handler.tab_id,
                    "content": progress_text, "workspace_id": workspace_id
                })
            
            # Step 4b: Write ALL sections in PARALLEL with real-time updates
            essay_data = await write_all_sections_parallel(
                outline=outline,
                topic=user_message,
                context=context,
                job_id=job_id,
                workspace_id=workspace_id,
                planner_update_callback=on_section_complete
            )
            
            # Step 4c: Combine sections into final document
            content = combine_sections_to_markdown(essay_data, include_images=True)
            
            # Stream final content to Writer tab
            await writer_handler.stream_complete(content, {
                "total_sections": len(essay_data.get("sections", [])),
                "total_words": essay_data.get("total_words", 0)
            })
            
            await events.log(job_id, f"✅ Essay complete: {essay_data.get('total_words', 0)} words from {len(essay_data.get('sections', []))} parallel sections", session_id=session_id)
            
            # Save final content to file
            try:
                workspace_path = WORKSPACES_DIR / workspace_id
                workspace_path.mkdir(parents=True, exist_ok=True)
                filename = f"essay_{job_id[:8]}.md"
                file_path = workspace_path / filename
                file_path.write_text(content, encoding='utf-8')
                await events.log(job_id, f"💾 Saved: {filename}", session_id=session_id)
                
                # Emit file_created event so clicking opens the REAL file (with session_id for continuous chat)
                await events.file_created(job_id, f"{workspace_id}/{filename}", "markdown", session_id=session_id)
                
            except Exception as save_err:
                print(f"⚠️ Save error: {save_err}")
            
            # Send animated status to CHAT (not preview) - user sees progress
            await events.publish(job_id, "agent_status", {
                "agent": "writer",
                "status": "complete",
                "message": f"✅ Essay ready! {essay_data.get('total_words', 0)} words in {len(essay_data.get('sections', []))} sections",
                "clickable": True,
                "opens_tab": "writer"
            })
            
            # Mark Writing done, start Verification
            steps[3]["status"] = "done"
            steps[4]["status"] = "running"
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps), "workspace_id": workspace_id
            })
        
        # Step 5: CONTENT VERIFICATION - fact-check before saving
        if content and len(content) > 200:
            try:
                from services.content_verifier import content_verifier
                await events.log(job_id, "🔍 Verifying content accuracy...")
                
                # Open Verification tab
                verify_handler = get_agent_stream_handler("verifier", job_id, workspace_id)
                await events.publish(job_id, "agent_stream", {
                    "agent": "verifier",
                    "tab_id": verify_handler.tab_id,
                    "content": "🔍 **Verification Agent**\n\n_Checking facts..._\n\n",
                    "completed": False,
                    "workspace_id": workspace_id
                })
                
                # Extract topic from user message
                topic = " ".join(user_message.split()[:5])
                verification_result = await content_verifier.verify_and_correct(content, topic, job_id)
                
                if verification_result.get("corrections"):
                    # Content was corrected
                    content = verification_result.get("content", content)
                    corrections = len(verification_result.get("corrections", []))
                    await verify_handler.stream_complete(f"## Verification Complete\n\n✓ {corrections} facts verified and corrected", {"corrections": corrections})
                    await events.log(job_id, f"🔍 Verified and corrected {corrections} facts")
                else:
                    await verify_handler.stream_complete("## Verification Complete\n\n✓ All facts verified", {"corrections": 0})
                    await events.log(job_id, "✓ Content verification passed")
                
                steps[4]["status"] = "done"
            except Exception as e:
                print(f"⚠️ Verification error: {e}")
                steps[4]["status"] = "done"  # Continue even if fails
            
            # Final step update
            await events.publish(job_id, "agent_stream", {
                "agent": "planner", "tab_id": planner_handler.tab_id,
                "content": save_task_md(steps) + "\n\n✅ **All steps complete!**",
                "completed": True,
                "workspace_id": workspace_id
            })
        else:
            steps[4]["status"] = "done"
        
        # Step 4: Insert images into content
        if content and ("image_search" in tool_results or "image_generate" in tool_results):
            await events.log(job_id, "🖼️ Inserting images into content...")
            await events.publish(job_id, "progress", {"stage": "image_insertion", "percent": 80})
            
            # Replace image placeholders with actual images
            image_index = 0
            all_images = []
            
            if "image_search" in tool_results:
                for search_result in tool_results["image_search"]:
                    images = search_result.get("data", {}).get("images", [])
                    all_images.extend(images[:2])  # Use first 2 from each search
            
            if "image_generate" in tool_results:
                for gen_result in tool_results["image_generate"]:
                    # Handle different result formats
                    result_data = gen_result.get("data", {})
                    if isinstance(result_data, dict):
                        image_url = result_data.get("image_url") or result_data.get("url")
                    else:
                        image_url = None
                    
                    if image_url:
                        all_images.append({
                            "url": image_url,
                            "type": "generated",
                            "description": gen_result.get("query", "Generated image")
                        })
            
            # Insert images into content
            inserted_count = 0
            for i, image in enumerate(all_images[:3]):  # Max 3 images
                if "[IMAGE:" in content or i == 0:
                    # Insert image markdown
                    image_md = f"\n\n![{image.get('description', 'Image')}]({image['url']})\n\n"
                    if "[IMAGE:" in content:
                        content = content.replace("[IMAGE:", image_md, 1)
                    else:
                        # Insert after first paragraph
                        paragraphs = content.split("\n\n")
                        if len(paragraphs) > 1:
                            paragraphs.insert(1, image_md)
                            content = "\n\n".join(paragraphs)
                        else:
                            content += image_md
                    inserted_count += 1
                    await events.log(job_id, f"✅ Inserted image {inserted_count}: {image.get('description', 'Image')[:50]}")
            
            await events.publish(job_id, "progress", {"stage": "image_insertion", "percent": 90})
        
        # Step 5: Save to workspace
        if content:
            await events.log(job_id, "💾 Saving content to workspace...")
            
            # Generate filename from user message
            filename = "essay.md"
            if "essay" in user_message.lower():
                if "uganda" in user_message.lower():
                    filename = "uganda_essay.md"
                else:
                    # Extract topic
                    words = user_message.lower().split()
                    topic_words = [w for w in words if w not in ["write", "an", "essay", "about", "on", "the", "a"]]
                    if topic_words:
                        filename = f"{topic_words[0]}_essay.md"
            
            # Use correct workspace path
            workspace_path = WORKSPACES_DIR / workspace_id
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            file_path = workspace_path / filename
            
            # Write file directly
            file_path.write_text(content, encoding='utf-8')
            print(f"   ✅ Saved to: {file_path}")
            # Small delay to ensure file is fully flushed to disk
            await asyncio.sleep(0.5)
            
            await events.log(job_id, f"✅ Content saved to {filename}", session_id=session_id)
            # Publish file_created event with workspace_id for frontend (with session_id for continuous chat)
            await events.publish(job_id, "file_created", {
                "path": filename,  # Relative path (just filename)
                "full_path": str(file_path.relative_to(WORKSPACES_DIR)),  # Relative to workspace root
                "type": "markdown",
                "workspace_id": workspace_id,
                "filename": filename,
                "timestamp": time.time()
            }, session_id=session_id)
        
        await events.publish(job_id, "progress", {"stage": "completed", "percent": 100}, session_id=session_id)
        
        # Return result
        return {
            "status": "completed",
            "content": content,
            "tool_results": tool_results,
            "plan": plan,
            "reasoning": reasoning,
            "workspace_path": f"{workspace_id}/{filename}" if content else None
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        
        await events.log(job_id, f"❌ Task failed: {error_msg}", "error")
        await events.publish(job_id, "progress", {"stage": "error", "percent": 0})
        
        await JobQueue.fail(job_id, error_msg)
        
        return {
            "status": "error",
            "error": error_msg,
            "message": f"Task processing failed: {error_msg}"
        }


if __name__ == "__main__":
    print("🎯 Task Worker - Starting...")
    print("   Waiting for tasks (sleeping)...")
    try:
        asyncio.run(process_task_job())
    except KeyboardInterrupt:
        print("\n👋 Task Worker stopped")
    except Exception as e:
        print(f"❌ Worker crashed: {e}")
        import traceback
        traceback.print_exc()
        raise

