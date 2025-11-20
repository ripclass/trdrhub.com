#!/usr/bin/env python3
"""
Import rules into the normalized governance table using the shared RulesImporter service.
"""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.ruleset import Ruleset, RulesetStatus  # noqa: E402
from app.services.rules_importer import RulesImporter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized trade rules from JSON.")
    parser.add_argument(
        "rules_path",
        nargs="?",
        default=str(Path(__file__).parent.parent / "Data" / "ucp600.json"),
        help="Path to the rules JSON payload (default: Data/ucp600.json)",
    )
    parser.add_argument("--ruleset-id", type=str, help="Existing ruleset ID to associate with the import")
    parser.add_argument("--domain", default="icc", help="Domain fallback when no ruleset is provided")
    parser.add_argument("--jurisdiction", default="global", help="Jurisdiction fallback when no ruleset is provided")
    parser.add_argument("--ruleset-version", default="cli-import", help="Ruleset version label for detached imports")
    parser.add_argument("--rulebook-version", default="unversioned", help="Rulebook version label for detached imports")
    parser.add_argument("--activate", action="store_true", help="Mark imported rules as active")
    return parser.parse_args()


def resolve_ruleset(session, args: argparse.Namespace):
    if args.ruleset_id:
        ruleset = session.query(Ruleset).filter(Ruleset.id == UUID(args.ruleset_id)).first()
        if not ruleset:
            raise ValueError(f"Ruleset {args.ruleset_id} not found")
        return ruleset

    status = RulesetStatus.ACTIVE.value if args.activate else RulesetStatus.DRAFT.value
    return SimpleNamespace(
        id=None,
        domain=args.domain,
        jurisdiction=args.jurisdiction,
        ruleset_version=args.ruleset_version,
        rulebook_version=args.rulebook_version,
        status=status,
    )


def main() -> None:
    args = parse_args()
    rules_path = Path(args.rules_path).resolve()
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    with rules_path.open("r", encoding="utf-8") as handle:
        payload: List[dict] = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Rules file must contain an array of rule objects")

    session = SessionLocal()
    try:
        ruleset = resolve_ruleset(session, args)
        importer = RulesImporter(session)
        summary = importer.import_ruleset(
            ruleset=ruleset,
            rules_payload=payload,
            activate=args.activate,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    data = summary.as_dict()
    print("Rules import complete:")
    print(f"  Total:    {data['total_rules']}")
    print(f"  Inserted: {data['inserted']}")
    print(f"  Updated:  {data['updated']}")
    print(f"  Skipped:  {data['skipped']}")
    if data["warnings"]:
        print(f"  Warnings: {len(data['warnings'])}")
    if data["errors"]:
        print(f"  Errors:   {len(data['errors'])}")


if __name__ == "__main__":
    main()

