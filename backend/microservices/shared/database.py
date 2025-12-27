"""
Shared database connection for all services.
"""
import os
from supabase import create_client, Client


class DatabaseConnection:
    """Singleton Supabase connection."""
    
    _instance: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._instance is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
            
            cls._instance = create_client(url, key)
        
        return cls._instance


# Convenience function
def get_db() -> Client:
    """Get database client."""
    return DatabaseConnection.get_client()
