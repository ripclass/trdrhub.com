"""
Rewrite URDG758 and eUCP rulesets with strict deterministic condition requirements.

Rules:
1. Every rule MUST have at least one deterministic, machine-checkable condition
2. If no deterministic condition: remove rule OR move narrative to notes (no conditions=[])
3. No rule may contain "conditions": []
4. No rule may have custom or narrative condition types
5. Every rule must validate cleanly under RuleRecord model
"""

import json
from pathlib import Path
from typing import Any, Dict, List

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


def has_valid_conditions(rule: Dict[str, Any]) -> bool:
    """Check if rule has at least one valid deterministic condition."""
    conditions = rule.get("conditions", [])
    if not conditions:
        return False
    
    for condition in conditions:
        if isinstance(condition, dict):
            cond_type = condition.get("type", "")
            if cond_type in VALID_CONDITION_TYPES:
                return True
    return False


def filter_valid_conditions(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter conditions to only include valid deterministic types."""
    valid_conditions = []
    for condition in conditions:
        if isinstance(condition, dict):
            cond_type = condition.get("type", "")
            if cond_type in VALID_CONDITION_TYPES:
                valid_conditions.append(condition)
    return valid_conditions


def extract_narrative_to_notes(rule: Dict[str, Any]) -> List[str]:
    """Extract narrative text from rule into notes array."""
    notes = rule.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    
    # Extract from description
    if rule.get("description"):
        notes.append(f"rule: {rule['description']}")
    
    # Extract from expected_outcome
    expected = rule.get("expected_outcome", {})
    if isinstance(expected, dict):
        for key in ["valid", "invalid"]:
            if key in expected:
                items = expected[key]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str):
                            notes.append(f"expected_{key}: {item}")
    
    # Extract from examples
    examples = rule.get("examples", [])
    if isinstance(examples, list):
        for example in examples:
            if isinstance(example, dict):
                for key in ["valid", "invalid"]:
                    if key in example:
                        items = example[key]
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, str):
                                    notes.append(f"example_{key}: {item}")
    
    # Extract from sub_articles if present
    sub_articles = rule.get("sub_articles", {})
    if isinstance(sub_articles, dict):
        for sub_key, sub_data in sub_articles.items():
            if isinstance(sub_data, dict):
                if sub_data.get("summary"):
                    notes.append(f"sub_article_{sub_key}: {sub_data['summary']}")
                if sub_data.get("key_points"):
                    for point in sub_data["key_points"]:
                        if isinstance(point, str):
                            notes.append(f"sub_article_{sub_key}_point: {point}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_notes = []
    for note in notes:
        if note not in seen:
            seen.add(note)
            unique_notes.append(note)
    
    return unique_notes


def process_rule(rule: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Process a single rule according to strict requirements.
    Returns None if rule should be removed, otherwise returns cleaned rule.
    """
    # Get current conditions
    conditions = rule.get("conditions", [])
    
    # Filter to only valid condition types
    valid_conditions = filter_valid_conditions(conditions)
    
    # If no valid conditions, remove the rule entirely
    if not valid_conditions:
        return None
    
    # Create cleaned rule
    cleaned_rule = {
        "rule_id": rule.get("rule_id"),
        "rule_version": rule.get("rule_version", "1.0"),
        "domain": rule.get("domain", "icc"),
        "jurisdiction": rule.get("jurisdiction", "global"),
        "document_type": rule.get("document_type", "lc"),
        "version": rule.get("version"),
        "article": rule.get("article"),
        "title": rule.get("title"),
        "reference": rule.get("reference"),
        "description": rule.get("description"),
        "conditions": valid_conditions,  # Only valid deterministic conditions
        "expected_outcome": rule.get("expected_outcome", {}),
        "tags": rule.get("tags", []),
        "severity": rule.get("severity", "fail"),
        "deterministic": rule.get("deterministic", True),
        "requires_llm": rule.get("requires_llm", False),
        "metadata": rule.get("metadata", {}),
    }
    
    # Add notes (preserve existing + extract narrative)
    existing_notes = rule.get("notes", [])
    if not isinstance(existing_notes, list):
        existing_notes = []
    
    # Extract narrative from removed conditions and other fields
    narrative_notes = extract_narrative_to_notes(rule)
    
    # Combine and deduplicate
    all_notes = existing_notes + narrative_notes
    seen = set()
    unique_notes = []
    for note in all_notes:
        if note not in seen:
            seen.add(note)
            unique_notes.append(note)
    
    cleaned_rule["notes"] = unique_notes
    
    # Ensure required fields
    if not cleaned_rule.get("rule_id"):
        return None
    
    return cleaned_rule


def process_ruleset_file(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """Process a ruleset JSON file and write cleaned version."""
    print(f"Processing: {input_path}")
    
    # Read file
    with open(input_path, "r", encoding="utf-8-sig") as f:
        rules = json.load(f)
    
    if not isinstance(rules, list):
        raise ValueError(f"Expected list of rules, got {type(rules)}")
    
    original_count = len(rules)
    print(f"  Original rules: {original_count}")
    
    # Process each rule
    cleaned_rules = []
    removed_count = 0
    
    for rule in rules:
        cleaned = process_rule(rule)
        if cleaned:
            cleaned_rules.append(cleaned)
        else:
            removed_count += 1
            print(f"  Removed rule: {rule.get('rule_id', 'unknown')} (no valid conditions)")
    
    print(f"  Cleaned rules: {len(cleaned_rules)}")
    print(f"  Removed rules: {removed_count}")
    
    # Validate: no rule should have empty conditions
    for rule in cleaned_rules:
        conditions = rule.get("conditions", [])
        if not conditions:
            raise ValueError(f"Rule {rule.get('rule_id')} has empty conditions array!")
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_rules, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Written to: {output_path}")
    
    return {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "original_count": original_count,
        "cleaned_count": len(cleaned_rules),
        "removed_count": removed_count,
    }


def main():
    """Main entry point."""
    rulesets_dir = Path(__file__).parent.parent / "rulesets"
    
    # Process URDG758
    urdg_input = rulesets_dir / "icc.urdg758" / "urdg758-v1.0.0.json"
    urdg_output = rulesets_dir / "icc.urdg758" / "urdg758-v1.0.0.json"
    
    # Process eUCP
    eucp_input = rulesets_dir / "icc.eucp2.1" / "eucp2.1-v1.0.0.json"
    eucp_output = rulesets_dir / "icc.eucp2.1" / "eucp2.1-v1.0.0.json"
    
    print("=" * 80)
    print("REWRITING RULESETS WITH STRICT DETERMINISTIC CONDITIONS")
    print("=" * 80)
    print()
    
    results = []
    
    if urdg_input.exists():
        result = process_ruleset_file(urdg_input, urdg_output)
        results.append(result)
        print()
    else:
        print(f"⚠ URDG758 file not found: {urdg_input}")
    
    if eucp_input.exists():
        result = process_ruleset_file(eucp_input, eucp_output)
        results.append(result)
        print()
    else:
        print(f"⚠ eUCP file not found: {eucp_input}")
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for result in results:
        print(f"\n{Path(result['input_file']).name}:")
        print(f"  Original: {result['original_count']} rules")
        print(f"  Cleaned: {result['cleaned_count']} rules")
        print(f"  Removed: {result['removed_count']} rules")
    
    print("\n✓ All rulesets processed!")


if __name__ == "__main__":
    main()

