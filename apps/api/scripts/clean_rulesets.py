"""
Clean ICC ruleset JSON files:
- Fix severity: "warning" -> "warn"
- Remove invalid condition types
- Extract narrative text to notes[]
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Valid condition types from RuleEvaluator
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

# Narrative keywords that indicate non-programmatic conditions
NARRATIVE_KEYWORDS = [
    "liability",
    "force majeure",
    "disclaimer",
    "definition",
    "definitions",
    "scope",
    "timeline",
    "bank responsibility",
    "responsibility",
    "obligation",
    "right",
    "rights",
    "exclusion",
    "exclusions",
]


def extract_narrative_text(condition: Dict[str, Any]) -> str:
    """Extract human-readable text from a condition for notes."""
    narrative_parts = []
    
    # Common text fields that might contain narrative
    text_fields = ["description", "message", "text", "note", "explanation", "comment"]
    for field in text_fields:
        if field in condition and isinstance(condition[field], str):
            narrative_parts.append(condition[field])
    
    # If condition type suggests narrative content
    cond_type = condition.get("type", "").lower()
    if any(keyword in cond_type for keyword in NARRATIVE_KEYWORDS):
        narrative_parts.append(f"Condition type: {cond_type}")
    
    # Extract any string values that look like narrative
    for key, value in condition.items():
        if isinstance(value, str) and len(value) > 50:  # Likely narrative if long
            if key not in text_fields:
                narrative_parts.append(f"{key}: {value[:200]}")  # Truncate long text
    
    return " | ".join(narrative_parts) if narrative_parts else ""


def is_narrative_condition(condition: Dict[str, Any]) -> bool:
    """Check if a condition is narrative-only and not programmatically evaluable."""
    cond_type = condition.get("type", "").lower()
    
    # Check if type contains narrative keywords
    if any(keyword in cond_type for keyword in NARRATIVE_KEYWORDS):
        return True
    
    # Check if condition lacks evaluable fields
    evaluable_fields = ["field", "path", "left_path", "right_path", "operator", "value", "allowed_values", "disallowed_values"]
    has_evaluable = any(field in condition for field in evaluable_fields)
    
    # If it's a valid type but has no evaluable fields, it might be narrative
    if cond_type in VALID_CONDITION_TYPES and not has_evaluable:
        return False  # Valid type, keep it even if empty
    
    # If type is invalid and has no evaluable fields, it's narrative
    if cond_type not in VALID_CONDITION_TYPES and not has_evaluable:
        return True
    
    return False


def clean_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Clean a single rule."""
    # Fix severity
    severity = rule.get("severity", "").lower()
    if severity == "warning":
        rule["severity"] = "warn"
    
    # Ensure notes array exists
    if "notes" not in rule:
        rule["notes"] = []
    elif not isinstance(rule["notes"], list):
        rule["notes"] = []
    
    # Process conditions
    conditions = rule.get("conditions", [])
    if not isinstance(conditions, list):
        conditions = []
    
    valid_conditions = []
    removed_narratives = []
    
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        
        cond_type = condition.get("type", "")
        
        # Check if condition type is valid
        if cond_type in VALID_CONDITION_TYPES:
            # Check if it's actually narrative despite valid type
            if is_narrative_condition(condition):
                narrative = extract_narrative_text(condition)
                if narrative:
                    removed_narratives.append(narrative)
            else:
                valid_conditions.append(condition)
        else:
            # Invalid type - extract narrative and remove
            narrative = extract_narrative_text(condition)
            if narrative:
                removed_narratives.append(narrative)
    
    # Update conditions
    rule["conditions"] = valid_conditions
    
    # Add removed narratives to notes
    if removed_narratives:
        rule["notes"].extend(removed_narratives)
        # Remove duplicates while preserving order
        seen = set()
        unique_notes = []
        for note in rule["notes"]:
            if note not in seen:
                seen.add(note)
                unique_notes.append(note)
        rule["notes"] = unique_notes
    
    return rule


def clean_ruleset_file(file_path: Path) -> None:
    """Clean a single ruleset JSON file."""
    print(f"Processing: {file_path}")
    
    try:
        # Try utf-8-sig first (handles BOM), fallback to utf-8
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                rules = json.load(f)
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
        
        if not isinstance(rules, list):
            print(f"  ERROR: Expected array, got {type(rules)}")
            return
        
        original_count = len(rules)
        cleaned_rules = []
        severity_fixes = 0
        conditions_removed = 0
        rules_with_zero_conditions = 0
        
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            
            original_severity = rule.get("severity", "")
            original_condition_count = len(rule.get("conditions", []))
            
            cleaned_rule = clean_rule(rule.copy())
            
            if original_severity.lower() == "warning":
                severity_fixes += 1
            
            removed_count = original_condition_count - len(cleaned_rule.get("conditions", []))
            conditions_removed += removed_count
            
            if len(cleaned_rule.get("conditions", [])) == 0:
                rules_with_zero_conditions += 1
            
            cleaned_rules.append(cleaned_rule)
        
        # Write cleaned rules back
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_rules, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Processed {original_count} rules")
        print(f"  ✓ Fixed {severity_fixes} severity values")
        print(f"  ✓ Removed {conditions_removed} invalid/narrative conditions")
        print(f"  ✓ {rules_with_zero_conditions} rules now have zero conditions (kept with notes)")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    rulesets_dir = Path(__file__).parent.parent / "rulesets"
    
    if not rulesets_dir.exists():
        print(f"ERROR: Rulesets directory not found: {rulesets_dir}")
        sys.exit(1)
    
    # Find all JSON files in rulesets directory
    json_files = list(rulesets_dir.rglob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {rulesets_dir}")
        sys.exit(1)
    
    print(f"Found {len(json_files)} ruleset files to process\n")
    
    for json_file in sorted(json_files):
        clean_ruleset_file(json_file)
        print()
    
    print("✓ All rulesets cleaned successfully!")


if __name__ == "__main__":
    main()

