"""Snapshot serializer type preservation tests.

``pipeline_runner._jsonable`` is the function that writes ``_setup_snapshot``
into ``validation_session.extracted_data`` during extract_only, and whose
output is read back verbatim by ``_reconstruct_setup_state`` on resume.  The
old implementation fell through to ``str(value)`` for anything non-primitive,
which meant ``Decimal('12345.67')`` became the literal string
``"Decimal('12345.67')"`` after round trip — crashing downstream code that
expected a numeric type.  These tests lock in the type-preserving behaviour
so that regression cannot happen again.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from app.routers.validation.pipeline_runner import _jsonable, _snapshot_setup_state


class _Color(Enum):
    RED = "red"
    BLUE = "blue"


def test_decimal_round_trips_as_float() -> None:
    snap = _jsonable({"amount": Decimal("36450.00")})
    assert snap == {"amount": 36450.0}
    reloaded = json.loads(json.dumps(snap))
    assert isinstance(reloaded["amount"], float)
    assert reloaded["amount"] == 36450.0


def test_decimal_european_format_preserved() -> None:
    # Regression: the old serializer produced "Decimal('36450.00')" which
    # looks innocuous until downstream float() on the string crashes.
    snap = _jsonable({"amount": Decimal("36450.00")})
    assert isinstance(snap["amount"], float)
    assert snap["amount"] != "Decimal('36450.00')"


def test_date_and_datetime_round_trip_as_iso() -> None:
    snap = _jsonable(
        {
            "issue_date": date(2026, 4, 15),
            "expiry_date": date(2026, 10, 15),
            "timestamp": datetime(2026, 4, 9, 18, 30, 0),
        }
    )
    assert snap == {
        "issue_date": "2026-04-15",
        "expiry_date": "2026-10-15",
        "timestamp": "2026-04-09T18:30:00",
    }
    reloaded = json.loads(json.dumps(snap))
    assert isinstance(reloaded["issue_date"], str)
    assert reloaded["issue_date"] == "2026-04-15"


def test_enum_unwraps_to_value() -> None:
    snap = _jsonable({"status": _Color.RED})
    assert snap == {"status": "red"}


def test_bytes_decoded_as_utf8_string() -> None:
    snap = _jsonable({"payload": b"hello world"})
    assert snap == {"payload": "hello world"}


def test_non_utf8_bytes_become_none() -> None:
    # Truncated multibyte sequence — must not raise, must not become a str
    # repr like "b'\\xff\\xfe'".
    snap = _jsonable({"payload": b"\xff\xfe"})
    assert snap == {"payload": None}


def test_nested_dict_preserves_types() -> None:
    snap = _jsonable(
        {
            "lc_context": {
                "lc_number": "EXP2026BD001",
                "amount": Decimal("250000.00"),
                "currency": "USD",
                "issue_date": date(2026, 4, 15),
            },
            "extracted_context": {
                "documents": [
                    {"id": "doc1", "amount_raw": Decimal("35000")},
                    {"id": "doc2", "amount_raw": Decimal("15000")},
                ]
            },
        }
    )
    lc = snap["lc_context"]
    assert isinstance(lc["amount"], float)
    assert lc["amount"] == 250000.0
    assert lc["issue_date"] == "2026-04-15"

    docs = snap["extracted_context"]["documents"]
    assert isinstance(docs[0]["amount_raw"], float)
    assert docs[0]["amount_raw"] == 35000.0
    assert isinstance(docs[1]["amount_raw"], float)
    assert docs[1]["amount_raw"] == 15000.0


def test_list_tuple_set_coerced_to_list() -> None:
    snap = _jsonable(
        {
            "as_list": [1, 2, 3],
            "as_tuple": (1, 2, 3),
            "as_set": {1, 2, 3},
            "as_frozenset": frozenset([1, 2, 3]),
        }
    )
    assert snap["as_list"] == [1, 2, 3]
    assert snap["as_tuple"] == [1, 2, 3]
    assert sorted(snap["as_set"]) == [1, 2, 3]
    assert sorted(snap["as_frozenset"]) == [1, 2, 3]


def test_none_passes_through() -> None:
    assert _jsonable(None) is None
    assert _jsonable({"field": None}) == {"field": None}


def test_dict_with_non_string_keys_stringified() -> None:
    # Note: in Python, ``True == 1`` and ``hash(True) == hash(1)``, so a dict
    # literal ``{1: "one", True: "yes"}`` only keeps one entry.  We test
    # separately to avoid that collapse.
    snap = _jsonable({1: "one", 2.5: "two-point-five"})
    assert set(snap.keys()) == {"1", "2.5"}
    snap_bool = _jsonable({True: "yes", False: "no"})
    assert set(snap_bool.keys()) == {"True", "False"}


def test_snapshot_setup_state_drops_validation_session() -> None:
    # validation_session is a SQLAlchemy row — we never want to serialize it.
    # It gets re-attached on resume via DB lookup by job_id.
    class FakeSession:
        def __repr__(self) -> str:  # pragma: no cover - defensive
            return "<ValidationSession>"

    state = {
        "validation_session": FakeSession(),
        "lc_context": {"lc_number": "TEST"},
        "status": "extraction_ready",
    }
    snap = _snapshot_setup_state(state)
    assert "validation_session" not in snap
    assert snap["lc_context"] == {"lc_number": "TEST"}
    assert snap["status"] == "extraction_ready"


def test_full_roundtrip_via_json() -> None:
    # End-to-end: realistic setup_state → _jsonable → json.dumps → json.loads
    # → assertions.  This is what actually happens: the snapshot is stored in
    # validation_session.extracted_data (a JSON column) and reloaded as a
    # dict on resume.
    state = {
        "lc_context": {
            "lc_number": "EXP2026BD001",
            "amount": Decimal("250000.00"),
            "currency": "USD",
            "issue_date": date(2026, 4, 15),
            "expiry_date": date(2026, 10, 15),
        },
        "extracted_context": {
            "documents": [
                {
                    "id": "doc1",
                    "document_type": "commercial_invoice",
                    "extracted_fields": {
                        "invoice_number": "INV-001",
                        "amount": Decimal("250000.00"),
                        "invoice_date": date(2026, 4, 10),
                    },
                }
            ]
        },
    }

    snap = _snapshot_setup_state(state)
    reloaded = json.loads(json.dumps(snap))

    lc = reloaded["lc_context"]
    assert lc["lc_number"] == "EXP2026BD001"
    assert lc["amount"] == 250000.0
    assert isinstance(lc["amount"], float)
    assert lc["issue_date"] == "2026-04-15"

    doc = reloaded["extracted_context"]["documents"][0]
    assert doc["extracted_fields"]["amount"] == 250000.0
    assert isinstance(doc["extracted_fields"]["amount"], float)
    assert doc["extracted_fields"]["invoice_date"] == "2026-04-10"
