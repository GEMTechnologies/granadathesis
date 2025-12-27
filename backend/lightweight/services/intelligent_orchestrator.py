"""
Intelligent Agent Orchestrator

A dynamic AI agent that can reason about tasks and call ANY available tool/service
at any step. All actions are streamed to the frontend in real-time.

Features:
- LLM-based reasoning to decide next action
- Access to all system tools and services
- Real-time streaming of thought process and actions
- Self-correcting behavior on errors
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime

from services.deepseek_direct import deepseek_direct_service


class IntelligentOrchestrator:
    """
    Dynamic agent that thinks and acts, calling tools as needed.
    
    Not a fixed pipeline - uses LLM reasoning to decide actions.
    """
    
    # All available tools the agent can use
    AVAILABLE_TOOLS = {
        # File operations
        "list_files": {
            "description": "List files in a directory",
            "parameters": {"path": "string - directory path (optional, defaults to workspace root)"}
        },
        "read_file": {
            "description": "Read contents of a file",
            "parameters": {"path": "string - file path to read"}
        },
        "write_file": {
            "description": "Write content to a file",
            "parameters": {"path": "string - file path", "content": "string - file content"}
        },
        "create_folder": {
            "description": "Create a folder",
            "parameters": {"path": "string - folder path to create"}
        },
        
        # Research tools
        "search_papers": {
            "description": "Search for academic papers on a topic",
            "parameters": {"query": "string - search query", "max_results": "number - max papers (default 10)"}
        },
        "synthesize_literature": {
            "description": "Generate a synthesis/review of papers in the workspace",
            "parameters": {"topic": "string - focus topic for synthesis"}
        },
        "get_sources": {
            "description": "List all academic sources/papers in the workspace",
            "parameters": {}
        },
        
        # Search tools
        "web_search": {
            "description": "Search the web for information",
            "parameters": {"query": "string - search query"}
        },
        "image_search": {
            "description": "Search for images on a topic",
            "parameters": {"query": "string - image search query", "limit": "number - max images (default 5)"}
        },
        
        # Generation tools
        "image_generate": {
            "description": "Generate an AI image from a prompt",
            "parameters": {"prompt": "string - image generation prompt", "size": "string - size (default 1024x1024)"}
        },
        "generate_content": {
            "description": "Generate text content on a topic",
            "parameters": {"topic": "string - what to write about", "style": "string - academic/casual/technical", "length": "string - short/medium/long"}
        },
        
        # Analysis tools
        "summarize_pdf": {
            "description": "Summarize a PDF document",
            "parameters": {"filename": "string - PDF filename (optional, uses most recent if not specified)"}
        },
        "analyze_data": {
            "description": "Analyze a data file (CSV, Excel, JSON)",
            "parameters": {"filename": "string - data file name"}
        },
        
        # Planning
        "create_outline": {
            "description": "Create a structured outline for a document",
            "parameters": {"topic": "string - document topic", "sections": "number - number of sections (default 5)"}
        },
        
        # Thinking/Reasoning (meta-tool)
        "think": {
            "description": "Pause to think/reason about the problem before acting",
            "parameters": {"question": "string - what to think about"}
        },
        
        # Completion
        "complete": {
            "description": "Mark task as complete and provide final response",
            "parameters": {"response": "string - final response to user", "files_created": "list - any files created"}
        }
    }
    
    def __init__(self):
        self.max_iterations = 15  # Prevent infinite loops
        self.current_context = []  # Accumulated results
    
    async def _execute_tool(self, tool_name: str, arguments: Dict, workspace_id: str) -> Dict:
        """Execute a tool and return results."""
        
        if tool_name == "search_papers":
            from services.sources_service import sources_service
            result = await sources_service.search_and_save(
                workspace_id=workspace_id,
                query=arguments.get("query", ""),
                max_results=arguments.get("max_results", 10),
                auto_save=True
            )
            return {
                "status": "success",
                "papers_found": result.get("total_results", 0),
                "papers_saved": result.get("saved_count", 0),
                "papers": [{"title": p.get("title"), "authors": p.get("authors", [])[:2], "year": p.get("year")} 
                          for p in result.get("results", [])[:5]]
            }
        
        elif tool_name == "synthesize_literature":
            from services.literature_synthesis import literature_synthesis_service
            content = ""
            async for chunk in literature_synthesis_service.synthesize_literature(
                workspace_id=workspace_id,
                topic=arguments.get("topic", ""),
                output_format="markdown"
            ):
                content += chunk
            return {"status": "success", "content": content, "word_count": len(content.split())}
        
        elif tool_name == "get_sources":
            from services.sources_service import sources_service
            sources = sources_service.list_sources(workspace_id)
            return {
                "status": "success",
                "sources": [{"title": s.get("title"), "year": s.get("year")} for s in sources[:10]],
                "total": len(sources)
            }
        
        elif tool_name == "web_search":
            from services.web_search import web_search_service
            results = await web_search_service.search(arguments.get("query", ""), max_results=5)
            return {"status": "success", "results": results[:5]}
        
        elif tool_name == "image_search":
            from services.intelligent_image_search import intelligent_image_search_service
            results = await intelligent_image_search_service.search(
                arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )
            return {"status": "success", "images": [r.get("url") for r in results[:5]] if results else []}
        
        elif tool_name == "image_generate":
            from services.image_generation import image_generation_service
            result = await image_generation_service.generate(
                prompt=arguments.get("prompt", ""),
                size=arguments.get("size", "1024x1024")
            )
            return {"status": "success" if result.get("success") else "error", 
                    "image_url": result.get("image_url") or result.get("url")}
        
        elif tool_name == "generate_content":
            content = await deepseek_direct_service.generate_content(
                prompt=f"Write {arguments.get('length', 'medium')}-length {arguments.get('style', 'academic')} content about: {arguments.get('topic', '')}",
                max_tokens=2000
            )
            return {"status": "success", "content": content}
        
        elif tool_name == "summarize_pdf":
            from services.pdf_service import get_pdf_service
            from services.workspace_service import WORKSPACES_DIR
            
            pdf_service = get_pdf_service()
            workspace_path = WORKSPACES_DIR / workspace_id
            
            # Find PDF
            pdf_files = list(workspace_path.rglob("*.pdf"))
            if not pdf_files:
                return {"status": "error", "error": "No PDF files found in workspace"}
            
            pdf_path = pdf_files[0]
            text = pdf_service.extract_text_simple(pdf_path)
            
            summary = await deepseek_direct_service.generate_content(
                prompt=f"Summarize this document:\n\n{text[:10000]}",
                max_tokens=1000
            )
            return {"status": "success", "summary": summary, "file": pdf_path.name}
        
        elif tool_name == "create_outline":
            from services.planner import planner_service
            outline = await planner_service.generate_outline(
                topic=arguments.get("topic", ""),
                word_count=1500
            )
            return {"status": "success", "outline": outline}
        
        elif tool_name in ["list_files", "read_file", "write_file", "create_folder"]:
            # Delegate to existing execute_tool
            from services.workspace_service import WORKSPACES_DIR
            workspace_path = WORKSPACES_DIR / workspace_id
            
            if tool_name == "list_files":
                path = arguments.get("path", "")
                search_path = workspace_path / path if path else workspace_path
                if not search_path.exists():
                    return {"status": "success", "files": []}
                files = [{"name": f.name, "type": "folder" if f.is_dir() else "file"} 
                        for f in search_path.iterdir() if not f.name.startswith('.')]
                return {"status": "success", "files": files}
            
            elif tool_name == "read_file":
                file_path = workspace_path / arguments.get("path", "")
                if file_path.exists() and file_path.is_file():
                    return {"status": "success", "content": file_path.read_text()[:5000]}
                return {"status": "error", "error": "File not found"}
            
            elif tool_name == "write_file":
                file_path = workspace_path / arguments.get("path", "output.md")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(arguments.get("content", ""), encoding='utf-8')
                return {"status": "success", "file": str(file_path.name)}
        
        elif tool_name == "think":
            # Meta-tool for reasoning
            thought = await deepseek_direct_service.generate_content(
                prompt=f"Think step by step about: {arguments.get('question', '')}",
                max_tokens=500
            )
            return {"status": "success", "thought": thought}
        
        elif tool_name == "complete":
            return {
                "status": "complete",
                "response": arguments.get("response", "Task completed"),
                "files_created": arguments.get("files_created", [])
            }
        
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}
    
    async def _get_next_action(self, task: str, history: List[Dict]) -> Dict:
        """Use LLM to decide the next action based on task and history."""
        
        # Format tools for prompt
        tools_desc = "\n".join([
            f"- **{name}**: {info['description']}\n  Parameters: {json.dumps(info['parameters'])}"
            for name, info in self.AVAILABLE_TOOLS.items()
        ])
        
        # Format history
        history_text = ""
        for h in history[-5:]:  # Last 5 actions to avoid context overflow
            history_text += f"\n[{h['action']}] {h.get('tool', 'N/A')}: {json.dumps(h.get('result', {}))[:300]}..."
        
        prompt = f"""You are an intelligent AI agent. Analyze the task and decide the NEXT action.

## TASK
{task}

## AVAILABLE TOOLS
{tools_desc}

## ACTION HISTORY
{history_text if history_text else "No actions taken yet."}

## INSTRUCTIONS
1. Think about what needs to be done to complete the task
2. Consider what's already been done (see history)
3. Choose the SINGLE next best action
4. If the task is complete, use the "complete" tool

Respond with ONLY a JSON object (no markdown):
{{"tool": "tool_name", "arguments": {{"arg1": "value1"}}, "reasoning": "Why this action"}}
"""
        
        response = await deepseek_direct_service.generate_content(
            prompt=prompt,
            system_prompt="You are a task execution agent. Respond only with valid JSON. Choose actions that make progress toward completing the task.",
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse JSON from response
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            return json.loads(response)
        except:
            # Fallback
            return {"tool": "think", "arguments": {"question": f"How to approach: {task}"}, "reasoning": "Need to plan"}
    
    async def run(
        self,
        task: str,
        workspace_id: str,
        session_id: str,
        job_id: str
    ) -> AsyncGenerator[Dict, None]:
        """
        Run the intelligent agent on a task.
        
        Yields SSE events for each action taken.
        """
        from core.events import events
        
        history = []
        iteration = 0
        
        await events.connect()
        
        # Start event
        yield {"event": "agent_start", "data": json.dumps({
            "task": task,
            "timestamp": datetime.now().isoformat()
        })}
        
        await events.log(job_id, f"🧠 Starting intelligent agent: {task[:50]}...", "info", session_id=session_id)
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get next action from LLM
            yield {"event": "thinking", "data": json.dumps({
                "message": "Deciding next action...",
                "iteration": iteration
            })}
            
            try:
                action = await self._get_next_action(task, history)
            except Exception as e:
                yield {"event": "error", "data": json.dumps({"message": f"Reasoning error: {e}"})}
                break
            
            tool_name = action.get("tool", "think")
            arguments = action.get("arguments", {})
            reasoning = action.get("reasoning", "")
            
            # Emit action event
            yield {"event": "action", "data": json.dumps({
                "tool": tool_name,
                "arguments": arguments,
                "reasoning": reasoning,
                "iteration": iteration
            })}
            
            await events.log(job_id, f"🔧 [{tool_name}] {reasoning[:50]}...", "info", session_id=session_id)
            
            # Check for completion
            if tool_name == "complete":
                yield {"event": "result", "data": json.dumps({
                    "tool": "complete",
                    "result": arguments
                })}
                
                yield {"event": "agent_complete", "data": json.dumps({
                    "response": arguments.get("response", "Task completed"),
                    "files": arguments.get("files_created", []),
                    "iterations": iteration
                })}
                
                await events.log(job_id, f"✅ Task complete!", "info", session_id=session_id)
                break
            
            # Execute the tool
            try:
                result = await self._execute_tool(tool_name, arguments, workspace_id)
                
                # Emit result
                yield {"event": "result", "data": json.dumps({
                    "tool": tool_name,
                    "result": result
                })}
                
                # Add to history
                history.append({
                    "action": f"iteration_{iteration}",
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result
                })
                
                # If synthesis was run, stream the content
                if tool_name == "synthesize_literature" and result.get("content"):
                    content = result["content"]
                    accumulated = ""
                    # Stream in chunks for better UX
                    chunk_size = 200
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i+chunk_size]
                        accumulated += chunk
                        yield {"event": "response_chunk", "data": json.dumps({
                            "chunk": chunk,
                            "accumulated": accumulated
                        })}
                        await asyncio.sleep(0.05)
                
            except Exception as e:
                yield {"event": "tool_error", "data": json.dumps({
                    "tool": tool_name,
                    "error": str(e)
                })}
                history.append({
                    "action": f"iteration_{iteration}",
                    "tool": tool_name,
                    "error": str(e)
                })
            
            await asyncio.sleep(0.1)  # Small delay between actions
        
        if iteration >= self.max_iterations:
            yield {"event": "agent_complete", "data": json.dumps({
                "response": "Reached maximum iterations. Task may be incomplete.",
                "iterations": iteration
            })}


# Singleton
intelligent_orchestrator = IntelligentOrchestrator()
