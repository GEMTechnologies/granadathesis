"""
Image Worker - Background Image Processing

Handles batch image generation and editing.
"""

from celery_config import celery_app
from typing import List, Dict
import asyncio


@celery_app.task(bind=True, name='image.generate_batch')
def generate_images_batch(self, prompts: List[str], workspace_id: str, method='auto'):
    """
    Generate multiple images in batch.
    
    Args:
        prompts: List of image prompts
        workspace_id: Workspace ID
        method: 'auto', 'dalle', 'python', or 'search'
    """
    
    self.update_state(state='STARTED', meta={'total': len(prompts), 'completed': 0})
    
    from services.image_creator import ImageCreator
    import os
    
    creator = ImageCreator(
        workspace_id=workspace_id,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    results = []
    
    async def generate_all():
        for i, prompt in enumerate(prompts):
            self.update_state(
                state='PROGRESS',
                meta={
                    'total': len(prompts),
                    'completed': i,
                    'current': prompt
                }
            )
            
            image = await creator.generate(prompt=prompt, method=method)
            results.append({
                'prompt': prompt,
                'image_id': image.image_id,
                'path': image.file_path
            })
        
        return results
    
    return asyncio.run(generate_all())


@celery_app.task(name='image.process_edits')
def process_image_edits(self, image_id: str, workspace_id: str, edit_pipeline: List[Dict]):
    """
    Apply multiple edits to an image in sequence.
    
    Args:
        image_id: Source image ID
        workspace_id: Workspace ID
        edit_pipeline: List of edit operations
    """
    
    from services.image_creator import ImageCreator
    
    creator = ImageCreator(workspace_id=workspace_id)
    
    async def apply_edits():
        current_id = image_id
        
        for i, edit in enumerate(edit_pipeline):
            self.update_state(
                state='PROGRESS',
                meta={'step': i + 1, 'total': len(edit_pipeline)}
            )
            
            edited = await creator.edit(
                image_id=current_id,
                edit_prompt=edit.get('prompt', ''),
                operations=edit.get('operations', [])
            )
            
            current_id = edited.image_id
        
        return {'final_image_id': current_id}
    
    return asyncio.run(apply_edits())
