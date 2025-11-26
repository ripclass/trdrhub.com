"""
Metrics for gold corpus evaluation.

Key metrics tracked:
- Extraction coverage: % of critical fields successfully extracted
- False positive rate: Issues raised that shouldn't have been
- False negative rate: Issues missed that should have been raised
- Critical miss rate: Critical issues missed (target: 0%)
- Latency: End-to-end processing time
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics for field extraction quality."""
    total_fields: int = 0
    extracted_fields: int = 0
    critical_fields: int = 0
    critical_extracted: int = 0
    
    @property
    def coverage(self) -> float:
        """Overall extraction coverage (0-100)."""
        if self.total_fields == 0:
            return 100.0
        return (self.extracted_fields / self.total_fields) * 100
    
    @property
    def critical_coverage(self) -> float:
        """Critical field extraction coverage (0-100)."""
        if self.critical_fields == 0:
            return 100.0
        return (self.critical_extracted / self.critical_fields) * 100


@dataclass
class ValidationMetrics:
    """Metrics for validation accuracy."""
    true_positives: int = 0   # Correctly identified issues
    false_positives: int = 0  # Incorrectly raised issues
    true_negatives: int = 0   # Correctly passed checks
    false_negatives: int = 0  # Missed issues
    critical_missed: int = 0  # Critical issues missed
    
    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)."""
        total = self.true_positives + self.false_positives
        if total == 0:
            return 1.0
        return self.true_positives / total
    
    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)."""
        total = self.true_positives + self.false_negatives
        if total == 0:
            return 1.0
        return self.true_positives / total
    
    @property
    def f1_score(self) -> float:
        """F1 Score: harmonic mean of precision and recall."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
    
    @property
    def false_positive_rate(self) -> float:
        """FPR: FP / (FP + TN)."""
        total = self.false_positives + self.true_negatives
        if total == 0:
            return 0.0
        return self.false_positives / total
    
    @property
    def critical_miss_rate(self) -> float:
        """Critical miss rate (target: 0%)."""
        total = self.true_positives + self.false_negatives
        if total == 0:
            return 0.0
        return self.critical_missed / total


@dataclass
class CorpusResult:
    """Result of running the corpus."""
    timestamp: str
    corpus_version: str
    engine_version: str
    
    # Counts
    total_sets: int = 0
    sets_passed: int = 0
    sets_failed: int = 0
    
    # Aggregate metrics
    extraction: ExtractionMetrics = field(default_factory=ExtractionMetrics)
    validation: ValidationMetrics = field(default_factory=ValidationMetrics)
    
    # Per-set results
    set_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Performance
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "corpus_version": self.corpus_version,
            "engine_version": self.engine_version,
            "summary": {
                "total_sets": self.total_sets,
                "sets_passed": self.sets_passed,
                "sets_failed": self.sets_failed,
                "pass_rate": self.sets_passed / self.total_sets * 100 if self.total_sets > 0 else 0,
            },
            "extraction": {
                "coverage": round(self.extraction.coverage, 2),
                "critical_coverage": round(self.extraction.critical_coverage, 2),
                "total_fields": self.extraction.total_fields,
                "extracted_fields": self.extraction.extracted_fields,
            },
            "validation": {
                "precision": round(self.validation.precision, 4),
                "recall": round(self.validation.recall, 4),
                "f1_score": round(self.validation.f1_score, 4),
                "false_positive_rate": round(self.validation.false_positive_rate, 4),
                "critical_miss_rate": round(self.validation.critical_miss_rate, 4),
                "true_positives": self.validation.true_positives,
                "false_positives": self.validation.false_positives,
                "false_negatives": self.validation.false_negatives,
                "critical_missed": self.validation.critical_missed,
            },
            "performance": {
                "total_latency_ms": round(self.total_latency_ms, 2),
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "p95_latency_ms": round(self.p95_latency_ms, 2),
            },
            "set_results": self.set_results,
            "errors": self.errors,
        }
    
    def save(self, path: Path):
        """Save result to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "CorpusResult":
        """Load result from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        result = cls(
            timestamp=data["timestamp"],
            corpus_version=data["corpus_version"],
            engine_version=data["engine_version"],
            total_sets=data["summary"]["total_sets"],
            sets_passed=data["summary"]["sets_passed"],
            sets_failed=data["summary"]["sets_failed"],
            set_results=data.get("set_results", {}),
            errors=data.get("errors", []),
        )
        
        # Restore extraction metrics
        ext = data.get("extraction", {})
        result.extraction.total_fields = ext.get("total_fields", 0)
        result.extraction.extracted_fields = ext.get("extracted_fields", 0)
        
        # Restore validation metrics
        val = data.get("validation", {})
        result.validation.true_positives = val.get("true_positives", 0)
        result.validation.false_positives = val.get("false_positives", 0)
        result.validation.false_negatives = val.get("false_negatives", 0)
        result.validation.critical_missed = val.get("critical_missed", 0)
        
        # Restore performance
        perf = data.get("performance", {})
        result.total_latency_ms = perf.get("total_latency_ms", 0)
        result.avg_latency_ms = perf.get("avg_latency_ms", 0)
        result.p95_latency_ms = perf.get("p95_latency_ms", 0)
        
        return result


def compare_results(current: CorpusResult, baseline: CorpusResult) -> Dict[str, Any]:
    """
    Compare current results against baseline.
    
    Returns dict with:
    - improved: List of metrics that improved
    - regressed: List of metrics that regressed
    - summary: Overall pass/fail
    """
    comparison = {
        "improved": [],
        "regressed": [],
        "unchanged": [],
        "summary": "pass",
    }
    
    # Compare extraction coverage
    cov_delta = current.extraction.coverage - baseline.extraction.coverage
    if abs(cov_delta) < 0.5:
        comparison["unchanged"].append(f"extraction_coverage: {current.extraction.coverage:.1f}%")
    elif cov_delta > 0:
        comparison["improved"].append(f"extraction_coverage: {baseline.extraction.coverage:.1f}% → {current.extraction.coverage:.1f}%")
    else:
        comparison["regressed"].append(f"extraction_coverage: {baseline.extraction.coverage:.1f}% → {current.extraction.coverage:.1f}%")
        comparison["summary"] = "fail"
    
    # Compare false positive rate (lower is better)
    fpr_delta = current.validation.false_positive_rate - baseline.validation.false_positive_rate
    if abs(fpr_delta) < 0.001:
        comparison["unchanged"].append(f"false_positive_rate: {current.validation.false_positive_rate:.2%}")
    elif fpr_delta < 0:
        comparison["improved"].append(f"false_positive_rate: {baseline.validation.false_positive_rate:.2%} → {current.validation.false_positive_rate:.2%}")
    else:
        comparison["regressed"].append(f"false_positive_rate: {baseline.validation.false_positive_rate:.2%} → {current.validation.false_positive_rate:.2%}")
        comparison["summary"] = "fail"
    
    # Compare critical miss rate (must be 0)
    if current.validation.critical_missed > 0:
        comparison["regressed"].append(f"critical_missed: {current.validation.critical_missed} (must be 0)")
        comparison["summary"] = "fail"
    
    # Compare F1 score
    f1_delta = current.validation.f1_score - baseline.validation.f1_score
    if abs(f1_delta) < 0.01:
        comparison["unchanged"].append(f"f1_score: {current.validation.f1_score:.3f}")
    elif f1_delta > 0:
        comparison["improved"].append(f"f1_score: {baseline.validation.f1_score:.3f} → {current.validation.f1_score:.3f}")
    else:
        comparison["regressed"].append(f"f1_score: {baseline.validation.f1_score:.3f} → {current.validation.f1_score:.3f}")
    
    return comparison


def print_comparison(comparison: Dict[str, Any]):
    """Pretty print comparison results."""
    print("\n" + "=" * 60)
    print("CORPUS COMPARISON RESULTS")
    print("=" * 60)
    
    if comparison["improved"]:
        print("\n✅ IMPROVED:")
        for item in comparison["improved"]:
            print(f"   {item}")
    
    if comparison["regressed"]:
        print("\n❌ REGRESSED:")
        for item in comparison["regressed"]:
            print(f"   {item}")
    
    if comparison["unchanged"]:
        print("\n➡️  UNCHANGED:")
        for item in comparison["unchanged"]:
            print(f"   {item}")
    
    print("\n" + "-" * 60)
    if comparison["summary"] == "pass":
        print("✅ OVERALL: PASS - No regressions detected")
    else:
        print("❌ OVERALL: FAIL - Regressions detected")
    print("=" * 60 + "\n")

