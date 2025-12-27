"""
Autonomous Agent Brain - Planning Engine

Multi-step reasoning and strategic planning.
Breaks complex problems into executable steps.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Types of actions the agent can take."""
    SEARCH_DOCUMENTS = "search_documents"
    EXECUTE_CODE = "execute_code"
    CREATE_TOOL = "create_tool"
    USE_TOOL = "use_tool"
    ASK_USER = "ask_user"
    GENERATE_TEXT = "generate_text"
    GENERATE_IMAGE = "generate_image"  # NEW: Image generation
    EDIT_IMAGE = "edit_image"  # NEW: Image editing
    BROWSE_WEB = "browse_web"  # NEW: Browser automation
    SCRAPE_DATA = "scrape_data"  # NEW: Web scraping


@dataclass
class Step:
    """Single step in agent's plan."""
    action: ActionType
    description: str
    params: Dict
    expected_outcome: str
    fallback_action: Optional[str] = None
    requires_approval: bool = False


@dataclass
class Plan:
    """Complete execution plan."""
    goal: str
    steps: List[Step]
    success_criteria: str
    estimated_time: str
    complexity: str  # 'simple', 'moderate', 'complex'


class PlanningEngine:
    """
    Creates executable plans to achieve goals.
    
    Capabilities:
    - Breaks down complex tasks into steps
    - Identifies dependencies
    - Plans for failure scenarios
    - Estimates complexity and time
    """
    
    def __init__(self, llm_service):
        self.llm = llm_service
    
    async def create_plan(
        self,
        goal: str,
        reflection: 'Reflection',
        available_tools: List[str],
        workspace_id: str
    ) -> Plan:
        """
        Generate detailed, executable plan.
        
        The agent thinks through:
        - What needs to be done
        - In what order
        - What could fail
        - How to recover from failures
        """
        
        planning_prompt = self._build_planning_prompt(
            goal,
            reflection,
            available_tools
        )
        
        # Get plan from LLM
        raw_plan = await self.llm.generate(
            prompt=planning_prompt,
            temperature=0.5,  # Balanced creativity/precision
            max_tokens=1000
        )
        
        # Parse into structured plan
        plan = self._parse_plan(raw_plan, goal)
        
        return plan
    
    def _build_planning_prompt(
        self,
        goal: str,
        reflection: 'Reflection',
        available_tools: List[str]
    ) -> str:
        """Build the planning prompt."""
        
        return f"""You are planning how to achieve a goal autonomously.

GOAL:
{goal}

YOUR REFLECTION:
- Understanding: {reflection.understanding}
- What you know: {', '.join(reflection.assumptions) if reflection.assumptions else 'Starting fresh'}
- What you don't know: {', '.join(reflection.unknowns) if reflection.unknowns else 'All clear'}
- Confidence: {reflection.confidence.name}

AVAILABLE TOOLS:
{', '.join(available_tools) if available_tools else 'Standard capabilities'}

AVAILABLE ACTIONS:
1. SEARCH_DOCUMENTS - Search RAG database for relevant information
2. EXECUTE_CODE - Run Python code in secure sandbox
3. CREATE_TOOL - Generate new Python function/tool
4. USE_TOOL - Use existing tool
5. ASK_USER - Request clarification or input
6. GENERATE_TEXT - Generate content/response

Create a step-by-step plan. For EACH step specify:
- ACTION: One of the actions above
- DESCRIPTION: What this step does
- PARAMS: Parameters needed (e.g., code, search query, tool name)
- EXPECTED_OUTCOME: What you expect to happen
- FALLBACK: What to do if this step fails

Format:
STEP 1:
ACTION: [action_type]
DESCRIPTION: [what it does]
PARAMS: [parameters]
EXPECTED_OUTCOME: [expected result]
FALLBACK: [alternative if fails]

STEP 2:
...

SUCCESS_CRITERIA: [How to know you've achieved the goal]
ESTIMATED_TIME: [rough estimate]
COMPLEXITY: [simple/moderate/complex]

If you need to CREATE a new tool because existing tools aren't sufficient, plan that explicitly.
Be specific and actionable.
"""
    
    def _parse_plan(self, raw_text: str, goal: str) -> Plan:
        """Parse LLM output into structured Plan."""
        
        steps = []
        current_step = {}
        
        for line in raw_text.split('\n'):
            line = line.strip()
            
            if line.startswith('STEP'):
                # Save previous step
                if current_step:
                    steps.append(self._create_step(current_step))
                current_step = {}
            
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                current_step[key] = value.strip()
        
        # Save last step
        if current_step:
            steps.append(self._create_step(current_step))
        
        # Extract metadata
        success_criteria = current_step.get('success_criteria', 'Goal achieved')
        estimated_time = current_step.get('estimated_time', 'Unknown')
        complexity = current_step.get('complexity', 'moderate')
        
        return Plan(
            goal=goal,
            steps=steps,
            success_criteria=success_criteria,
            estimated_time=estimated_time,
            complexity=complexity
        )
    
    def _create_step(self, step_data: Dict) -> Step:
        """Create Step object from parsed data."""
        
        action_str = step_data.get('action', 'generate_text').upper().replace(' ', '_')
        
        # Map string to ActionType
        try:
            action = ActionType[action_str]
        except KeyError:
            action = ActionType.GENERATE_TEXT
        
        # Parse params
        params_str = step_data.get('params', '{}')
        try:
            params = eval(params_str) if params_str.startswith('{') else {'input': params_str}
        except:
            params = {'input': params_str}
        
        return Step(
            action=action,
            description=step_data.get('description', 'Execute action'),
            params=params,
            expected_outcome=step_data.get('expected_outcome', 'Success'),
            fallback_action=step_data.get('fallback'),
            requires_approval='CREATE_TOOL' in action_str or 'MODIFY' in step_data.get('description', '')
        )
    
    async def adapt_plan(
        self,
        original_plan: Plan,
        failed_step: Step,
        error: str
    ) -> Plan:
        """
        Adapt plan when a step fails.
        
        Agent learns from failure and creates new plan.
        """
        
        adapt_prompt = f"""A step in your plan failed. Adapt the plan to work around it.

ORIGINAL GOAL: {original_plan.goal}

FAILED STEP:
Action: {failed_step.action.value}
Description: {failed_step.description}
Error: {error}

FALLBACK SUGGESTED: {failed_step.fallback_action or 'None'}

Create a NEW plan that:
1. Acknowledges the failure
2. Uses the fallback if available
3. OR finds an alternative approach
4. Continues toward the goal

Use the same format as before (STEP 1, STEP 2, etc.)
"""
        
        raw_adapted_plan = await self.llm.generate(adapt_prompt, temperature=0.6)
        
        return self._parse_plan(raw_adapted_plan, original_plan.goal)
