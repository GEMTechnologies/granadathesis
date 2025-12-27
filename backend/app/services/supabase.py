from supabase import create_client, Client
from app.core.config import settings

class SupabaseService:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.client: Client = create_client(self.url, self.key)

    def get_client(self) -> Client:
        return self.client

supabase_service = SupabaseService()
