"""
Application Configuration Module

Centralized configuration for thresholds, constants, and settings.
"""

from .thresholds import (
    ValidationThresholds,
    SimilarityThresholds,
    AIThresholds,
    PerformanceThresholds,
    ComplianceThresholds,
    get_all_thresholds,
    # Backward-compatible aliases
    VALIDATION,
    CONFIDENCE,
    SIMILARITY,
)

__all__ = [
    # New class names
    "ValidationThresholds",
    "SimilarityThresholds",
    "AIThresholds",
    "PerformanceThresholds",
    "ComplianceThresholds",
    "get_all_thresholds",
    # Backward-compatible aliases
    "VALIDATION",
    "CONFIDENCE",
    "SIMILARITY",
]
