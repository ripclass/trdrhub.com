#!/usr/bin/env python3
"""
Bootstrap a SQLite (or Postgres) test database using Alembic migrations.

Usage:
    python scripts/bootstrap_test_db.py --database sqlite:///./test_lcopilot.db

If --database is omitted the script will look for DATABASE_URL or fall back to
``sqlite:///./test_lcopilot.db`` relative to apps/api.
"""

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def build_alembic_config(database_url: str) -> Config:
    """Create an Alembic Config wired to the provided URL."""
    api_dir = Path(__file__).resolve().parents[1]
    config = Config(str(api_dir / "alembic.ini"))
    config.set_main_option("script_location", str(api_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def bootstrap(database_url: str, target: str) -> None:
    config = build_alembic_config(database_url)
    command.upgrade(config, target)
    print(f"✅ Database upgraded to {target} ({database_url})")


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap test database via Alembic")
    parser.add_argument(
        "--database",
        dest="database_url",
        default=None,
        help="SQLAlchemy database URL (defaults to DATABASE_URL env or sqlite test db)",
    )
    parser.add_argument(
        "--target",
        dest="target",
        default="heads",
        help="Alembic revision target (default: heads)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    database_url = (
        args.database_url
        or os.getenv("DATABASE_URL")
        or f"sqlite:///{Path(__file__).resolve().parents[1] / 'test_lcopilot.db'}"
    )
    bootstrap(database_url, args.target)


if __name__ == "__main__":
    main()

