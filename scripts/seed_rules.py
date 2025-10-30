import sys
from pathlib import Path


# Ensure apps/api is on sys.path for "app.*" imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.rules import Rule  # noqa: E402


def main() -> None:
    rules = [
        {
            "code": "UCP600-14(a)",
            "title": "Consistency of Data",
            "description": "All documents must be consistent with the LC terms.",
            "condition": {"field": "consistency", "operator": "equals", "value": True},
            "expected_outcome": {"message": "All data consistent with LC"},
            "domain": "icc",
            "document_type": "lc",
        },
        {
            "code": "ISBP745-23",
            "title": "Date Format",
            "description": "Dates must follow the format DD/MM/YYYY.",
            "condition": {"field": "date_format", "operator": "matches", "value": "^\\d{2}/\\d{2}/\\d{4}$"},
            "expected_outcome": {"message": "Valid date format"},
            "domain": "icc",
            "document_type": "invoice",
        },
    ]

    db = SessionLocal()
    try:
        for r in rules:
            db.add(Rule(**r))
        db.commit()
        print("✅  Rules seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()


