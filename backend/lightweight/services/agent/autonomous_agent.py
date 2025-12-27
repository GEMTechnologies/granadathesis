"""
Autonomous Agent - Main Orchestrator

Ties together all components into a self-improving,
autonomous problem-solving system.

This is the BRAIN.
"""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import json

from .reflection_engine import ReflectionEngine, Reflection
from .planning_engine import PlanningEngine, Plan, ActionType
from .tool_creator import ToolCreator, ToolSpec


class AutonomousAgent:
    """
    Truly autonomous agent with:
    - Self-reflection
    - Multi-step planning
    - Dynamic tool creation
    - Code execution
    - Learning from experience
    
    The agent can solve problems it's never seen before.
    """
    
    def __init__(
        self,
        workspace_id: str,
        llm_service,
        sandbox_manager,
        vector_service,
        conversation_memory
    ):
        self.workspace_id = workspace_id
        self.llm = llm_service
        self.sandbox = sandbox_manager
        self.vector = vector_service
        self.memory = conversation_memory
        
        # Initialize engines
        self.reflection_engine = ReflectionEngine(llm_service)
        self.planning_engine = PlanningEngine(llm_service)
        self.tool_creator = ToolCreator(llm_service, sandbox_manager)
        
        # State
        self.current_goal: Optional[str] = None
        self.current_plan: Optional[Plan] = None
        self.execution_history: List[Dict] = []
        self.created_tools: List = []
    
    async def solve(
        self,
        user_request: str,
        context: Dict = None,
        stream_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Autonomous problem-solving loop.
        
        Process:
        1. REFLECT on the problem
        2. REASON (argue if needed)
        3. PLAN multi-step solution
        4. EXECUTE plan (create tools if needed)
        5. LEARN from results
        6. IMPROVE if failed
        
        Returns:
            Dict: {
                "success": bool,
                "result": any,
                "thoughts": str,
                "plan": Plan,
                "tools_created": list,
                "execution_log": list
            }
        """
        self.current_goal = user_request
        context = context or {}
        
        try:
            # Stream: Agent is thinking
            if stream_callback:
                await stream_callback("🧠 Agent is reflecting on your request...")
            
            # 1. REFLECT
            reflection = await self._reflect(user_request, context)
            
            if stream_callback:
                await stream_callback(f"💭 Thoughts: {reflection.understanding[:200]}...")
                await stream_callback(f"📊 Confidence: {reflection.confidence.name}")
            
            # 2. REASON (Challenge if needed)
            if reflection.needs_clarification:
                return {
                    "success": False,
                    "needs_clarification": True,
                    "questions": reflection.clarification_questions,
                    "reflection": reflection
                }
            
            # Check if should argue for better approach
            argument = await self.reflection_engine.should_argue(reflection, user_request)
            if argument:
                if stream_callback:
                    await stream_callback(f"💬 Agent suggests: {argument}")
                
                return {
                    "success": False,
                    "suggests_alternative": True,
                    "argument": argument,
                    "reflection": reflection
                }
            
            # 3. PLAN
            if stream_callback:
                await stream_callback("📋 Creating execution plan...")
            
            plan = await self._plan(user_request, reflection, context)
            self.current_plan = plan
            
            if stream_callback:
                await stream_callback(f"📝 Plan: {len(plan.steps)} steps | Complexity: {plan.complexity}")
            
            # 4. EXECUTE
            if stream_callback:
                await stream_callback("⚡ Executing plan...")
            
            result = await self._execute_plan(plan, stream_callback)
            
            # 5. LEARN
            await self._learn_from_execution(user_request, reflection, plan, result)
            
            return {
                "success": result['success'],
                "result": result['output'],
                "thoughts": reflection.understanding,
                "plan": plan,
                "tools_created": self.created_tools,
                "execution_log": self.execution_history
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_log": self.execution_history
            }
    
    async def _reflect(self, user_request: str, context: Dict) -> Reflection:
        """Agent reflects on the problem."""
        
        # Get conversation history
        history = await self.memory.get_recent_messages(self.workspace_id, limit=10)
        
        # Add context
        context['available_tools'] = await self._get_available_tools()
        context['workspace_files'] = await self._get_workspace_files()
        
        reflection = await self.reflection_engine.reflect(
            user_request=user_request,
            context=context,
            conversation_history=history,
            workspace_id=self.workspace_id
        )
        
        return reflection
    
    async def _plan(
        self,
        user_request: str,
        reflection: Reflection,
        context: Dict
    ) -> Plan:
        """Agent creates execution plan."""
        
        available_tools = await self._get_available_tools()
        
        plan = await self.planning_engine.create_plan(
            goal=user_request,
            reflection=reflection,
            available_tools=available_tools,
            workspace_id=self.workspace_id
        )
        
        return plan
    
    async def _execute_plan(
        self,
        plan: Plan,
        stream_callback: Optional[Callable] = None
    ) -> Dict:
        """Execute the plan step by step."""
        
        results = []
        
        for i, step in enumerate(plan.steps, 1):
            if stream_callback:
                await stream_callback(f"▶️ Step {i}/{len(plan.steps)}: {step.description}")
            
            try:
                result = await self._execute_step(step, stream_callback)
                results.append(result)
                
                self.execution_history.append({
                    "step": i,
                    "action": step.action.value,
                    "description": step.description,
                    "success": True,
                    "result": result
                })
                
                if stream_callback:
                    await stream_callback(f"✅ Step {i} completed")
            
            except Exception as e:
                # Step failed - try fallback or adapt plan
                if stream_callback:
                    await stream_callback(f"❌ Step {i} failed: {str(e)}")
                
                self.execution_history.append({
                    "step": i,
                    "action": step.action.value,
                    "description": step.description,
                    "success": False,
                    "error": str(e)
                })
                
                # Try fallback
                if step.fallback_action:
                    if stream_callback:
                        await stream_callback(f"🔄 Trying fallback: {step.fallback_action}")
                    # TODO: Execute fallback
                
                # Or adapt plan
                else:
                    if stream_callback:
                        await stream_callback("🔄 Adapting plan...")
                    
                    new_plan = await self.planning_engine.adapt_plan(
                        original_plan=plan,
                        failed_step=step,
                        error=str(e)
                    )
                    
                    # Continue with adapted plan
                    return await self._execute_plan(new_plan, stream_callback)
        
        # Combine results
        final_output = self._combine_results(results)
        
        return {
            "success": True,
            "output": final_output,
            "steps_completed": len(results)
        }
    
    async def _execute_step(self, step, stream_callback: Optional[Callable] = None) -> Any:
        """Execute a single step."""
        
        if step.action == ActionType.SEARCH_DOCUMENTS:
            # RAG search
            query = step.params.get('query', '')
            results = await self.vector.search(
                workspace_id=self.workspace_id,
                query=query,
                n_results=5
            )
            return results
        
        elif step.action == ActionType.EXECUTE_CODE:
            # Execute code in sandbox
            code = step.params.get('code', '')
            result = await self.sandbox.execute_code(
                workspace_id=self.workspace_id,
                code=code,
                language='python'
            )
            return result
        
        elif step.action == ActionType.CREATE_TOOL:
            # Generate new tool
            tool_spec = ToolSpec(
                name=step.params.get('name', 'custom_tool'),
                purpose=step.params.get('purpose', ''),
                inputs=step.params.get('inputs', {}),
                outputs=step.params.get('outputs', 'any'),
                requirements=step.params.get('requirements', [])
            )
            
            tool = await self.tool_creator.create_tool(
                tool_spec=tool_spec,
                workspace_id=self.workspace_id
            )
            
            self.created_tools.append(tool)
            
            if stream_callback:
                await stream_callback(f"🔨 Created tool: {tool.name}")
            
            return tool
        
        elif step.action == ActionType.GENERATE_TEXT:
            # Generate content
            prompt = step.params.get('prompt', '')
            text = await self.llm.generate(prompt)
            return text
        
        elif step.action == ActionType.GENERATE_IMAGE:
            # Generate image
            from services.image_creator import ImageCreator
            import os
            
            creator = ImageCreator(
                workspace_id=self.workspace_id,
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            
            image = await creator.generate(
                prompt=step.params.get('prompt', ''),
                method=step.params.get('method', 'auto'),
                size=step.params.get('size', '1024x1024')
            )
            
            if stream_callback:
                await stream_callback(f"🎨 Generated image: {image.image_id}")
            
            return image
        
        elif step.action == ActionType.EDIT_IMAGE:
            # Edit existing image
            from services.image_creator import ImageCreator
            
            creator = ImageCreator(workspace_id=self.workspace_id)
            
            edited = await creator.edit(
                image_id=step.params.get('image_id', ''),
                edit_prompt=step.params.get('edit_prompt', ''),
                operations=step.params.get('operations', [])
            )
            
            if stream_callback:
                await stream_callback(f"✏️ Edited image: {edited.image_id}")
            
            return edited
        
        else:
            raise ValueError(f"Unknown action type: {step.action}")
    
    async def _learn_from_execution(
        self,
        request: str,
        reflection: Reflection,
        plan: Plan,
        result: Dict
    ):
        """Learn from this interaction for future improvements."""
        
        # Store successful pattern
        if result['success']:
            pattern = {
                "request": request,
                "approach": reflection.approach,
                "plan_steps": [s.description for s in plan.steps],
                "tools_created": [t.name for t in self.created_tools],
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            # Index in vector DB for future retrieval
            await self.vector.add_documents(
                workspace_id=self.workspace_id,
                documents=[{
                    "text": json.dumps(pattern),
                    "metadata": {
                        "type": "successful_pattern",
                        "complexity": plan.complexity
                    }
                }]
            )
    
    async def _get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        from config import get_tools_dir
        
        tools_dir = get_tools_dir(self.workspace_id)
        if not tools_dir.exists():
            return []
        
        return [f.stem for f in tools_dir.glob("*.py")]
    
    async def _get_workspace_files(self) -> List[str]:
        """Get list of workspace files."""
        from config import get_workspace_dir
        
        workspace_dir = get_workspace_dir(self.workspace_id)
        if not workspace_dir.exists():
            return []
        
        return [str(f.relative_to(workspace_dir)) for f in workspace_dir.rglob("*") if f.is_file()][:20]
    
    def _combine_results(self, results: List) -> Any:
        """Combine step results into final output."""
        if len(results) == 1:
            return results[0]
        return results
