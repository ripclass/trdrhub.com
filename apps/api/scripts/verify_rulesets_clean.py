"""
Verify that all ruleset JSON files are properly cleaned.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

VALID_SEVERITIES = {"fail", "warn", "info"}
VALID_CONDITION_TYPES = {
    "enum_value",
    "field_presence",
    "doc_required",
    "equality_match",
    "consistency_check",
    "date_order",
    "numeric_range",
    "time_constraint",
}


def verify_ruleset_file(file_path: Path) -> tuple[bool, List[str]]:
    """Verify a single ruleset file."""
    errors = []
    
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            rules = json.load(f)
        
        if not isinstance(rules, list):
            errors.append(f"Expected array, got {type(rules)}")
            return False, errors
        
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"Rule {idx}: Not a dict")
                continue
            
            rule_id = rule.get("rule_id", f"rule_{idx}")
            
            # Check severity
            severity = rule.get("severity", "").lower()
            if severity not in VALID_SEVERITIES:
                errors.append(f"{rule_id}: Invalid severity '{rule.get('severity')}' (must be fail/warn/info)")
            
            # Check conditions
            conditions = rule.get("conditions", [])
            if not isinstance(conditions, list):
                errors.append(f"{rule_id}: conditions must be an array")
                continue
            
            for cond_idx, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    errors.append(f"{rule_id}: condition[{cond_idx}] is not a dict")
                    continue
                
                cond_type = condition.get("type", "")
                if cond_type not in VALID_CONDITION_TYPES:
                    errors.append(f"{rule_id}: condition[{cond_idx}] has invalid type '{cond_type}'")
            
            # Check that notes exists if conditions are empty
            if len(conditions) == 0:
                notes = rule.get("notes", [])
                if not isinstance(notes, list):
                    errors.append(f"{rule_id}: notes must be an array when conditions are empty")
        
        return len(errors) == 0, errors
    
    except Exception as e:
        return False, [f"Error reading file: {e}"]


def main():
    """Main entry point."""
    rulesets_dir = Path(__file__).parent.parent / "rulesets"
    
    if not rulesets_dir.exists():
        print(f"ERROR: Rulesets directory not found: {rulesets_dir}")
        return
    
    json_files = list(rulesets_dir.rglob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {rulesets_dir}")
        return
    
    print(f"Verifying {len(json_files)} ruleset files...\n")
    
    all_valid = True
    for json_file in sorted(json_files):
        is_valid, errors = verify_ruleset_file(json_file)
        status = "✓" if is_valid else "✗"
        print(f"{status} {json_file.name}")
        
        if errors:
            all_valid = False
            for error in errors[:5]:  # Show first 5 errors
                print(f"    - {error}")
            if len(errors) > 5:
                print(f"    ... and {len(errors) - 5} more errors")
    
    print()
    if all_valid:
        print("✓ All rulesets are properly cleaned!")
    else:
        print("✗ Some rulesets have issues")


if __name__ == "__main__":
    main()

