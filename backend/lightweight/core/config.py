from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Agent concurrency settings
    MAX_CONCURRENT_AGENTS: int = Field(
        default=50,  # Increased from 10 to support 20+ agents
        description="Maximum number of agents that can run concurrently"
    )
    PROJECT_NAME: str = "PhD Thesis Generator"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Redis - defaults to localhost if not in Docker
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Keys
    DEEPSEEK_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None  # For Gemini/Imagen direct API
    OPENROUTER_API_KEY: Optional[str] = None
    
    # Search & Research Tools
    TAVILY_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_URL: Optional[str] = "https://api.firecrawl.dev"
    CORE_API_KEY: Optional[str] = None  # CORE API for open access papers
    RAPID_API_KEY: Optional[str] = None  # RapidAPI for various APIs
    
    # Code & Tool Execution
    MORPH_API_KEY: Optional[str] = None
    E2B_API_KEY: Optional[str] = None
    
    # Image APIs
    UNSPLASH_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    PIXABAY_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None  # For DALL-E
    REPLICATE_API_TOKEN: Optional[str] = None  # For Stable Diffusion
    STABILITY_API_KEY: Optional[str] = None  # Direct Stability AI API
    
    # Zotero Integration
    ZOTERO_API_KEY: Optional[str] = None
    ZOTERO_USER_ID: Optional[str] = None
    ZOTERO_GROUP_ID: Optional[str] = None
    
    # Composio Agent Integration
    COMPOSIO_API_KEY: Optional[str] = None
    COMPOSIO_WEBHOOK_SECRET: Optional[str] = None
    COMPOSIO_API_BASE: Optional[str] = "https://backend.composio.dev"
    
    # Webhooks
    WEBHOOK_BASE_URL: Optional[str] = None
    TRIGGER_WEBHOOK_SECRET: Optional[str] = None
    SUPABASE_WEBHOOK_SECRET: Optional[str] = None
    
    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
