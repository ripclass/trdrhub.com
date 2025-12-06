"""
LCopilot V2 - Next Generation Validation Pipeline

Target Specs:
- Processing Time: <30 seconds for 10 documents
- Accuracy: 99% with ensemble AI
- Document Quality: Any (handles poor scans, handwriting, stamps)
- Max Documents: 10

Architecture:
1. Intelligent Intake (0-2s): Classify and prioritize documents
2. Parallel Preprocessing (2-8s): OCR with image enhancement
3. AI Extraction Engine (8-18s): Ensemble extraction with voting
4. Validation Engine (18-25s): Rules + CrossDoc + Sanctions
5. Response Generator (25-30s): Format with citations

Key Differentiators:
- Always includes UCP600/ISBP745 citations
- Field-level confidence with provider agreement
- Smart AI routing based on document quality
- Handwriting, stamp, signature detection
"""

__version__ = "2.0.0"
__author__ = "TRDR Hub"

from .core.types import (
    DocumentType,
    DocumentQuality,
    RegionType,
    IssueSeverity,
    VerdictStatus,
)

from .core.config import V2Config

__all__ = [
    "DocumentType",
    "DocumentQuality", 
    "RegionType",
    "IssueSeverity",
    "VerdictStatus",
    "V2Config",
]

