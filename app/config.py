from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # CORS - Accept as string and convert to list
    ALLOWED_ORIGINS: str = "http://localhost:8080"
    
    # Storage
    STORAGE_BUCKET: str = "media"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # Redis (optional) - ADDED THIS LINE
    REDIS_URL: Optional[str] = None
    
    # App
    DEBUG: bool = False
    PORT: int = 8000
    
    # Database (optional) - you can add this later if needed
    DATABASE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    @property
    def get_allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS
    
    @property
    def is_redis_configured(self) -> bool:
        """Check if Redis is configured"""
        return self.REDIS_URL is not None and self.REDIS_URL.strip() != ""

# Create settings instance
settings = Settings()

# Optional: Print config status on startup (remove in production)
if settings.DEBUG:
    print("✅ Settings loaded successfully")
    print(f"🔧 Environment: {'Production' if not settings.DEBUG else 'Development'}")
    print(f"🔌 Redis configured: {settings.is_redis_configured}")
