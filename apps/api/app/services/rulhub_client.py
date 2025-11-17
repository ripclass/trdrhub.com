import os
import logging
from typing import Any, Dict, List

import requests

from app.database import SessionLocal
from app.models.rules import Rule


def fetch_rules_from_rulhub(document_type: str) -> List[Dict[str, Any]]:
    base = os.getenv("RULHUB_API_URL", "")
    key = os.getenv("RULHUB_API_KEY", "")
    if not base:
        raise RuntimeError("RULHUB_API_URL not configured")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    resp = requests.get(
        f"{base}/rules",
        params={"document_type": document_type},
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    # Expect list of rule dicts compatible with Rule model
    return data


def sync_rules_from_rulhub() -> None:
    """Full sync for common document types."""
    session = SessionLocal()
    try:
        for dtype in ["lc", "invoice", "bol", "packing_list", "certificate_of_origin", "insurance_certificate", "inspection_certificate"]:
            rules = fetch_rules_from_rulhub(dtype)
            for r in rules:
                existing = session.query(Rule).filter(Rule.code == r.get("code")).first()
                if existing:
                    for k, v in r.items():
                        setattr(existing, k, v)
                else:
                    session.add(Rule(**r))
        session.commit()
        logging.info("✅  RulHub sync complete.")
    except Exception as e:  # noqa: BLE001
        session.rollback()
        logging.error(f"❌ RulHub sync failed: {e}")
    finally:
        session.close()


