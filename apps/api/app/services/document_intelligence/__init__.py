"""
Document Intelligence Layer - Phase 0 of LCopilot Validation Engine.

This module provides intelligent document processing capabilities:
- Document Type Classification (content-based + AI-enhanced)
- LC Flow Type Detection (export/import/draft)
- OCR Quality Gate
- Multi-Page Document Splitting
- Language Detection

These components run BEFORE validation to ensure documents are correctly
identified and of sufficient quality for downstream processing.
"""

from .doc_type_classifier import DocumentTypeClassifier, ClassificationResult
from .ocr_quality_gate import OCRQualityGate, QualityAssessment
from .language_detector import LanguageDetector, LanguageResult
from .ai_classifier import (
    AIDocumentClassifier,
    AIClassificationResult,
    LCFlowType,
    TradeRelevance,
    get_ai_classifier,
    classify_document,
    detect_lc_type_ai,
)

__all__ = [
    # Pattern-based classifier
    "DocumentTypeClassifier",
    "ClassificationResult",
    # AI-enhanced classifier
    "AIDocumentClassifier",
    "AIClassificationResult",
    "LCFlowType",
    "TradeRelevance",
    "get_ai_classifier",
    "classify_document",
    "detect_lc_type_ai",
    # Quality & Language
    "OCRQualityGate", 
    "QualityAssessment",
    "LanguageDetector",
    "LanguageResult",
]

