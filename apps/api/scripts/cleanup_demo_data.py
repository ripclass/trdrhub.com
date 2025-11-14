"""
Utility to purge known demo/test data from production databases.

Usage:
    python cleanup_demo_data.py --pattern "%@demo.trdrhub.com" --pattern "test+%@trdrhub.com" --apply
"""
import argparse
import os
from typing import List

from sqlalchemy import create_engine, text


def build_filters(patterns: List[str]) -> str:
    clauses = [f"email ILIKE '{pattern}'" for pattern in patterns]
    return " OR ".join(clauses)


def cleanup(patterns: List[str], apply: bool = False) -> None:
    if not patterns:
        raise SystemExit("At least one --pattern is required to identify demo data")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL environment variable is required")

    email_clause = build_filters(patterns)
    statements = [
        f"DELETE FROM validation_sessions WHERE user_id IN (SELECT id FROM users WHERE {email_clause});",
        f"DELETE FROM users WHERE {email_clause};",
        f"DELETE FROM companies WHERE contact_email ILIKE ANY(ARRAY[{', '.join([f\"'{p}'\" for p in patterns])}]);",
        f"DELETE FROM system_alerts WHERE metadata->>'demo' = 'true';",
    ]

    if not apply:
        print("Dry run - the following SQL statements would be executed:\n")
        for stmt in statements:
            print(stmt)
        print("\nRe-run with --apply to execute.")
        return

    engine = create_engine(database_url)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print("Demo data cleanup complete.")


def main():
    parser = argparse.ArgumentParser(description="Cleanup demo/test data from the database.")
    parser.add_argument("--pattern", action="append", help="SQL ILIKE pattern for emails to delete", required=True)
    parser.add_argument("--apply", action="store_true", help="Execute deletion instead of printing SQL")
    args = parser.parse_args()
    cleanup(args.pattern, apply=args.apply)


if __name__ == "__main__":
    main()

