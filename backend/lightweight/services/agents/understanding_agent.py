"""
Understanding Agent - The First Agent That Runs

This agent's job is to deeply understand before any action:
1. Parse user intent
2. Extract entities and goals
3. Check if clarification needed
4. Build rich context for other agents
5. Determine what actions are needed

"Understanding is paramount to achieve a goal"
"""

import re
from typing import Dict, Any, List, Optional
from services.agent_spawner import BaseAgent, AgentType, AgentStatus, AgentContext


class UnderstandingAgent(BaseAgent):
    """
    The Understanding Agent - ALWAYS runs first.
    
    This agent:
    - Deeply analyzes user message
    - Extracts intent, entities, goals
    - Checks conversation history for context
    - Determines what actions are needed
    - Decides which agents to spawn next
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id, job_id)
        
        # Intent patterns for classification
        self.intent_patterns = {
            "search_web": [
                r"search\s+(?:the\s+)?(?:web|internet|online)",
                r"find\s+(?:information|info)\s+(?:about|on)",
                r"look\s+up",
                r"google",
                r"statistics\s+(?:on|for)",
                r"latest\s+data\s+(?:on|for)",
                r"current\s+info",
            ],
            "search_papers": [
                r"search\s+(?:for\s+)?papers?",
                r"find\s+(?:research|academic|scientific)\s+papers?",
                r"search\s+(?:literature|publications)",
                r"find\s+studies\s+(?:about|on)",
            ],
            "create_file": [
                r"create\s+(?:a\s+)?(?:new\s+)?file",
                r"make\s+(?:me\s+)?(?:a\s+)?(?:new\s+)?(?:md|txt|file)",
                r"write\s+(?:a\s+)?file",
            ],
            "summarize": [
                r"summarize",
                r"summarise",
                r"sumarise",
                r"summary\s+of",
                r"give\s+me\s+(?:a\s+)?summary",
                r"brief\s+(?:me\s+)?(?:on|about)",
            ],
            "question": [
                r"^(?:what|who|where|when|why|how|is|are|can|do|does|will|would)\s+",
                r"\?$",
            ],
            "greeting": [
                r"^(?:hi|hello|hey|good\s+(?:morning|afternoon|evening))",
            ],
            "thesis": [
                r"thesis",
                r"chapter\s+(?:one|two|three|1|2|3)",
                r"write\s+(?:my\s+)?(?:intro|introduction|literature|methodology)",
            ],
            "browse": [
                r"browse\s+(?:to)?",
                r"open\s+(?:the\s+)?(?:url|website|page)",
                r"go\s+to\s+(?:the\s+)?(?:url|website)",
                r"visit\s+(?:the\s+)?(?:url|website)",
            ],
            "chat_with_document": [
                r"chat\s+with\s+(?:my\s+)?(?:thesis|document|file)",
                r"ask\s+(?:questions?\s+)?about\s+(?:my\s+)?(?:thesis|pdf)",
                r"what\s+does\s+(?:my\s+)?(?:thesis|document)\s+say",
            ],
            "edit_document": [
                r"edit\s+(?:parts\s+in|pages?\s+in|sections?\s+in)\s+(?:my\s+)?(?:thesis|file|document)",
                r"rewrite\s+(?:section|page|part)",
                r"improve\s+(?:section|page|part)",
                r"change\s+(?:page|part|section)",
            ],
            "auto_cite": [
                r"auto-cite",
                r"do\s+auto\s+citation",
                r"fix\s+citations",
                r"add\s+references",
                r"cite\s+this",
            ],
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            "topic": r"(?:about|on|regarding|for)\s+([^,\.]+)",
            "location": r"(?:in|at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "name": r"(?:am|i'm|my\s+name\s+is|call\s+me)\s+([A-Za-z]+)",
            "url": r"(https?://[^\s]+)",
            "filename": r"(?:file\s+(?:named?|called))\s+([^\s,\.]+(?:\.[a-z]+)?)",
        }
        
    def _parse_slash_command(self, message: str) -> Optional[Dict[str, Any]]:
        """Strictly parse slash commands like /uoj_phd n=120 topic='...'"""
        if not message.strip().startswith("/"):
            return None
            
        # Extract command
        command_match = re.match(r"^/(\w+)", message)
        if not command_match:
            return None
            
        command = command_match.group(1)
        args = {}
        
        # Parse arguments: key="value", key='value', or key=value
        pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^"\'\s]+))'
        for match in re.finditer(pattern, message):
            key = match.group(1)
            # Group 2 is double quotes, 3 is single quotes, 4 is no quotes
            val = match.group(2) or match.group(3) or match.group(4)
            args[key] = val
            
        return {"command": command, "args": args}
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main understanding process using DeepSeek LLM.
        """
        await self.report_status(AgentStatus.THINKING, "🧠 Analyzing request...")
        
        try:
            # 1. Deterministic Command Parsing
            cmd = self._parse_slash_command(context.user_message)
            if cmd:
                # Map commands to intents
                if cmd["command"] in ["uoj_phd", "thesis", "generate_thesis", "uoj_general"]:
                    context.intent = "workflow_thesis"
                    # Default actions for thesis generation
                    context.required_actions = ["spawn_action_agent"]
                    
                    # Set format based on command
                    if cmd["command"] == "uoj_general":
                         context.entities["thesis_type"] = "general"
                    elif cmd["command"] == "uoj_phd":
                         context.entities["thesis_type"] = "phd"
                else:
                    context.intent = "execute_code" # Default fallback
                
                context.entities.update(cmd["args"])
                
                # Specific entity handlings
                if "topic" in context.entities:
                     context.entities["topic"] = context.entities["topic"].strip('"\'')
                
                context.goals = [f"Execute command: {cmd['command']}"]
                
                await self.report_status(AgentStatus.COMPLETED, f"✅ Command Parsed: {cmd['command']}", data=context.entities)
                return context

            from services.deepseek_direct import deepseek_direct_service
            
            # Build prompt
            prompt = f"""You are the customized Understanding Agent for 'AntiGravity'—a PhD-level research assistant.
You are a PhD-level architect. Your first priority is to ensure the thesis follows a correct academic structure.

User Request: "{context.user_message}"
User Context: {context.user_preferences}
Workspace Files: {context.available_files}
History: {context.conversation_history[-8:] if context.conversation_history else "None"}

PHD PROTOCOL (CRITICAL):
1. Template Discovery: If the user wants a chapter or a thesis, look in 'Workspace Files' for 'outline.json', 'template.md', or 'structure.md'.
2. University Context: If the user mentions a location (e.g., South Sudan), recognize that specific university templates (like 'UoJ' for University of Juba) may be applicable.
3. Proactive Questioning: If NO outline/template exists and this is the start of a project, your 'reasoning' MUST suggest asking the user: "Do you have a specific university template or outline you'd like me to follow?"
4. Workflow: If it's a thesis task, set intent to 'workflow_thesis'.
5. Data Analysis: If the user asks for charts, graphs, plots, or 'analysis' (e.g., 'aalysis', 'generate chats', 'bar chart'), set intent to 'data_analysis'.

Capabilities:
1. Thesis: 'workflow_thesis' for structure/chapters.
2. Research: 'research' for data.
3. Writing: 'create_file' / 'edit_file'.
4. Chat: Greetings or general advice.

Output JSON ONLY:
{{
    "intent": "workflow_thesis" | "research" | "create_file" | "edit_file" | "delete_file" | "open_file" | "modify_file" | "insert_media" | "chat" | "chat_with_document" | "edit_document" | "auto_cite" | "create_image" | "execute_code" | "data_analysis",
    "required_analysis": "statistical" | "exploratory" | "forecasting" | "none",
    "confidence": 0.0-1.0,
    "entities": {{ "topic": "...", "filename": "...", "university": "...", "outline_found": true|false, "sections": ["..."], "image_prompt": "detailed prompt for AI generator", "paragraph_index": number, "line_number": number, "action_type": "insert" | "delete" | "replace", "content_update": "..." }},
    "missing_info": ["template_confirmation", "outline_details"],
    "goals": ["precisely what we are doing step-by-step (e.g., 'Gather statistics on Sudan food security', 'Generate a bar chart of displacement drivers', 'Update essay with analysis')"],
    "next_agent": "research" | "action" | "writer" | "none",
    "reasoning": "PhD architect reasoning. List the discrete tasks to be shown in the UI checklist."
}}
"""
            # Call DeepSeek
            response = await deepseek_direct_service.generate_content(
                prompt=prompt,
                system_prompt="You are a strict JSON-outputting analysis agent.",
                temperature=0.1
            )
            
            # Parse JSON
            import json
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            analysis = json.loads(cleaned_response)
            
            # Update Context
            context.intent = analysis.get("intent")
            context.entities = analysis.get("entities", {})
            context.goals = analysis.get("goals", [])
            
            # Determine Actions and Next Agent
            next_agent = analysis.get("next_agent")
            
            # Reset actions and build based on analysis
            context.required_actions = []
            
            # 1. Check for Research Need (keywords in message or explicit agent choice)
            research_keywords = ["studies", "citation", "research", "papers", "factual", "real", "academic", "statistics", "data", "current", "latest", "search", "find", "trends"]
            needs_research = next_agent == "research" or any(k in context.user_message.lower() for k in research_keywords)
            print(f"DEBUG: needs_research={needs_research}")
            
            if needs_research:
                context.required_actions.append("spawn_research_agent")
                if "search_papers" not in context.required_actions:
                    context.required_actions.append("search_papers")
                if "search_web" not in context.required_actions:
                    context.required_actions.append("search_web")

            # 2. Check for Writing/Action Need
            analysis_keywords = ["chart", "charting", "plot", "graph", "analysis", "aalysis", "analyze", "calculation", "statistic", "visualization", "chats"]
            user_msg_lower = context.user_message.lower()
            needs_analysis = context.intent in ["execute_code", "data_analysis"] or any(k in user_msg_lower for k in analysis_keywords)
            print(f"DEBUG: needs_analysis={needs_analysis}, user_msg='{user_msg_lower[:50]}...'")

            if next_agent == "action" or context.intent in ["create_file", "edit_file", "delete_file", "open_file", "modify_file", "insert_media", "summarize_document", "workflow_thesis", "chat_with_document", "edit_document", "auto_cite", "create_image", "present_results", "execute_code", "data_analysis"] or needs_analysis:
                 context.required_actions.append("spawn_action_agent")
                 
                 if needs_analysis and context.intent not in ["execute_code", "data_analysis"]:
                     context.intent = "data_analysis"
                 
                 # NEW: If data analysis is needed, add it to action plan
                 if context.intent in ["execute_code", "data_analysis"]:
                     if "execute_code" not in context.required_actions:
                         context.required_actions.append("execute_code")
                     if "present_results" not in context.required_actions:
                         context.required_actions.append("present_results")
                     
                     # Add to action_plan so ActionAgent knows what to do
                     from services.agent_spawner import AgentAction
                     context.action_plan.append(AgentAction(
                         action="data_analysis",
                         parameters={"type": analysis.get("required_analysis", "statistical")},
                         description=f"Perform {analysis.get('required_analysis', 'statistical')} data analysis and generate charts"
                     ))
            elif next_agent == "writer":
                 context.required_actions.append("spawn_writer_agent")
            
            # 3. Handle specific research intents
            if context.intent == "research" and "spawn_research_agent" not in context.required_actions:
                context.required_actions.append("spawn_research_agent")
            
            # Log understanding
            await self.report_status(
                AgentStatus.COMPLETED,
                f"✅ Understood: {context.intent} | Next: {next_agent}",
                data=analysis
            )
            
            return context
            
        except Exception as e:
            print(f"⚠️ Understanding Agent LLM failed: {e}")
            # Fallback to simple classification (legacy logic could go here or just chat)
            context.intent = "chat"
            return context

# Export for agent spawner
__agent_class__ = UnderstandingAgent
