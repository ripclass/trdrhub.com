"""
LC Extraction Services

This module provides structured extraction of Letter of Credit documents.

Key Components:
- lc_extractor: Original extraction (extract_lc_structured)
- lc_extractor_v2: Enhanced extraction with baseline tracking
- lc_baseline: LCBaseline dataclass for field tracking
- ai_lc_extractor: AI-powered extraction fallback (GPT/Claude)
- swift_mt700_full: SWIFT MT700 parser
- docs_46a_parser: Documentary requirements parser
- clauses_47a_parser: Additional conditions parser
- goods_46a_parser: Goods description parser
- hs_code_extractor: HS code extraction
"""

from .lc_extractor import (
    extract_lc_structured,
    extract_lc_structured_with_ai_fallback,
)
from .ai_lc_extractor import (
    extract_lc_with_ai,
    convert_ai_to_lc_structure,
)
from .iso20022_lc_extractor import (
    extract_iso20022_lc_enhanced,
    extract_iso20022_with_ai_fallback,
    detect_iso20022_schema,
    ISO20022ParseError,
)
from .lc_extractor_v2 import (
    extract_lc_with_baseline,
    extract_lc_structured_v2,
    check_lc_extraction_gate,
    get_lc_baseline_for_validation,
    LCExtractionResult,
)
from .lc_baseline import (
    LCBaseline,
    FieldResult,
    FieldPriority,
    ExtractionStatus,
    PartyInfo,
    AmountInfo,
    PortInfo,
    TimelineInfo,
    GoodsItem,
    create_lc_baseline_from_extraction,
)

__all__ = [
    # Original extraction
    "extract_lc_structured",
    
    # Extraction with AI fallback
    "extract_lc_structured_with_ai_fallback",
    "extract_lc_with_ai",
    "convert_ai_to_lc_structure",
    
    # ISO 20022 extraction
    "extract_iso20022_lc_enhanced",
    "extract_iso20022_with_ai_fallback",
    "detect_iso20022_schema",
    "ISO20022ParseError",
    
    # V2 extraction with baseline
    "extract_lc_with_baseline",
    "extract_lc_structured_v2",
    "check_lc_extraction_gate",
    "get_lc_baseline_for_validation",
    "LCExtractionResult",
    
    # Baseline types
    "LCBaseline",
    "FieldResult",
    "FieldPriority",
    "ExtractionStatus",
    "PartyInfo",
    "AmountInfo",
    "PortInfo",
    "TimelineInfo",
    "GoodsItem",
    "create_lc_baseline_from_extraction",
]

