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
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id)
        
        # Intent patterns for classification
        self.intent_patterns = {
            "search_web": [
                r"search\s+(?:the\s+)?(?:web|internet|online)",
                r"find\s+(?:information|info)\s+(?:about|on)",
                r"look\s+up",
                r"google",
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
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            "topic": r"(?:about|on|regarding|for)\s+([^,\.]+)",
            "location": r"(?:in|at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            "name": r"(?:am|i'm|my\s+name\s+is|call\s+me)\s+([A-Za-z]+)",
            "url": r"(https?://[^\s]+)",
            "filename": r"(?:file\s+(?:named?|called))\s+([^\s,\.]+(?:\.[a-z]+)?)",
        }
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main understanding process.
        
        Steps:
        1. Extract basic intent
        2. Extract entities
        3. Check conversation history
        4. Determine goals
        5. Plan required actions
        """
        await self.report_status(AgentStatus.THINKING, "🧠 Understanding your request...")
        
        message = context.user_message
        msg_lower = message.lower().strip()
        
        # Step 1: Classify intent
        await self.report_status(AgentStatus.WORKING, "📋 Analyzing intent...")
        intent = self._classify_intent(msg_lower)
        context.intent = intent
        
        # Step 2: Extract entities
        await self.report_status(AgentStatus.WORKING, "🔍 Extracting key information...")
        entities = self._extract_entities(message)
        context.entities = entities
        
        # Step 3: Check for user info (name, etc.)
        if "name" in entities:
            context.user_name = entities["name"]
            await self.report_status(AgentStatus.WORKING, f"👋 Hello {entities['name']}!")
        
        # Step 4: Determine goals
        await self.report_status(AgentStatus.WORKING, "🎯 Identifying goals...")
        goals = self._determine_goals(intent, entities, message)
        context.goals = goals
        
        # Step 5: Plan required actions
        await self.report_status(AgentStatus.WORKING, "📝 Planning actions...")
        actions = self._plan_actions(intent, entities, goals)
        context.required_actions = actions
        context.action_plan = [{"action": a, "status": "pending"} for a in actions]
        
        # Build summary for other agents
        understanding_summary = {
            "intent": intent,
            "entities": entities,
            "goals": goals,
            "required_actions": actions,
            "confidence": self._calculate_confidence(intent, entities, goals)
        }
        
        await self.report_status(
            AgentStatus.COMPLETED,
            f"✅ Understood: {intent} | Goals: {len(goals)} | Actions: {len(actions)}",
            data=understanding_summary
        )
        
        return context
    
    def _classify_intent(self, msg_lower: str) -> str:
        """Classify the user's intent from message."""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    return intent
        
        # Default to question if ends with ?
        if msg_lower.endswith("?"):
            return "question"
        
        # Default to general conversation
        return "conversation"
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract named entities from message."""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                # Take first match for single entities, all for lists
                if entity_type in ["url"]:
                    entities[entity_type] = matches
                else:
                    entities[entity_type] = matches[0] if len(matches) == 1 else matches
        
        # Extract quoted content
        quoted = re.findall(r'"([^"]+)"', message)
        if quoted:
            entities["quoted_content"] = quoted
        
        # Extract word content from "with word X" pattern
        word_match = re.search(r'with\s+word\s+(.+?)(?:\s|$|,|\.)', message, re.IGNORECASE)
        if word_match:
            entities["word_content"] = word_match.group(1).strip()
        
        return entities
    
    def _determine_goals(self, intent: str, entities: Dict, message: str) -> List[str]:
        """Determine the user's goals based on intent and entities."""
        goals = []
        
        if intent == "search_web":
            topic = entities.get("topic", message)
            goals.append(f"Find information about: {topic}")
            goals.append("Present search results clearly")
        
        elif intent == "search_papers":
            topic = entities.get("topic", message)
            goals.append(f"Find academic papers about: {topic}")
            goals.append("Extract key findings")
            if "summarize" in message.lower() or "summary" in message.lower():
                goals.append("Synthesize findings into summary")
        
        elif intent == "create_file":
            filename = entities.get("filename", "new_file")
            content = entities.get("word_content", entities.get("quoted_content", [""])[0] if entities.get("quoted_content") else "")
            goals.append(f"Create file: {filename}")
            if content:
                goals.append(f"Include content: {content}")
        
        elif intent == "summarize":
            topic = entities.get("topic", message)
            goals.append(f"Summarize: {topic}")
            goals.append("Make it concise and clear")
        
        elif intent == "question":
            goals.append("Answer the user's question accurately")
            goals.append("Provide helpful context")
        
        elif intent == "greeting":
            goals.append("Greet the user warmly")
            goals.append("Offer assistance")
        
        elif intent == "thesis":
            goals.append("Help with academic writing")
            goals.append("Follow university formatting")
        
        elif intent == "browse":
            urls = entities.get("url", [])
            if urls:
                goals.append(f"Navigate to: {urls[0]}")
                goals.append("Extract relevant content")
        
        else:
            goals.append("Understand and assist with request")
        
        return goals
    
    def _plan_actions(self, intent: str, entities: Dict, goals: List[str]) -> List[str]:
        """Plan the sequence of actions needed."""
        actions = []
        
        if intent == "search_web":
            actions.append("spawn_research_agent")
            actions.append("search_web")
            actions.append("present_results")
        
        elif intent == "search_papers":
            actions.append("spawn_research_agent")
            actions.append("search_papers")
            if any("summary" in g.lower() or "synthesize" in g.lower() for g in goals):
                actions.append("spawn_writer_agent")
                actions.append("write_summary")
        
        elif intent == "create_file":
            actions.append("spawn_action_agent")
            actions.append("create_file")
        
        elif intent == "browse":
            actions.append("spawn_browser_agent")
            actions.append("navigate")
            actions.append("extract_content")
        
        elif intent == "thesis":
            actions.append("spawn_research_agent")
            actions.append("gather_context")
            actions.append("spawn_writer_agent")
            actions.append("write_content")
            actions.append("spawn_verification_agent")
            actions.append("verify_quality")
        
        elif intent in ["question", "conversation", "greeting"]:
            actions.append("direct_llm_response")
        
        return actions
    
    def _calculate_confidence(self, intent: str, entities: Dict, goals: List[str]) -> float:
        """Calculate confidence in understanding."""
        confidence = 0.5  # Base
        
        # Intent clarity
        if intent not in ["conversation"]:
            confidence += 0.2
        
        # Entity extraction success
        if entities:
            confidence += min(0.2, len(entities) * 0.05)
        
        # Goal clarity
        if goals:
            confidence += min(0.1, len(goals) * 0.03)
        
        return min(1.0, confidence)


# Export for agent spawner
__agent_class__ = UnderstandingAgent
