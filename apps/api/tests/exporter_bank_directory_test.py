from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.exporter_bank_directory import list_exporter_available_banks  # noqa: E402


def test_list_exporter_available_banks_returns_safe_directory_payload() -> None:
    active_counts_subquery = SimpleNamespace(
        c=SimpleNamespace(
            company_id=object(),
            active_user_count=object(),
        )
    )

    active_counts_query = MagicMock()
    active_counts_query.filter.return_value = active_counts_query
    active_counts_query.group_by.return_value = active_counts_query
    active_counts_query.subquery.return_value = active_counts_subquery

    first_bank_id = uuid4()
    second_bank_id = uuid4()
    company_rows = [
        (
            SimpleNamespace(
                id=first_bank_id,
                name="Eastern Bank PLC",
                legal_name="Eastern Bank PLC",
                country="BD",
                regulator_id="EAST-01",
            ),
            3,
        ),
        (
            SimpleNamespace(
                id=second_bank_id,
                name="Dutch-Bangla Bank PLC",
                legal_name=None,
                country="BD",
                regulator_id=None,
            ),
            1,
        ),
    ]

    companies_query = MagicMock()
    companies_query.join.return_value = companies_query
    companies_query.filter.return_value = companies_query
    companies_query.order_by.return_value = companies_query
    companies_query.all.return_value = company_rows

    fallback_query = MagicMock()
    fallback_query.filter.return_value = fallback_query
    fallback_query.order_by.return_value = fallback_query
    fallback_query.all.return_value = []

    db = MagicMock()
    db.query.side_effect = [active_counts_query, companies_query, fallback_query]

    response = list_exporter_available_banks(db)

    assert response["total"] == 2
    assert [item["name"] for item in response["items"]] == [
        "Eastern Bank PLC",
        "Dutch-Bangla Bank PLC",
    ]
    assert response["items"][0]["id"] == first_bank_id
    assert response["items"][0]["active_user_count"] == 3
    assert response["items"][1]["id"] == second_bank_id
    assert response["items"][1]["active_user_count"] == 1


def test_list_exporter_available_banks_falls_back_to_explicit_bank_companies() -> None:
    active_counts_subquery = SimpleNamespace(
        c=SimpleNamespace(
            company_id=object(),
            active_user_count=object(),
        )
    )

    active_counts_query = MagicMock()
    active_counts_query.filter.return_value = active_counts_query
    active_counts_query.group_by.return_value = active_counts_query
    active_counts_query.subquery.return_value = active_counts_subquery

    companies_query = MagicMock()
    companies_query.join.return_value = companies_query
    companies_query.filter.return_value = companies_query
    companies_query.order_by.return_value = companies_query
    companies_query.all.return_value = []

    fallback_bank_id = uuid4()
    fallback_query = MagicMock()
    fallback_query.filter.return_value = fallback_query
    fallback_query.order_by.return_value = fallback_query
    fallback_query.all.return_value = [
        SimpleNamespace(
            id=fallback_bank_id,
            name="SABL Bank",
            legal_name=None,
            country="BD",
            regulator_id=None,
            event_metadata=None,
        ),
        SimpleNamespace(
            id=uuid4(),
            name="IEC Trading",
            legal_name=None,
            country="BD",
            regulator_id=None,
            event_metadata=None,
        ),
    ]

    db = MagicMock()
    db.query.side_effect = [active_counts_query, companies_query, fallback_query]

    response = list_exporter_available_banks(db)

    assert response == {
        "items": [
            {
                "id": fallback_bank_id,
                "name": "SABL Bank",
                "legal_name": None,
                "country": "BD",
                "regulator_id": None,
                "active_user_count": 0,
            }
        ],
        "total": 1,
    }
