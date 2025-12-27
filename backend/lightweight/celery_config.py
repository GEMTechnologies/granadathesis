"""
Celery Configuration for Background Workers

Handles async tasks:
- Essay/document generation
- Image batch processing
- Browser scraping jobs
- Long-running code execution
"""

from celery import Celery
import os

# Redis as broker and backend
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery
celery_app = Celery(
    'autonomous_ai',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'workers.agent_worker',
        'workers.image_worker',
        'workers.browser_worker',
        'workers.document_worker'
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'workers.agent_worker.*': {'queue': 'agent'},
        'workers.image_worker.*': {'queue': 'images'},
        'workers.browser_worker.*': {'queue': 'browser'},
        'workers.document_worker.*': {'queue': 'documents'},
    },
    
    # Concurrency
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Results
    result_expires=3600,  # 1 hour
)

if __name__ == '__main__':
    celery_app.start()
