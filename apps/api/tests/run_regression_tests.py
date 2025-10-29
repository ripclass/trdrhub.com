#!/usr/bin/env python3
"""
LCopilot Trust Platform Regression Test Runner
Executes comprehensive regression tests across all fixture categories and validates system stability.
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone
import traceback

# Add trust platform to path
sys.path.append(str(Path(__file__).parent.parent))

from trust_platform.compliance.compliance_engine import UCP600ISBPComplianceEngine
from pipeline.safe_validator import SafeRuleValidator
from trust_platform.logging.structured_logger import get_logger, LogContext

class RegressionTestRunner:
    """
    Comprehensive regression test runner for LCopilot Trust Platform.
    Tests all fixture categories and validates system stability under various conditions.
    """

    def __init__(self, fixtures_dir: str, output_dir: str):
        self.fixtures_dir = Path(fixtures_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.compliance_engine = UCP600ISBPComplianceEngine("test")
        self.safe_validator = SafeRuleValidator()
        self.logger = get_logger("regression_tests", "test")

        # Test results tracking
        self.test_results = {
            'summary': {
                'total_fixtures': 0,
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'error_tests': 0,
                'skipped_tests': 0,
                'start_time': None,
                'end_time': None,
                'duration_seconds': 0
            },
            'categories': {},
            'detailed_results': [],
            'performance_metrics': [],
            'stability_metrics': {
                'memory_usage_mb': [],
                'avg_processing_time_ms': [],
                'error_rate_percent': []
            }
        }

    def discover_fixtures(self) -> Dict[str, List[Path]]:
        """Discover all test fixtures organized by category"""
        fixtures = {
            'icc': [],
            'isbp': [],
            'local_bd': [],
            'fuzz': []
        }

        for category in fixtures.keys():
            category_dir = self.fixtures_dir / category
            if category_dir.exists():
                fixture_files = list(category_dir.glob('*.json'))
                fixtures[category] = fixture_files
                print(f"Found {len(fixture_files)} fixtures in {category} category")

        return fixtures

    def load_fixture(self, fixture_path: Path) -> Dict[str, Any]:
        """Load and validate fixture file"""
        try:
            with open(fixture_path, 'r') as f:
                fixture_data = json.load(f)

            # Validate fixture structure
            if 'input' not in fixture_data or 'expected_output' not in fixture_data:
                raise ValueError(f"Invalid fixture structure in {fixture_path}")

            return fixture_data
        except Exception as e:
            self.logger.error(f"Failed to load fixture {fixture_path}: {str(e)}")
            raise

    def run_single_test(self, fixture_path: Path, category: str) -> Dict[str, Any]:
        """Execute a single regression test"""
        test_start = time.time()
        test_context = self.logger.create_context(
            request_id=f"regression_{fixture_path.stem}_{int(time.time())}",
            component="regression_tests",
            lc_reference=fixture_path.stem
        )

        try:
            # Load fixture
            fixture_data = self.load_fixture(fixture_path)
            lc_input = fixture_data['input']
            expected_output = fixture_data['expected_output']

            self.logger.info(
                f"Starting regression test: {fixture_path.name}",
                context=test_context,
                extra_data={'category': category, 'fixture_path': str(fixture_path)}
            )

            # Execute validation
            if category == 'fuzz':
                # For fuzz tests, focus on system resilience
                result = self._test_fuzz_resilience(lc_input, test_context)
            else:
                # For compliance tests, validate against expected output
                result = self._test_compliance_validation(lc_input, expected_output, test_context)

            test_duration = (time.time() - test_start) * 1000

            # Determine test outcome
            test_passed = self._evaluate_test_result(result, expected_output, category)

            test_result = {
                'fixture_name': fixture_path.name,
                'category': category,
                'status': 'passed' if test_passed else 'failed',
                'duration_ms': test_duration,
                'actual_result': result,
                'expected_result': expected_output,
                'compliance_score': result.get('compliance_score', 0.0),
                'error_count': result.get('error_summary', {}).get('total_errors', 0),
                'critical_errors': result.get('error_summary', {}).get('critical_errors', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            self.logger.info(
                f"Regression test completed: {fixture_path.name} - {'PASSED' if test_passed else 'FAILED'}",
                context=test_context,
                extra_data={
                    'test_passed': test_passed,
                    'duration_ms': test_duration,
                    'compliance_score': result.get('compliance_score', 0.0)
                }
            )

            return test_result

        except Exception as e:
            test_duration = (time.time() - test_start) * 1000

            self.logger.error(
                f"Regression test error: {fixture_path.name} - {str(e)}",
                context=test_context,
                extra_data={
                    'error_type': type(e).__name__,
                    'stack_trace': traceback.format_exc()
                }
            )

            return {
                'fixture_name': fixture_path.name,
                'category': category,
                'status': 'error',
                'duration_ms': test_duration,
                'error_message': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    def _test_compliance_validation(self, lc_input: Dict[str, Any],
                                  expected_output: Dict[str, Any],
                                  context: LogContext) -> Dict[str, Any]:
        """Test compliance validation against expected output"""

        # Create mock rules for testing (in production, these would come from the compliance engine)
        mock_rules = [
            {
                'func': lambda doc, **kwargs: {'status': 'pass', 'score': 1.0},
                'rule_id': 'TEST-RULE-001',
                'timeout': 10
            },
            {
                'func': lambda doc, **kwargs: {'status': 'pass', 'score': 0.8},
                'rule_id': 'TEST-RULE-002',
                'timeout': 10
            }
        ]

        # Execute safe validation
        result = self.safe_validator.safe_validate_document(lc_input, mock_rules)

        return result

    def _test_fuzz_resilience(self, lc_input: Dict[str, Any], context: LogContext) -> Dict[str, Any]:
        """Test system resilience against fuzz input"""

        # Create rules that might fail with corrupted input
        resilience_rules = [
            {
                'func': self._resilience_test_rule,
                'rule_id': 'FUZZ-RESILIENCE-001',
                'timeout': 5,
                'kwargs': {'test_type': 'null_handling'}
            },
            {
                'func': self._resilience_test_rule,
                'rule_id': 'FUZZ-RESILIENCE-002',
                'timeout': 5,
                'kwargs': {'test_type': 'type_safety'}
            },
            {
                'func': self._resilience_test_rule,
                'rule_id': 'FUZZ-RESILIENCE-003',
                'timeout': 5,
                'kwargs': {'test_type': 'memory_safety'}
            }
        ]

        # Execute with safe validator to ensure no crashes
        result = self.safe_validator.safe_validate_document(lc_input, resilience_rules)

        return result

    def _resilience_test_rule(self, lc_document: Dict[str, Any], test_type: str = 'basic') -> Dict[str, Any]:
        """Mock rule for testing system resilience"""

        if test_type == 'null_handling':
            # Test null value handling
            lc_number = lc_document.get('lc_number')
            if lc_number is None:
                return {'status': 'handled', 'message': 'Null LC number handled gracefully'}

        elif test_type == 'type_safety':
            # Test type safety
            amount = lc_document.get('amount')
            if isinstance(amount, str) and amount == "not-a-number":
                return {'status': 'handled', 'message': 'Invalid amount type handled gracefully'}

        elif test_type == 'memory_safety':
            # Test with potentially large data
            description = lc_document.get('extremely_long_field', '')
            if len(str(description)) > 10000:  # Large string
                return {'status': 'handled', 'message': 'Large data handled without memory issues'}

        return {'status': 'pass', 'message': 'Resilience test passed'}

    def _evaluate_test_result(self, actual_result: Dict[str, Any],
                            expected_result: Dict[str, Any],
                            category: str) -> bool:
        """Evaluate if test result matches expectations"""

        if category == 'fuzz':
            # For fuzz tests, success is measured by system stability (no crashes)
            return (actual_result.get('overall_status') in ['compliant', 'discrepant', 'non_compliant', 'critical_failure'] and
                    actual_result.get('error_summary', {}).get('system_behavior') == 'graceful_degradation')

        # For compliance tests, compare key metrics
        actual_score = actual_result.get('compliance_score', 0.0)
        expected_score = expected_result.get('compliance_score', 0.0)

        actual_status = actual_result.get('overall_status', 'unknown')
        expected_status = expected_result.get('overall_status', 'unknown')

        # Allow some tolerance in scoring (±0.1)
        score_match = abs(actual_score - expected_score) <= 0.1
        status_match = actual_status == expected_status

        return score_match and status_match

    def run_category_tests(self, category: str, fixtures: List[Path]) -> Dict[str, Any]:
        """Run all tests in a specific category"""
        category_start = time.time()
        category_results = {
            'category': category,
            'total_fixtures': len(fixtures),
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'avg_duration_ms': 0,
            'avg_compliance_score': 0,
            'test_results': []
        }

        print(f"\n=== Running {category.upper()} Category Tests ===")

        for fixture_path in fixtures:
            print(f"  Testing: {fixture_path.name}")

            test_result = self.run_single_test(fixture_path, category)
            category_results['test_results'].append(test_result)

            # Update counters
            if test_result['status'] == 'passed':
                category_results['passed'] += 1
            elif test_result['status'] == 'failed':
                category_results['failed'] += 1
            else:  # error
                category_results['errors'] += 1

        # Calculate category metrics
        if fixtures:
            category_results['avg_duration_ms'] = sum(
                t['duration_ms'] for t in category_results['test_results']
            ) / len(fixtures)

            valid_scores = [t.get('compliance_score', 0) for t in category_results['test_results']
                           if t.get('compliance_score') is not None]
            if valid_scores:
                category_results['avg_compliance_score'] = sum(valid_scores) / len(valid_scores)

        category_duration = time.time() - category_start
        print(f"  Category {category} completed in {category_duration:.2f}s")
        print(f"  Results: {category_results['passed']} passed, {category_results['failed']} failed, {category_results['errors']} errors")

        return category_results

    def run_all_tests(self) -> Dict[str, Any]:
        """Execute complete regression test suite"""
        print("=== LCopilot Trust Platform Regression Test Suite ===")

        # Initialize test run
        test_start = time.time()
        self.test_results['summary']['start_time'] = datetime.now(timezone.utc).isoformat()

        # Discover fixtures
        fixtures_by_category = self.discover_fixtures()
        total_fixtures = sum(len(fixtures) for fixtures in fixtures_by_category.values())

        print(f"Discovered {total_fixtures} total fixtures across {len(fixtures_by_category)} categories")

        if total_fixtures == 0:
            print("No fixtures found. Please check fixtures directory.")
            return self.test_results

        self.test_results['summary']['total_fixtures'] = total_fixtures

        # Run tests by category
        for category, fixtures in fixtures_by_category.items():
            if not fixtures:
                print(f"Skipping {category} - no fixtures found")
                continue

            category_results = self.run_category_tests(category, fixtures)
            self.test_results['categories'][category] = category_results

            # Update overall results
            self.test_results['detailed_results'].extend(category_results['test_results'])
            self.test_results['summary']['passed_tests'] += category_results['passed']
            self.test_results['summary']['failed_tests'] += category_results['failed']
            self.test_results['summary']['error_tests'] += category_results['errors']

        # Finalize test run
        test_end = time.time()
        self.test_results['summary']['end_time'] = datetime.now(timezone.utc).isoformat()
        self.test_results['summary']['duration_seconds'] = test_end - test_start
        self.test_results['summary']['total_tests'] = len(self.test_results['detailed_results'])

        # Calculate success rate
        total_tests = self.test_results['summary']['total_tests']
        passed_tests = self.test_results['summary']['passed_tests']
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Generate performance metrics
        self._generate_performance_metrics()

        # Print summary
        print(f"\n=== Regression Test Summary ===")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {self.test_results['summary']['failed_tests']}")
        print(f"Errors: {self.test_results['summary']['error_tests']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Duration: {self.test_results['summary']['duration_seconds']:.2f}s")

        # Save results
        self._save_results()

        return self.test_results

    def _generate_performance_metrics(self):
        """Generate performance and stability metrics"""
        detailed_results = self.test_results['detailed_results']

        if not detailed_results:
            return

        # Calculate performance metrics
        durations = [r['duration_ms'] for r in detailed_results if 'duration_ms' in r]
        compliance_scores = [r.get('compliance_score', 0) for r in detailed_results
                           if r.get('compliance_score') is not None]
        error_counts = [r.get('error_count', 0) for r in detailed_results]

        self.test_results['performance_metrics'] = {
            'avg_processing_time_ms': sum(durations) / len(durations) if durations else 0,
            'min_processing_time_ms': min(durations) if durations else 0,
            'max_processing_time_ms': max(durations) if durations else 0,
            'avg_compliance_score': sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0,
            'avg_errors_per_test': sum(error_counts) / len(error_counts) if error_counts else 0,
            'total_processing_time_ms': sum(durations) if durations else 0
        }

        # Calculate stability metrics
        failed_tests = self.test_results['summary']['failed_tests']
        error_tests = self.test_results['summary']['error_tests']
        total_tests = self.test_results['summary']['total_tests']

        self.test_results['stability_metrics'] = {
            'error_rate_percent': ((failed_tests + error_tests) / total_tests * 100) if total_tests > 0 else 0,
            'crash_rate_percent': (error_tests / total_tests * 100) if total_tests > 0 else 0,
            'system_stability': 'stable' if error_tests == 0 else 'unstable'
        }

    def _save_results(self):
        """Save test results to output directory"""

        # Save detailed JSON results
        results_file = self.output_dir / f'regression_results_{int(time.time())}.json'
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)

        # Save summary report
        summary_file = self.output_dir / f'regression_summary_{int(time.time())}.txt'
        with open(summary_file, 'w') as f:
            f.write("LCopilot Trust Platform Regression Test Summary\n")
            f.write("=" * 50 + "\n\n")

            # Overall summary
            summary = self.test_results['summary']
            f.write(f"Test Run: {summary['start_time']}\n")
            f.write(f"Duration: {summary['duration_seconds']:.2f} seconds\n")
            f.write(f"Total Tests: {summary['total_tests']}\n")
            f.write(f"Passed: {summary['passed_tests']}\n")
            f.write(f"Failed: {summary['failed_tests']}\n")
            f.write(f"Errors: {summary['error_tests']}\n")

            success_rate = (summary['passed_tests'] / summary['total_tests'] * 100) if summary['total_tests'] > 0 else 0
            f.write(f"Success Rate: {success_rate:.1f}%\n\n")

            # Category breakdown
            f.write("Category Results:\n")
            for category, results in self.test_results['categories'].items():
                f.write(f"  {category.upper()}:\n")
                f.write(f"    Total: {results['total_fixtures']}\n")
                f.write(f"    Passed: {results['passed']}\n")
                f.write(f"    Failed: {results['failed']}\n")
                f.write(f"    Errors: {results['errors']}\n")
                f.write(f"    Avg Score: {results['avg_compliance_score']:.3f}\n\n")

            # Performance metrics
            if 'performance_metrics' in self.test_results:
                perf = self.test_results['performance_metrics']
                f.write("Performance Metrics:\n")
                f.write(f"  Avg Processing Time: {perf['avg_processing_time_ms']:.2f}ms\n")
                f.write(f"  Min Processing Time: {perf['min_processing_time_ms']:.2f}ms\n")
                f.write(f"  Max Processing Time: {perf['max_processing_time_ms']:.2f}ms\n")
                f.write(f"  Total Processing Time: {perf['total_processing_time_ms']:.2f}ms\n\n")

            # Stability metrics
            if 'stability_metrics' in self.test_results:
                stability = self.test_results['stability_metrics']
                f.write("Stability Metrics:\n")
                f.write(f"  Error Rate: {stability['error_rate_percent']:.1f}%\n")
                f.write(f"  Crash Rate: {stability['crash_rate_percent']:.1f}%\n")
                f.write(f"  System Stability: {stability['system_stability']}\n")

        print(f"\nResults saved to:")
        print(f"  Detailed: {results_file}")
        print(f"  Summary: {summary_file}")

def main():
    parser = argparse.ArgumentParser(description='LCopilot Trust Platform Regression Test Runner')
    parser.add_argument('--fixtures-dir', default='fixtures/', help='Directory containing test fixtures')
    parser.add_argument('--output-dir', default='test-results/', help='Output directory for test results')
    parser.add_argument('--category', help='Run tests for specific category only (icc, isbp, local_bd, fuzz)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Initialize test runner
    runner = RegressionTestRunner(args.fixtures_dir, args.output_dir)

    try:
        # Run tests
        results = runner.run_all_tests()

        # Return appropriate exit code
        total_tests = results['summary']['total_tests']
        failed_tests = results['summary']['failed_tests'] + results['summary']['error_tests']

        if total_tests == 0:
            print("No tests were run")
            sys.exit(1)
        elif failed_tests == 0:
            print("All tests passed!")
            sys.exit(0)
        else:
            print(f"{failed_tests} out of {total_tests} tests failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test run failed with error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()