"""
Smart Bill of Lading Extractor

Automatically detects B/L format and routes to appropriate parser:
- Electronic B/L (DCSA, BOLERO, essDOCS, WaveBL) → Direct parsing (100% accuracy)
- PDF/Image B/L → OCR + AI extraction

Usage:
    from app.services.extraction.smart_bl_extractor import extract_bl_smart
    
    result = await extract_bl_smart(content, filename="BL.json")
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .ebl_parser import (
    parse_ebl,
    detect_ebl_format,
    is_ebl_document,
    EBLParseResult,
)
from .ai_first_extractor import extract_bl_ai_first

logger = logging.getLogger(__name__)


@dataclass
class SmartBLExtractionResult:
    """Result from smart B/L extraction."""
    success: bool
    format_detected: str  # "dcsa_ebl", "bolero_ebl", "essdocs_ebl", "wavebl_ebl", "pdf_ocr"
    platform: str  # "DCSA", "BOLERO", "essDOCS", "WaveBL", "PDF/OCR"
    extraction_method: str  # "ebl_parser", "ai_first", "ocr"
    confidence: float
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    raw_content: str = ""
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    is_electronic: bool = False
    blockchain_ref: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "format_detected": self.format_detected,
            "platform": self.platform,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "extracted_fields": self.extracted_fields,
            "errors": self.errors,
            "warnings": self.warnings,
            "is_electronic": self.is_electronic,
            "blockchain_ref": self.blockchain_ref,
        }


def detect_bl_format(content: str, filename: Optional[str] = None) -> str:
    """
    Detect the format of B/L content.
    
    Returns:
        Format string: "dcsa_ebl", "bolero_ebl", "pdf_text", etc.
    """
    # Check if it's an electronic B/L
    if is_ebl_document(content):
        format_type, _ = detect_ebl_format(content)
        return f"{format_type}_ebl"
    
    # Check filename for hints
    if filename:
        filename_lower = filename.lower()
        if filename_lower.endswith(".json"):
            # Could be eBL even if not detected
            return "json_bl"
        if filename_lower.endswith(".xml"):
            return "xml_bl"
    
    return "pdf_text"


async def extract_bl_smart(
    content: str,
    filename: Optional[str] = None,
    force_format: Optional[str] = None,
) -> SmartBLExtractionResult:
    """
    Smart B/L extraction that auto-detects format.
    
    Args:
        content: Raw content (text, JSON, XML, or OCR output)
        filename: Optional filename for format hints
        force_format: Force a specific format
        
    Returns:
        SmartBLExtractionResult with standardized B/L data
    """
    result = SmartBLExtractionResult(
        success=False,
        format_detected="unknown",
        platform="Unknown",
        extraction_method="unknown",
        confidence=0.0,
        raw_content=content,
    )
    
    # Detect format
    if force_format:
        format_detected = force_format
    else:
        format_detected = detect_bl_format(content, filename)
    
    result.format_detected = format_detected
    logger.info(f"Smart B/L extraction: detected format = {format_detected}")
    
    # Route to appropriate extractor
    if "_ebl" in format_detected or format_detected in ("json_bl", "xml_bl"):
        # Try electronic B/L parser
        ebl_result = parse_ebl(content)
        
        if ebl_result.success:
            result.success = True
            result.platform = ebl_result.platform
            result.extraction_method = "ebl_parser"
            result.confidence = 1.0  # Electronic B/L is deterministic
            result.extracted_fields = ebl_result.extracted_fields
            result.is_electronic = True
            result.blockchain_ref = ebl_result.blockchain_ref
            result.errors = ebl_result.errors
            result.warnings = ebl_result.warnings
            
            # Add source format metadata
            result.extracted_fields["_source_format"] = f"eBL ({ebl_result.platform})"
            result.extracted_fields["_is_electronic_bl"] = True
            
            logger.info(f"eBL extraction successful: {ebl_result.platform}")
            return result
        else:
            result.warnings.append("eBL parsing failed, falling back to AI extraction")
    
    # Fall back to OCR/AI extraction for PDF or failed eBL
    try:
        ai_result = await extract_bl_ai_first(content)
        
        result.success = bool(ai_result.get("bl_number") or ai_result.get("vessel_name"))
        result.platform = "PDF/OCR"
        result.extraction_method = ai_result.get("_extraction_method", "ai_first")
        result.confidence = ai_result.get("_extraction_confidence", 0.75)
        result.extracted_fields = ai_result
        result.is_electronic = False
        
        # Add source format metadata
        result.extracted_fields["_source_format"] = "PDF/OCR"
        result.extracted_fields["_is_electronic_bl"] = False
        
        logger.info(f"PDF/OCR B/L extraction: confidence={result.confidence}")
        
    except Exception as e:
        result.errors.append(f"B/L extraction failed: {str(e)}")
        logger.error(f"B/L extraction error: {e}", exc_info=True)
    
    return result


def get_bl_format_display(format_code: str) -> Dict[str, str]:
    """Get display information for a B/L format."""
    formats = {
        "dcsa_ebl": {
            "name": "DCSA eBL",
            "icon": "🔗",
            "color": "emerald",
            "description": "Digital Container Shipping Association electronic B/L",
        },
        "bolero_ebl": {
            "name": "BOLERO eBL",
            "icon": "📋",
            "color": "blue",
            "description": "BOLERO electronic B/L platform",
        },
        "essdocs_ebl": {
            "name": "essDOCS eBL",
            "icon": "📦",
            "color": "purple",
            "description": "essDOCS CargoDocs electronic B/L",
        },
        "wavebl_ebl": {
            "name": "WaveBL",
            "icon": "⛓️",
            "color": "cyan",
            "description": "Blockchain-based electronic B/L",
        },
        "pdf_text": {
            "name": "PDF B/L",
            "icon": "📄",
            "color": "gray",
            "description": "Traditional PDF Bill of Lading",
        },
    }
    
    return formats.get(format_code, {
        "name": format_code,
        "icon": "📄",
        "color": "gray",
        "description": "Unknown format",
    })

