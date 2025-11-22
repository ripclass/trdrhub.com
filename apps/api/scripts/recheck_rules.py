"""
Automated Ruleset Integrity Re-Check Script

Validates JSON ruleset files and compares with database state.
Run after editing JSON files or uploading via dashboard.

Usage:
    PYTHONPATH=. python apps/api/scripts/recheck_rules.py
    OR
    make audit-rules
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

# Import audit functions
# Handle both PYTHONPATH=. (from root) and direct execution (from apps/api)
import sys
from pathlib import Path

script_dir = Path(__file__).parent
api_dir = script_dir.parent
project_root = api_dir.parent

# Add api directory to path if not already there
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

try:
    from scripts.audit_rules_integrity import (
        AuditSummary,
        KNOWN_CONDITION_TYPES,
        run_full_audit,
    )
    from app.database import SessionLocal
    from app.models.rule_record import RuleRecord
    from app.models.ruleset import Ruleset, RulesetStatus
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print(f"Script dir: {script_dir}")
    print(f"API dir: {api_dir}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}")
    print("\nMake sure you're running with PYTHONPATH=. from the project root")
    print("OR run from apps/api directory: cd apps/api && python scripts/recheck_rules.py")
    sys.exit(1)

VALID_SEVERITIES = {"fail", "warn", "info"}


class RulesetCheckResult:
    """Result of checking a single ruleset JSON file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.json_rule_count = 0
        self.db_rule_count: Optional[int] = None
        self.db_ruleset: Optional[Ruleset] = None


def validate_json_schema(rules: List[Dict[str, Any]], file_path: Path) -> tuple[bool, List[str]]:
    """
    Validate minimal schema requirements for ruleset JSON.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(rules, list):
        errors.append("Root must be an array")
        return False, errors
    
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"Rule[{idx}]: Must be an object")
            continue
        
        rule_id = rule.get("rule_id", f"rule_{idx}")
        
        # Required fields
        if "rule_id" not in rule or not rule["rule_id"]:
            errors.append(f"Rule[{idx}]: Missing or empty 'rule_id'")
        
        if "severity" not in rule:
            errors.append(f"{rule_id}: Missing 'severity'")
        elif rule.get("severity", "").lower() not in VALID_SEVERITIES:
            errors.append(f"{rule_id}: Invalid severity '{rule.get('severity')}' (must be fail/warn/info)")
        
        if "conditions" not in rule:
            errors.append(f"{rule_id}: Missing 'conditions'")
        elif not isinstance(rule.get("conditions"), list):
            errors.append(f"{rule_id}: 'conditions' must be an array")
        else:
            # Validate condition types
            for cond_idx, condition in enumerate(rule.get("conditions", [])):
                if not isinstance(condition, dict):
                    errors.append(f"{rule_id}: condition[{cond_idx}] is not an object")
                    continue
                
                cond_type = condition.get("type", "")
                if cond_type and cond_type not in KNOWN_CONDITION_TYPES:
                    errors.append(f"{rule_id}: condition[{cond_idx}] has unknown type '{cond_type}'")
        
        if "expected_outcome" not in rule:
            errors.append(f"{rule_id}: Missing 'expected_outcome'")
        elif not isinstance(rule.get("expected_outcome"), dict):
            errors.append(f"{rule_id}: 'expected_outcome' must be an object")
    
    return len(errors) == 0, errors


def extract_ruleset_metadata(file_path: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract domain, rulebook_version, and ruleset_version from filename or JSON.
    
    Returns:
        (domain, rulebook_version, ruleset_version)
    """
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            rules = json.load(f)
        
        if not isinstance(rules, list) or len(rules) == 0:
            return None, None, None
        
        # Try to extract from first rule
        first_rule = rules[0]
        domain = first_rule.get("domain")
        version = first_rule.get("version", "")
        rule_version = first_rule.get("rule_version")
        
        # Parse version string (e.g., "UCP600:2007" -> rulebook_version="UCP600:2007")
        rulebook_version = version
        
        # Try to infer from filename
        filename = file_path.stem
        if "ucp600" in filename.lower():
            domain = domain or "icc.ucp600"
        elif "eucp" in filename.lower():
            domain = domain or "icc.eucp2.1"
        elif "urdg" in filename.lower():
            domain = domain or "icc.urdg758"
        elif "crossdoc" in filename.lower():
            domain = domain or "icc.lcopilot.crossdoc"
        
        return domain, rulebook_version, rule_version
    
    except Exception as e:
        return None, None, None


def check_ruleset_file(file_path: Path, session: Session) -> RulesetCheckResult:
    """Check a single ruleset JSON file."""
    result = RulesetCheckResult(file_path)
    
    try:
        # Load and validate JSON
        with open(file_path, "r", encoding="utf-8-sig") as f:
            rules = json.load(f)
        
        is_valid, errors = validate_json_schema(rules, file_path)
        result.is_valid = is_valid
        result.errors = errors
        result.json_rule_count = len(rules) if isinstance(rules, list) else 0
        
        # Try to find matching DB ruleset
        domain, rulebook_version, ruleset_version = extract_ruleset_metadata(file_path)
        
        if domain:
            # Look for matching ruleset in DB
            query = session.query(Ruleset).filter(Ruleset.domain == domain)
            
            if rulebook_version:
                query = query.filter(Ruleset.rulebook_version == rulebook_version)
            if ruleset_version:
                query = query.filter(Ruleset.ruleset_version == ruleset_version)
            
            db_ruleset = query.first()
            
            if db_ruleset:
                result.db_ruleset = db_ruleset
                result.db_rule_count = (
                    session.query(func.count(RuleRecord.rule_id))
                    .filter(RuleRecord.ruleset_id == db_ruleset.id)
                    .scalar()
                    or 0
                )
                
                # Check for count mismatch
                if result.json_rule_count != result.db_rule_count:
                    result.warnings.append(
                        f"Count mismatch: JSON has {result.json_rule_count} rules, "
                        f"DB has {result.db_rule_count} rules"
                    )
            else:
                result.warnings.append(
                    f"No matching DB ruleset found for domain={domain}, "
                    f"rulebook={rulebook_version}, version={ruleset_version}"
                )
    
    except json.JSONDecodeError as e:
        result.is_valid = False
        result.errors.append(f"Invalid JSON: {e}")
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Error reading file: {e}")
    
    return result


def main() -> None:
    """Main entry point."""
    # Find rulesets directory
    script_dir = Path(__file__).parent
    rulesets_dir = script_dir.parent / "rulesets"
    
    if not rulesets_dir.exists():
        print(f"ERROR: Rulesets directory not found: {rulesets_dir}")
        sys.exit(1)
    
    # Find all JSON files
    json_files = list(rulesets_dir.rglob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {rulesets_dir}")
        sys.exit(0)
    
    print("=" * 80)
    print("RULESET INTEGRITY RE-CHECK")
    print("=" * 80)
    print(f"\nFound {len(json_files)} ruleset file(s) to check\n")
    
    session: Session = SessionLocal()
    results: List[RulesetCheckResult] = []
    
    try:
        # Check each JSON file
        for json_file in sorted(json_files):
            result = check_ruleset_file(json_file, session)
            results.append(result)
            
            # Print per-file results
            relative_path = json_file.relative_to(rulesets_dir.parent)
            domain, rulebook_version, ruleset_version = extract_ruleset_metadata(json_file)
            display_name = f"{domain or 'unknown'} v{ruleset_version or '?'}"
            
            print(f"=== Checking {display_name} ===")
            print(f"File: {relative_path}")
            print(f"Local JSON: {result.json_rule_count} rules")
            
            if result.db_ruleset:
                print(f"DB: {result.db_rule_count} rules (status: {result.db_ruleset.status})")
            else:
                print("DB: No matching ruleset found")
            
            if result.is_valid and not result.warnings:
                print("Integrity: ✓ PASS")
            elif result.is_valid:
                print("Integrity: ⚠ PASS (with warnings)")
                for warning in result.warnings:
                    print(f"  ⚠ {warning}")
            else:
                print("Integrity: ✗ FAIL")
                for error in result.errors[:5]:  # Show first 5 errors
                    print(f"  ✗ {error}")
                if len(result.errors) > 5:
                    print(f"  ... and {len(result.errors) - 5} more errors")
            
            print()
        
        # Run full DB audit
        print("=" * 80)
        print("RUNNING FULL DATABASE AUDIT")
        print("=" * 80)
        
        audit_summary = run_full_audit(session)
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        json_errors = sum(1 for r in results if not r.is_valid)
        json_warnings = sum(len(r.warnings) for r in results)
        total_json_rules = sum(r.json_rule_count for r in results)
        
        print(f"\nJSON Files:")
        print(f"  Total files checked: {len(results)}")
        print(f"  Files with errors: {json_errors}")
        print(f"  Total warnings: {json_warnings}")
        print(f"  Total rules in JSON: {total_json_rules}")
        
        print(f"\nDatabase:")
        print(f"  Total ICC rulesets: {audit_summary.total_icc_rulesets}")
        print(f"  Active ICC rulesets: {audit_summary.active_icc_rulesets}")
        print(f"  Total rules in DB: {audit_summary.total_icc_rules}")
        print(f"  Rulesets with count mismatch: {audit_summary.rulesets_count_mismatch}")
        print(f"  Rules with missing fields: {audit_summary.rules_missing_fields}")
        print(f"  Rules with bad severity/flags: {audit_summary.rules_bad_severity_flags}")
        print(f"  Rules with bad condition types: {audit_summary.rules_bad_condition_types}")
        print(f"  Duplicate rule_ids (within ruleset): {audit_summary.duplicate_rule_ids_within_ruleset}")
        print(f"  Cross-ruleset collisions: {audit_summary.cross_ruleset_collisions}")
        print(f"  Orphan rules: {audit_summary.orphan_rules}")
        
        # Final status
        has_issues = (
            json_errors > 0
            or audit_summary.rulesets_count_mismatch > 0
            or audit_summary.rules_missing_fields > 0
            or audit_summary.rules_bad_severity_flags > 0
            or audit_summary.rules_bad_condition_types > 0
            or audit_summary.duplicate_rule_ids_within_ruleset > 0
            or audit_summary.cross_ruleset_collisions > 0
            or audit_summary.orphan_rules > 0
        )
        
        print("\n" + "=" * 80)
        if has_issues:
            print("✗ ISSUES FOUND - Please review and fix")
            sys.exit(1)
        else:
            print("✓ ALL CHECKS PASSED")
            sys.exit(0)
    
    finally:
        session.close()


if __name__ == "__main__":
    main()

