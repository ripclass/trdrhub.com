#!/usr/bin/env python3
"""
Compliance Documentation Validation Tool

This script validates the compliance documentation structure, cross-references,
and ensures consistency across all compliance documents.

Usage:
    python validate_docs.py [--fix] [--verbose]
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    file_path: str = ""
    line_number: int = 0


class ComplianceValidator:
    """Validates compliance documentation structure and content."""

    def __init__(self, docs_path: str, verbose: bool = False):
        self.docs_path = Path(docs_path)
        self.verbose = verbose
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []

        # Expected document structure
        self.required_files = {
            "01_ucp600_mapping.md",
            "02_isbp745_mapping.md",
            "03_eucp_mapping.md",
            "04_compliance_glossary.md",
            "05_annex_for_sla.md",
            "06_version_history.md"
        }

        self.template_files = {
            "_includes/rule_mapping_template.md",
            "_includes/glossary_entry_template.md"
        }

    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[INFO] {message}")

    def validate_file_structure(self) -> List[ValidationResult]:
        """Validate that all required files exist."""
        results = []

        # Check main compliance directory exists
        if not self.docs_path.exists():
            results.append(ValidationResult(
                passed=False,
                message=f"Compliance directory does not exist: {self.docs_path}",
                file_path=str(self.docs_path)
            ))
            return results

        # Check required files
        for required_file in self.required_files:
            file_path = self.docs_path / required_file
            if not file_path.exists():
                results.append(ValidationResult(
                    passed=False,
                    message=f"Missing required file: {required_file}",
                    file_path=str(file_path)
                ))
            else:
                self.log(f"Found required file: {required_file}")

        # Check template files
        for template_file in self.template_files:
            file_path = self.docs_path / template_file
            if not file_path.exists():
                results.append(ValidationResult(
                    passed=False,
                    message=f"Missing template file: {template_file}",
                    file_path=str(file_path)
                ))
            else:
                self.log(f"Found template file: {template_file}")

        return results

    def validate_cross_references(self) -> List[ValidationResult]:
        """Validate cross-references between documents."""
        results = []

        # Extract all references from documents
        references = self._extract_references()

        # Validate UCP 600 article references
        ucp_articles = self._extract_ucp_articles()
        for ref in references.get("ucp600", []):
            if ref not in ucp_articles:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Invalid UCP 600 reference: {ref}",
                    file_path=ref
                ))

        # Validate ISBP 745 section references
        isbp_sections = self._extract_isbp_sections()
        for ref in references.get("isbp745", []):
            if ref not in isbp_sections:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Invalid ISBP 745 reference: {ref}",
                    file_path=ref
                ))

        return results

    def validate_glossary_terms(self) -> List[ValidationResult]:
        """Validate glossary terms and their usage across documents."""
        results = []

        # Extract glossary terms
        glossary_file = self.docs_path / "04_compliance_glossary.md"
        if not glossary_file.exists():
            return [ValidationResult(
                passed=False,
                message="Glossary file missing, cannot validate terms",
                file_path=str(glossary_file)
            )]

        glossary_terms = self._extract_glossary_terms(glossary_file)

        # Check minimum term count (≥60 as specified)
        if len(glossary_terms) < 60:
            results.append(ValidationResult(
                passed=False,
                message=f"Glossary has only {len(glossary_terms)} terms, minimum 60 required",
                file_path=str(glossary_file)
            ))
        else:
            self.log(f"Glossary contains {len(glossary_terms)} terms (meets minimum requirement)")

        # Validate glossary term format
        for term, line_num in glossary_terms.items():
            if not self._validate_glossary_entry_format(glossary_file, term, line_num):
                results.append(ValidationResult(
                    passed=False,
                    message=f"Glossary term '{term}' does not follow template format",
                    file_path=str(glossary_file),
                    line_number=line_num
                ))

        return results

    def validate_compliance_coverage(self) -> List[ValidationResult]:
        """Validate compliance coverage percentages and implementation status."""
        results = []

        # UCP 600 mapping validation
        ucp_file = self.docs_path / "01_ucp600_mapping.md"
        if ucp_file.exists():
            coverage = self._extract_coverage_stats(ucp_file)
            if coverage and coverage.get("total_mapped", 0) < 15:
                results.append(ValidationResult(
                    passed=False,
                    message=f"UCP 600 mapping covers only {coverage.get('total_mapped', 0)} articles, should be ≥15",
                    file_path=str(ucp_file)
                ))

        # ISBP 745 mapping validation
        isbp_file = self.docs_path / "02_isbp745_mapping.md"
        if isbp_file.exists():
            coverage = self._extract_coverage_stats(isbp_file)
            if coverage and coverage.get("total_mapped", 0) < 12:
                results.append(ValidationResult(
                    passed=False,
                    message=f"ISBP 745 mapping covers only {coverage.get('total_mapped', 0)} sections, should be ≥12",
                    file_path=str(isbp_file)
                ))

        return results

    def validate_markdown_syntax(self) -> List[ValidationResult]:
        """Validate Markdown syntax and formatting."""
        results = []

        for md_file in self.docs_path.glob("*.md"):
            if md_file.name.startswith("_"):
                continue

            file_results = self._validate_markdown_file(md_file)
            results.extend(file_results)

        return results

    def _extract_references(self) -> Dict[str, List[str]]:
        """Extract cross-references from all documents."""
        references = {"ucp600": [], "isbp745": [], "eucp": []}

        for md_file in self.docs_path.glob("*.md"):
            if md_file.name.startswith("_"):
                continue

            content = md_file.read_text(encoding='utf-8')

            # Extract UCP 600 references
            ucp_refs = re.findall(r'UCP 600 Art\. (\d+)', content)
            references["ucp600"].extend(ucp_refs)

            # Extract ISBP 745 references
            isbp_refs = re.findall(r'ISBP 745 ([A-Z]\d+)', content)
            references["isbp745"].extend(isbp_refs)

            # Extract eUCP references
            eucp_refs = re.findall(r'eUCP (?:Version )?(\d+\.\d+)', content)
            references["eucp"].extend(eucp_refs)

        return references

    def _extract_ucp_articles(self) -> Set[str]:
        """Extract UCP 600 article numbers from mapping document."""
        ucp_file = self.docs_path / "01_ucp600_mapping.md"
        if not ucp_file.exists():
            return set()

        content = ucp_file.read_text(encoding='utf-8')
        articles = re.findall(r'### Article (\d+):', content)
        return set(articles)

    def _extract_isbp_sections(self) -> Set[str]:
        """Extract ISBP 745 section codes from mapping document."""
        isbp_file = self.docs_path / "02_isbp745_mapping.md"
        if not isbp_file.exists():
            return set()

        content = isbp_file.read_text(encoding='utf-8')
        sections = re.findall(r'#### ([A-Z]\d+):', content)
        return set(sections)

    def _extract_glossary_terms(self, glossary_file: Path) -> Dict[str, int]:
        """Extract glossary terms and their line numbers."""
        terms = {}
        content = glossary_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Look for glossary term headers (#### Term)
            match = re.match(r'^#### ([A-Za-z0-9\s\(\)/\-]+)$', line.strip())
            if match:
                term = match.group(1).strip()
                terms[term] = i

        return terms

    def _validate_glossary_entry_format(self, glossary_file: Path, term: str, line_num: int) -> bool:
        """Validate that a glossary entry follows the template format."""
        content = glossary_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Check if the entry has the required fields
        required_fields = ["**Definition:**", "**Bank/Legal Context:**", "**LCopilot Relevance:**", "**Related Rules/Docs:**"]

        # Find the entry section
        start_line = line_num - 1
        end_line = len(lines)

        # Find the end of this entry (next #### or end of file)
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip().startswith("####"):
                end_line = i
                break

        entry_text = '\n'.join(lines[start_line:end_line])

        # Check for required fields
        for field in required_fields:
            if field not in entry_text:
                return False

        return True

    def _extract_coverage_stats(self, mapping_file: Path) -> Dict[str, int]:
        """Extract coverage statistics from mapping documents."""
        content = mapping_file.read_text(encoding='utf-8')

        # Look for coverage summary
        total_match = re.search(r'\*\*Total (?:Articles|Sections) Mapped:\*\* (\d+)', content)
        implemented_match = re.search(r'\*\*Fully Implemented \(✅\):\*\* (\d+)', content)
        partial_match = re.search(r'\*\*Partially Implemented \(🟡\):\*\* (\d+)', content)

        if total_match:
            return {
                "total_mapped": int(total_match.group(1)),
                "implemented": int(implemented_match.group(1)) if implemented_match else 0,
                "partial": int(partial_match.group(1)) if partial_match else 0
            }

        return {}

    def _validate_markdown_file(self, md_file: Path) -> List[ValidationResult]:
        """Validate individual Markdown file for syntax issues."""
        results = []
        content = md_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Check for required document header
        if not content.startswith('#'):
            results.append(ValidationResult(
                passed=False,
                message="Document should start with a main heading (#)",
                file_path=str(md_file),
                line_number=1
            ))

        # Check for balanced code blocks
        code_block_count = content.count('```')
        if code_block_count % 2 != 0:
            results.append(ValidationResult(
                passed=False,
                message="Unbalanced code blocks (```)",
                file_path=str(md_file)
            ))

        # Check for proper table formatting
        for i, line in enumerate(lines, 1):
            if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                # This looks like a table row, validate basic format
                if not re.match(r'^\|[^|]+(\|[^|]*)*\|$', line.strip()):
                    results.append(ValidationResult(
                        passed=False,
                        message="Malformed table row",
                        file_path=str(md_file),
                        line_number=i
                    ))

        return results

    def run_all_validations(self) -> Tuple[List[ValidationResult], List[ValidationResult]]:
        """Run all validation checks and return errors and warnings."""
        all_errors = []
        all_warnings = []

        # File structure validation
        self.log("Validating file structure...")
        results = self.validate_file_structure()
        all_errors.extend([r for r in results if not r.passed])

        # Cross-reference validation
        self.log("Validating cross-references...")
        results = self.validate_cross_references()
        all_errors.extend([r for r in results if not r.passed])

        # Glossary validation
        self.log("Validating glossary terms...")
        results = self.validate_glossary_terms()
        all_errors.extend([r for r in results if not r.passed])

        # Coverage validation
        self.log("Validating compliance coverage...")
        results = self.validate_compliance_coverage()
        all_errors.extend([r for r in results if not r.passed])

        # Markdown syntax validation
        self.log("Validating Markdown syntax...")
        results = self.validate_markdown_syntax()
        all_errors.extend([r for r in results if not r.passed])

        return all_errors, all_warnings


def main():
    """Main validation script entry point."""
    parser = argparse.ArgumentParser(description="Validate compliance documentation")
    parser.add_argument("--docs-path", default="docs/compliance",
                       help="Path to compliance documentation directory")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--fix", action="store_true",
                       help="Attempt to fix certain validation issues")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")

    args = parser.parse_args()

    # Initialize validator
    validator = ComplianceValidator(args.docs_path, args.verbose)

    # Run validations
    errors, warnings = validator.run_all_validations()

    # Output results
    if args.json:
        result = {
            "errors": [{"message": e.message, "file": e.file_path, "line": e.line_number} for e in errors],
            "warnings": [{"message": w.message, "file": w.file_path, "line": w.line_number} for w in warnings],
            "summary": {
                "total_errors": len(errors),
                "total_warnings": len(warnings),
                "validation_passed": len(errors) == 0
            }
        }
        print(json.dumps(result, indent=2))
    else:
        # Text output
        if errors:
            print(f"\n❌ VALIDATION ERRORS ({len(errors)}):")
            for error in errors:
                location = f"{error.file_path}:{error.line_number}" if error.line_number else error.file_path
                print(f"  • {error.message} ({location})")

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                location = f"{warning.file_path}:{warning.line_number}" if warning.line_number else warning.file_path
                print(f"  • {warning.message} ({location})")

        if not errors and not warnings:
            print("✅ All validations passed!")
        elif not errors:
            print(f"\n✅ Validation passed with {len(warnings)} warnings")
        else:
            print(f"\n❌ Validation failed with {len(errors)} errors and {len(warnings)} warnings")

    # Exit with appropriate code
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()