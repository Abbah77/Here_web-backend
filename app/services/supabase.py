# app/services/supabase.py
from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseService:
    """Supabase client service"""
    
    def __init__(self):
        self.client: Client = None
        self._initialized = False

    def initialize(self):
        """Initialize Supabase client"""
        if self._initialized:
            return

        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY  # Use service key for backend operations
            )
            self._initialized = True
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def get_client(self) -> Client:
        """Get Supabase client instance"""
        if not self._initialized:
            self.initialize()
        return self.client

    async def execute_query(self, table: str, query_builder):
        """Execute a Supabase query"""
        try:
            result = query_builder.execute()
            return result
        except Exception as e:
            logger.error(f"Supabase query error on table {table}: {e}")
            raise

    async def select(self, table: str, columns: str = "*"):
        """Select from table"""
        client = self.get_client()
        return client.table(table).select(columns)

    async def insert(self, table: str, data: dict):
        """Insert into table"""
        client = self.get_client()
        return client.table(table).insert(data)

    async def update(self, table: str, data: dict, match_column: str, match_value: str):
        """Update table"""
        client = self.get_client()
        return client.table(table).update(data).eq(match_column, match_value)

    async def delete(self, table: str, match_column: str, match_value: str):
        """Delete from table"""
        client = self.get_client()
        return client.table(table).delete().eq(match_column, match_value)

    async def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str):
        """Upload file to Supabase storage"""
        client = self.get_client()
        return client.storage.from_(bucket).upload(path, file_data, {"content-type": content_type})

    async def get_public_url(self, bucket: str, path: str) -> str:
        """Get public URL for file"""
        client = self.get_client()
        return client.storage.from_(bucket).get_public_url(path)

    async def delete_file(self, bucket: str, path: str):
        """Delete file from storage"""
        client = self.get_client()
        return client.storage.from_(bucket).remove([path])

# Create global instance
supabase_client = SupabaseService()