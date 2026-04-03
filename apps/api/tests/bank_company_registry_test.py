from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.bank_company_registry import is_bank_company, mark_company_as_bank  # noqa: E402


def test_is_bank_company_accepts_explicit_bank_metadata() -> None:
    company = SimpleNamespace(
        name="Trade Operations Ltd",
        legal_name=None,
        event_metadata={"tenant_type": "bank"},
    )

    assert is_bank_company(company) is True


def test_is_bank_company_accepts_legacy_name_signal() -> None:
    company = SimpleNamespace(
        name="SABL Bank",
        legal_name=None,
        event_metadata=None,
    )

    assert is_bank_company(company) is True


def test_mark_company_as_bank_preserves_existing_metadata() -> None:
    company = SimpleNamespace(
        event_metadata={"company_size": "enterprise"},
    )

    mark_company_as_bank(company)

    assert company.event_metadata == {
        "company_size": "enterprise",
        "tenant_type": "bank",
        "company_type": "bank",
        "business_type": "bank",
    }
