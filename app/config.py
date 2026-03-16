from typing import List
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # ... other settings ...
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If ALLOWED_ORIGINS is a string (from env var), parse it
        if isinstance(self.ALLOWED_ORIGINS, str):
            # Split by comma and strip whitespace
            self.ALLOWED_ORIGINS = [x.strip() for x in self.ALLOWED_ORIGINS.split(",")]

settings = Settings()
