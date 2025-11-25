"""
OCR Quality Gate - Phase 0.2

Assesses OCR output quality before validation proceeds.
Documents with poor OCR quality are flagged for review or re-processing.

Quality Factors:
1. Confidence Score - Overall OCR confidence
2. Text Coverage - Ratio of text to document area
3. Character Recognition Rate - Valid vs garbled characters
4. Line Coherence - Readable line structure
5. Field Extraction Potential - Can we extract required fields?
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


logger = logging.getLogger(__name__)


class QualityLevel(str, Enum):
    """OCR quality assessment level."""
    EXCELLENT = "excellent"  # >= 0.90 - High quality, proceed with confidence
    GOOD = "good"            # >= 0.75 - Acceptable quality, proceed
    FAIR = "fair"            # >= 0.60 - Marginal quality, proceed with caution
    POOR = "poor"            # >= 0.40 - Poor quality, manual review recommended
    UNACCEPTABLE = "unacceptable"  # < 0.40 - Cannot proceed, re-scan required


@dataclass
class QualityMetric:
    """Individual quality metric."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float  # Contribution to overall score
    details: str
    passed: bool


@dataclass
class QualityAssessment:
    """Complete OCR quality assessment."""
    overall_score: float  # 0.0 to 1.0
    quality_level: QualityLevel
    metrics: List[QualityMetric]
    can_proceed: bool  # True if quality is sufficient for validation
    recommendations: List[str]
    warnings: List[str]
    raw_confidence: Optional[float] = None  # Original OCR confidence if available
    text_length: int = 0
    estimated_word_count: int = 0


class OCRQualityGate:
    """
    Assesses OCR output quality to determine if validation can proceed.
    
    This gate prevents garbage-in-garbage-out scenarios where poor OCR
    leads to false validation results.
    """
    
    # Minimum thresholds for proceeding
    MIN_OVERALL_SCORE = 0.50  # Below this, cannot proceed
    MIN_TEXT_LENGTH = 100     # Minimum characters for a valid document
    MIN_WORD_COUNT = 20       # Minimum words for a valid document
    
    # Quality metric weights
    METRIC_WEIGHTS = {
        "confidence": 0.30,
        "text_coverage": 0.20,
        "character_quality": 0.20,
        "structure_coherence": 0.15,
        "field_density": 0.15,
    }
    
    # Common OCR garbage patterns
    GARBAGE_PATTERNS = [
        r'[^\x00-\x7F]{3,}',  # Non-ASCII clusters
        r'[!@#$%^&*()]{3,}',  # Symbol clusters
        r'[0-9]{10,}',        # Long number sequences (unless expected)
        r'(.)\1{4,}',         # Repeated characters
        r'\b[bcdfghjklmnpqrstvwxz]{5,}\b',  # Consonant clusters (no vowels)
    ]
    
    # Expected field patterns for trade documents
    EXPECTED_FIELD_PATTERNS = {
        "date": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b|\b\d{6}\b',
        "amount": r'[A-Z]{3}\s*[\d,\.]+|[\d,\.]+\s*(USD|EUR|GBP)',
        "party_name": r'\b[A-Z][A-Za-z]+(\s+[A-Z][A-Za-z]+){1,5}',
        "address": r'\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd)',
        "reference": r'\b[A-Z0-9]{5,15}\b',
    }
    
    def __init__(self):
        """Initialize the quality gate."""
        self._garbage_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.GARBAGE_PATTERNS
        ]
        self._field_compiled = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.EXPECTED_FIELD_PATTERNS.items()
        }
    
    def assess(
        self,
        text: str,
        ocr_confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityAssessment:
        """
        Assess OCR output quality.
        
        Args:
            text: OCR extracted text
            ocr_confidence: Original confidence from OCR provider (0.0 to 1.0)
            metadata: Additional OCR metadata (page count, processing time, etc.)
            
        Returns:
            QualityAssessment with overall score and detailed metrics
        """
        metrics: List[QualityMetric] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        
        metadata = metadata or {}
        text_length = len(text) if text else 0
        word_count = len(text.split()) if text else 0
        
        # Check minimum requirements
        if text_length < self.MIN_TEXT_LENGTH:
            warnings.append(f"Text too short ({text_length} chars). Minimum: {self.MIN_TEXT_LENGTH}")
            recommendations.append("Re-scan document with higher resolution")
        
        if word_count < self.MIN_WORD_COUNT:
            warnings.append(f"Too few words ({word_count}). Minimum: {self.MIN_WORD_COUNT}")
        
        # Metric 1: OCR Confidence
        confidence_metric = self._assess_confidence(ocr_confidence, text)
        metrics.append(confidence_metric)
        
        # Metric 2: Text Coverage (character density)
        coverage_metric = self._assess_text_coverage(text, metadata)
        metrics.append(coverage_metric)
        
        # Metric 3: Character Quality (garbage detection)
        char_quality_metric = self._assess_character_quality(text)
        metrics.append(char_quality_metric)
        if not char_quality_metric.passed:
            warnings.append("High proportion of unreadable characters detected")
            recommendations.append("Check scan quality and re-process if needed")
        
        # Metric 4: Structure Coherence (line/paragraph structure)
        structure_metric = self._assess_structure_coherence(text)
        metrics.append(structure_metric)
        
        # Metric 5: Field Density (expected field patterns found)
        field_metric = self._assess_field_density(text)
        metrics.append(field_metric)
        if not field_metric.passed:
            warnings.append("Few extractable fields detected")
            recommendations.append("Verify document is complete and properly scanned")
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        quality_level = self._get_quality_level(overall_score)
        
        # Determine if we can proceed
        can_proceed = (
            overall_score >= self.MIN_OVERALL_SCORE
            and text_length >= self.MIN_TEXT_LENGTH
        )
        
        if not can_proceed:
            recommendations.append("Document quality too low for reliable validation")
            recommendations.append("Re-scan at minimum 300 DPI with clear lighting")
        
        logger.info(
            "OCR quality assessment: score=%.2f, level=%s, can_proceed=%s",
            overall_score, quality_level.value, can_proceed
        )
        
        return QualityAssessment(
            overall_score=overall_score,
            quality_level=quality_level,
            metrics=metrics,
            can_proceed=can_proceed,
            recommendations=recommendations,
            warnings=warnings,
            raw_confidence=ocr_confidence,
            text_length=text_length,
            estimated_word_count=word_count,
        )
    
    def _assess_confidence(
        self,
        ocr_confidence: Optional[float],
        text: str,
    ) -> QualityMetric:
        """Assess OCR confidence score."""
        if ocr_confidence is not None:
            score = ocr_confidence
            details = f"OCR provider confidence: {ocr_confidence:.0%}"
        else:
            # Estimate confidence from text quality
            score = self._estimate_confidence(text)
            details = f"Estimated confidence: {score:.0%} (no provider confidence available)"
        
        return QualityMetric(
            name="confidence",
            score=score,
            weight=self.METRIC_WEIGHTS["confidence"],
            details=details,
            passed=score >= 0.70,
        )
    
    def _estimate_confidence(self, text: str) -> float:
        """Estimate confidence when OCR provider doesn't provide one."""
        if not text:
            return 0.0
        
        # Check for common quality indicators
        indicators = []
        
        # Word length distribution (should be 3-12 chars mostly)
        words = text.split()
        if words:
            avg_word_len = sum(len(w) for w in words) / len(words)
            word_len_score = 1.0 if 4 <= avg_word_len <= 8 else 0.5
            indicators.append(word_len_score)
        
        # Uppercase/lowercase ratio (should be mixed)
        if text:
            upper = sum(1 for c in text if c.isupper())
            lower = sum(1 for c in text if c.islower())
            total = upper + lower
            if total > 0:
                case_ratio = min(upper, lower) / max(upper, lower) if max(upper, lower) > 0 else 0
                indicators.append(min(case_ratio * 2, 1.0))
        
        # Space distribution (should be regular)
        if text:
            space_count = text.count(' ')
            space_ratio = space_count / len(text) if len(text) > 0 else 0
            space_score = 1.0 if 0.10 <= space_ratio <= 0.25 else 0.5
            indicators.append(space_score)
        
        return sum(indicators) / len(indicators) if indicators else 0.5
    
    def _assess_text_coverage(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> QualityMetric:
        """Assess text coverage/density."""
        # If we have page count, calculate density per page
        page_count = metadata.get("page_count", 1)
        text_length = len(text) if text else 0
        
        chars_per_page = text_length / page_count if page_count > 0 else text_length
        
        # Expected: 500-5000 chars per page for trade documents
        if chars_per_page >= 1000:
            score = 1.0
        elif chars_per_page >= 500:
            score = 0.8
        elif chars_per_page >= 200:
            score = 0.6
        elif chars_per_page >= 100:
            score = 0.4
        else:
            score = 0.2
        
        return QualityMetric(
            name="text_coverage",
            score=score,
            weight=self.METRIC_WEIGHTS["text_coverage"],
            details=f"{chars_per_page:.0f} characters per page (expected: 500-5000)",
            passed=score >= 0.6,
        )
    
    def _assess_character_quality(self, text: str) -> QualityMetric:
        """Assess character quality (garbage detection)."""
        if not text:
            return QualityMetric(
                name="character_quality",
                score=0.0,
                weight=self.METRIC_WEIGHTS["character_quality"],
                details="No text to assess",
                passed=False,
            )
        
        total_chars = len(text)
        garbage_chars = 0
        
        for pattern in self._garbage_compiled:
            matches = pattern.findall(text)
            garbage_chars += sum(len(m) if isinstance(m, str) else len(m[0]) for m in matches)
        
        garbage_ratio = garbage_chars / total_chars if total_chars > 0 else 0
        score = max(0.0, 1.0 - (garbage_ratio * 5))  # Penalize garbage heavily
        
        return QualityMetric(
            name="character_quality",
            score=score,
            weight=self.METRIC_WEIGHTS["character_quality"],
            details=f"{garbage_ratio:.1%} potentially garbled characters",
            passed=score >= 0.70,
        )
    
    def _assess_structure_coherence(self, text: str) -> QualityMetric:
        """Assess line and paragraph structure coherence."""
        if not text:
            return QualityMetric(
                name="structure_coherence",
                score=0.0,
                weight=self.METRIC_WEIGHTS["structure_coherence"],
                details="No text to assess",
                passed=False,
            )
        
        lines = text.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        if not non_empty_lines:
            return QualityMetric(
                name="structure_coherence",
                score=0.2,
                weight=self.METRIC_WEIGHTS["structure_coherence"],
                details="No line structure detected",
                passed=False,
            )
        
        # Check line length distribution
        line_lengths = [len(l) for l in non_empty_lines]
        avg_line_length = sum(line_lengths) / len(line_lengths)
        
        # Good structure: varied line lengths, not all same
        length_variance = sum((l - avg_line_length) ** 2 for l in line_lengths) / len(line_lengths)
        
        # Expect some variance (not all same length, not too random)
        if 100 <= length_variance <= 10000:
            structure_score = 1.0
        elif 50 <= length_variance <= 20000:
            structure_score = 0.7
        else:
            structure_score = 0.4
        
        # Check for consistent line count (should have multiple lines)
        line_count_score = min(len(non_empty_lines) / 20, 1.0)
        
        score = (structure_score + line_count_score) / 2
        
        return QualityMetric(
            name="structure_coherence",
            score=score,
            weight=self.METRIC_WEIGHTS["structure_coherence"],
            details=f"{len(non_empty_lines)} lines, avg length {avg_line_length:.0f}",
            passed=score >= 0.5,
        )
    
    def _assess_field_density(self, text: str) -> QualityMetric:
        """Assess density of extractable field patterns."""
        if not text:
            return QualityMetric(
                name="field_density",
                score=0.0,
                weight=self.METRIC_WEIGHTS["field_density"],
                details="No text to assess",
                passed=False,
            )
        
        fields_found = {}
        for field_name, pattern in self._field_compiled.items():
            matches = pattern.findall(text)
            if matches:
                fields_found[field_name] = len(matches)
        
        # Score based on diversity of fields found
        total_field_types = len(self._field_compiled)
        found_types = len(fields_found)
        
        diversity_score = found_types / total_field_types
        
        # Also consider total matches
        total_matches = sum(fields_found.values())
        density_score = min(total_matches / 10, 1.0)  # Expect at least 10 field matches
        
        score = (diversity_score + density_score) / 2
        
        fields_summary = ", ".join(f"{k}:{v}" for k, v in fields_found.items())
        
        return QualityMetric(
            name="field_density",
            score=score,
            weight=self.METRIC_WEIGHTS["field_density"],
            details=f"Found {found_types}/{total_field_types} field types: {fields_summary or 'none'}",
            passed=score >= 0.4,
        )
    
    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """Calculate weighted overall score."""
        if not metrics:
            return 0.0
        
        weighted_sum = sum(m.score * m.weight for m in metrics)
        total_weight = sum(m.weight for m in metrics)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _get_quality_level(self, score: float) -> QualityLevel:
        """Map overall score to quality level."""
        if score >= 0.90:
            return QualityLevel.EXCELLENT
        elif score >= 0.75:
            return QualityLevel.GOOD
        elif score >= 0.60:
            return QualityLevel.FAIR
        elif score >= 0.40:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def quick_check(self, text: str) -> bool:
        """
        Quick pass/fail check for minimum quality.
        
        Use this for fast gating before full assessment.
        """
        if not text or len(text) < self.MIN_TEXT_LENGTH:
            return False
        
        if len(text.split()) < self.MIN_WORD_COUNT:
            return False
        
        # Quick garbage check
        garbage_count = 0
        for pattern in self._garbage_compiled[:2]:  # Check only first 2 patterns
            matches = pattern.findall(text)
            garbage_count += len(matches)
        
        if garbage_count > 10:  # Too much garbage
            return False
        
        return True


# Module-level instance
_quality_gate: Optional[OCRQualityGate] = None


def get_ocr_quality_gate() -> OCRQualityGate:
    """Get the global OCR quality gate instance."""
    global _quality_gate
    if _quality_gate is None:
        _quality_gate = OCRQualityGate()
    return _quality_gate

