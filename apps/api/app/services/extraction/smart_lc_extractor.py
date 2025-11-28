"""
Smart LC Extractor

Automatically detects document format and routes to the appropriate extractor:
- ISO20022 XML → Direct XML parsing (100% accuracy)
- MT700 text → Structured text parsing
- PDF/Image → OCR + AI extraction

Usage:
    from app.services.extraction.smart_lc_extractor import extract_lc_smart
    
    result = await extract_lc_smart(content, filename="LC.xml")
    # Returns standardized LC data regardless of input format
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .iso20022_parser import (
    ISO20022Parser,
    ISO20022ParseResult,
    is_iso20022_document,
    parse_iso20022_lc,
)
from .ai_first_extractor import extract_lc_ai_first
from .lc_extractor import extract_lc_structured

logger = logging.getLogger(__name__)


@dataclass
class SmartExtractionResult:
    """Result from smart extraction."""
    success: bool
    format_detected: str  # "iso20022", "mt700", "pdf_ocr", "unknown"
    extraction_method: str  # "xml_parse", "ai_first", "regex", "hybrid"
    confidence: float
    extracted_fields: Dict[str, Any]
    raw_content: str
    errors: list
    warnings: list
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "format_detected": self.format_detected,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "extracted_fields": self.extracted_fields,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def detect_lc_format(content: str, filename: Optional[str] = None) -> str:
    """
    Detect the format of LC content.
    
    Args:
        content: Raw content (text or XML)
        filename: Optional filename for hints
        
    Returns:
        Format string: "iso20022", "mt700", "pdf_text", "unknown"
    """
    content_stripped = content.strip() if content else ""
    
    # Check filename extension first
    if filename:
        filename_lower = filename.lower()
        if filename_lower.endswith(".xml"):
            # Verify it's actually ISO20022
            if is_iso20022_document(content):
                return "iso20022"
            return "xml_other"
    
    # Check content signatures
    if content_stripped.startswith("<?xml") or content_stripped.startswith("<Document"):
        if is_iso20022_document(content):
            return "iso20022"
        return "xml_other"
    
    # Check for MT700 SWIFT format indicators
    mt700_indicators = [
        ":27:",  # Sequence of Total
        ":40A:", # Form of Documentary Credit
        ":20:",  # Documentary Credit Number
        ":31C:", # Date of Issue
        ":40E:", # Applicable Rules
        ":31D:", # Date and Place of Expiry
        ":50:",  # Applicant
        ":59:",  # Beneficiary
        ":32B:", # Currency Code, Amount
        ":39A:", # Percentage Credit Amount Tolerance
        ":41D:", # Available With...By...
        ":42C:", # Drafts at...
        ":43P:", # Partial Shipments
        ":43T:", # Transhipment
        ":44A:", # Place of Taking in Charge
        ":44E:", # Port of Loading
        ":44F:", # Port of Discharge
        ":44B:", # Place of Final Destination
        ":44C:", # Latest Date of Shipment
        ":45A:", # Description of Goods
        ":46A:", # Documents Required
        ":47A:", # Additional Conditions
        ":71D:", # Charges
        ":48:",  # Period for Presentation
        ":49:",  # Confirmation Instructions
        ":78:",  # Instructions to Paying/Accepting/Negotiating Bank
    ]
    
    # Count MT700 indicators
    mt700_count = sum(1 for ind in mt700_indicators if ind in content)
    if mt700_count >= 3:
        return "mt700"
    
    # If it looks like structured text with LC-related content
    lc_keywords = ["letter of credit", "documentary credit", "beneficiary", "applicant", "issuing bank"]
    if any(kw in content.lower() for kw in lc_keywords):
        return "pdf_text"
    
    return "unknown"


async def extract_lc_smart(
    content: str,
    filename: Optional[str] = None,
    force_format: Optional[str] = None,
) -> SmartExtractionResult:
    """
    Smart LC extraction that auto-detects format and uses the best extractor.
    
    Args:
        content: Raw content (text, XML, or OCR output)
        filename: Optional filename for format hints
        force_format: Force a specific format ("iso20022", "mt700", "ocr")
        
    Returns:
        SmartExtractionResult with standardized LC data
    """
    errors = []
    warnings = []
    
    # Detect format
    if force_format:
        format_detected = force_format
    else:
        format_detected = detect_lc_format(content, filename)
    
    logger.info(f"Smart LC extraction: detected format = {format_detected}")
    
    result = SmartExtractionResult(
        success=False,
        format_detected=format_detected,
        extraction_method="unknown",
        confidence=0.0,
        extracted_fields={},
        raw_content=content,
        errors=errors,
        warnings=warnings,
        metadata={
            "filename": filename,
            "content_length": len(content) if content else 0,
        },
    )
    
    # Route to appropriate extractor
    if format_detected == "iso20022":
        result = await _extract_iso20022(content, result)
    elif format_detected == "mt700":
        result = await _extract_mt700(content, result)
    elif format_detected in ("pdf_text", "unknown"):
        result = await _extract_ocr_text(content, result)
    else:
        result.errors.append(f"Unsupported format: {format_detected}")
    
    return result


async def _extract_iso20022(content: str, result: SmartExtractionResult) -> SmartExtractionResult:
    """Extract from ISO20022 XML."""
    try:
        parse_result = parse_iso20022_lc(content)
        
        result.extraction_method = "xml_parse"
        result.confidence = 1.0 if parse_result.success else 0.0
        result.extracted_fields = parse_result.extracted_fields
        result.errors.extend(parse_result.errors)
        result.warnings.extend(parse_result.warnings)
        result.success = parse_result.success
        
        result.metadata.update({
            "iso20022_message_type": parse_result.message_type,
            "iso20022_version": parse_result.version,
        })
        
        # Add format badge info
        result.extracted_fields["_source_format"] = "ISO20022"
        result.extracted_fields["_source_message_type"] = parse_result.message_type
        
        logger.info(f"ISO20022 extraction: success={result.success}, fields={len(result.extracted_fields)}")
        
    except Exception as e:
        result.errors.append(f"ISO20022 extraction failed: {str(e)}")
        logger.error(f"ISO20022 extraction error: {e}", exc_info=True)
    
    return result


async def _extract_mt700(content: str, result: SmartExtractionResult) -> SmartExtractionResult:
    """Extract from MT700 SWIFT format."""
    try:
        # Use regex-based structured extraction for MT700
        extracted = extract_lc_structured(content)
        
        result.extraction_method = "mt700_structured"
        result.confidence = 0.95  # High confidence for structured format
        result.extracted_fields = extracted
        result.success = bool(extracted.get("lc_number") or extracted.get("amount"))
        
        # Add format badge info
        result.extracted_fields["_source_format"] = "MT700"
        
        logger.info(f"MT700 extraction: success={result.success}, fields={len(result.extracted_fields)}")
        
    except Exception as e:
        result.errors.append(f"MT700 extraction failed: {str(e)}")
        logger.error(f"MT700 extraction error: {e}", exc_info=True)
        
        # Fallback to AI extraction
        result = await _extract_ocr_text(content, result)
    
    return result


async def _extract_ocr_text(content: str, result: SmartExtractionResult) -> SmartExtractionResult:
    """Extract from OCR/PDF text using AI-first approach."""
    try:
        extracted = await extract_lc_ai_first(content)
        
        result.extraction_method = extracted.get("_extraction_method", "ai_first")
        result.confidence = extracted.get("_extraction_confidence", 0.75)
        result.extracted_fields = extracted
        result.success = bool(extracted.get("lc_number") or extracted.get("amount"))
        
        # Add format badge info
        result.extracted_fields["_source_format"] = "PDF/OCR"
        
        logger.info(f"OCR/AI extraction: success={result.success}, confidence={result.confidence}")
        
    except Exception as e:
        result.errors.append(f"OCR/AI extraction failed: {str(e)}")
        logger.error(f"OCR/AI extraction error: {e}", exc_info=True)
    
    return result


def get_format_display_name(format_code: str) -> str:
    """Get human-readable format name."""
    format_names = {
        "iso20022": "ISO 20022 XML",
        "mt700": "SWIFT MT700",
        "pdf_text": "PDF (OCR)",
        "pdf_ocr": "PDF (OCR)",
        "xml_other": "XML (Non-standard)",
        "unknown": "Unknown Format",
    }
    return format_names.get(format_code, format_code)


def get_format_confidence_note(format_code: str) -> str:
    """Get confidence note for the format."""
    notes = {
        "iso20022": "Extracted from structured XML with 100% field accuracy",
        "mt700": "Parsed from SWIFT MT700 structured format",
        "pdf_text": "Extracted using OCR and AI analysis",
        "pdf_ocr": "Extracted using OCR and AI analysis",
    }
    return notes.get(format_code, "")

