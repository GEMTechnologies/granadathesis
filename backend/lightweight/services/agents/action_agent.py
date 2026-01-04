"""
Action Agent - Executes Tasks Based on Understanding

This agent:
1. Creates and edits files
2. Executes code
3. Performs browser automation
4. Completes tasks
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from services.agent_spawner import BaseAgent, AgentType, AgentStatus, AgentContext


class ActionAgent(BaseAgent):
    """
    Action Agent - Executes tasks after understanding.
    
    Capabilities:
    - Create files
    - Edit files
    - Execute code
    - Browser automation
    - Task completion
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id, job_id)
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main action execution process.
        
        Based on context.required_actions, performs:
        - create_file
        - edit_file
        - execute_code
        - present_results
        """
        await self.report_status(AgentStatus.THINKING, "⚡ Planning execution...")
        
        actions = context.required_actions
        
        # Execute actions based on intent and required_actions
        if context.intent == "create_file" or "create_file" in actions:
            await self._handle_create_file(context)
        
        if context.intent == "edit_file" or "edit_file" in actions:
            await self._handle_edit_file(context)
        
        if context.intent == "delete_file" or "delete_file" in actions:
            await self._handle_delete_file(context)
            
        if context.intent == "open_file" or "open_file" in actions:
            await self._handle_open_file(context)
            
        if context.intent == "modify_file" or "modify_file" in actions:
            await self._handle_modify_file(context)
            
        if context.intent == "insert_media" or "insert_media" in actions:
            await self._handle_insert_media(context)
            
        if "present_results" in actions:
            await self._handle_present_results(context)
        
        if "write_summary" in actions:
            await self._handle_write_summary(context)
        
        if context.intent == "summarize_document" or "summarize_document" in actions:
            await self._handle_summarize_document(context)
        
        if context.intent == "create_image" or "create_image" in actions:
            await self._handle_create_image(context)
            
        if context.intent == "workflow_thesis":
            await self._handle_workflow_thesis(context)
        
        if context.intent == "chat_with_document":
            await self._handle_chat_with_document(context)
            
        if context.intent == "edit_document":
            await self._handle_edit_document(context)
            
        if context.intent == "auto_cite":
            await self._handle_auto_cite(context)
            
        if "execute_code" in actions or context.intent == "execute_code":
            # If it's a data_analysis intent, we need to generate code first
            if context.intent == "data_analysis" or any(a.get("action") == "data_analysis" for a in context.action_plan):
                await self._handle_data_analysis(context)
            else:
                await self._handle_execute_code(context)
        
        # Fallback if somehow data_analysis was in plan but not intent
        elif any(a.get("action") == "data_analysis" for a in context.action_plan) or context.intent == "data_analysis":
            await self._handle_data_analysis(context)
        
        await self.report_status(
            AgentStatus.COMPLETED,
            f"✅ Completed {len([a for a in context.action_plan if a.get('status') == 'completed'])} actions"
        )
        
        return context
    
    async def _handle_create_file(self, context: AgentContext):
        """Create a file based on context."""
        await self.report_status(AgentStatus.WORKING, "📄 Creating file...")
        
        # 1. Get filename from entities
        filename = context.entities.get("filename", "new_file.md")
        if not isinstance(filename, str):
            filename = filename[0] if filename else "new_file.md"
        
        # 2. Path consistency
        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / (context.workspace_id or "default")
        file_path = workspace_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Intelligent "Rewrite" detection: If file exists, maybe we should be editing
        if file_path.exists() and any(k in context.user_message.lower() for k in ["rewrite", "update", "improve", "add"]):
            await self.report_status(AgentStatus.WORKING, f"🔄 File '{filename}' exists. Redirecting to edit...")
            return await self._handle_edit_file(context)

        # 4. Determine Content (Synthesize if research performed, otherwise use entities)
        content = None
        
        # Priority 1: Synthesize from research
        if context.search_results:
             await self.report_status(AgentStatus.WORKING, "✍️ Synthesizing academic content from research findings...")
             content = await self._generate_academic_content(context)
             
        # Priority 2: Use provided word_content
        if not content:
            content = context.entities.get("word_content")
            
        # Priority 3: Use instructions
        if not content:
            instr = context.entities.get("instructions")
            if instr and len(instr) > 50:
                content = instr
        
        # Priority 4: Quoted content
        if not content and context.entities.get("quoted_content"):
            content = context.entities["quoted_content"][0]
            
        # Priority 5: User message
        if not content:
            content = context.user_message
        
        # Write file
        file_path.write_text(content)
        
        # Record action
        context.completed_actions.append({
            "action": "create_file",
            "filename": filename,
            "path": str(file_path),
            "content": content
        })
        
        # Update action plan
        for action in context.action_plan:
            if action["action"] == "create_file":
                action["status"] = "completed"
                action["result"] = {"path": str(file_path)}
        
        # Publish file created event
        await self._ensure_connections()
        if self.events:
            await self.events.publish(
                self.id,
                "file_created",
                {"path": filename, "full_path": str(file_path)},
                session_id=self.session_id
            )
        
        await self.report_status(AgentStatus.WORKING, f"✅ Created: {filename}")
    
    async def _handle_edit_file(self, context: AgentContext):
        """Edit an existing file."""
        await self.report_status(AgentStatus.WORKING, "✏️ Editing file...")
        
        # 1. Get filename from entities
        filename = context.entities.get("filename")
        if not filename:
             # Intelligent Search for most relevant file if not specified
             search_keywords = ["essay", "thesis", "report", "analysis", "chapter"]
             relevant_files = [f for f in context.available_files if any(k in f.lower() for k in search_keywords)]
             if relevant_files:
                 filename = relevant_files[0] # Pick most likely target
             elif context.available_files:
                 filename = context.available_files[0]
        
        if not filename:
            await self.report_status(AgentStatus.FAILED, "❌ No file to edit")
            return
            
        # 2. Determine Content (Synthesize if research performed, otherwise use entities)
        new_content = None
        
        # Priority 1: Synthesize from research if results available (The "PhD" way)
        if context.search_results:
             await self.report_status(AgentStatus.WORKING, "✍️ Synthesizing academic prose from research findings...")
             new_content = await self._generate_academic_content(context)
        
        # Priority 2: Use provided word_content
        if not new_content:
            new_content = context.entities.get("word_content")
            
        # Priority 3: Use instructions (only if we didn't synthesize and no word_content)
        if not new_content:
            instr = context.entities.get("instructions")
            if instr and len(instr) > 50: # Only use if it looks substantial
                new_content = instr
        
        # Priority 4: Final fallback (User message)
        if not new_content:
            new_content = context.user_message
            
        # 3. Use consistent workspace dir
        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / (context.workspace_id or "default")
        file_path = workspace_dir / Path(filename).name # Stay in root for now
        
        if not file_path.exists():
            # If "edit" requested but file missing, maybe we should create it?
            if "rewrite" in context.user_message.lower():
                return await self._handle_create_file(context)
            await self.report_status(AgentStatus.FAILED, f"❌ File not found: {filename}")
            return
            
        # 4. Perform update
        file_path.write_text(new_content)
        
        context.completed_actions.append({
            "action": "edit_file",
            "filename": filename,
            "path": str(file_path),
            "content": new_content
        })
        
        await self.report_status(AgentStatus.WORKING, f"✅ Updated: {file_path.name}")

    async def _generate_academic_content(self, context: AgentContext) -> str:
        """Helper to generate high-quality academic content from research results and persistent sources."""
        from services.deepseek_direct import deepseek_direct
        from services.sources_service import sources_service
        import json
        
        # 1. Pull immediate research results
        research_context = ""
        for r in context.search_results[:8]:
            if r.get("type") == "paper":
                research_context += f"Source: {r.get('title')} ({r.get('year')})\nAbstract: {r.get('abstract')}\n\n"
            else:
                research_context += f"Source: {r.get('url')}\nContent: {r.get('content', '')[:300]}\n\n"
        
        # 2. Pull persistent sources (RAG)
        persistent_context = sources_service.get_all_sources_full_text(context.workspace_id, topic=context.user_message)
        if persistent_context:
            research_context += "\n--- PERSISTENT KNOWLEDGE BASE ---\n" + persistent_context
        
        prompt = f"""You are AntiGravity, a PhD-level research architect.
Based on the following research data and persistent knowledge base, fulfill the user's request.

User Request: {context.user_message}
Entities: {json.dumps(context.entities)}

RESEARCH DATA:
{research_context}

Instruction: Write high-quality, continuous academic prose with technical precision. 
If the user asks for statistics or current info, prioritize the most recent data found.
Provide in-text citations in (Author, Year) format. Use BibTeX keys if evident (e.g. [author2024title]).

Your Output (Markdown Format):
"""
        result = await deepseek_direct.generate_content(prompt, system_prompt="You are a PhD-level academic writer.")
        return result
    
    async def _handle_present_results(self, context: AgentContext):
        """Format and present search results."""
        await self.report_status(AgentStatus.WORKING, "📊 Formatting results...")
        
        results = context.search_results
        if not results:
            return
        
        # Format results for display
        formatted = []
        for i, r in enumerate(results[:10]):
            if r.get("type") == "paper":
                formatted.append(f"📚 **{r.get('title', 'Untitled')}** ({r.get('year', 'N/A')})")
                formatted.append(f"   Authors: {', '.join(r.get('authors', [])[:3])}")
                if r.get("abstract"):
                    formatted.append(f"   {r['abstract'][:150]}...")
            else:
                formatted.append(f"🌐 **[{r.get('title', 'Result')}]({r.get('url', '')})**")
                if r.get("content"):
                    formatted.append(f"   {r['content'][:150]}...")
            formatted.append("")
        
        context.gathered_data["formatted_results"] = "\n".join(formatted)
    
    async def _handle_write_summary(self, context: AgentContext):
        """Write a summary of gathered research."""
        await self.report_status(AgentStatus.WORKING, "📝 Writing summary...")
        
        # Use LLM to summarize
        try:
            from services.deepseek_direct import deepseek_direct
            
            # Build prompt from research results
            research_content = []
            for r in context.search_results[:5]:
                if r.get("content"):
                    research_content.append(r["content"][:500])
                elif r.get("abstract"):
                    research_content.append(r["abstract"])
            
            prompt = f"""Based on the following research findings, write a concise summary:

{chr(10).join(research_content)}

Write a clear, well-structured summary of the key findings."""

            summary = ""
            async for chunk in deepseek_direct.generate_stream(prompt):
                summary += chunk
            
            context.gathered_data["summary"] = summary
            
            # Save summary to file
            from services.workspace_service import WORKSPACES_DIR
            workspace_dir = WORKSPACES_DIR / (context.workspace_id or "default")
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            summary_path = workspace_dir / "summary.md"
            summary_path.write_text(f"# Research Summary\n\n{summary}")
            
            context.completed_actions.append({
                "action": "write_summary",
                "path": str(summary_path),
                "content": summary
            })
            
        except Exception as e:
            print(f"⚠️ Summary writing failed: {e}")

    async def _handle_workflow_thesis(self, context: AgentContext):
        """Handle full thesis/chapter generation workflow."""
        await self.report_status(AgentStatus.WORKING, "🎓 Organizing PhD workflow...")
        
        from services.outline_parser import outline_parser
        from services.complete_thesis_generator import CompleteThesisGenerator
        import re
        
        from services.parallel_chapter_generator import parallel_chapter_generator
        
        # 1. Parse Topic and Case Study from Config or Message
        job_params = context.metadata.get("job_parameters", {})
        topic = job_params.get("topic") or context.entities.get("topic") or thesis_config.get("topic")
        case_study = job_params.get("caseStudy") or context.entities.get("case_study") or thesis_config.get("case_study")
        custom_instructions = job_params.get("customInstructions") or ""
        
        if not topic:
            # Fallback extraction
            import re
            topic_match = re.search(r"topic\s*[:=]\s*['\"]?([^'\"]+)['\"]?", context.user_message, re.IGNORECASE)
            topic = topic_match.group(1) if topic_match else context.user_message[:50]
            
        if not case_study:
            case_match = re.search(r"case\s*study\s*[:=]\s*['\"]?([^'\"]+)['\"]?", context.user_message, re.IGNORECASE)
            case_study = case_match.group(1) if case_match else "General Context"

        # Parse Sample Size (n=120 or sample_size=120)
        sample_size = context.entities.get("n") or context.entities.get("sample_size") or thesis_config.get("sample_size")
        if not sample_size:
            n_match = re.search(r"\b(n|sample_size)\s*[:=]\s*(\d+)", context.user_message, re.IGNORECASE)
            if n_match:
                sample_size = int(n_match.group(2))
            else:
                sample_size = 385 # Default academic standard
        else:
            try:
                sample_size = int(sample_size)
            except:
                sample_size = 385

        # 1.1 Parse Objectives if provided (format: "Obj 1 | Obj 2 | Obj 3")
        custom_objectives = context.entities.get("objectives")
        objectives = []
        if custom_objectives:
            if "|" in custom_objectives:
                objectives = [o.strip() for o in custom_objectives.split("|")]
            elif ";" in custom_objectives:
                objectives = [o.strip() for o in custom_objectives.split(";")]
            else:
                # Try to detect list format or just a single objective
                objectives = [custom_objectives.strip()]
        
        # 1.2 Parse Research Design / Study Type
        research_design = context.entities.get("design") or context.entities.get("study_type") or thesis_config.get("research_design", "survey")
        
        # 1.3 Parse Preferred Analyses
        analyses = context.entities.get("analyses") or context.entities.get("analyses_list")
        if isinstance(analyses, str):
            analyses = [a.strip() for a in analyses.split(",")]

        # CLEAN TOPIC AND CASE STUDY
        if topic:
            # Clean Topic
            topic = re.sub(r'n\s*=\s*\d+', '', topic, flags=re.IGNORECASE)
            topic = re.sub(r'topic\s*=\s*["\'].*?["\']', '', topic, flags=re.IGNORECASE)
            topic = re.sub(r'case[_\s]?study\s*=\s*["\'].*?["\']', '', topic, flags=re.IGNORECASE)
            topic = re.sub(r'design\s*=\s*\w+', '', topic, flags=re.IGNORECASE)
            topic = re.sub(r'/uoj_phd\s*\w*', '', topic, flags=re.IGNORECASE)
            topic = re.sub(r'\s+', ' ', topic).strip()
        
        if case_study:
            case_study = re.sub(r'case[_\s]?study\s*=\s*["\'].*?["\']', '', case_study, flags=re.IGNORECASE)
            case_study = re.sub(r'\s+', ' ', case_study).strip()


        # 2. Determine specific task (Chapter vs Full)
        chapter_match = re.search(r"chapter\s+(\d+)", context.user_message.lower())
        
        if chapter_match:
            try:
                chapter_num = int(chapter_match.group(1))
                await self.report_status(AgentStatus.WORKING, f"🚀 Launching Parallel Generator for Chapter {chapter_num}...")
                
                content = ""
                
                # Dynamic dispatch based on chapter number
                if chapter_num == 1:
                    content = await parallel_chapter_generator.generate(
                        topic=topic,
                        case_study=case_study,
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                elif chapter_num == 2:
                    content = await parallel_chapter_generator.generate_chapter_two(
                        topic=topic,
                        case_study=case_study,
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                elif chapter_num == 3:
                    content = await parallel_chapter_generator.generate_chapter_three(
                        topic=topic,
                        case_study=case_study,
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                elif chapter_num == 4:
                    content = await parallel_chapter_generator.generate_chapter_four(
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                elif chapter_num == 5:
                    content = await parallel_chapter_generator.generate_chapter_five(
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                elif chapter_num == 6:
                    content = await parallel_chapter_generator.generate_chapter_six(
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        custom_instructions=custom_instructions
                    )
                else:
                    await self.report_status(AgentStatus.FAILED, f"❌ Chapter {chapter_num} not supported yet.")
                    return

                await self.report_status(AgentStatus.COMPLETED, f"✅ Chapter {chapter_num} Generated Successfully.")
                
            except Exception as e:
                await self.report_status(AgentStatus.FAILED, f"❌ Chapter generation failed: {str(e)}")
                
            # Full Thesis Generation
            thesis_type = context.entities.get("thesis_type", "phd")
            
            # Override: Detect /uoj_general explicitly
            if "/uoj_general" in context.user_message.lower():
                thesis_type = "general"
            elif "/uoj_phd" in context.user_message.lower():
                thesis_type = "uoj_phd"
            
            if thesis_type or "uo_phd" in context.user_message.lower() or "generate thesis" in context.user_message.lower() or "/uoj_general" in context.user_message.lower():
                 msg = "🏛️ Preparing Complete University of Juba PhD Thesis..." if thesis_type == "phd" else "📝 Preparing General Academic Thesis (5 chapters)..."
                 await self.report_status(AgentStatus.WORKING, msg)
                 
                 try:
                     results = await parallel_chapter_generator.generate_full_thesis_sequence(
                        topic=topic,
                        case_study=case_study,
                        job_id=self.job_id,
                        session_id=self.session_id,
                        workspace_id=context.workspace_id or "default",
                        sample_size=sample_size,
                        thesis_type=thesis_type,
                        objectives=objectives,
                        research_design=research_design,
                        preferred_analyses=analyses,
                        custom_instructions=custom_instructions
                     )
                     await self.report_status(AgentStatus.COMPLETED, f"✅ Full Thesis Generated ({len(results)} Chapters).")
                 except Exception as e:
                     await self.report_status(AgentStatus.FAILED, f"❌ Thesis generation failed: {str(e)}")
                     
            else:
                 # Fallback specific logic or suggestion
                 pass

    async def _handle_summarize_document(self, context: AgentContext):
        """Summarize a specific document from the workspace."""
        await self._publish_stage("reading_doc", f"📄 Reading {context.entities.get('filename', 'document')} for summary...")
        
        filename = context.entities.get("filename")
        if not filename:
            # Try to find a PDF in available files if none specified
            pdfs = [f for f in context.available_files if f.lower().endswith(".pdf")]
            if pdfs:
                filename = pdfs[0]
            else:
                await self.report_status(AgentStatus.FAILED, "❌ No PDF found to summarize")
                return

        try:
            from services.sources_service import SourcesService
            sources_service = SourcesService()
            
            # Find source ID in index
            index = sources_service._load_index(context.workspace_id)
            source_id = None
            for s in index.get("sources", []):
                if s.get("local_path") and Path(s["local_path"]).name == filename:
                    source_id = s.get("id")
                    break
            
            text = ""
            if source_id:
                text = sources_service.get_source_text(context.workspace_id, source_id)
            
            if not text:
                # Fallback: Try direct extraction if not indexed
                from services.pdf_service import get_pdf_service
                pdf_service = get_pdf_service()
                from services.workspace_service import WORKSPACES_DIR
                pdf_path = WORKSPACES_DIR / context.workspace_id / filename
                if pdf_path.exists():
                    text = await pdf_service.extract_text(pdf_path)
            
            if not text:
                await self.report_status(AgentStatus.FAILED, f"❌ Could not extract text from {filename}")
                return

            # Summarize using DeepSeek
            from services.deepseek_direct import deepseek_direct
            
            await self._publish_stage("summarizing", f"✍️ Generating PhD-level summary for {filename}...")
            msg = f"""Summarize the following document: {filename}
            
STRICT GROUNDING RULES:
1. ONLY use information present in the text below.
2. If the document does not mention specific outcomes, methodologies, or data, DO NOT invent them.
3. Your summary should reflect the ACTUAL content, even if it is incomplete or limited.
4. If the text is insufficient for a full summary, state: "The document provides limited information on [X], only covering [Y]."

Content:
{text[:15000]}
"""
            summary = ""
            async for chunk in deepseek_direct.generate_stream(msg):
                summary += chunk
            
            context.gathered_data["document_summary"] = summary
            
            # Record action
            context.completed_actions.append({
                "action": "summarize_document",
                "filename": filename,
                "summary": summary
            })
            
            await self._publish_stage("summarizing", "✅ Summary complete", completed=True)
            await self.report_status(AgentStatus.WORKING, f"✅ Summary complete for {filename}")
            
        except Exception as e:
            await self.report_status(AgentStatus.FAILED, f"❌ Summarization failed: {e}")

    async def _handle_chat_with_document(self, context: AgentContext):
        """Answer questions about a specific document."""
        filename = context.entities.get("filename")
        if not filename and context.available_files:
            filename = context.available_files[0]
            
        await self._publish_stage("reading_doc", f"🧠 Consulting {filename} for answers...")
        
        # Load content
        from services.workspace_service import WORKSPACES_DIR
        file_path = WORKSPACES_DIR / context.workspace_id / filename
        
        from services.file_upload_service import get_file_upload_service
        upload_service = get_file_upload_service()
        content_res = upload_service.read_file(context.workspace_id, filename)
        
        if not content_res.get("success"):
            await self.report_status(AgentStatus.FAILED, f"❌ Cannot read {filename}")
            return
            
        content = content_res.get("content", "")
        
        from services.deepseek_direct import deepseek_direct
        prompt = f"""You are a PhD Research Assistant. Answer the question based ONLY on the provided document.

DOCUMENT: {filename}
CONTENT:
{content[:15000]}

USER QUESTION: {context.user_message}

STRICT INSTRUCTIONS:
- If the answer is not contained within the provided CONTENT, you MUST state: "I cannot find information regarding [X] in the document provided."
- DO NOT use your general knowledge to fill in gaps.
- DO NOT hallucinate or guess.
"""
        
        await self._publish_stage("answering", "✍️ Formulating academic response...")
        answer = await deepseek_direct.generate_content(prompt)
        
        context.gathered_data["chat_answer"] = answer
        await self._publish_stage("answering", "✅ Answer ready", completed=True)
        await self.report_status(AgentStatus.WORKING, "✅ Document analysis complete")

    async def _handle_edit_document(self, context: AgentContext):
        """Perform targeted rewrites or edits on a document."""
        filename = context.entities.get("filename")
        if not filename and context.available_files:
            filename = context.available_files[0]
            
        await self._publish_stage("editing_doc", f"✏️ Refining {filename}...")
        
        # Pull context and execute (reuse _handle_edit_file logic essentially)
        await self._handle_edit_file(context)
        await self._publish_stage("editing_doc", "✅ Document updated", completed=True)

    async def _handle_auto_cite(self, context: AgentContext):
        """Automatically suggest citations for a document."""
        filename = context.entities.get("filename")
        if not filename and context.available_files:
             filename = context.available_files[0]
             
        await self._publish_stage("citing", f"📚 Analyzing {filename} for citation gaps...")
        
        from services.workspace_service import WORKSPACES_DIR
        file_path = WORKSPACES_DIR / context.workspace_id / filename
        content = file_path.read_text(errors='ignore') if file_path.exists() else ""
        
        from services.deepseek_direct import deepseek_direct
        prompt = f"""Analyze the provided text and identify 3-5 specific locations where a scholarly citation is needed to support a claim.

STRICT INSTRUCTIONS:
- DO NOT suggest citations for personal reflections, research objectives, or internal project logic.
- ONLY suggest citations for empirical claims, theoretical definitions, or established facts.
- For each suggestion, describe the TYPE of source required (e.g., "Statistical report on South Sudan literacy rates").
- If you can infer a specific paper or BibTeX key, suggest it, but prioritize accuracy over volume.

TEXT TO ANALYZE:
{content[:10000]}
"""
        
        await self._publish_stage("analyzing_cites", "🔍 Seeking relevant literature matches...")
        suggestions = await deepseek_direct.generate_content(prompt)
        
        context.gathered_data["citation_suggestions"] = suggestions
        await self._publish_stage("analyzing_cites", "✅ Citations suggested", completed=True)
        await self.report_status(AgentStatus.WORKING, "✅ Citation analysis complete")

    async def _handle_create_image(self, context: AgentContext):
        """Generate an image using AI and save it to the workspace."""
        await self.report_status(AgentStatus.WORKING, "🖼️ Generating AI image/chart...")
        
        prompt = context.entities.get("image_prompt") or context.user_message
        filename = context.entities.get("filename", f"image_{uuid.uuid4().hex[:8]}.png")
        if not filename.endswith(('.png', '.jpg', '.jpeg')):
            filename += ".png"
            
        # Ensure subdirectory support
        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / (context.workspace_id or "default")
        file_path = workspace_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from services.image_generation import image_generation_service
            result = await image_generation_service.generate(prompt)
            
            if result.get("success") and result.get("url"):
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.get(result["url"])
                    resp.raise_for_status()
                    file_path.write_bytes(resp.content)
                
                context.completed_actions.append({
                    "action": "create_image",
                    "filename": filename,
                    "path": str(file_path),
                    "prompt": prompt
                })
                
                await self.report_status(AgentStatus.WORKING, f"✅ Image saved: {filename}")
                
                # Signal for UI visibility
                if self.events:
                    await self.events.publish(self.job_id, "agent_activity", {
                        "agent": "action",
                        "status": "completed",
                        "action": f"Generated image: {filename}",
                        "icon": "🖼️",
                        "data": {"image_path": str(file_path)}
                    }, session_id=self.session_id)
            else:
                await self.report_status(AgentStatus.FAILED, f"❌ Image generation failed: {result.get('error')}")
        except Exception as e:
            await self.report_status(AgentStatus.FAILED, f"❌ Image error: {e}")

    async def _handle_execute_code(self, context: AgentContext):
        """Execute Python code for data analysis or math."""
        await self.report_status(AgentStatus.WORKING, "🧮 Executing analysis code...")
        
        # Extract code from entities or actions
        code = None
        for action in context.action_plan:
            if action.get("action") == "execute_code" and action.get("status") == "pending":
                code = action.get("parameters", {}).get("code")
                break
        
        if not code:
            code = context.entities.get("code")
            
        if not code:
            # Check if we have code from a previous data_analysis step in this same run
            code = context.gathered_data.get("generated_analysis_code")
            
        if not code:
            await self.report_status(AgentStatus.FAILED, "❌ No code provided for execution")
            return
            
        await self._publish_stage("executing_code", "Analyzing data and generating charts...")
        
        # ... rest of the original execute_code logic remains the same ...
        import subprocess
        import sys
        import tempfile
        import os
        from pathlib import Path
        
        # Workspace dir
        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / (context.workspace_id or "default")
        figures_dir = workspace_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
            
        header = f"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path

# Set plotting style
plt.style.use('ggplot')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 100

# Working directory
os.chdir(r'{workspace_dir.absolute()}')
FIGURES_DIR = Path('figures')
if not FIGURES_DIR.exists(): FIGURES_DIR.mkdir()

"""
        full_code = header + code
        
        with tempfile.NamedTemporaryFile(suffix=".py", mode='w', delete=False) as tmp:
            tmp.write(full_code)
            tmp_path = tmp.name
        
        print(f"DEBUG: Executing code (first 100 chars): {code[:100]}...", flush=True)
            
        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            status = "completed" if result.returncode == 0 else "failed"
            
            for action in context.action_plan:
                if action.get("action") == "execute_code" and action.get("status") == "pending":
                    action["status"] = status
                    action["result"] = output
                    break
                    
            if status == "completed":
                images = list(figures_dir.glob("*.png")) + list(figures_dir.glob("*.jpg"))
                image_notes = f"\n\nGenerated {len(images)} figure(s) in {figures_dir.name}"
                
                await self.report_status(AgentStatus.WORKING, f"✅ Analysis complete. {image_notes}")
                context.gathered_data["execution_output"] = output + image_notes
                
                print(f"DEBUG: Execution successful. Found images: {[img.name for img in images]}", flush=True)
                for img in images:
                    await self._publish_stage("figure_generated", f"Generated figure: {img.name}", completed=True)
            else:
                await self.report_status(AgentStatus.FAILED, f"❌ Execution failed: {output[:100]}...")
                
        except Exception as e:
            await self.report_status(AgentStatus.FAILED, f"❌ Error running code: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _handle_data_analysis(self, context: AgentContext):
        """Generate analysis code based on search results/gathered data."""
        await self.report_status(AgentStatus.WORKING, "📊 Synthesizing data for analysis...")
        
        # 1. Gather data from context
        data_sources = ""
        if context.search_results:
            data_sources += "SEARCH RESULTS:\n"
            for res in context.search_results[:10]:
                data_sources += f"- {res.get('title')}: {res.get('snippet')}\n"
        
        if context.gathered_data:
            data_sources += "\nGATHERED DATA:\n"
            for k, v in context.gathered_data.items():
                data_sources += f"- {k}: {v}\n"
                
        if not data_sources:
            await self.report_status(AgentStatus.FAILED, "❌ No data found to analyze. Please research first.")
            return

        # 2. Build code generation prompt
        prompt = f"""You are a data analyst. Write a Python script to analyze the following research data and generate professional charts.

DATA:
{data_sources}

GOAL: {context.user_message}

REQUIREMENTS:
1. Use pandas for data structures.
2. Use matplotlib or seaborn for charts.
3. Save all charts to the 'figures/' directory as PNG files.
4. Give charts professional titles, axis labels, and legends.
5. If specific numerical trends are found (e.g., GDP figures), use them accurately.
6. If data is sparse, create a comparative analysis or thematic chart.
7. Print a summary of the analysis to stdout.

IMPORTANT:
- Use `plt.savefig('figures/chart_name.png')` for each chart.
- Do NOT use plt.show().
- Ensure the 'figures/' directory exists (already handled in header, but be sure).

Write the Python code ONLY. No explanation."""

        from services.deepseek_direct import deepseek_direct_service
        response = await deepseek_direct_service.generate_content(
            prompt=prompt,
            system_prompt="You are a strict Python-only data analysis agent.",
            temperature=0.1
        )
        
        code = response.replace("```python", "").replace("```", "").strip()
        context.gathered_data["generated_analysis_code"] = code
        
        # 3. Now execute it using the existing handler
        print(f"DEBUG: Generated code length: {len(code)}", flush=True)
        await self._handle_execute_code(context)
        
        # Mark action as completed if it was in the plan
        print(f"DEBUG: Marking data_analysis action as completed. Plan size: {len(context.action_plan)}", flush=True)
        for action in context.action_plan:
            print(f"DEBUG: Checking action: {action.get('action')} with status: {action.get('status')}", flush=True)
            if action.get("action") == "data_analysis" and action.get("status") == "pending":
                action["status"] = "completed"
                print("DEBUG: Action marked COMPLETED", flush=True)
                break

    async def _handle_delete_file(self, context: AgentContext):
        """Delete a file from the workspace."""
        filename = context.entities.get("filename")
        if not filename:
            await self.report_status(AgentStatus.FAILED, "❌ No file specified to delete")
            return

        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / context.workspace_id
        file_path = workspace_dir / Path(filename).name

        if file_path.exists():
            file_path.unlink()
            await self.report_status(AgentStatus.WORKING, f"🗑️ Deleted: {filename}")
            
            # Record action
            context.completed_actions.append({
                "action": "delete_file",
                "filename": filename,
                "status": "success"
            })
            
            # Refresh file explorer
            if self.events:
                await self.events.publish(self.job_id, "workspace-refresh", {}, session_id=self.session_id)
        else:
            await self.report_status(AgentStatus.FAILED, f"❌ File not found: {filename}")

    async def _handle_open_file(self, context: AgentContext):
        """Signal frontend to open a specific file."""
        filename = context.entities.get("filename")
        if not filename:
            # Try to find the last created file or most relevant
            if context.completed_actions:
                last_file = next((a["filename"] for a in reversed(context.completed_actions) if "filename" in a), None)
                if last_file:
                    filename = last_file

        if not filename:
            await self.report_status(AgentStatus.FAILED, "❌ No file to open")
            return

        await self.report_status(AgentStatus.WORKING, f"📂 Opening: {filename}...")
        
        if self.events:
            await self.events.publish(self.job_id, "open-file-preview", {
                "path": filename,
                "type": "file"
            }, session_id=self.session_id)
            
        # LIVE BROWSER PREVIEW:
        # If it's a PDF or web file, show it in the browser panel too!
        if filename.lower().endswith(('.pdf', '.html', '.htm')):
             try:
                 from services.workspace_service import WORKSPACES_DIR
                 from services.browser_automation import get_browser
                 import asyncio
                 
                 workspace_dir = WORKSPACES_DIR / context.workspace_id
                 # If filename is relative "pdfs/x.pdf" or just "x.pdf"
                 file_path = workspace_dir / filename
                 if file_path.exists():
                     browser = await get_browser(context.workspace_id, headless=True)
                     file_url = f"file://{file_path.absolute()}"
                     
                     await self.report_status(AgentStatus.WORKING, f"🎥 Loading preview in browser...")
                     await browser.navigate(file_url)
             except Exception as e:
                 print(f"Browser preview failed: {e}")
            
        context.completed_actions.append({
            "action": "open_file",
            "filename": filename,
            "status": "success"
        })

    async def _handle_modify_file(self, context: AgentContext):
        """Perform granular edits like paragraph-level changes."""
        filename = context.entities.get("filename")
        if not filename and context.available_files:
            filename = context.available_files[0]

        if not filename:
            await self.report_status(AgentStatus.FAILED, "❌ No file to modify")
            return

        await self.report_status(AgentStatus.WORKING, f"📝 Modifying {filename}...")

        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / context.workspace_id
        file_path = workspace_dir / Path(filename).name

        if not file_path.exists():
            await self.report_status(AgentStatus.FAILED, f"❌ File not found: {filename}")
            return

        content = file_path.read_text()
        action_type = context.entities.get("action_type", "replace")
        target_p = context.entities.get("paragraph_index")
        target_l = context.entities.get("line_number")
        new_text = context.entities.get("content_update") or context.user_message

        # Split into paragraphs (basic split by double newline)
        paragraphs = content.split('\n\n')

        if target_p is not None:
            p_idx = int(target_p) - 1 # 1-indexed to 0-indexed
            if 0 <= p_idx < len(paragraphs):
                if action_type == "delete":
                    paragraphs.pop(p_idx)
                elif action_type == "insert":
                    paragraphs.insert(p_idx, new_text)
                else: # replace
                    paragraphs[p_idx] = new_text
                
                new_content = '\n\n'.join(paragraphs)
                file_path.write_text(new_content)
                await self.report_status(AgentStatus.WORKING, f"✅ Modified paragraph {target_p} in {filename}")
            else:
                await self.report_status(AgentStatus.FAILED, f"❌ Paragraph {target_p} out of range (total {len(paragraphs)})")
                return
        elif target_l is not None:
            # Line-based edit
            lines = content.splitlines()
            l_idx = int(target_l) - 1
            if 0 <= l_idx < len(lines):
                if action_type == "delete":
                    lines.pop(l_idx)
                elif action_type == "insert":
                    lines.insert(l_idx, new_text)
                else: # replace
                    lines[l_idx] = new_text
                
                new_content = '\n'.join(lines)
                file_path.write_text(new_content)
                await self.report_status(AgentStatus.WORKING, f"✅ Modified line {target_l} in {filename}")
            else:
                await self.report_status(AgentStatus.FAILED, f"❌ Line {target_l} out of range")
                return
        else:
            # Search and replace or general LLM-based edit
            await self.report_status(AgentStatus.WORKING, "🤖 Using PhD logic for intelligent edit...")
            from services.deepseek_direct import deepseek_direct
            
            prompt = f"""You are editing the file: {filename}
            
ORIGINAL CONTENT:
{content}

USER INSTRUCTION: {context.user_message}

TASKS:
1. Identify EXACTLY what the user wants to change.
2. If they say 'delete paragh 2', locate it and remove it.
3. If they say 'modify it' or 'rewrite', use your academic judgment to improve the flow.
4. Provide the FULL UPDATED CONTENT.

Updated Content:
"""
            new_content = await deepseek_direct.generate_content(prompt)
            file_path.write_text(new_content)
            await self.report_status(AgentStatus.WORKING, f"✅ Intelligent edit complete: {filename}")

        context.completed_actions.append({
            "action": "modify_file",
            "filename": filename,
            "status": "success"
        })

    async def _handle_insert_media(self, context: AgentContext):
        """Insert an image or table into a document."""
        filename = context.entities.get("filename")
        if not filename and context.available_files:
            filename = context.available_files[0]

        if not filename:
            await self.report_status(AgentStatus.FAILED, "❌ No file to insert media into")
            return

        await self.report_status(AgentStatus.WORKING, f"🖼️ Inserting media into {filename}...")

        from services.workspace_service import WORKSPACES_DIR
        workspace_dir = WORKSPACES_DIR / context.workspace_id
        file_path = workspace_dir / Path(filename).name

        if not file_path.exists():
            await self.report_status(AgentStatus.FAILED, f"❌ File not found: {filename}")
            return

        media_type = "image" if "image" in context.user_message.lower() else "table"
        media_path = context.entities.get("image_path") or context.entities.get("filepath")
        
        # If no media path provided, but we just generated an image, use it
        if not media_path and context.completed_actions:
            media_path = next((a["path"] for a in reversed(context.completed_actions) if a["action"] == "create_image"), None)

        content = file_path.read_text()
        
        if media_type == "image" and media_path:
            # Insert markdown image link at the end or at specified paragraph
            image_name = Path(media_path).name
            markdown_link = f"\n\n![{image_name}](figures/{image_name})\n"
            content += markdown_link
            file_path.write_text(content)
            await self.report_status(AgentStatus.WORKING, f"✅ Inserted image into {filename}")
        elif media_type == "table":
            # Generate a table using LLM if not provided
            await self.report_status(AgentStatus.WORKING, "📊 Generating academic table...")
            from services.deepseek_direct import deepseek_direct
            prompt = f"""Generate a professional Markdown table based on the following context:
            {context.user_message}
            
            Research results: {str(context.search_results)[:2000]}
            
            Markdown Table Only:"""
            table_md = await deepseek_direct.generate_content(prompt)
            content += f"\n\n{table_md}\n"
            file_path.write_text(content)
            await self.report_status(AgentStatus.WORKING, f"✅ Inserted table into {filename}")
        else:
            await self.report_status(AgentStatus.FAILED, "❌ Could not determine media to insert")
            return

        context.completed_actions.append({
            "action": "insert_media",
            "filename": filename,
            "status": "success"
        })

    async def _publish_stage(self, stage: str, message: str, completed: bool = False):
        """Helper to publish stage events for the UI checklist."""
        if not self.events:
            await self._ensure_connections()
            
        if self.events:
            event_type = "stage_completed" if completed else "stage_started"
            await self.events.publish(self.job_id, event_type, {
                "stage": stage,
                "message": message
            }, session_id=self.session_id)


# Export for agent spawner
__agent_class__ = ActionAgent
