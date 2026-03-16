# app/database.py
from supabase import create_client, Client
from app.config import settings
import asyncpg
import redis.asyncio as redis
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """Initialize all database connections"""
        try:
            # Supabase client (REST API)
            self.supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            logger.info("✅ Supabase client initialized")
            
            # Test Supabase connection with a simple query
            try:
                # Try to fetch one record to test connection
                test_query = self.supabase.table("profiles").select("*").limit(1).execute()
                logger.info("✅ Supabase connection test successful")
            except Exception as e:
                logger.warning(f"⚠️ Supabase connection test failed: {e}")
            
            # PostgreSQL direct connection (optional)
            database_url = os.getenv("DATABASE_URL") or getattr(settings, 'DATABASE_URL', None)
            if database_url:
                try:
                    self.pg_pool = await asyncpg.create_pool(
                        database_url,
                        min_size=1,
                        max_size=10,
                        command_timeout=30,
                        max_queries=50000,
                        max_inactive_connection_lifetime=300
                    )
                    logger.info("✅ PostgreSQL pool initialized")
                    
                    # Test PostgreSQL connection
                    async with self.pg_pool.acquire() as conn:
                        await conn.execute("SELECT 1")
                    logger.info("✅ PostgreSQL connection test successful")
                    
                except Exception as e:
                    logger.error(f"❌ PostgreSQL connection failed: {e}")
                    self.pg_pool = None
            else:
                logger.info("ℹ️ PostgreSQL direct connection not configured (optional)")
            
            # Redis for real-time and caching (optional)
            if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
                try:
                    self.redis = await redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                    # Test Redis connection
                    await self.redis.ping()
                    logger.info("✅ Redis initialized and connected")
                except Exception as e:
                    logger.error(f"❌ Redis connection failed: {e}")
                    self.redis = None
            else:
                logger.info("ℹ️ Redis not configured (optional)")
            
            self._initialized = True
            logger.info("✅ Database initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def close(self):
        """Close all connections"""
        logger.info("Closing database connections...")
        
        if self.pg_pool:
            try:
                await self.pg_pool.close()
                logger.info("✅ PostgreSQL pool closed")
            except Exception as e:
                logger.error(f"❌ Error closing PostgreSQL pool: {e}")
        
        if self.redis:
            try:
                await self.redis.close()
                logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing Redis connection: {e}")
        
        self._initialized = False
        logger.info("✅ All database connections closed")

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized

    async def health_check(self) -> dict:
        """Check health of all database connections"""
        status = {
            "supabase": "unknown",
            "postgresql": "not_configured",
            "redis": "not_configured"
        }
        
        # Check Supabase
        if self.supabase:
            try:
                # Simple test query
                await self.supabase.table("profiles").select("*").limit(1).execute()
                status["supabase"] = "healthy"
            except Exception:
                status["supabase"] = "unhealthy"
        
        # Check PostgreSQL
        if self.pg_pool:
            try:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                status["postgresql"] = "healthy"
            except Exception:
                status["postgresql"] = "unhealthy"
        elif hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            status["postgresql"] = "disconnected"
        
        # Check Redis
        if self.redis:
            try:
                await self.redis.ping()
                status["redis"] = "healthy"
            except Exception:
                status["redis"] = "unhealthy"
        elif hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            status["redis"] = "disconnected"
        
        return status

# Global database instance
db = Database()
