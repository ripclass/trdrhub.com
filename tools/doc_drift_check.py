#!/usr/bin/env python3
"""
BMAD Document Drift Check Script

Analyzes repository to detect implemented features and verifies that corresponding
documentation exists in PRD v5, Architecture v5, and Stories. Generates a report
identifying gaps and missing links between code and documentation.

Usage:
    python tools/doc_drift_check.py
    python tools/doc_drift_check.py --output docs/reports/drift-report.md
    python tools/doc_drift_check.py --config .bmad-core/core-config.yaml --verbose
"""

import os
import sys
import argparse
try:
    import yaml
except ImportError:
    yaml = None
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class DriftStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"

@dataclass
class ComponentCheck:
    name: str
    code_paths: List[str]
    prd_sections: List[str]
    arch_sections: List[str]
    stories: List[str]
    status: DriftStatus
    notes: str

class BMadDocDriftChecker:
    def __init__(self, config_path: str = ".bmad-core/core-config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.repo_root = Path(".")
        self.components = {}
        self.results = []

    def _load_config(self) -> Dict:
        """Load BMAD core configuration"""
        if yaml is None:
            print(f"Warning: PyYAML not available, using default config")
            return self._default_config()

        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Default configuration if file missing"""
        return {
            'driftCheckConfig': {
                'trackedComponents': [
                    'rules_engine', 'audit_service', 'ocr_service',
                    'llm_service', 'bank_connectors', 'queue_systems', 'storage_service'
                ]
            },
            'prd': {'prdShardedLocation': 'docs/prd'},
            'architecture': {'architectureShardedLocation': 'docs/architecture'},
            'devStoryLocation': 'docs/stories'
        }

    def detect_implemented_components(self) -> Dict[str, List[str]]:
        """Detect implemented components by analyzing codebase structure"""
        components = {}

        # Check API app structure
        api_path = Path("apps/api/app")
        if api_path.exists():
            for subdir in api_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('_'):
                    component_name = subdir.name
                    code_files = list(subdir.rglob("*.py"))
                    if code_files:
                        components[component_name] = [str(f) for f in code_files]

        # Check for specific service patterns
        service_patterns = {
            'rules_engine': ['**/rules/**', '**/compliance/**'],
            'audit_service': ['**/audit/**', '**/logging/**'],
            'ocr_service': ['**/ocr/**', '**/document**'],
            'llm_service': ['**/llm/**', '**/ai/**', '**/prompt**'],
            'bank_connectors': ['**/bank**', '**/swift**', '**/connector**'],
            'queue_systems': ['**/queue**', '**/celery**', '**/task**'],
            'storage_service': ['**/storage**', '**/s3**', '**/minio**'],
            'auth_service': ['**/auth**', '**/security**'],
            'monitoring': ['**/monitoring/**', '**/observability/**']
        }

        for component, patterns in service_patterns.items():
            files = []
            for pattern in patterns:
                files.extend(self.repo_root.glob(pattern))

            py_files = [str(f) for f in files if f.suffix == '.py' and f.is_file()]
            if py_files:
                components[component] = py_files

        return components

    def check_prd_coverage(self, component: str) -> Tuple[List[str], bool]:
        """Check if component is documented in PRD v5"""
        prd_path = Path(self.config.get('prd', {}).get('prdShardedLocation', 'docs/prd'))
        found_sections = []

        if not prd_path.exists():
            return found_sections, False

        # Search for component mentions in PRD files
        search_terms = [
            component.replace('_', ' '),
            component.replace('_', '-'),
            component
        ]

        for prd_file in prd_path.glob("*.md"):
            content = prd_file.read_text(encoding='utf-8').lower()
            for term in search_terms:
                if term.lower() in content:
                    found_sections.append(str(prd_file.relative_to('docs')))
                    break

        return found_sections, len(found_sections) > 0

    def check_architecture_coverage(self, component: str) -> Tuple[List[str], bool]:
        """Check if component is documented in Architecture v5"""
        arch_path = Path(self.config.get('architecture', {}).get('architectureShardedLocation', 'docs/architecture'))
        found_sections = []

        if not arch_path.exists():
            return found_sections, False

        search_terms = [
            component.replace('_', ' '),
            component.replace('_', '-'),
            component
        ]

        for arch_file in arch_path.glob("*.md"):
            content = arch_file.read_text(encoding='utf-8').lower()
            for term in search_terms:
                if term.lower() in content:
                    found_sections.append(str(arch_file.relative_to('docs')))
                    break

        return found_sections, len(found_sections) > 0

    def check_story_coverage(self, component: str) -> Tuple[List[str], bool]:
        """Check if component has corresponding stories"""
        story_path = Path(self.config.get('devStoryLocation', 'docs/stories'))
        found_stories = []

        if not story_path.exists():
            return found_stories, False

        # Look for stories that mention the component
        search_terms = [
            component.replace('_', '-'),
            component.replace('_', ' '),
            component
        ]

        for story_file in story_path.glob("*.md"):
            content = story_file.read_text(encoding='utf-8').lower()
            filename_lower = story_file.name.lower()

            # Check filename first
            for term in search_terms:
                if term.lower() in filename_lower:
                    found_stories.append(story_file.name)
                    break
            else:
                # Check content
                for term in search_terms:
                    if term.lower() in content:
                        found_stories.append(story_file.name)
                        break

        return found_stories, len(found_stories) > 0

    def assess_component_status(self, component: str, code_paths: List[str],
                              prd_sections: List[str], arch_sections: List[str],
                              stories: List[str]) -> Tuple[DriftStatus, str]:
        """Assess overall status of component documentation"""
        has_code = len(code_paths) > 0
        has_prd = len(prd_sections) > 0
        has_arch = len(arch_sections) > 0
        has_stories = len(stories) > 0

        if has_code and has_prd and has_arch and has_stories:
            return DriftStatus.PASS, "Complete documentation coverage"
        elif has_code and (has_prd or has_arch):
            missing = []
            if not has_prd:
                missing.append("PRD")
            if not has_arch:
                missing.append("Architecture")
            if not has_stories:
                missing.append("Stories")
            return DriftStatus.WARNING, f"Missing: {', '.join(missing)}"
        elif has_code:
            return DriftStatus.FAIL, "Code exists but no documentation found"
        else:
            return DriftStatus.PASS, "No implementation detected"

    def run_drift_check(self) -> List[ComponentCheck]:
        """Run complete drift check analysis"""
        print("🔍 BMAD Document Drift Check - Analyzing repository...")

        # Detect implemented components
        print("📁 Detecting implemented components...")
        implemented = self.detect_implemented_components()
        print(f"   Found {len(implemented)} potential components")

        # Get tracked components from config
        tracked = self.config.get('driftCheckConfig', {}).get('trackedComponents', [])
        all_components = set(tracked) | set(implemented.keys())

        results = []

        for component in sorted(all_components):
            print(f"📋 Checking {component}...")

            # Get code paths
            code_paths = implemented.get(component, [])

            # Check documentation coverage
            prd_sections, has_prd = self.check_prd_coverage(component)
            arch_sections, has_arch = self.check_architecture_coverage(component)
            stories, has_stories = self.check_story_coverage(component)

            # Assess status
            status, notes = self.assess_component_status(
                component, code_paths, prd_sections, arch_sections, stories
            )

            check = ComponentCheck(
                name=component,
                code_paths=code_paths,
                prd_sections=prd_sections,
                arch_sections=arch_sections,
                stories=stories,
                status=status,
                notes=notes
            )

            results.append(check)

            # Print immediate feedback
            status_emoji = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}
            print(f"   {status_emoji[status.value]} {component}: {notes}")

        return results

    def generate_report(self, results: List[ComponentCheck], output_path: str) -> bool:
        """Generate markdown report of drift check results"""

        # Count results by status
        pass_count = sum(1 for r in results if r.status == DriftStatus.PASS)
        warning_count = sum(1 for r in results if r.status == DriftStatus.WARNING)
        fail_count = sum(1 for r in results if r.status == DriftStatus.FAIL)

        overall_status = DriftStatus.PASS
        if fail_count > 0:
            overall_status = DriftStatus.FAIL
        elif warning_count > 0:
            overall_status = DriftStatus.WARNING

        # Generate markdown report
        report = f"""# BMAD Document Drift Check Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Asia/Dhaka)
**Overall Status:** {overall_status.value}
**Components Analyzed:** {len(results)}

## Summary

| Status | Count | Components |
|--------|-------|------------|
| ✅ PASS | {pass_count} | Complete documentation coverage |
| ⚠️ WARNING | {warning_count} | Partial documentation gaps |
| ❌ FAIL | {fail_count} | Code without documentation |

## Component Analysis

"""

        for result in sorted(results, key=lambda x: (x.status.value, x.name)):
            status_emoji = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}

            report += f"""### {status_emoji[result.status.value]} {result.name}

**Status:** {result.status.value}
**Notes:** {result.notes}

"""

            if result.code_paths:
                report += f"**Code Paths ({len(result.code_paths)}):**\n"
                for path in result.code_paths[:5]:  # Limit to first 5
                    report += f"- `{path}`\n"
                if len(result.code_paths) > 5:
                    report += f"- ... and {len(result.code_paths) - 5} more files\n"
                report += "\n"

            if result.prd_sections:
                report += f"**PRD Documentation:**\n"
                for section in result.prd_sections:
                    report += f"- [{section}]({section})\n"
                report += "\n"

            if result.arch_sections:
                report += f"**Architecture Documentation:**\n"
                for section in result.arch_sections:
                    report += f"- [{section}]({section})\n"
                report += "\n"

            if result.stories:
                report += f"**Stories:**\n"
                for story in result.stories:
                    report += f"- [{story}](stories/{story})\n"
                report += "\n"

            report += "---\n\n"

        # Add recommendations
        if overall_status != DriftStatus.PASS:
            report += """## Recommendations

### For FAIL Components (Code without Documentation)
1. Create corresponding stories in `docs/stories/`
2. Add feature descriptions to PRD sections
3. Document technical implementation in Architecture
4. Follow BMAD workflow for future development

### For WARNING Components (Partial Documentation)
1. Complete missing documentation sections
2. Ensure cross-references between docs are consistent
3. Update stories to reflect current implementation status

### Next Steps
1. Run `python tools/doc_drift_check.py` weekly
2. Address FAIL items before merging new features
3. Update documentation when modifying existing components
4. Use BMAD SM→Dev→QA workflow for new development

"""

        # Write report
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        return overall_status == DriftStatus.PASS

def main():
    parser = argparse.ArgumentParser(description='BMAD Document Drift Check')
    parser.add_argument('--config', default='.bmad-core/core-config.yaml',
                       help='Path to BMAD config file')
    parser.add_argument('--output', default='docs/reports/doc-drift-latest.md',
                       help='Output path for drift report')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    # Initialize checker
    checker = BMadDocDriftChecker(args.config)

    # Run drift check
    results = checker.run_drift_check()

    # Generate report
    success = checker.generate_report(results, args.output)

    print(f"\n📊 Report generated: {args.output}")

    # Print summary
    pass_count = sum(1 for r in results if r.status == DriftStatus.PASS)
    warning_count = sum(1 for r in results if r.status == DriftStatus.WARNING)
    fail_count = sum(1 for r in results if r.status == DriftStatus.FAIL)

    print(f"📈 Summary: {pass_count} PASS, {warning_count} WARNING, {fail_count} FAIL")

    if not success:
        print("❌ DRIFT CHECK FAILED - Documentation gaps detected")
        sys.exit(1)
    else:
        print("✅ DRIFT CHECK PASSED - Documentation is up to date")
        sys.exit(0)

if __name__ == "__main__":
    main()