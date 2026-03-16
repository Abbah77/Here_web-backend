# app/database.py
from supabase import create_client, Client
from app.config import settings
import asyncpg
import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize all database connections"""
        # Supabase client (REST API)
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        logger.info("✅ Supabase client initialized")
        
        # For PostgreSQL direct connection, you need the DATABASE_URL
        # You can get this from your Supabase dashboard:
        # Project Settings → Database → Connection string → URI
        
        # If you have the DATABASE_URL in your environment, uncomment this:
        # database_url = os.getenv("DATABASE_URL")
        # if database_url:
        #     self.pg_pool = await asyncpg.create_pool(
        #         database_url,
        #         min_size=5,
        #         max_size=20,
        #         command_timeout=60
        #     )
        #     logger.info("✅ PostgreSQL pool initialized")
        
        # Redis for real-time and caching (optional)
        if settings.REDIS_URL:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            logger.info("✅ Redis initialized")

    async def close(self):
        """Close all connections"""
        if self.pg_pool:
            await self.pg_pool.close()
        if self.redis:
            await self.redis.close()
        logger.info("Database connections closed")

# Global database instance
db = Database()
