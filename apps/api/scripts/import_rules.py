#!/usr/bin/env python3
"""
Import rules from JSON file into the rules table.

Usage:
    python scripts/import_rules.py [path_to_rules.json]

If no path is provided, defaults to Data/ucp600.json
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import Json
from app.config import settings


def compute_checksum(rule: Dict[str, Any]) -> str:
    """Compute MD5 checksum for a rule."""
    # Create a normalized representation for checksum
    normalized = json.dumps(rule, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def map_json_to_db(rule_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map JSON rule structure to database schema.
    
    JSON fields -> DB fields:
    - rule_id -> rule_id
    - version -> rule_version
    - article -> article
    - source -> domain (inferred, e.g., "UCP600" -> "icc")
    - title -> title
    - reference -> reference
    - text -> description
    - condition -> conditions (singular to plural)
    - expected_outcome -> expected_outcome
    - tags -> tags
    - deterministic -> deterministic
    - requires_llm -> requires_llm
    - severity -> severity (may need mapping: "high" -> "fail")
    """
    # Map source to domain
    source = rule_json.get("source", "").upper()
    domain_map = {
        "UCP600": "icc",
        "ISBP": "icc",
        "ICC": "icc",
    }
    domain = domain_map.get(source, "icc")
    
    # Map severity: "high" -> "fail", "medium" -> "warn", "low" -> "info"
    severity_map = {
        "high": "fail",
        "medium": "warn",
        "low": "info",
        "fail": "fail",
        "warn": "warn",
        "info": "info",
    }
    severity = severity_map.get(rule_json.get("severity", "fail").lower(), "fail")
    
    # Infer rule_type from deterministic flag
    rule_type = "deterministic" if rule_json.get("deterministic", True) else "semantic"
    
    # Default document_type to "lc" if not specified
    document_type = rule_json.get("document_type", "lc")
    
    # Map condition (singular) to conditions (plural)
    condition = rule_json.get("condition", [])
    conditions = condition if isinstance(condition, list) else [condition]
    
    # Build metadata from extra fields
    metadata = {
        "source": source,
        "examples": rule_json.get("examples", []),
    }
    
    # Compute checksum
    checksum = compute_checksum(rule_json)
    
    return {
        "rule_id": rule_json.get("rule_id"),
        "rule_version": rule_json.get("version"),
        "article": rule_json.get("article"),
        "version": f"{source}:2007" if source == "UCP600" else rule_json.get("version", ""),
        "domain": domain,
        "jurisdiction": rule_json.get("jurisdiction", "global"),
        "document_type": document_type,
        "rule_type": rule_type,
        "severity": severity,
        "deterministic": rule_json.get("deterministic", True),
        "requires_llm": rule_json.get("requires_llm", False),
        "title": rule_json.get("title"),
        "reference": rule_json.get("reference"),
        "description": rule_json.get("text") or rule_json.get("description"),
        "conditions": Json(conditions),
        "expected_outcome": Json(rule_json.get("expected_outcome", {})),
        "tags": Json(rule_json.get("tags", [])),
        "metadata": Json(metadata),
        "checksum": checksum,
    }


def import_rules(json_file_path: str, connection_string: Optional[str] = None):
    """Import rules from JSON file into the rules table."""
    # Use provided connection string or get from settings
    if connection_string:
        conn_str = connection_string
    else:
        # Get DATABASE_URL from settings and convert to psycopg2 format if needed
        conn_str = settings.DATABASE_URL
        # psycopg2.connect() can handle postgresql:// URLs directly
    
    print(f"Connecting to database...")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    print(f"Loading rules from {json_file_path}...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    
    if not isinstance(rules, list):
        raise ValueError("JSON file must contain an array of rules")
    
    print(f"Found {len(rules)} rules to import")
    
    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    for idx, rule_json in enumerate(rules, 1):
        try:
            db_rule = map_json_to_db(rule_json)
            
            # Validate required fields
            if not db_rule["rule_id"]:
                print(f"  Warning: Rule {idx} missing rule_id, skipping")
                error_count += 1
                continue
            
            if not db_rule["title"]:
                print(f"  Warning: Rule {db_rule['rule_id']} missing title, skipping")
                error_count += 1
                continue
            
            # Insert or update
            cur.execute("""
                insert into rules (
                    rule_id, rule_version, article, version,
                    domain, jurisdiction, document_type, rule_type,
                    severity, deterministic, requires_llm,
                    title, reference, description,
                    conditions, expected_outcome, tags,
                    metadata, checksum
                )
                values (
                    %(rule_id)s, %(rule_version)s, %(article)s, %(version)s,
                    %(domain)s, %(jurisdiction)s, %(document_type)s, %(rule_type)s,
                    %(severity)s, %(deterministic)s, %(requires_llm)s,
                    %(title)s, %(reference)s, %(description)s,
                    %(conditions)s, %(expected_outcome)s, %(tags)s,
                    %(metadata)s, %(checksum)s
                )
                on conflict (rule_id)
                do update set
                    rule_version = excluded.rule_version,
                    article = excluded.article,
                    version = excluded.version,
                    domain = excluded.domain,
                    jurisdiction = excluded.jurisdiction,
                    document_type = excluded.document_type,
                    rule_type = excluded.rule_type,
                    severity = excluded.severity,
                    deterministic = excluded.deterministic,
                    requires_llm = excluded.requires_llm,
                    title = excluded.title,
                    reference = excluded.reference,
                    description = excluded.description,
                    conditions = excluded.conditions,
                    expected_outcome = excluded.expected_outcome,
                    tags = excluded.tags,
                    metadata = excluded.metadata,
                    checksum = excluded.checksum,
                    updated_at = now()
                returning rule_id, (xmax = 0) as inserted
            """, db_rule)
            
            result = cur.fetchone()
            if result and result[1]:  # inserted flag
                inserted_count += 1
            else:
                updated_count += 1
            
            if idx % 50 == 0:
                print(f"  Processed {idx}/{len(rules)} rules...")
                
        except Exception as e:
            print(f"  Error importing rule {idx} ({rule_json.get('rule_id', 'unknown')}): {e}")
            error_count += 1
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\nImport complete!")
    print(f"  Inserted: {inserted_count}")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(rules)}")


if __name__ == "__main__":
    # Default to Data/ucp600.json if no argument provided
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Default path relative to project root
        project_root = Path(__file__).parent.parent.parent
        json_file = project_root / "Data" / "ucp600.json"
    
    if not Path(json_file).exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    import_rules(str(json_file))

