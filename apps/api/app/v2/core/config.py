"""
LCopilot V2 Configuration

Central configuration for V2 pipeline with performance targets.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PerformanceTargets:
    """Performance SLA targets."""
    max_processing_seconds: float = 30.0
    target_accuracy: float = 0.99  # 99%
    max_documents: int = 10
    
    # Stage budgets (must sum to <= max_processing_seconds)
    intake_budget_seconds: float = 2.0
    preprocessing_budget_seconds: float = 6.0
    extraction_budget_seconds: float = 10.0
    validation_budget_seconds: float = 7.0
    response_budget_seconds: float = 2.0


@dataclass
class AIProviderConfig:
    """AI provider configuration."""
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_fallback_model: str = "gpt-4o-mini"
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_fallback_model: str = "claude-3-haiku-20240307"
    
    # Google
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    gemini_fallback_model: str = "gemini-1.5-flash"
    
    # Ensemble settings
    min_providers_for_ensemble: int = 2
    extraction_temperature: float = 0.1
    max_extraction_tokens: int = 2000
    
    @classmethod
    def from_env(cls) -> "AIProviderConfig":
        """Load from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            gemini_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        )
    
    def available_providers(self) -> List[str]:
        """List available providers based on API keys."""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.gemini_api_key:
            providers.append("gemini")
        return providers
    
    def can_ensemble(self) -> bool:
        """Check if ensemble extraction is possible."""
        return len(self.available_providers()) >= self.min_providers_for_ensemble


@dataclass
class OCRConfig:
    """OCR configuration."""
    primary_provider: str = "docai"  # 'docai', 'textract', 'azure'
    fallback_provider: str = "textract"
    
    # Quality thresholds
    min_confidence_threshold: float = 0.3
    enhancement_threshold: float = 0.6  # Enhance if below this
    
    # Preprocessing
    enable_deskew: bool = True
    enable_denoise: bool = True
    enable_contrast_enhancement: bool = True
    enable_upscaling: bool = True
    
    # Handwriting
    enable_handwriting_detection: bool = True
    handwriting_providers: List[str] = field(default_factory=lambda: ["azure", "google"])
    
    # Parallel processing
    max_parallel_pages: int = 10
    worker_pool_size: int = 5


@dataclass
class ValidationConfig:
    """Validation engine configuration."""
    # Rules
    enable_ucp600_rules: bool = True
    enable_isbp745_rules: bool = True
    enable_crossdoc_checks: bool = True
    enable_sanctions_screening: bool = True
    
    # Strictness
    strict_mode: bool = False
    tolerance_default_percent: float = 5.0
    
    # Citations (THE KEY FEATURE)
    always_include_citations: bool = True
    citation_format: str = "full"  # 'full', 'short', 'minimal'
    
    # Amendment generation
    generate_amendments: bool = True
    include_mt707: bool = True
    include_iso20022: bool = True


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for different field types."""
    # Critical fields (must be right)
    critical_min_confidence: float = 0.95
    critical_min_agreement: float = 1.0  # All providers must agree
    critical_fields: List[str] = field(default_factory=lambda: [
        "lc_number", "amount", "currency", "expiry_date", "latest_shipment_date"
    ])
    
    # Important fields
    important_min_confidence: float = 0.85
    important_min_agreement: float = 0.66
    important_fields: List[str] = field(default_factory=lambda: [
        "beneficiary", "applicant", "issuing_bank"
    ])
    
    # Standard fields
    standard_min_confidence: float = 0.70
    standard_min_agreement: float = 0.50
    
    # Auto-review thresholds
    auto_review_below_confidence: float = 0.90
    auto_review_critical_below: float = 0.98


@dataclass
class V2Config:
    """Master V2 configuration."""
    performance: PerformanceTargets = field(default_factory=PerformanceTargets)
    ai: AIProviderConfig = field(default_factory=AIProviderConfig.from_env)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    confidence: ConfidenceThresholds = field(default_factory=ConfidenceThresholds)
    
    # Feature flags (V2 specific)
    enable_v2_pipeline: bool = True
    enable_smart_routing: bool = True
    enable_image_enhancement: bool = True
    enable_handwriting_ocr: bool = True
    enable_parallel_processing: bool = True
    
    # Logging
    debug_mode: bool = False
    log_extraction_details: bool = False
    log_ai_responses: bool = False
    
    @classmethod
    def from_env(cls) -> "V2Config":
        """Load from environment variables."""
        return cls(
            ai=AIProviderConfig.from_env(),
            debug_mode=os.getenv("V2_DEBUG", "false").lower() == "true",
        )
    
    @classmethod
    def default(cls) -> "V2Config":
        """Get default configuration."""
        return cls()


# Global config instance
_config: Optional[V2Config] = None


def get_v2_config() -> V2Config:
    """Get or create V2 configuration."""
    global _config
    if _config is None:
        _config = V2Config.from_env()
    return _config


def set_v2_config(config: V2Config) -> None:
    """Set V2 configuration (for testing)."""
    global _config
    _config = config

