# app/database.py
from supabase import create_client, Client
from app.config import settings
import asyncpg
import redis.asyncio as redis
from typing import Optional

class Database:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize all database connections"""
        # Supabase client
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # PostgreSQL connection pool
        self.pg_pool = await asyncpg.create_pool(
            settings.SUPABASE_URL.replace(
                "https://", "postgresql://"
            ),  # Convert to PostgreSQL URL
            min_size=5,
            max_size=20
        )
        
        # Redis for real-time and caching
        if settings.REDIS_URL:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )

    async def close(self):
        """Close all connections"""
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis:
            await self.redis.close()

# Global database instance
db = Database()