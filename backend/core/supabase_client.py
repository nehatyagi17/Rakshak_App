import os
from supabase import create_client, Client
from decouple import config

class SupabaseManager:
    _instance = None
    
    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            url: str = config("SUPABASE_URL")
            key: str = config("SUPABASE_KEY")
            cls._instance = create_client(url, key)
        return cls._instance

# Export the initialized client
supabase: Client = SupabaseManager.get_client()
