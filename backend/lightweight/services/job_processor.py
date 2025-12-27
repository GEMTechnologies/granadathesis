"""
Job Processor - Executes jobs in the background

This module processes jobs created by job_manager.
Jobs run independently of frontend and persist through disconnects.
"""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.job_manager import Job, JobManager


async def process_job(job: 'Job', manager: 'JobManager'):
    """
    Main job processor.
    
    This function is called by job_manager.start_job() and runs in background.
    It should:
    1. Check for @mentioned agents and route directly to them
    2. Parse the user's message
    3. Route to appropriate handler (planning, writing, search, etc.)
    4. Update progress and emit events
    5. Save results
    """
    from services.task_classifier import classify_task
    from services.planner import planner_service
    from services.workspace_service import WorkspaceService
    
    workspace_id = job.workspace_id
    message = job.message
    mentioned_agents = job.mentioned_agents or []
    
    await manager.emit_log(job.job_id, f"🚀 Starting job: {message[:50]}...")
    await manager.add_step(job, "analyzing", "running")
    
    try:
        # Step 0: Check for @mentioned agents - route directly to them
        if mentioned_agents:
            await manager.emit_log(job.job_id, f"🎯 Mentioned agents: {', '.join(mentioned_agents)}")
            await route_to_mentioned_agents(job, manager, message, workspace_id, mentioned_agents)
            return
        
        # Step 1: Classify the task
        await manager.update_progress(job, 0.05, "Analyzing request...")
        task_type = classify_task(message)
        await manager.emit_log(job.job_id, f"📋 Task type: {task_type}")
        await manager.complete_step(job, "analyzing")
        
        # Step 2: Check for simple questions
        if is_simple_question(message):
            await process_simple_question(job, manager, message, workspace_id)
            return
        
        # Step 3: Check for paper search
        if is_paper_search_request(message):
            await process_paper_search(job, manager, message, workspace_id)
            return
        
        # Step 4: Check for literature synthesis request
        if is_synthesis_request(message):
            await process_synthesis(job, manager, message, workspace_id)
            return
        
        # Step 5: Complex task - use planning
        await process_complex_task(job, manager, message, workspace_id, task_type)
        
    except asyncio.CancelledError:
        await manager.emit_log(job.job_id, "🛑 Job cancelled by user")
        raise
    except Exception as e:
        await manager.emit_log(job.job_id, f"❌ Error: {str(e)}", "error")
        raise


async def route_to_mentioned_agents(
    job: 'Job', 
    manager: 'JobManager', 
    message: str, 
    workspace_id: str,
    mentioned_agents: list
):
    """
    Route request directly to mentioned agents.
    
    Supports: research, writer, editor, search, citation, synthesis, planner
    """
    await manager.complete_step(job, "analyzing")
    
    # Map agent names to handlers
    agent_handlers = {
        # Research/Search agents
        'research': 'search',
        'search': 'search',
        'academic': 'search',
        'papers': 'search',
        
        # Writing agents  
        'writer': 'write',
        'write': 'write',
        'author': 'write',
        
        # Synthesis agents
        'synthesis': 'synthesis',
        'synthesize': 'synthesis',
        'review': 'synthesis',
        'literature': 'synthesis',
        
        # Citation agents
        'citation': 'citation',
        'cite': 'citation',
        'reference': 'citation',
        
        # Editor agents
        'editor': 'edit',
        'edit': 'edit',
        'proofread': 'edit',
        
        # Planner agents
        'planner': 'plan',
        'plan': 'plan',
        'outline': 'plan',
    }
    
    # Determine primary action from mentioned agents
    primary_action = None
    for agent in mentioned_agents:
        agent_lower = agent.lower()
        if agent_lower in agent_handlers:
            primary_action = agent_handlers[agent_lower]
            break
    
    if not primary_action:
        # Default to complex task handling
        await manager.emit_log(job.job_id, f"⚠️ Unknown agent(s): {mentioned_agents}, using default processing")
        from services.task_classifier import classify_task
        task_type = classify_task(message)
        await process_complex_task(job, manager, message, workspace_id, task_type)
        return
    
    await manager.emit_log(job.job_id, f"🎯 Routing to {primary_action} handler")
    
    # Route to specific handler
    if primary_action == 'search':
        await process_paper_search(job, manager, message, workspace_id)
    
    elif primary_action == 'synthesis':
        await process_synthesis(job, manager, message, workspace_id)
    
    elif primary_action == 'write':
        await process_write_request(job, manager, message, workspace_id)
    
    elif primary_action == 'citation':
        await process_citation_request(job, manager, message, workspace_id)
    
    elif primary_action == 'edit':
        await process_edit_request(job, manager, message, workspace_id)
    
    elif primary_action == 'plan':
        await process_plan_request(job, manager, message, workspace_id)
    
    else:
        # Fallback to complex task
        from services.task_classifier import classify_task
        task_type = classify_task(message)
        await process_complex_task(job, manager, message, workspace_id, task_type)


async def process_write_request(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle direct writing requests from @writer agent."""
    from core.llm_client import LLMClient
    
    await manager.add_step(job, "writing", "running")
    await manager.update_progress(job, 0.2, "Writing content...")
    
    llm = LLMClient()
    response = ""
    
    system = """You are an expert academic writer. Write clear, well-structured, scholarly content.
Use proper academic language and citation format when referencing sources.
Be thorough but concise."""
    
    async for chunk in llm.stream_generate(message, system=system):
        response += chunk
        await manager.emit_content(job.job_id, chunk)
    
    await manager.complete_step(job, "writing")
    job.result = {"type": "write", "content": response}
    await manager.update_progress(job, 1.0, "Complete")


async def process_citation_request(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle citation requests from @citation agent."""
    from services.sources_service import sources_service
    
    await manager.add_step(job, "citing", "running")
    await manager.update_progress(job, 0.3, "Generating citations...")
    
    # Get all sources from workspace
    sources = sources_service.list_sources(workspace_id)
    
    if not sources:
        await manager.emit_content(job.job_id, "No sources found in workspace. Add papers first using @search.")
        job.result = {"type": "citation", "content": "No sources"}
    else:
        # Generate BibTeX
        bibtex = sources_service.generate_bibtex(workspace_id)
        response = f"## References ({len(sources)} sources)\n\n```bibtex\n{bibtex}\n```"
        await manager.emit_content(job.job_id, response)
        job.result = {"type": "citation", "content": bibtex, "count": len(sources)}
    
    await manager.complete_step(job, "citing")
    await manager.update_progress(job, 1.0, "Complete")


async def process_edit_request(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle editing requests from @editor agent."""
    from core.llm_client import LLMClient
    
    await manager.add_step(job, "editing", "running")
    await manager.update_progress(job, 0.2, "Editing content...")
    
    llm = LLMClient()
    response = ""
    
    system = """You are an expert academic editor. Your task is to:
1. Improve clarity and flow
2. Fix grammar and spelling
3. Enhance academic tone
4. Ensure logical organization
5. Maintain consistency

Provide the edited version with brief notes on major changes."""
    
    async for chunk in llm.stream_generate(f"Edit and improve the following:\n\n{message}", system=system):
        response += chunk
        await manager.emit_content(job.job_id, chunk)
    
    await manager.complete_step(job, "editing")
    job.result = {"type": "edit", "content": response}
    await manager.update_progress(job, 1.0, "Complete")


async def process_plan_request(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle planning requests from @planner agent."""
    from services.planner import planner_service
    
    await manager.add_step(job, "planning", "running")
    await manager.update_progress(job, 0.2, "Creating plan...")
    
    plan = await planner_service.create_plan(
        topic=message,
        case_study="",
        workspace_id=workspace_id
    )
    
    # Format plan for display
    response = f"## Research Plan\n\n"
    response += f"**Topic:** {plan.get('topic', message)}\n\n"
    response += "### Steps:\n\n"
    
    for i, step in enumerate(plan.get('steps', []), 1):
        response += f"{i}. **{step.get('name', 'Step')}**: {step.get('description', '')}\n"
    
    await manager.emit_content(job.job_id, response)
    await manager.complete_step(job, "planning", {"plan": plan})
    job.result = {"type": "plan", "plan": plan}
    await manager.update_progress(job, 1.0, "Complete")


async def process_simple_question(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle simple questions with direct AI response."""
    from core.llm_client import LLMClient
    
    await manager.add_step(job, "answering", "running")
    await manager.update_progress(job, 0.3, "Generating response...")
    
    llm = LLMClient()
    response = ""
    
    async for chunk in llm.stream_generate(
        f"Answer this question concisely:\n\n{message}",
        system="You are a helpful research assistant. Be concise and accurate."
    ):
        response += chunk
        await manager.emit_content(job.job_id, chunk)
    
    await manager.complete_step(job, "answering", {"response": response})
    job.result = {"type": "answer", "content": response}
    await manager.update_progress(job, 1.0, "Complete")


async def process_paper_search(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """Handle paper search requests."""
    from services.sources_service import sources_service
    import re
    
    await manager.add_step(job, "searching", "running")
    await manager.update_progress(job, 0.2, "Searching academic databases...")
    
    # Extract search query
    query = message
    patterns = [
        r"(?:search|find|look for|get)(?: me)?(?: papers?| articles?| research)? (?:on|about|for|regarding) (.+)",
        r"papers? (?:on|about) (.+)",
        r"research (?:on|about) (.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            break
    
    await manager.emit_log(job.job_id, f"🔍 Searching for: {query}")
    
    # Search papers
    result = await sources_service.search_and_save(
        workspace_id=workspace_id,
        query=query,
        max_results=10,
        auto_save=True
    )
    
    await manager.update_progress(job, 0.8, f"Found {result['total_results']} papers...")
    
    # Format response
    response = f"## Found {result['total_results']} papers on \"{query}\"\n\n"
    for i, paper in enumerate(result['results'][:10], 1):
        authors = paper.get('authors', [])
        author_str = ", ".join([a.get('name', a) if isinstance(a, dict) else a for a in authors[:2]])
        if len(authors) > 2:
            author_str += " et al."
        
        response += f"**{i}. {paper.get('title', 'Untitled')}**\n"
        response += f"   {author_str} ({paper.get('year', 'N/A')})\n"
        response += f"   Citations: {paper.get('citationCount', 0)}\n\n"
    
    await manager.emit_content(job.job_id, response)
    await manager.complete_step(job, "searching", {"papers_found": result['total_results']})
    
    job.result = {"type": "search", "query": query, "results": result}
    await manager.update_progress(job, 1.0, "Complete")


async def process_synthesis(job: 'Job', manager: 'JobManager', message: str, workspace_id: str):
    """
    Handle literature synthesis requests.
    
    Reads all collected sources and generates a well-cited synthesis report.
    """
    from services.literature_synthesis import literature_synthesis_service
    import re
    
    await manager.add_step(job, "synthesizing", "running")
    await manager.emit_log(job.job_id, "📚 Starting literature synthesis...")
    
    # Extract topic from message
    topic = message
    topic_patterns = [
        r"(?:synthesize|synthesis|review|summarize|analyze)(?: literature| sources| papers)?(?: on| about| for| regarding)? (.+)",
        r"(?:write|create|generate)(?: a)?(?: literature)? (?:review|synthesis)(?: on| about| for)? (.+)",
    ]
    for pattern in topic_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            break
    
    await manager.emit_log(job.job_id, f"📖 Synthesizing literature on: {topic}")
    
    # Stream synthesis to user
    full_content = ""
    async for chunk in literature_synthesis_service.synthesize_literature(
        workspace_id=workspace_id,
        topic=topic,
        job_manager=manager,
        job_id=job.job_id
    ):
        full_content += chunk
        await manager.emit_content(job.job_id, chunk)
    
    await manager.complete_step(job, "synthesizing", {"word_count": len(full_content.split())})
    
    # Save synthesis to file
    from services.workspace_service import WORKSPACES_DIR
    from datetime import datetime
    
    output_dir = WORKSPACES_DIR / workspace_id / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path = output_dir / filename
    output_path.write_text(full_content, encoding='utf-8')
    
    await manager.emit_log(job.job_id, f"💾 Saved synthesis to: outputs/{filename}")
    
    job.result = {
        "type": "synthesis",
        "topic": topic,
        "content": full_content,
        "file_path": str(output_path),
        "word_count": len(full_content.split())
    }
    await manager.update_progress(job, 1.0, "Complete")


async def process_complex_task(job: 'Job', manager: 'JobManager', message: str, workspace_id: str, task_type: str):
    """Handle complex tasks that require planning and multi-step execution."""
    from services.planner import planner_service
    from workers.task_worker import TaskWorker
    
    # Step 1: Planning
    await manager.add_step(job, "planning", "running")
    await manager.update_progress(job, 0.1, "Creating plan...")
    await manager.emit_log(job.job_id, "🧠 Analyzing and creating plan...")
    
    plan = await planner_service.create_plan(
        topic=message,
        case_study="",
        workspace_id=workspace_id
    )
    
    await manager.emit_log(job.job_id, f"✅ Plan created with {len(plan.get('steps', []))} steps")
    await manager.complete_step(job, "planning", {"plan": plan})
    
    # Stream plan to user
    plan_text = f"## Plan\n\n"
    for i, step in enumerate(plan.get('steps', []), 1):
        plan_text += f"{i}. {step.get('description', step.get('name', 'Step'))}\n"
    await manager.emit_content(job.job_id, plan_text)
    
    # Step 2: Execute plan steps
    steps = plan.get('steps', [])
    total_steps = len(steps)
    
    if total_steps == 0:
        await manager.emit_log(job.job_id, "⚠️ No steps in plan")
        job.result = {"type": "plan_only", "plan": plan}
        return
    
    worker = TaskWorker(workspace_id)
    results = []
    
    for i, step in enumerate(steps):
        step_name = step.get('name', f'step_{i+1}')
        step_desc = step.get('description', step_name)
        
        # Check for pause/cancel between steps
        await manager.update_progress(
            job, 
            0.2 + (0.7 * (i / total_steps)), 
            f"Executing: {step_desc[:50]}..."
        )
        
        await manager.add_step(job, step_name, "running")
        await manager.emit_log(job.job_id, f"⚡ Executing step {i+1}/{total_steps}: {step_desc[:50]}...")
        
        try:
            result = await worker.execute_step(step, job_id=job.job_id)
            results.append(result)
            
            # Stream generated content if any
            if result.get('content'):
                await manager.emit_content(job.job_id, result['content'], result.get('file_path'))
            
            await manager.complete_step(job, step_name, result)
            
        except Exception as e:
            await manager.emit_log(job.job_id, f"⚠️ Step failed: {e}", "warning")
            await manager.complete_step(job, step_name, {"error": str(e)})
    
    # Finalize
    await manager.update_progress(job, 1.0, "Complete")
    job.result = {"type": "complex", "plan": plan, "results": results}
    await manager.emit_log(job.job_id, "✅ All steps completed!")


def is_simple_question(message: str) -> bool:
    """Check if message is a simple question."""
    message_lower = message.lower().strip()
    
    # Quick info patterns
    simple_patterns = [
        "what is", "what are", "who is", "who are",
        "define", "explain", "describe",
        "how do you", "how does",
        "give me", "tell me about",
        "write the equation", "write einstein",
    ]
    
    # Check if short and simple
    if len(message_lower.split()) <= 15:
        for pattern in simple_patterns:
            if message_lower.startswith(pattern):
                return True
    
    return False


def is_paper_search_request(message: str) -> bool:
    """Check if message is a paper search request."""
    message_lower = message.lower()
    
    search_patterns = [
        "search for papers",
        "find papers",
        "search papers",
        "look for papers",
        "find me papers",
        "search for research",
        "find articles",
        "academic search",
        "look up papers",
        "get papers on",
    ]
    
    return any(pattern in message_lower for pattern in search_patterns)


def is_synthesis_request(message: str) -> bool:
    """Check if message is a literature synthesis request."""
    message_lower = message.lower()
    
    synthesis_patterns = [
        "synthesize",
        "synthesis",
        "literature review",
        "review the literature",
        "analyze the sources",
        "analyze sources",
        "summarize the papers",
        "summarize papers",
        "summarize the sources",
        "summarize sources",
        "write a review",
        "create a synthesis",
        "generate a synthesis",
        "combine the sources",
        "integrate the literature",
    ]
    
    return any(pattern in message_lower for pattern in synthesis_patterns)

