"""
Agent Worker - Background Agent Tasks

Handles long-running autonomous agent tasks asynchronously.
"""

from celery_config import celery_app
from typing import Dict
import asyncio


@celery_app.task(bind=True, name='agent.solve_async')
def solve_problem_async(self, user_request: str, workspace_id: str, context: Dict = None):
    """
    Asynchronously solve a problem with the autonomous agent.
    
    Use for:
    - Complex multi-step tasks
    - Essay generation
    - System building
    - Research tasks
    """
    
    # Update task state
    self.update_state(state='STARTED', meta={'status': 'Agent is reflecting...'})
    
    # Import here to avoid circular imports
    from services.agent.autonomous_agent import AutonomousAgent
    from services.llm_service import llm_service
    from services.sandbox_manager import sandbox_manager
    from services.vector_service import vector_service
    from services.conversation_memory import conversation_memory
    
    # Create agent
    agent = AutonomousAgent(
        workspace_id=workspace_id,
        llm_service=llm_service,
        sandbox_manager=sandbox_manager,
        vector_service=vector_service,
        conversation_memory=conversation_memory
    )
    
    # Progress callback
    def update_progress(message: str):
        self.update_state(state='PROGRESS', meta={'status': message})
    
    # Run agent (sync wrapper for async)
    async def run():
        return await agent.solve(user_request, context, stream_callback=update_progress)
    
    result = asyncio.run(run())
    
    return {
        'success': result.get('success'),
        'result': result.get('result'),
        'workspace_id': workspace_id
    }


@celery_app.task(name='agent.create_essay')
def create_essay_async(self, topic: str, workspace_id: str, **kwargs):
    """
    Generate a complete essay with images and tables.
    
    Example: "Make me an essay about Uganda with 3 images and 1 table"
    """
    
    self.update_state(state='STARTED', meta={'status': 'Planning essay structure...'})
    
    # Build the request
    num_images = kwargs.get('num_images', 3)
    has_table = kwargs.get('has_table', True)
    
    request = f"Create a comprehensive essay about {topic}"
    if num_images > 0:
        request += f" with {num_images} relevant images"
    if has_table:
        request += " and 1 data table with key statistics"
    
    # Delegate to main solve task
    return solve_problem_async(self, request, workspace_id)
