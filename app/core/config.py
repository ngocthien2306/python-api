from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    MONGODB_URL: str
    DATABASE_NAME: str
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "local"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Push Notification Settings
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_SUBJECT: str = "mailto:your-email@example.com"
    
    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        # Determine which env file to use based on ENV variable
        env = os.getenv('ENV', 'local')
        if env == 'prod':
            self.Config.env_file = '.env.prod'
        elif env == 'local':
            self.Config.env_file = '.env.local'
        else:
            self.Config.env_file = '.env'
        super().__init__(**kwargs)
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]

settings = Settings()
