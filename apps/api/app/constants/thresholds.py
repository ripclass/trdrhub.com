"""
Validation Thresholds Configuration

Centralized configuration for all magic numbers used in validation.
Each threshold is documented with its purpose and UCP600/ISBP745 reference where applicable.

Usage:
    from app.constants.thresholds import ValidationThresholds, AIThresholds, SimilarityThresholds
"""

from decimal import Decimal
from typing import Dict, Any


class ValidationThresholds:
    """
    Thresholds for document validation rules.
    Based on UCP600 and ISBP745 standards.
    """
    
    # Amount tolerance per UCP600 Article 30(a)
    # "words 'about' or 'approximately' allow a tolerance not exceeding 10%"
    AMOUNT_TOLERANCE_PERCENT = Decimal("0.05")  # 5% for strict validation
    AMOUNT_TOLERANCE_ABOUT = Decimal("0.10")  # 10% when "about" is used
    
    # Quantity tolerance per UCP600 Article 30(b)
    # "A tolerance not to exceed 5% more or 5% less than the quantity"
    QUANTITY_TOLERANCE_PERCENT = Decimal("0.05")  # 5%
    
    # Unit price tolerance per UCP600 Article 30(c)
    # Unit price must not exceed LC unit price
    UNIT_PRICE_MAX_VARIANCE = Decimal("0.00")  # No tolerance by default
    
    # Insurance minimum coverage per UCP600 Article 28(f)(ii)
    # "minimum amount of coverage must be at least 110% of CIF or CIP value"
    INSURANCE_MIN_COVERAGE_PERCENT = Decimal("1.10")  # 110%
    
    # Presentation period per UCP600 Article 14(c)
    # "must be presented within 21 calendar days after shipment"
    DEFAULT_PRESENTATION_DAYS = 21
    
    # Bank examination period per UCP600 Article 14(b)
    # "maximum of five banking days following receipt"
    BANK_EXAMINATION_DAYS = 5


class SimilarityThresholds:
    """
    Thresholds for text similarity matching.
    Used in cross-document validation.
    """
    
    # Goods description similarity
    # Per UCP600 Article 18(c): "correspond with" not "identical to"
    # Lowered from 0.5 to 0.35 to allow general terms
    GOODS_DESCRIPTION_MIN = 0.35
    
    # Port name matching
    # Allows for variations like "CHITTAGONG" vs "Chattogram Port"
    PORT_NAME_MIN = 0.4
    
    # Party name matching
    # For beneficiary, applicant, consignee matching
    PARTY_NAME_MIN = 0.5
    
    # Address matching
    # Per UCP600 Article 14(j): "need not be identical"
    ADDRESS_MIN = 0.3
    
    # Jaccard similarity for set comparison
    # Used for comparing lists of items
    JACCARD_MIN = 0.5
    
    # Fuzzy match threshold for sanctions screening
    SANCTIONS_FUZZY_MATCH = 0.85


class AIThresholds:
    """
    Thresholds for AI extraction and confidence scoring.
    """
    
    # Default confidence when AI doesn't provide one
    DEFAULT_CONFIDENCE = 0.7
    
    # Minimum confidence to trust AI extraction
    # Below this, manual review is recommended
    LOW_CONFIDENCE_THRESHOLD = 0.6
    
    # High confidence threshold for auto-approval
    HIGH_CONFIDENCE_THRESHOLD = 0.9
    
    # Ensemble voting - minimum agreement required
    ENSEMBLE_MIN_AGREEMENT = 2  # out of 3 providers
    
    # Calibration adjustment factor
    CONFIDENCE_CALIBRATION_FACTOR = 0.95
    
    # OCR confidence thresholds
    OCR_HIGH_QUALITY = 0.85
    OCR_MEDIUM_QUALITY = 0.7
    OCR_LOW_QUALITY = 0.5


class PerformanceThresholds:
    """
    Thresholds for performance and timeout settings.
    """
    
    # Maximum processing time before timeout (seconds)
    EXTRACTION_TIMEOUT = 30
    VALIDATION_TIMEOUT = 60
    OCR_TIMEOUT = 45
    
    # Maximum file size (bytes)
    MAX_FILE_SIZE_MB = 25
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Maximum documents per session
    MAX_DOCUMENTS_PER_SESSION = 10
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 30


class ComplianceThresholds:
    """
    Thresholds for compliance scoring and verdicts.
    """
    
    # Compliance score thresholds
    EXCELLENT_SCORE = 95  # Submit with confidence
    GOOD_SCORE = 85       # Minor issues, likely to pass
    FAIR_SCORE = 70       # Review recommended
    POOR_SCORE = 50       # High risk of rejection
    
    # Severity weights for scoring
    CRITICAL_WEIGHT = 25
    MAJOR_WEIGHT = 10
    MINOR_WEIGHT = 3
    WARNING_WEIGHT = 1
    
    # Maximum issues before auto-reject recommendation
    MAX_CRITICAL_FOR_SUBMIT = 0
    MAX_MAJOR_FOR_SUBMIT = 2
    

def get_all_thresholds() -> Dict[str, Any]:
    """Export all thresholds as a dictionary for API/debugging."""
    return {
        "validation": {
            "amount_tolerance": float(ValidationThresholds.AMOUNT_TOLERANCE_PERCENT),
            "quantity_tolerance": float(ValidationThresholds.QUANTITY_TOLERANCE_PERCENT),
            "insurance_min_coverage": float(ValidationThresholds.INSURANCE_MIN_COVERAGE_PERCENT),
            "presentation_days": ValidationThresholds.DEFAULT_PRESENTATION_DAYS,
        },
        "similarity": {
            "goods_description": SimilarityThresholds.GOODS_DESCRIPTION_MIN,
            "port_name": SimilarityThresholds.PORT_NAME_MIN,
            "party_name": SimilarityThresholds.PARTY_NAME_MIN,
        },
        "ai": {
            "default_confidence": AIThresholds.DEFAULT_CONFIDENCE,
            "low_confidence": AIThresholds.LOW_CONFIDENCE_THRESHOLD,
            "high_confidence": AIThresholds.HIGH_CONFIDENCE_THRESHOLD,
        },
        "compliance": {
            "excellent_score": ComplianceThresholds.EXCELLENT_SCORE,
            "good_score": ComplianceThresholds.GOOD_SCORE,
            "fair_score": ComplianceThresholds.FAIR_SCORE,
        },
    }


# Backward-compatible aliases for existing code
# TODO: Migrate code to use the new class names
class VALIDATION:
    """Backward-compatible alias for ValidationThresholds."""
    AMOUNT_TOLERANCE = float(ValidationThresholds.AMOUNT_TOLERANCE_PERCENT)
    QUANTITY_TOLERANCE = float(ValidationThresholds.QUANTITY_TOLERANCE_PERCENT)
    INSURANCE_MIN_COVERAGE = float(ValidationThresholds.INSURANCE_MIN_COVERAGE_PERCENT)
    PRESENTATION_DAYS = ValidationThresholds.DEFAULT_PRESENTATION_DAYS
    BANK_EXAMINATION_DAYS = ValidationThresholds.BANK_EXAMINATION_DAYS


class CONFIDENCE:
    """Backward-compatible alias for AIThresholds."""
    DEFAULT = AIThresholds.DEFAULT_CONFIDENCE
    LOW = AIThresholds.LOW_CONFIDENCE_THRESHOLD
    HIGH = AIThresholds.HIGH_CONFIDENCE_THRESHOLD
    OCR_HIGH = AIThresholds.OCR_HIGH_QUALITY
    OCR_MEDIUM = AIThresholds.OCR_MEDIUM_QUALITY
    OCR_LOW = AIThresholds.OCR_LOW_QUALITY


class SIMILARITY:
    """Backward-compatible alias for SimilarityThresholds."""
    GOODS = SimilarityThresholds.GOODS_DESCRIPTION_MIN
    PORT = SimilarityThresholds.PORT_NAME_MIN
    PARTY = SimilarityThresholds.PARTY_NAME_MIN
    ADDRESS = SimilarityThresholds.ADDRESS_MIN
    JACCARD = SimilarityThresholds.JACCARD_MIN
