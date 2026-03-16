from pydantic_settings import BaseSettings
from typing import List
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
    MAX_UPLOAD_SIZE: int = 10485760
    
    # App
    DEBUG: bool = False
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def get_allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS

# Create settings instance
settings = Settings()
