"""
Configuration for workspace paths and system settings

Makes all paths configurable instead of hardcoded
"""

import os
from pathlib import Path

# Base directories - configurable via environment variables
WORKSPACES_ROOT = os.getenv('WORKSPACES_ROOT', '/tmp/workspaces')
UPLOADS_ROOT = os.getenv('UPLOADS_ROOT', '/tmp/uploads')
CACHE_ROOT = os.getenv('CACHE_ROOT', '/tmp/cache')

# Create base directories
Path(WORKSPACES_ROOT).mkdir(parents=True, exist_ok=True)
Path(UPLOADS_ROOT).mkdir(parents=True, exist_ok=True)
Path(CACHE_ROOT).mkdir(parents=True, exist_ok=True)


def get_workspace_dir(workspace_id: str) -> Path:
    """Get workspace directory path"""
    return Path(WORKSPACES_ROOT) / workspace_id


def get_workspace_subdir(workspace_id: str, subdir: str) -> Path:
    """Get workspace subdirectory (images, tools, browser, etc.)"""
    path = get_workspace_dir(workspace_id) / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_images_dir(workspace_id: str) -> Path:
    """Get images directory for workspace"""
    return get_workspace_subdir(workspace_id, 'images')


def get_tools_dir(workspace_id: str) -> Path:
    """Get tools directory for workspace"""
    return get_workspace_subdir(workspace_id, 'tools')


def get_browser_dir(workspace_id: str) -> Path:
    """Get browser screenshots directory for workspace"""
    return get_workspace_subdir(workspace_id, 'browser')


def get_datasets_dir(workspace_id: str) -> Path:
    """Get datasets directory for workspace"""
    return get_workspace_subdir(workspace_id, 'datasets')


def get_appendices_dir(workspace_id: str) -> Path:
    """Get appendices directory for workspace"""
    return get_workspace_subdir(workspace_id, 'appendices')


# Redis & Database configs
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/thesis_db')

# API configs
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')

# Worker configs
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
