from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    MONGODB_URL: str
    DATABASE_NAME: str
    API_HOST: str = "0.0.0.0"
    API_HOST_UPLOAD: str = "26.208.148.9"
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
    
    # Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "taskmanagement.agent@gmail.com"
    SMTP_PASSWORD: str = ""  # App password for Gmail
    SMTP_FROM_EMAIL: str = "taskmanagement.agent@gmail.com"
    SMTP_FROM_NAME: str = "Task Management"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = "http://localhost:5173"
    
    # API Base URL for file serving (for production, set to your domain)
    BASE_URL: Optional[str] = None  # If None, will auto-construct from API_HOST:API_PORT

    # Stripe Settings
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

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
