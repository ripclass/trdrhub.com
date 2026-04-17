"""
Configuration settings for LCopilot application.
"""

import os
import json
from typing import Optional, List, Any, Dict
from urllib.parse import urlparse
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
    GOOGLE_DOCUMENTAI_LOCATION: str = "eu"
    GOOGLE_DOCUMENTAI_PROCESSOR_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None  # JSON string for Render deployment
    
    # OCR Configuration
    OCR_ENABLED: bool = True  # Enable OCR fallback when pdfminer/PyPDF2 return empty
    # Google DocAI is suspended — Textract is the primary external OCR provider.
    # Set OCR_PROVIDER_ORDER env var to override (e.g., to re-enable gdocai).
    OCR_PROVIDER_ORDER: List[str] = ["textract"]
    OCR_MAX_PAGES: int = 50  # Maximum pages for OCR processing
    OCR_TIMEOUT_SEC: int = 120  # Timeout for OCR operations (increased for 30+ page docs)
    OCR_MAX_BYTES: int = 50 * 1024 * 1024  # 50MB max file size for OCR
    OCR_MIN_TEXT_CHARS_FOR_SKIP: int = 1200  # Hard skip OCR when native text is already rich enough
    OCR_NATIVE_TEXT_SOFT_SKIP_CHARS: int = 250  # For file-native PDFs, skip OCR when native text is already usable support text
    OCR_MAX_CONCURRENCY: int = 4  # Max parallel OCR operations (for 10-12 doc batches)
    EXTRACTION_LLM_CONCURRENCY: int = 4  # Max parallel vision LLM extraction calls
    OCR_RUNTIME_DIAGNOSTICS_ENABLED: bool = True  # Track bounded OCR runtime diagnostics
    OCR_DIAGNOSTICS_MAX_ERRORS: int = 10  # Max recent OCR errors exposed by diagnostics endpoint
    OCR_HEALTH_ENDPOINT_ENABLED: bool = True  # Enable internal OCR health endpoint
    OCR_HEALTH_TOKEN: Optional[str] = None  # Optional shared token for OCR health endpoint
    OCR_NORMALIZATION_SHIM_ENABLED: bool = True  # Normalize PDFs/images before OCR provider calls
    OCR_NORMALIZATION_DPI: int = 300  # Deterministic render DPI for OCR normalization
    OCR_NORMALIZATION_IMAGE_FORMAT: str = "TIFF"  # Provider-friendly normalized output for PDFs
    OCR_STAGE_SCORER_ENABLED: bool = True  # Score competing OCR/native stages before selecting text
    OCR_STAGE_WEIGHT_TEXT_LEN: float = 0.30
    OCR_STAGE_WEIGHT_ALNUM_RATIO: float = 0.20
    OCR_STAGE_WEIGHT_ANCHOR_HIT: float = 0.25
    OCR_STAGE_WEIGHT_FIELD_PATTERN: float = 0.25
    OCR_STAGE_SELECTION_PRIORITY: List[str] = [
        "ocr_provider_primary",
        "ocr_secondary",
        "native_pdf_text",
        "binary_metadata_scrape",
    ]
    
    # Document Set Configuration (based on UCP600/ISBP745 norms)
    DOC_SET_MIN_DOCS: int = 1  # Minimum docs for validation (LC-only mode)
    DOC_SET_MAX_DOCS: int = 15  # Maximum docs per validation
    DOC_SET_RECOMMENDED_MIN: int = 4  # Recommended minimum for full compliance check
    DOC_SET_LC_AVG_PAGES: int = 6  # Average pages per LC document (MT700/MT760)
    DOC_SET_FULL_AVG_PAGES: int = 20  # Average pages for full document set
    DOC_SET_WARN_MISSING: bool = True  # Warn when common documents are missing
    
    # DeepSeek OCR Configuration
    USE_DEEPSEEK_OCR: bool = False  # Enable DeepSeek OCR as primary provider
    DEEPSEEK_OCR_MODEL_NAME: str = "deepseek-ai/deepseek-ocr"  # Hugging Face model identifier
    DEEPSEEK_OCR_DEVICE: Optional[str] = None  # 'cuda', 'cpu', or None for auto-detect
    
    # Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SUPABASE_URL: Optional[str] = None  # Supabase project URL (e.g., https://xxx.supabase.co)
    SUPABASE_ISSUER: Optional[str] = None
    SUPABASE_AUDIENCE: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None  # JWT secret for validating Supabase tokens
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None  # Service role key (can be used as JWT secret)
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
    DEBUG_EXTRACTION_TRACE: bool = False

    # Runtime recovery controls (Cycle-2)
    DAY1_CONTRACT_ENABLED: bool = False
    CYCLE2_RUNTIME_RECOVERY_ENABLED: bool = True
    CYCLE2_RUNTIME_FORCE_PASS_ENABLED: bool = True

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"

    # RulHub Integration
    USE_RULHUB_API: bool = False  # Set True + provide key to route rules through api.rulhub.com
    RULHUB_API_URL: str = "https://api.rulhub.com"
    RULHUB_API_KEY: str = ""  # rlh_... (server-side only, from env)

    # Rules System (DB-backed fallback when USE_RULHUB_API=False)
    USE_JSON_RULES: bool = True  # Enable JSON ruleset validation system
    RULESET_CACHE_TTL_MINUTES: int = 10  # Cache TTL for rulesets
    RULES_STORAGE_BUCKET: str = "rules"

    # Stripe configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_STARTER: Optional[str] = None
    STRIPE_PRICE_PROFESSIONAL: Optional[str] = None
    STRIPE_PRICE_ENTERPRISE: Optional[str] = None

    # Stub tooling guard
    STUB_STATUS_TOKEN: Optional[str] = None
    ENABLE_PUBLIC_VALIDATE_DEMO: bool = False

    # SSLCommerz configuration
    SSLCOMMERZ_STORE_ID: Optional[str] = None
    SSLCOMMERZ_STORE_PASSWORD: Optional[str] = None
    SSLCOMMERZ_SANDBOX: bool = True
    
    # AI/LLM Configuration
    AI_ENRICHMENT: bool = False  # Enable AI enrichment in validation pipeline
    # Three-pass validation: tiered AI (L1→L2→L3) + deterministic rules + Opus veto.
    #
    # As of C1 of the consolidation plan the three layers have distinct jobs:
    #   - Tiered AI: parse the LC's own 46A/47A clauses into a structured
    #     requirement graph. Does NOT invent findings. (The discrepancy-finding
    #     behaviour was the root cause of hallucinated UCP rules that weren't
    #     in the LC under review.)
    #   - Deterministic rules (doc_matcher): the ONLY source of findings.
    #     Every finding cites a specific 46A/47A clause of THIS LC.
    #   - Opus veto: confirm / drop / modify only. May not add findings.
    #
    # Tiered AI is OFF in C1 — the current prompt asks the LLM to "find
    # compliance issues", and that's the hallucination vector we are
    # eliminating. C2 will re-enable it with a rewritten prompt ("parse the
    # LC's 46A/47A clauses into a requirement graph") and it will feed the
    # deterministic spine, not produce findings directly.
    #
    # Opus veto stays ON — it correctly drops false positives from the
    # deterministic spine, and its anomaly-injection branch is already
    # removed in tiered_validation._run_opus_veto_pass.
    VALIDATION_TIERED_AI_ENABLED: bool = False
    VALIDATION_OPUS_VETO_ENABLED: bool = True
    # Hard timeout for the tiered AI validation pass (seconds).
    VALIDATION_AI_PASS_TIMEOUT_SECONDS: int = 60
    # Hard timeout for the Opus veto pass (seconds).
    VALIDATION_VETO_TIMEOUT_SECONDS: int = 90
    # Legacy parallel engine — CrossDocValidator in
    # app.services.validation.crossdoc_validator. It runs UCP600 Art 28
    # (insurance), port/amount/goods checks on its own, WITHOUT consulting
    # the LC's 46A/47A clause graph. That produced the IDEAL SAMPLE's
    # "Insurance Coverage Below LC Requirement" false positive on an LC
    # that never asked for insurance. Off by default; enable only for
    # side-by-side debugging against the doc_matcher spine.
    VALIDATION_LEGACY_CROSSDOC_ENABLED: bool = False
    # L3 "advanced anomaly review" inside ai_validator — produces
    # "Low Extraction Confidence" items that are extraction-quality signals,
    # not LC-clause discrepancies. Belongs in an advisory/intelligence
    # channel (C3 of the consolidation plan). Off by default; enable if
    # you want the raw signals surfaced in the findings list for debugging.
    VALIDATION_L3_ANOMALY_REVIEW_ENABLED: bool = False
    # LLM-driven clause graph (C2 spinal change). When on, the LC's own
    # 46A/47A text is parsed by an LLM into a structured RichClause list
    # drawn from a closed condition / value_constraint vocabulary. The
    # deterministic rich matcher then produces findings — every finding
    # cites the exact clause it came from. Fallback to regex clause_parser
    # on any failure.
    VALIDATION_LLM_CLAUSE_GRAPH_ENABLED: bool = True
    LLM_PROVIDER: str = "openrouter"  # openrouter|openai|anthropic|gemini
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL_VERSION: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    # Preferred model for primary generation (used by OpenRouter/OpenAI paths)
    LLM_PRIMARY_MODEL: Optional[str] = None
    # Optional explicit fallback model (e.g., openai/gpt-4o-mini)
    LLM_FALLBACK_MODEL: Optional[str] = None
    LLM_MODEL_VERSION: str = "gpt-4o-mini"  # Legacy default model (kept for backward compatibility)
    ANTHROPIC_MODEL_VERSION: str = "claude-3-haiku-20240307"  # Anthropic model
    AI_MAX_OUTPUT_TOKENS_SYSTEM: int = 600  # System enrichment max tokens
    AI_MAX_OUTPUT_TOKENS_LETTER: int = 800  # Letter generation max tokens
    AI_MAX_OUTPUT_TOKENS_TRANSLATE: int = 600  # Translation max tokens
    AI_MAX_OUTPUT_TOKENS_CHAT: int = 400  # Chat max tokens
    AI_TIMEOUT_MS: int = 15000  # LLM API timeout
    # Extraction-specific routing: keep separate from validation AI router layers.
    EXTRACTION_AI_ENABLED: bool = True
    EXTRACTION_PRIMARY_PROVIDER: str = "openrouter"
    EXTRACTION_PRIMARY_MODEL: Optional[str] = None
    EXTRACTION_FALLBACK_PROVIDER: Optional[str] = None
    EXTRACTION_FALLBACK_MODEL: Optional[str] = None
    EXTRACTION_TIMEOUT_MS: int = 30000
    EXTRACTION_MAX_TOKENS: int = 2000
    AI_SEMANTIC_ENABLED: bool = True  # Enable semantic rule operator
    AI_SEMANTIC_MODEL: str = "gpt-4o-mini"
    AI_SEMANTIC_LOW_COST_MODEL: str = "gpt-4o-mini"
    AI_SEMANTIC_THRESHOLD_DEFAULT: float = 0.82
    AI_SEMANTIC_TIMEOUT_MS: int = 6000
    
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

    @model_validator(mode='after')
    def validate_required_environment(cls, values: 'Settings') -> 'Settings':
        """Fail fast when mandatory production configuration is missing."""
        if values.is_production():
            missing: List[str] = []
            if not values.DATABASE_URL:
                missing.append("DATABASE_URL")
            if not values.SECRET_KEY or values.SECRET_KEY == "dev-secret-key-change-in-production":
                missing.append("SECRET_KEY")
            if missing:
                raise ValueError(
                    "Missing required environment variables for production: "
                    + ", ".join(missing)
                )
        return values


def normalize_origin(origin: str) -> str:
    parsed = urlparse(str(origin or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _dedupe_origins(origins: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for origin in origins:
        normalized = normalize_origin(origin)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def resolve_allowed_cors_origins(config: Settings) -> List[str]:
    configured_origins = config.CORS_ALLOW_ORIGINS or []

    if not config.is_production() and configured_origins == ["http://localhost:5173"]:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    wildcard_configured = any(str(origin).strip() == "*" for origin in configured_origins)
    normalized_configured = _dedupe_origins(configured_origins)

    if config.is_production():
        production_frontends = _dedupe_origins([
            "https://trdrhub.com",
            "https://www.trdrhub.com",
            "https://app.trdrhub.com",
            "https://trdrhub.vercel.app",
            config.FRONTEND_URL,
        ])

        if wildcard_configured:
            return production_frontends

        return _dedupe_origins([*normalized_configured, *production_frontends])

    if wildcard_configured:
        return ["*"]

    return normalized_configured or ["http://localhost:5173"]


def build_cors_headers_for_origin(config: Settings, origin: str) -> Dict[str, str]:
    normalized_origin = normalize_origin(origin)
    if not normalized_origin:
        return {}

    allowed_origins = resolve_allowed_cors_origins(config)
    if "*" in allowed_origins or normalized_origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": normalized_origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }

    return {}


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
