"""
Configuration settings for LCopilot application.
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/lcopilot"
    
    # AWS Services
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "lcopilot-documents"
    
    # Google Cloud
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_DOCUMENTAI_LOCATION: str = "us"
    GOOGLE_DOCUMENTAI_PROCESSOR_ID: Optional[str] = None
    
    # Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Stub Mode Configuration
    USE_STUBS: bool = False
    STUB_SCENARIO: str = "lc_happy.json"
    STUB_FAIL_OCR: bool = False
    STUB_FAIL_STORAGE: bool = False
    STUB_DATA_DIR: str = "./stubs"
    STUB_UPLOAD_DIR: str = "/tmp/lcopilot_uploads"
    
    # Application Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        # Load .env.production if ENVIRONMENT is production, otherwise .env
        env_file = ".env.production" if os.getenv("ENVIRONMENT") == "production" else ".env"
        case_sensitive = True
    
    @field_validator('USE_STUBS', mode='before')
    @classmethod
    def parse_use_stubs(cls, v):
        """Parse USE_STUBS from string or boolean."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)
    
    @field_validator('STUB_FAIL_OCR', 'STUB_FAIL_STORAGE', mode='before')
    @classmethod
    def parse_stub_fails(cls, v):
        """Parse stub failure flags from string or boolean."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)


# Global settings instance
settings = Settings()