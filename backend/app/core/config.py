from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "PhD Thesis Generator"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # AI Keys
    DEEPSEEK_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # Search Tools
    TAVILY_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    
    # Zotero Integration
    ZOTERO_API_KEY: Optional[str] = None
    ZOTERO_USER_ID: Optional[str] = None
    ZOTERO_GROUP_ID: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
