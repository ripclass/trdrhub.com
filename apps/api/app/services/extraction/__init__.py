"""
LC Extraction Services

This module provides structured extraction of Letter of Credit documents.

Key Components (active extraction pipeline, Part 1):
- multimodal_document_extractor: Layer 1, vision LLM tier L1/L2/L3
- swift_mt700_full: Layer 1.5, deterministic MT700 regex parser
- ai_first_extractor: Layer 2, text-based AI fallback (+ confidence wrap/unwrap helpers)
- iso20022_lc_extractor: ISO 20022 XML specialization
- lc_document: Canonical LCDocument Pydantic model
- launch_pipeline: Orchestrator (_process_lc_like, _shape_lc_financial_payload)

Secondary components still referenced by Part 2 (validation layer):
- lc_extractor, lc_extractor_v2, lc_baseline: LCBaseline dataclass + v2 extraction, used by
  the validation pipeline, issue_engine, compliance_scorer, crossdoc_validator, validation_gate
- ai_lc_extractor: AI-powered extraction fallback reached via lc_extractor chain
- two_stage_extractor: legacy two-stage validation, still wired from validate.py
- ensemble_extractor: health-endpoint status reporter + nested fallback for ai_lc_extractor

Clause + field parsers:
- docs_46a_parser, clauses_47a_parser, goods_46a_parser: Clause parsers
- hs_code_extractor: HS code extraction
- ebl_parser: Electronic Bill of Lading format detection and parsing
- iso20022_parser: ISO 20022 trad.001/002 low-level parser
- required_fields_derivation: Derives per-doc required field map from LC 46A/47A clauses
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
from .iso20022_parser import (
    ISO20022Parser,
    ISO20022ParseResult,
    parse_iso20022_lc,
    is_iso20022_document,
    get_iso20022_parser,
)
from .ebl_parser import (
    parse_ebl,
    detect_ebl_format,
    is_ebl_document,
    EBLParseResult,
    DCSAParser,
    BoleroParser,
    EssDocsParser,
    WaveBLParser,
    get_supported_ebl_formats,
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
    
    # ISO 20022 trad.001/002 parser
    "ISO20022Parser",
    "ISO20022ParseResult",
    "parse_iso20022_lc",
    "is_iso20022_document",
    "get_iso20022_parser",
    
    # Electronic Bill of Lading (eBL) parser
    "parse_ebl",
    "detect_ebl_format",
    "is_ebl_document",
    "EBLParseResult",
    "DCSAParser",
    "BoleroParser",
    "EssDocsParser",
    "WaveBLParser",
    "get_supported_ebl_formats",
    
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

