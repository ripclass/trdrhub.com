"""Validate rewritten rulesets meet strict requirements."""

import json
from pathlib import Path

VALID_CONDITION_TYPES = {
    "enum_value",
    "field_presence",
    "equality_match",
    "consistency_check",
    "numeric_range",
    "date_order",
    "time_constraint",
    "doc_required",
}


def validate_ruleset(filepath: Path) -> tuple[bool, list[str]]:
    """Validate a ruleset file."""
    errors = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        rules = json.load(f)
    
    if not isinstance(rules, list):
        errors.append("File does not contain a list of rules")
        return False, errors
    
    for rule in rules:
        rule_id = rule.get("rule_id", "unknown")
        
        # Check required fields
        if not rule.get("rule_id"):
            errors.append(f"Rule missing rule_id")
            continue
        
        # Check conditions
        conditions = rule.get("conditions", [])
        
        if not conditions:
            errors.append(f"Rule {rule_id} has empty conditions array (violates requirement)")
            continue
        
        if not isinstance(conditions, list):
            errors.append(f"Rule {rule_id} has invalid conditions (not a list)")
            continue
        
        # Check each condition
        for idx, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                errors.append(f"Rule {rule_id} condition[{idx}] is not an object")
                continue
            
            cond_type = condition.get("type", "")
            if not cond_type:
                errors.append(f"Rule {rule_id} condition[{idx}] missing 'type'")
                continue
            
            if cond_type not in VALID_CONDITION_TYPES:
                errors.append(f"Rule {rule_id} condition[{idx}] has invalid type '{cond_type}'")
    
    return len(errors) == 0, errors


def main():
    """Main entry point."""
    rulesets_dir = Path(__file__).parent.parent / "rulesets"
    
    urdg_file = rulesets_dir / "icc.urdg758" / "urdg758-v1.0.0.json"
    eucp_file = rulesets_dir / "icc.eucp2.1" / "eucp2.1-v1.0.0.json"
    
    print("=" * 80)
    print("VALIDATING REWRITTEN RULESETS")
    print("=" * 80)
    print()
    
    all_valid = True
    
    for filepath, name in [(urdg_file, "URDG758"), (eucp_file, "eUCP")]:
        print(f"Validating {name}...")
        if not filepath.exists():
            print(f"  ✗ File not found: {filepath}")
            all_valid = False
            continue
        
        valid, errors = validate_ruleset(filepath)
        
        if valid:
            with open(filepath, "r", encoding="utf-8") as f:
                rules = json.load(f)
            print(f"  ✓ Valid ({len(rules)} rules)")
        else:
            print(f"  ✗ Invalid:")
            for error in errors:
                print(f"    - {error}")
            all_valid = False
        print()
    
    print("=" * 80)
    if all_valid:
        print("✓ ALL RULESETS VALID")
    else:
        print("✗ VALIDATION FAILED")
    print("=" * 80)


if __name__ == "__main__":
    main()

