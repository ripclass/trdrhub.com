#!/usr/bin/env python3
"""
Gold Corpus Test Runner

Runs validation against all test sets and compares to expected results.

Usage:
    python -m tests.gold_corpus.run_corpus
    python -m tests.gold_corpus.run_corpus --set set_001_standard
    python -m tests.gold_corpus.run_corpus --baseline
    python -m tests.gold_corpus.run_corpus --compare baseline_v1.json
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.gold_corpus.expected import ExpectedResult, FalsePositiveCheck
from tests.gold_corpus.metrics import (
    CorpusResult,
    ExtractionMetrics,
    ValidationMetrics,
    compare_results,
    print_comparison,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
CORPUS_DIR = Path(__file__).parent
DOCUMENTS_DIR = CORPUS_DIR / "documents"
EXPECTED_DIR = CORPUS_DIR / "expected"
RESULTS_DIR = CORPUS_DIR / "results"
BASELINES_DIR = CORPUS_DIR / "baselines"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(exist_ok=True)
EXPECTED_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
BASELINES_DIR.mkdir(exist_ok=True)


class CorpusRunner:
    """Runs gold corpus tests."""
    
    def __init__(self, api_base_url: Optional[str] = None):
        self.api_base_url = api_base_url or "http://localhost:8000"
        self.corpus_version = self._get_corpus_version()
        self.engine_version = self._get_engine_version()
    
    def _get_corpus_version(self) -> str:
        """Get corpus version from version file or git."""
        version_file = CORPUS_DIR / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return datetime.now().strftime("%Y%m%d")
    
    def _get_engine_version(self) -> str:
        """Get engine version."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=CORPUS_DIR.parent.parent.parent,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def discover_sets(self) -> List[str]:
        """Discover all test sets in documents directory."""
        sets = []
        if DOCUMENTS_DIR.exists():
            for item in DOCUMENTS_DIR.iterdir():
                if item.is_dir() and item.name.startswith("set_"):
                    sets.append(item.name)
        return sorted(sets)
    
    async def run_validation(self, set_id: str) -> Tuple[Dict[str, Any], float]:
        """
        Run validation on a test set.
        
        Returns (result_dict, latency_ms)
        """
        set_dir = DOCUMENTS_DIR / set_id
        if not set_dir.exists():
            raise FileNotFoundError(f"Test set not found: {set_dir}")
        
        # Collect document files
        doc_files = list(set_dir.glob("*.pdf")) + list(set_dir.glob("*.png")) + list(set_dir.glob("*.jpg"))
        if not doc_files:
            raise ValueError(f"No documents found in {set_dir}")
        
        logger.info(f"Running validation on {set_id} with {len(doc_files)} documents")
        
        # For now, we'll use a mock implementation
        # In production, this would call the actual API
        start_time = time.perf_counter()
        
        try:
            result = await self._call_validation_api(doc_files)
        except Exception as e:
            logger.error(f"Validation failed for {set_id}: {e}")
            result = {"error": str(e), "issues": [], "structured_result": {}}
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return result, latency_ms
    
    async def _call_validation_api(self, doc_files: List[Path]) -> Dict[str, Any]:
        """Call the validation API with documents."""
        import aiohttp
        
        url = f"{self.api_base_url}/api/validate/"
        
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            
            for doc_file in doc_files:
                data.add_field(
                    'files',
                    open(doc_file, 'rb'),
                    filename=doc_file.name,
                    content_type='application/pdf' if doc_file.suffix == '.pdf' else 'image/png'
                )
            
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"API error {response.status}: {text}")
                return await response.json()
    
    def evaluate_set(
        self,
        set_id: str,
        result: Dict[str, Any],
        expected: ExpectedResult,
    ) -> Dict[str, Any]:
        """
        Evaluate validation result against expected.
        
        Returns evaluation dict with:
        - passed: bool
        - extraction_metrics: dict
        - validation_metrics: dict
        - field_results: list
        - issue_results: list
        - false_positives: list
        """
        evaluation = {
            "passed": True,
            "field_results": [],
            "issue_results": [],
            "false_positives": [],
            "errors": [],
        }
        
        structured = result.get("structured_result", {})
        issues = result.get("issues", []) or structured.get("issues", [])
        
        # Evaluate field extraction
        for expected_field in expected.expected_fields:
            actual_value = self._get_field_value(structured, expected_field.document_type, expected_field.field_name)
            matched = expected_field.matches(actual_value)
            
            evaluation["field_results"].append({
                "field": f"{expected_field.document_type}.{expected_field.field_name}",
                "expected": expected_field.expected_value,
                "actual": actual_value,
                "matched": matched,
                "criticality": expected_field.criticality.value,
            })
            
            if not matched and expected_field.criticality.value == "critical":
                evaluation["passed"] = False
                evaluation["errors"].append(f"Critical field not extracted: {expected_field.field_name}")
        
        # Evaluate expected issues (true positives)
        matched_issues = set()
        for expected_issue in expected.expected_issues:
            found = False
            for i, actual_issue in enumerate(issues):
                if expected_issue.matches(actual_issue):
                    found = True
                    matched_issues.add(i)
                    break
            
            evaluation["issue_results"].append({
                "rule_id": expected_issue.rule_id,
                "severity": expected_issue.severity.value,
                "found": found,
            })
            
            if not found and expected_issue.severity.value == "critical":
                evaluation["passed"] = False
                evaluation["errors"].append(f"Critical issue not raised: {expected_issue.rule_id}")
        
        # Check for false positives
        for i, actual_issue in enumerate(issues):
            if i in matched_issues:
                continue  # This was a true positive
            
            for fp_check in expected.false_positive_checks:
                if fp_check.triggered_by(actual_issue):
                    evaluation["false_positives"].append({
                        "rule_id": fp_check.rule_id,
                        "actual_issue": actual_issue,
                        "description": fp_check.description,
                    })
                    evaluation["passed"] = False
                    evaluation["errors"].append(f"False positive: {fp_check.rule_id}")
        
        # Check compliance rate
        if expected.expected_compliance_rate is not None:
            actual_compliance = structured.get("processing_summary", {}).get("compliance_rate", 0)
            diff = abs(actual_compliance - expected.expected_compliance_rate)
            if diff > expected.compliance_tolerance:
                evaluation["passed"] = False
                evaluation["errors"].append(
                    f"Compliance rate mismatch: expected {expected.expected_compliance_rate}%, got {actual_compliance}%"
                )
        
        return evaluation
    
    def _get_field_value(self, structured: Dict, doc_type: str, field_name: str) -> Any:
        """Extract field value from structured result."""
        # Try various paths where the field might be
        paths = [
            ["lc_structured", field_name],
            ["lc_structured", doc_type, field_name],
            ["documents_structured", doc_type, field_name],
            [field_name],
        ]
        
        for path in paths:
            value = structured
            for key in path:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                return value
        
        return None
    
    async def run_all(self, sets: Optional[List[str]] = None) -> CorpusResult:
        """Run all test sets and collect metrics."""
        if sets is None:
            sets = self.discover_sets()
        
        if not sets:
            logger.warning("No test sets found in %s", DOCUMENTS_DIR)
            # Return empty result
            return CorpusResult(
                timestamp=datetime.now().isoformat(),
                corpus_version=self.corpus_version,
                engine_version=self.engine_version,
            )
        
        result = CorpusResult(
            timestamp=datetime.now().isoformat(),
            corpus_version=self.corpus_version,
            engine_version=self.engine_version,
            total_sets=len(sets),
        )
        
        latencies = []
        
        for set_id in sets:
            logger.info(f"Running set: {set_id}")
            
            # Load expected results
            expected_file = EXPECTED_DIR / f"{set_id}.json"
            if not expected_file.exists():
                logger.warning(f"No expected.json for {set_id}, skipping evaluation")
                continue
            
            expected = ExpectedResult.load(expected_file)
            
            try:
                # Run validation
                validation_result, latency_ms = await self.run_validation(set_id)
                latencies.append(latency_ms)
                
                # Evaluate
                evaluation = self.evaluate_set(set_id, validation_result, expected)
                
                # Update metrics
                for field_result in evaluation["field_results"]:
                    result.extraction.total_fields += 1
                    if field_result["matched"]:
                        result.extraction.extracted_fields += 1
                    if field_result["criticality"] == "critical":
                        result.extraction.critical_fields += 1
                        if field_result["matched"]:
                            result.extraction.critical_extracted += 1
                
                for issue_result in evaluation["issue_results"]:
                    if issue_result["found"]:
                        result.validation.true_positives += 1
                    else:
                        result.validation.false_negatives += 1
                        if issue_result["severity"] == "critical":
                            result.validation.critical_missed += 1
                
                result.validation.false_positives += len(evaluation["false_positives"])
                
                if evaluation["passed"]:
                    result.sets_passed += 1
                else:
                    result.sets_failed += 1
                
                result.set_results[set_id] = evaluation
                result.errors.extend(evaluation["errors"])
                
            except Exception as e:
                logger.error(f"Error running {set_id}: {e}")
                result.sets_failed += 1
                result.errors.append(f"{set_id}: {str(e)}")
        
        # Calculate latency metrics
        if latencies:
            result.total_latency_ms = sum(latencies)
            result.avg_latency_ms = result.total_latency_ms / len(latencies)
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            result.p95_latency_ms = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Run gold corpus tests")
    parser.add_argument("--set", "-s", help="Run specific test set")
    parser.add_argument("--baseline", "-b", action="store_true", help="Save result as baseline")
    parser.add_argument("--compare", "-c", help="Compare against baseline file")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    runner = CorpusRunner(api_base_url=args.api_url)
    
    # Determine which sets to run
    sets = [args.set] if args.set else None
    
    # Run corpus
    result = asyncio.run(runner.run_all(sets))
    
    # Print summary
    print("\n" + "=" * 60)
    print("GOLD CORPUS RESULTS")
    print("=" * 60)
    print(f"Timestamp: {result.timestamp}")
    print(f"Corpus Version: {result.corpus_version}")
    print(f"Engine Version: {result.engine_version}")
    print(f"\nSets: {result.sets_passed}/{result.total_sets} passed")
    print(f"Extraction Coverage: {result.extraction.coverage:.1f}%")
    print(f"Critical Field Coverage: {result.extraction.critical_coverage:.1f}%")
    print(f"F1 Score: {result.validation.f1_score:.3f}")
    print(f"False Positive Rate: {result.validation.false_positive_rate:.2%}")
    print(f"Critical Missed: {result.validation.critical_missed}")
    print(f"Avg Latency: {result.avg_latency_ms:.0f}ms")
    print("=" * 60)
    
    # Save result
    result_file = RESULTS_DIR / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result.save(result_file)
    logger.info(f"Result saved to {result_file}")
    
    # Save as baseline if requested
    if args.baseline:
        baseline_file = BASELINES_DIR / f"baseline_{datetime.now().strftime('%Y%m%d')}.json"
        result.save(baseline_file)
        logger.info(f"Baseline saved to {baseline_file}")
    
    # Compare if requested
    if args.compare:
        compare_file = BASELINES_DIR / args.compare
        if compare_file.exists():
            baseline = CorpusResult.load(compare_file)
            comparison = compare_results(result, baseline)
            print_comparison(comparison)
            
            if comparison["summary"] == "fail":
                sys.exit(1)
        else:
            logger.error(f"Baseline file not found: {compare_file}")
            sys.exit(1)
    
    # Exit with error if any critical failures
    if result.validation.critical_missed > 0:
        logger.error("Critical issues missed - failing")
        sys.exit(1)
    
    if result.sets_failed > 0:
        logger.warning(f"{result.sets_failed} sets failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

