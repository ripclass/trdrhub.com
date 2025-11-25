"""
Document Intelligence Layer - Phase 0 of LCopilot Validation Engine.

This module provides intelligent document processing capabilities:
- Document Type Classification (content-based)
- OCR Quality Gate
- Multi-Page Document Splitting
- Language Detection

These components run BEFORE validation to ensure documents are correctly
identified and of sufficient quality for downstream processing.
"""

from .doc_type_classifier import DocumentTypeClassifier, ClassificationResult
from .ocr_quality_gate import OCRQualityGate, QualityAssessment
from .language_detector import LanguageDetector, LanguageResult

__all__ = [
    "DocumentTypeClassifier",
    "ClassificationResult",
    "OCRQualityGate", 
    "QualityAssessment",
    "LanguageDetector",
    "LanguageResult",
]

