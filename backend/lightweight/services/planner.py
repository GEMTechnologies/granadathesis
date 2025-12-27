"""
Planner Service - Reasoning and Plan Generation with Memory

Uses a reasoning model (e.g., GPT-4, Claude) to analyze user requests
and generate a structured plan before execution. Includes chat history
and workspace context for better memory.
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable
import json
from services.openrouter import openrouter_service
from services.deepseek_direct import deepseek_direct_service
from services.chat_history_service import chat_history_service
from services.workspace_service import WORKSPACES_DIR
from services.skills_manager import get_skills_manager
from pathlib import Path

class PlannerService:
    """
    Service for generating plans from user requests with memory/context.
    """
    
    def __init__(self):
        self.system_prompt = """You are an expert planning agent. Your goal is to analyze the user's request and create a step-by-step plan to achieve it.

        CRITICAL: You have access to conversation history and workspace state. You MUST use this context to:
        - Understand references like "it", "that folder", "the file we just created", "open it"
        - If user says "open it", look in recent actions for the LAST created folder/file
        - If user says "that folder", match to the most recent folder mentioned
        - Remember recent actions and their results
        - Know what files and folders exist in the workspace
        
        When user says "open it" or "open that folder":
        1. Check the MOST RECENT action in conversation history
        2. If a folder was just created, "it" refers to that folder
        3. Use list_files with that folder path
        
        You have access to the following tools:
        - list_files(path): List files in a directory. Use "." for root, "folder_name" for a folder.
        - read_file(path): Read the content of a file.
        - save_file(path, content): Create or update a file.
        - create_folder(path): Create a new folder.
        - delete_file(path): Delete a file or folder.
        - rename_file(old_path, new_path): Rename a file or folder.
        - web_search(query): Search the internet for information. Use this for maps, images, current events, etc.
        - image_search(query, limit): Search for images from multiple sources (Unsplash, Pexels, Pixabay). Use when user wants to see images, not just links.
        - image_generate(prompt, size, model): Generate an image using AI (DALL-E or Stable Diffusion). Use when user wants to create a new image.
        - analyze_image(image_path, prompt): Analyze an image using vision-capable LLM. Use when user uploads an image or asks about an image in workspace. Can understand what's in images, describe them, answer questions about them.
        
        Output your plan as a JSON object with the following structure:
        {
            "reasoning": "Explanation of your thought process...",
            "plan": [
                {
                    "step": 1,
                    "description": "Description of the step",
                    "tool": "tool_name",
                    "arguments": { "arg_name": "arg_value" }
                },
                ...
            ]
        }
        
        Keep the plan concise and efficient. If the request is simple (e.g., "hello"), you can return a plan with a single step or no steps if no tools are needed.
        """

    async def build_context(self, session_id: str, workspace_id: str, user_id: str = "default") -> str:
        """
        Build comprehensive context including chat history and workspace state.
        """
        context_parts = []
        
        # 1. Get chat history (last 10 messages) - MOST RECENT FIRST
        try:
            from services.chat_history_service import chat_history_service
            history = await chat_history_service.get_history(user_id, session_id, limit=10)
            if history:
                context_parts.append("=== RECENT CONVERSATION HISTORY (MOST RECENT FIRST) ===\n")
                # Show last 5 messages with full details
                for entry in reversed(history[-5:]):  # Reverse to show newest first
                    user_msg = entry.get('message', '')
                    assistant_resp = entry.get('response', '')
                    metadata = entry.get('metadata', {})
                    recent_actions = metadata.get('recent_actions', [])
                    
                    context_parts.append(f"User: {user_msg}")
                    if recent_actions:
                        context_parts.append(f"  → Actions taken: {', '.join(recent_actions)}")
                    context_parts.append(f"Assistant: {assistant_resp[:300]}...")
                    context_parts.append("")
        except Exception as e:
            print(f"⚠️ Error loading chat history for context: {e}")
        
        # 2. Get workspace files/folders (current state)
        try:
            workspace_path = WORKSPACES_DIR / workspace_id
            if workspace_path.exists():
                files = []
                folders = []
                for item in workspace_path.rglob("*"):
                    if item.name.startswith('.') or item.name == "workspace.json":
                        continue
                    rel_path = str(item.relative_to(workspace_path))
                    if item.is_file():
                        files.append(rel_path)
                    elif item.is_dir():
                        folders.append(rel_path)
                
                if files or folders:
                    context_parts.append("=== CURRENT WORKSPACE STATE ===\n")
                    if folders:
                        context_parts.append(f"Folders: {', '.join(folders[:20])}")  # Limit to 20
                    if files:
                        context_parts.append(f"Files: {', '.join(files[:20])}")  # Limit to 20
                    context_parts.append("")
        except Exception as e:
            print(f"⚠️ Error loading workspace state for context: {e}")
        
        return "\n".join(context_parts)

    async def generate_plan(
        self, 
        user_request: str, 
        session_id: str = "default", 
        workspace_id: str = "default", 
        user_id: str = "default",
        job_id: Optional[str] = None,
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        mentioned_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a plan for the given user request with full context and relevant skills.
        
        Args:
            user_request: User's request
            session_id: Session ID
            workspace_id: Workspace ID
            user_id: User ID
            job_id: Job ID for streaming events
            stream: Whether to stream the reasoning
        """
        # Build comprehensive context
        context = await self.build_context(session_id, workspace_id, user_id)
        
        # Get relevant skills for the task
        skills_manager = get_skills_manager()
        relevant_skills = skills_manager.get_skills_for_task(user_request)
        
        # Enhance system prompt with skill instructions
        enhanced_system_prompt = self.system_prompt
        if relevant_skills:
            skill_names = [skill.name for skill in relevant_skills]
            enhanced_system_prompt = skills_manager.inject_skill_instructions(
                skill_names, 
                self.system_prompt
            )
            print(f"🔧 Using skills: {', '.join(skill_names)}")
        
        # Add mentioned agents context to prompt
        agents_context = ""
        if mentioned_agents and len(mentioned_agents) > 0:
            agents_context = f"""

IMPORTANT: The user has specifically requested these agents to handle this task:
{', '.join([f'@{agent}' for agent in mentioned_agents])}

When creating the plan, prioritize using tools and approaches that these agents specialize in:
- @research: Use web_search, image_search for research tasks
- @writer: Focus on content generation, save_file for writing tasks
- @editor: Use read_file, save_file for editing and refinement tasks
- @planner: Already active (you are the planner), focus on comprehensive planning
- @search: Use web_search, image_search extensively
- @citation: Focus on academic citations and references

Ensure the plan leverages the strengths of the mentioned agents."""
            print(f"🤖 Mentioned agents: {', '.join(mentioned_agents)}")
        
        prompt = f"""User Request: {user_request}

{context}
{agents_context}

CRITICAL INSTRUCTIONS FOR UNDERSTANDING REFERENCES:
- If user says "open it", "open that", "it" refers to the MOST RECENT item created/mentioned in conversation history
- Look at the "Actions taken" in recent messages to find what was just created
- If a folder was just created (like "hh"), then "open it" means list files in that folder
- Be explicit about what "it" refers to in your reasoning

Generate a plan. Your reasoning MUST explain what "it" or "that" refers to if the user uses such references."""
        
        try:
            # Check cache first
            from services.performance_cache import performance_cache
            cache_key_context = {
                "session_id": session_id,
                "workspace_id": workspace_id
            }
            cached_plan = await performance_cache.get_plan(user_request, cache_key_context)
            if cached_plan:
                print("✅ Using cached plan")
                return cached_plan
            
            # Use circuit breaker for API calls
            from services.circuit_breaker import circuit_breakers
            planner_cb = circuit_breakers["planner"]
            deepseek_cb = circuit_breakers["deepseek"]
            
            # For planning, use standard model (faster, more reliable)
            # Reasoning model is too slow and often times out
            needs_reasoning = False  # Disable reasoning for planning - use standard model
            
            # Try DeepSeek direct API first (faster, cheaper)
            try:
                if deepseek_direct_service.api_key:
                    import asyncio
                    # Use circuit breaker
                    async def call_deepseek():
                        if stream and stream_callback:
                            # Streaming mode
                            return await deepseek_direct_service.generate_content(
                                prompt=prompt,
                                system_prompt=enhanced_system_prompt,
                                temperature=0.2,
                                use_reasoning=False,
                                max_tokens=2000,  # Limit tokens for faster response
                                stream=True,
                                stream_callback=stream_callback
                            )
                        else:
                            # Non-streaming mode
                            return await deepseek_direct_service.generate_content(
                                prompt=prompt,
                                system_prompt=enhanced_system_prompt,
                                temperature=0.2,
                                use_reasoning=False,
                                max_tokens=2000  # Limit tokens for faster response
                            )
                    
                    response = await asyncio.wait_for(
                        deepseek_cb.call(call_deepseek),
                        timeout=60.0  # Increased to 60 seconds for complex requests
                    )
                else:
                    # API key not configured, skip to OpenRouter
                    raise ValueError("DeepSeek API key not configured")
            except Exception as cb_error:
                # Circuit breaker may have rejected the call
                if "Circuit breaker" in str(cb_error):
                    print(f"⚠️ Circuit breaker open: {cb_error}")
                    raise Exception("Service temporarily unavailable. Please try again in a moment.")
            except asyncio.TimeoutError:
                print(f"⚠️ DeepSeek API timeout")
                raise Exception("Planning API call timed out. Please try again with a simpler request.")
            except (ValueError, Exception) as e:
                print(f"⚠️ DeepSeek direct API failed or not configured, using OpenRouter fallback: {e}")
                # Fallback to OpenRouter with streaming support
                try:
                    import asyncio
                    if stream and stream_callback:
                        # Streaming mode
                        response = await asyncio.wait_for(
                            openrouter_service.generate_content(
                                prompt=prompt,
                                model_key="deepseek",
                                system_prompt=enhanced_system_prompt,
                                temperature=0.2,
                                stream=True,
                                stream_callback=stream_callback
                            ),
                            timeout=60.0
                        )
                    else:
                        # Non-streaming mode
                        response = await asyncio.wait_for(
                            openrouter_service.generate_content(
                                prompt=prompt,
                                model_key="deepseek",
                                system_prompt=enhanced_system_prompt,
                                temperature=0.2
                            ),
                            timeout=30.0
                        )
                except asyncio.TimeoutError:
                    print(f"⚠️ OpenRouter timeout")
                    raise Exception("Planning API call timed out. Please try again.")
                except Exception as openrouter_error:
                    print(f"⚠️ OpenRouter also failed: {openrouter_error}")
                    # Last resort: return error message instead of crashing
                    raise Exception(f"Both DeepSeek direct API and OpenRouter failed. DeepSeek error: {e}, OpenRouter error: {openrouter_error}")
            
            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            try:
                plan_result = json.loads(json_str)
                # Cache the plan
                await performance_cache.set_plan(user_request, cache_key_context, plan_result)
                return plan_result
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse JSON from planner response: {e}")
                print(f"Response was: {response[:500]}")
                # Try to extract JSON more flexibly
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
                raise Exception(f"Failed to parse planner response as JSON: {str(e)}")
            
        except Exception as e:
            print(f"Planning Error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback plan
            return {
                "reasoning": f"Failed to generate plan: {str(e)}",
                "plan": []
            }
    
    async def generate_outline(
        self,
        topic: str,
        word_count: int = 1000,
        include_images: bool = True,
        job_id: str = None,
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Generate a structured outline for parallel section writing.
        
        Returns:
            {
                "title": "Essay Title",
                "sections": [
                    {"id": 1, "heading": "Introduction", "word_target": 150, "needs_image": False},
                    {"id": 2, "heading": "Section 1", "word_target": 250, "needs_image": True, "image_prompt": "..."},
                    ...
                ],
                "total_sections": 4,
                "bibliography": True
            }
        """
        from core.events import events
        
        if job_id:
            await events.log(job_id, "🧠 Using AI reasoning to generate intelligent outline...")
        
        # Use DeepSeek reasoning model for intelligent outline generation
        # The model will determine the optimal structure based on the topic
        reasoning_prompt = f"""You are an expert essay/document planner. Analyze this topic and create the optimal outline:

TOPIC: "{topic}"
TARGET LENGTH: {word_count:,} words

YOUR TASK:
1. First, THINK about what type of document this needs:
   - Is it argumentative, expository, narrative, or analytical?
   - What are the key aspects that must be covered?
   - What logical flow makes sense for this specific topic?

2. Then create a CUSTOM outline structure that fits THIS SPECIFIC TOPIC.
   - Do NOT use generic sections like "Background", "Analysis", "Discussion"
   - Create sections with SPECIFIC, DESCRIPTIVE headings related to the topic
   - For example, for "Uganda Economy":
     * "Agricultural Sector and Coffee Exports"
     * "Oil Discovery and Economic Transformation" 
     * "Trade Relations with East African Community"
   - Each heading should tell the reader exactly what that section covers

3. Word distribution should be logical:
   - Introduction: ~10-15% of total
   - Body sections: Distribute remaining ~75-80%
   - Conclusion: ~10% of total
   - More important topics get more words

4. Determine if visuals would help each section

OUTPUT FORMAT - JSON ONLY:
{{
    "title": "Specific, engaging title for the document",
    "document_type": "argumentative|expository|analytical|narrative",
    "sections": [
        {{
            "id": 1,
            "heading": "Specific Section Title",
            "word_target": 150,
            "key_points": ["point 1", "point 2"],
            "needs_image": true,
            "image_prompt": "specific image search query"
        }}
    ],
    "bibliography": true
}}

IMPORTANT:
- Total word count across all sections must equal approximately {word_count:,}
- Create the RIGHT number of sections for a {word_count:,}-word document (usually 3-7 for short essays, more for longer)
- EVERY section heading must be unique and specific to the topic
- NO generic headings like "Main Body" or "Discussion"

Generate the outline now:"""

        try:
            # Use DeepSeek reasoning model for intelligent analysis
            if job_id:
                await events.log(job_id, "🔍 Analyzing topic and determining optimal structure...")
            
            response = await deepseek_direct_service.generate_with_reasoning(
                prompt=reasoning_prompt,
                max_tokens=4000,
                temperature=0.3  # Slightly creative but structured
            )
            
            # Parse JSON from response
            import re
            
            # Handle potential markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                # Try to find JSON object
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")
            
            outline = json.loads(json_str)
            outline["total_sections"] = len(outline.get("sections", []))
            
            # Validate and fix word targets if needed
            total_words = sum(s.get("word_target", 0) for s in outline.get("sections", []))
            if abs(total_words - word_count) > word_count * 0.2:  # More than 20% off
                # Adjust proportionally
                ratio = word_count / max(1, total_words)
                for section in outline.get("sections", []):
                    section["word_target"] = int(section.get("word_target", 100) * ratio)
            
            if job_id:
                section_titles = [s.get("heading", "?") for s in outline.get("sections", [])]
                await events.log(job_id, f"📋 Generated {outline['total_sections']}-section outline:")
                for i, title in enumerate(section_titles):
                    word_target = outline["sections"][i].get("word_target", 0)
                    await events.log(job_id, f"   {i+1}. {title} ({word_target} words)")
            
            return outline
                
        except Exception as e:
            print(f"⚠️ Intelligent outline generation error: {e}")
            if job_id:
                await events.log(job_id, f"⚠️ Falling back to template outline due to: {str(e)[:50]}")
            
            # Smart fallback - at least make it topic-aware
            topic_lower = topic.lower()
            
            # Determine essay type from topic keywords
            if any(word in topic_lower for word in ["compare", "contrast", "vs", "versus"]):
                sections = [
                    {"id": 1, "heading": "Introduction", "word_target": int(word_count * 0.12), "needs_image": False},
                    {"id": 2, "heading": f"Overview of {topic.split()[0] if topic else 'First Subject'}", "word_target": int(word_count * 0.22), "needs_image": True, "image_prompt": topic},
                    {"id": 3, "heading": "Comparative Analysis", "word_target": int(word_count * 0.28), "needs_image": False},
                    {"id": 4, "heading": "Key Differences and Similarities", "word_target": int(word_count * 0.25), "needs_image": True, "image_prompt": topic},
                    {"id": 5, "heading": "Conclusion", "word_target": int(word_count * 0.13), "needs_image": False}
                ]
            elif any(word in topic_lower for word in ["history", "evolution", "development", "rise", "fall"]):
                sections = [
                    {"id": 1, "heading": "Introduction", "word_target": int(word_count * 0.12), "needs_image": False},
                    {"id": 2, "heading": "Historical Background", "word_target": int(word_count * 0.22), "needs_image": True, "image_prompt": f"historical {topic}"},
                    {"id": 3, "heading": "Key Developments", "word_target": int(word_count * 0.28), "needs_image": False},
                    {"id": 4, "heading": "Modern Implications", "word_target": int(word_count * 0.25), "needs_image": True, "image_prompt": f"modern {topic}"},
                    {"id": 5, "heading": "Conclusion", "word_target": int(word_count * 0.13), "needs_image": False}
                ]
            elif any(word in topic_lower for word in ["economy", "economic", "gdp", "trade", "market"]):
                sections = [
                    {"id": 1, "heading": "Introduction", "word_target": int(word_count * 0.12), "needs_image": False},
                    {"id": 2, "heading": "Economic Overview", "word_target": int(word_count * 0.20), "needs_image": True, "image_prompt": f"{topic} statistics chart"},
                    {"id": 3, "heading": "Key Economic Sectors", "word_target": int(word_count * 0.25), "needs_image": True, "image_prompt": topic},
                    {"id": 4, "heading": "Challenges and Opportunities", "word_target": int(word_count * 0.25), "needs_image": False},
                    {"id": 5, "heading": "Future Outlook", "word_target": int(word_count * 0.10), "needs_image": False},
                    {"id": 6, "heading": "Conclusion", "word_target": int(word_count * 0.08), "needs_image": False}
                ]
            else:
                # Generic but still somewhat topic-aware
                sections = [
                    {"id": 1, "heading": "Introduction", "word_target": int(word_count * 0.12), "needs_image": False},
                    {"id": 2, "heading": f"Understanding {topic.split()[0] if topic else 'the Topic'}", "word_target": int(word_count * 0.25), "needs_image": True, "image_prompt": topic},
                    {"id": 3, "heading": "Key Aspects and Analysis", "word_target": int(word_count * 0.30), "needs_image": False},
                    {"id": 4, "heading": "Implications and Perspectives", "word_target": int(word_count * 0.20), "needs_image": True, "image_prompt": topic},
                    {"id": 5, "heading": "Conclusion", "word_target": int(word_count * 0.13), "needs_image": False}
                ]
            
            return {
                "title": f"Essay on {topic}",
                "document_type": "expository",
                "sections": sections,
                "total_sections": len(sections),
                "bibliography": True
            }

planner_service = PlannerService()

