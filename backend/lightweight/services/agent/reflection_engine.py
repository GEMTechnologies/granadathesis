"""
Autonomous Agent Brain - Reflection Engine

Enables the agent to think deeply about problems before acting.
Self-aware reasoning about what it knows and doesn't know.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    """Agent's confidence in understanding the problem."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class Reflection:
    """Result of agent's self-reflection on a problem."""
    understanding: str  # What the agent knows
    unknowns: List[str]  # What it needs to find out
    assumptions: List[str]  # What it's assuming
    approach: str  # How it plans to solve this
    confidence: ConfidenceLevel
    risks: List[str]  # What could go wrong
    needs_clarification: bool
    clarification_questions: List[str]


class ReflectionEngine:
    """
    Makes the agent self-aware and thoughtful.
    
    Instead of jumping straight to action, the agent:
    1. Analyzes what it knows
    2. Identifies gaps in knowledge
    3. Questions its assumptions
    4. Plans its approach
    5. Estimates confidence
    """
    
    def __init__(self, llm_service):
        self.llm = llm_service
    
    async def reflect(
        self,
        user_request: str,
        context: Dict,
        conversation_history: List[Dict],
        workspace_id: str
    ) -> Reflection:
        """
        Deep thinking before acting.
        
        The agent analyzes the problem from multiple angles:
        - What is the user REALLY asking for?
        - What do I already know?
        - What tools/knowledge do I need?
        - What am I unsure about?
        - Should I ask for clarification?
        """
        
        reflection_prompt = self._build_reflection_prompt(
            user_request,
            context,
            conversation_history
        )
        
        # Get agent's thoughts
        raw_reflection = await self.llm.generate(
            prompt=reflection_prompt,
            temperature=0.7,  # Allow creative thinking
            max_tokens=800
        )
        
        # Parse into structured reflection
        reflection = self._parse_reflection(raw_reflection)
        
        return reflection
    
    def _build_reflection_prompt(
        self,
        user_request: str,
        context: Dict,
        history: List[Dict]
    ) -> str:
        """Build the reflection prompt."""
        
        recent_context = "\n".join([
            f"- {msg['role']}: {msg['content'][:200]}..."
            for msg in history[-5:]  # Last 5 messages
        ]) if history else "No previous context"
        
        available_tools = context.get('available_tools', [])
        workspace_files = context.get('workspace_files', [])
        
        return f"""You are an autonomous AI agent with the ability to reflect on problems before acting.

USER REQUEST:
{user_request}

RECENT CONVERSATION:
{recent_context}

AVAILABLE TOOLS:
{', '.join(available_tools) if available_tools else 'Standard chat capabilities'}

WORKSPACE FILES:
{', '.join(workspace_files[:10]) if workspace_files else 'Empty workspace'}

Take a moment to think deeply about this request. Analyze it from multiple angles:

1. UNDERSTANDING: What is the user REALLY asking for? (Look beyond surface request)
2. CURRENT KNOWLEDGE: What do I already know that helps solve this?
3. UNKNOWNS: What information am I missing?
4. ASSUMPTIONS: What am I assuming that might not be true?
5. APPROACH: What's my high-level strategy to solve this?
6. CONFIDENCE: How confident am I? (very_low, low, medium, high, very_high)
7. RISKS: What could go wrong with my approach?
8. CLARIFICATION: Should I ask the user for more information?

BE HONEST about limitations. If you're unsure, say so.
If you need to create a new tool or write code, identify that.

Format your response as:
UNDERSTANDING: [deep analysis]
UNKNOWNS: [comma-separated list]
ASSUMPTIONS: [comma-separated list]
APPROACH: [strategy]
CONFIDENCE: [level]
RISKS: [comma-separated list]
NEEDS_CLARIFICATION: [yes/no]
CLARIFICATION_QUESTIONS: [questions if needed]
"""
    
    def _parse_reflection(self, raw_text: str) -> Reflection:
        """Parse LLM output into structured Reflection."""
        
        lines = raw_text.strip().split('\n')
        data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip().lower().replace(' ', '_')] = value.strip()
        
        # Parse confidence level
        confidence_str = data.get('confidence', 'medium').lower()
        confidence_map = {
            'very_low': ConfidenceLevel.VERY_LOW,
            'low': ConfidenceLevel.LOW,
            'medium': ConfidenceLevel.MEDIUM,
            'high': ConfidenceLevel.HIGH,
            'very_high': ConfidenceLevel.VERY_HIGH
        }
        confidence = confidence_map.get(confidence_str, ConfidenceLevel.MEDIUM)
        
        # Parse lists
        unknowns = [u.strip() for u in data.get('unknowns', '').split(',') if u.strip()]
        assumptions = [a.strip() for a in data.get('assumptions', '').split(',') if a.strip()]
        risks = [r.strip() for r in data.get('risks', '').split(',') if r.strip()]
        
        # Parse clarification
        needs_clarification = data.get('needs_clarification', 'no').lower() == 'yes'
        clarification_questions = []
        if needs_clarification:
            q_text = data.get('clarification_questions', '')
            clarification_questions = [q.strip() for q in q_text.split(',') if q.strip()]
        
        return Reflection(
            understanding=data.get('understanding', 'Need more context'),
            unknowns=unknowns,
            assumptions=assumptions,
            approach=data.get('approach', 'Will determine based on user input'),
            confidence=confidence,
            risks=risks,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions
        )
    
    async def should_argue(
        self,
        reflection: Reflection,
        user_request: str
    ) -> Optional[str]:
        """
        Determine if agent should challenge the user's approach.
        
        Returns argument/suggestion if agent sees a better way.
        """
        if reflection.confidence.value < 0.5 and reflection.risks:
            # Low confidence + risks = suggest alternative
            
            argue_prompt = f"""You've reflected on this request and have concerns:

USER REQUEST: {user_request}
YOUR CONCERNS: {', '.join(reflection.risks)}
CONFIDENCE: {reflection.confidence.name}

Should you suggest a different approach? If yes, what would you recommend?

If you see a BETTER way to achieve their goal, argue for it respectfully.
If their approach is fine, return "APPROVED".

Response:"""
            
            argument = await self.llm.generate(argue_prompt, temperature=0.8)
            
            if argument.strip() != "APPROVED":
                return argument
        
        return None
