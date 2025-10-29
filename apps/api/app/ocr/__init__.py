"""
OCR processing package with adapter pattern.
"""

from .base import OCRAdapter, OCRResult
from .google_documentai import GoogleDocumentAIAdapter
from .aws_textract import AWSTextractAdapter
from .factory import OCRFactory

__all__ = [
    "OCRAdapter", 
    "OCRResult", 
    "GoogleDocumentAIAdapter", 
    "AWSTextractAdapter", 
    "OCRFactory"
]