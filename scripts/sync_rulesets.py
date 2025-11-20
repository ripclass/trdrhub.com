#!/usr/bin/env python3
"""
Bulk sync normalized rules for one or more rulesets.
"""

import argparse
import sys
from pathlib import Path
from typing import List
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models.ruleset import Ruleset, RulesetStatus  # noqa: E402
from app.services.rules_importer import RulesImporter  # noqa: E402
from app.services.rules_storage import RulesStorageService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync normalized rules from stored rulesets.")
    parser.add_argument("--ruleset-id", type=str, help="Limit sync to a single ruleset ID")
    parser.add_argument("--include-inactive", action="store_true", help="Include draft/archived rulesets")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of rulesets processed")
    return parser.parse_args()


def load_rulesets(session, args: argparse.Namespace) -> List[Ruleset]:
    query = session.query(Ruleset)
    if args.ruleset_id:
        query = query.filter(Ruleset.id == UUID(args.ruleset_id))
    elif not args.include_inactive:
        query = query.filter(Ruleset.status == RulesetStatus.ACTIVE.value)
    if args.limit:
        query = query.limit(args.limit)
    return query.order_by(Ruleset.updated_at.desc()).all()


def main() -> None:
    args = parse_args()
    session = SessionLocal()
    storage = RulesStorageService()
    importer = RulesImporter(session)

    try:
        rulesets = load_rulesets(session, args)
        if not rulesets:
            print("No matching rulesets found.")
            return

        results = []
        for ruleset in rulesets:
            if not ruleset.file_path:
                print(f"Skipping {ruleset.id} (no file path)")
                continue
            blob = storage.get_ruleset_file(ruleset.file_path)
            summary = importer.import_ruleset(
                ruleset=ruleset,
                rules_payload=blob["content"],
                activate=ruleset.status == RulesetStatus.ACTIVE.value,
            )
            results.append((ruleset, summary))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    for ruleset, summary in results:
        data = summary.as_dict()
        print(
            f"{ruleset.domain}/{ruleset.jurisdiction} "
            f"{ruleset.ruleset_version} -> total={data['total_rules']} "
            f"inserted={data['inserted']} updated={data['updated']} skipped={data['skipped']}"
        )


if __name__ == "__main__":
    main()

