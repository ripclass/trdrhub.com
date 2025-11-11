"""
Configuration settings for LCopilot application.
"""

import os
import json
from typing import Optional, List, Any, Dict
from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/lcopilot"
    DIRECT_DATABASE_URL: Optional[str] = None  # For migrations - direct connection (Supabase port 5432)
    
    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def normalize_database_url(cls, v: Any) -> str:
        """Normalize postgres:// to postgresql:// and remove pgbouncer=true parameter."""
        if isinstance(v, str):
            # Normalize postgres:// to postgresql://
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)
            # Remove pgbouncer=true parameter - psycopg2 doesn't recognize it
            if "pgbouncer=true" in v:
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                parsed = urlparse(v)
                query_params = parse_qs(parsed.query)
                if "pgbouncer" in query_params:
                    del query_params["pgbouncer"]
                new_query = urlencode(query_params, doseq=True)
                new_parsed = parsed._replace(query=new_query)
                v = urlunparse(new_parsed)
        return v
    
    # AWS Services
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "lcopilot-documents"
    
    # Google Cloud
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_DOCUMENTAI_LOCATION: str = "us"
    GOOGLE_DOCUMENTAI_PROCESSOR_ID: Optional[str] = None
    
    # DeepSeek OCR Configuration
    USE_DEEPSEEK_OCR: bool = False  # Enable DeepSeek OCR as primary provider
    DEEPSEEK_OCR_MODEL_NAME: str = "deepseek-ai/deepseek-ocr"  # Hugging Face model identifier
    DEEPSEEK_OCR_DEVICE: Optional[str] = None  # 'cuda', 'cpu', or None for auto-detect
    
    # Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SUPABASE_ISSUER: Optional[str] = None
    SUPABASE_AUDIENCE: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None
    AUTH0_ISSUER: Optional[str] = None
    AUTH0_AUDIENCE: Optional[str] = None
    AUTH0_JWKS_URL: Optional[str] = None
    
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

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"

    # RulHub Integration
    USE_RULHUB_API: bool = False
    
    # Rules System
    USE_JSON_RULES: bool = False  # Enable JSON ruleset validation system
    RULESET_CACHE_TTL_MINUTES: int = 10  # Cache TTL for rulesets
    RULHUB_API_URL: str = ""
    RULHUB_API_KEY: str = ""

    # Stripe configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_STARTER: Optional[str] = None
    STRIPE_PRICE_PROFESSIONAL: Optional[str] = None
    STRIPE_PRICE_ENTERPRISE: Optional[str] = None

    # Stub tooling guard
    STUB_STATUS_TOKEN: Optional[str] = None

    # SSLCommerz configuration
    SSLCOMMERZ_STORE_ID: Optional[str] = None
    SSLCOMMERZ_STORE_PASSWORD: Optional[str] = None
    SSLCOMMERZ_SANDBOX: bool = True
    
    # AI/LLM Configuration
    AI_ENRICHMENT: bool = False  # Enable AI enrichment in validation pipeline
    LLM_PROVIDER: str = "openai"  # openai|anthropic
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL_VERSION: str = "gpt-4o-mini"  # OpenAI model
    ANTHROPIC_MODEL_VERSION: str = "claude-3-haiku-20240307"  # Anthropic model
    AI_MAX_OUTPUT_TOKENS_SYSTEM: int = 600  # System enrichment max tokens
    AI_MAX_OUTPUT_TOKENS_LETTER: int = 800  # Letter generation max tokens
    AI_MAX_OUTPUT_TOKENS_TRANSLATE: int = 600  # Translation max tokens
    AI_MAX_OUTPUT_TOKENS_CHAT: int = 400  # Chat max tokens
    AI_TIMEOUT_MS: int = 15000  # LLM API timeout
    
    # AI Rate Limits
    AI_RATE_LIMIT_PER_USER_PER_MIN: int = 10
    AI_RATE_LIMIT_PER_TENANT_PER_MIN: int = 50
    AI_MIN_INTERVAL_PER_LC_MS: int = 2000
    
    # SME Per-LC Limits
    SME_PER_LC_LIMIT_LETTERS: int = 3
    SME_PER_LC_LIMIT_SUMMARIES: int = 3
    SME_PER_LC_LIMIT_TRANSLATIONS: int = 5
    SME_PER_LC_LIMIT_CHAT: int = 10
    
    # Bank Per-LC Limits
    BANK_PER_LC_LIMIT_LETTERS: int = 5
    BANK_PER_LC_LIMIT_SUMMARIES: int = 5
    BANK_PER_LC_LIMIT_TRANSLATIONS: int = 10
    BANK_PER_LC_LIMIT_CHAT: int = 20
    
    # Bank Tenant Monthly Pools
    BANK_TENANT_MONTHLY_LETTERS: int = 1000
    BANK_TENANT_MONTHLY_TRANSLATIONS: int = 2000
    BANK_TENANT_MONTHLY_SUMMARIES: int = 2000
    BANK_TENANT_MONTHLY_CHAT: int = 5000
    BANK_TENANT_RESERVE_PERCENT: float = 30.0  # Reserve 30% for system enrichment
    
    # CORS Configuration
    CORS_ALLOW_ORIGINS: List[str] = ["http://localhost:5173"]  # Override per environment
    
    model_config = SettingsConfigDict(
        # Load .env.production if ENVIRONMENT is production, otherwise .env
        env_file=".env.production" if os.getenv("ENVIRONMENT") == "production" else ".env",
        case_sensitive=True,
        env_ignore_empty=True,
    )
    
    @model_validator(mode='before')
    @classmethod
    def preprocess_cors_origins(cls, data: Any) -> Any:
        """Preprocess CORS_ALLOW_ORIGINS before pydantic-settings tries to JSON parse it."""
        if isinstance(data, dict):
            if 'CORS_ALLOW_ORIGINS' in data:
                cors_value = data['CORS_ALLOW_ORIGINS']
                # If it's an empty string or invalid value, remove it so default is used
                if isinstance(cors_value, str):
                    cors_stripped = cors_value.strip()
                    if not cors_stripped or cors_stripped == '':
                        # Remove empty value so default ["*"] is used
                        del data['CORS_ALLOW_ORIGINS']
                    # Otherwise leave it for the field validator to handle
        return data
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    def supabase_configured(self) -> bool:
        """Check if Supabase auth provider is configured."""
        return bool(self.SUPABASE_ISSUER and self.SUPABASE_JWKS_URL)

    def auth0_configured(self) -> bool:
        """Check if Auth0 provider is configured."""
        return bool(self.AUTH0_ISSUER and self.AUTH0_JWKS_URL)
    
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
    
    @field_validator('CORS_ALLOW_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string (comma-separated) or list."""
        # Handle None or empty values
        if v is None or v == "" or (isinstance(v, str) and v.strip() == ""):
            return ["*"]
        
        # If it's already a list, return it
        if isinstance(v, list):
            return v if v else ["*"]
        
        # Handle string input - pydantic-settings may try to JSON decode first
        if isinstance(v, str):
            # Strip whitespace
            v = v.strip()
            
            # Try to parse as JSON first (in case it's a JSON string like '["url1","url2"]')
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(origin) for origin in parsed]
                except (json.JSONDecodeError, ValueError, TypeError):
                    # If JSON parsing fails, fall through to comma-separated parsing
                    pass
            
            # Handle "*" case
            if v == "*":
                return ["*"]
            
            # Treat as comma-separated string
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else ["*"]
        
        # Fallback for any other type
        return ["*"]


# Global settings instance with error handling for CORS_ALLOW_ORIGINS
def create_settings():
    """Create Settings instance with error handling for CORS_ALLOW_ORIGINS parsing."""
    try:
        return Settings()
    except Exception as e:
        # If there's an error parsing CORS_ALLOW_ORIGINS, handle it
        error_str = str(e).lower()
        if 'cors_allow_origins' in error_str or ('json' in error_str and 'decode' in error_str):
            # Get the env var directly
            cors_env = os.getenv('CORS_ALLOW_ORIGINS', '')
            # Temporarily remove it so Settings can initialize with default
            old_value = os.environ.pop('CORS_ALLOW_ORIGINS', None)
            try:
                settings = Settings()
                # Now manually set CORS_ALLOW_ORIGINS using our parser
                if old_value:
                    settings.CORS_ALLOW_ORIGINS = Settings.parse_cors_origins(old_value)
                return settings
            finally:
                # Restore env var if we removed it
                if old_value:
                    os.environ['CORS_ALLOW_ORIGINS'] = old_value
        # If it's not a CORS/JSON error, re-raise
        raise

settings = create_settings()