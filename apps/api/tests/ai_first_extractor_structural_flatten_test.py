"""Unit tests for ``_flatten_structural_field_values_in_place``.

The vision LLM legitimately returns multi-item structured data when a
document has several line items (multi-SKU invoice, multi-size packing
list, multi-HS-code commercial invoice).  The Extract & Review form
widgets expect scalars, so the flattener collapses those structured
values into scalar + ``__items`` sidecar at the extraction boundary.

These tests lock down the behavior so a future change can't silently
regress multi-item handling or over-flatten structural party/amount
dicts that ``_shape_lc_financial_payload`` needs.
"""

from __future__ import annotations

import copy

from app.services.extraction.ai_first_extractor import (
    _flatten_structural_field_values_in_place,
)


def test_list_of_strings_joined_with_sidecar() -> None:
    result = {"hs_code": ["61091000", "62034200", "61044200"]}
    _flatten_structural_field_values_in_place(result)
    assert result["hs_code"] == "61091000, 62034200, 61044200"
    assert result["hs_code__items"] == ["61091000", "62034200", "61044200"]


def test_list_of_dicts_with_numeric_subkey_summed() -> None:
    result = {
        "quantity": [
            {"item": "T-Shirts", "quantity": 30000, "unit": "PCS"},
            {"item": "Trousers", "quantity": 12000, "unit": "PCS"},
            {"item": "Dresses", "quantity": 8500, "unit": "PCS"},
        ],
    }
    _flatten_structural_field_values_in_place(result)
    assert result["quantity"] == 50500
    assert isinstance(result["quantity__items"], list)
    assert len(result["quantity__items"]) == 3


def test_list_of_dicts_without_numeric_joined_by_description() -> None:
    result = {
        "conditions": [
            {"description": "First condition"},
            {"description": "Second condition"},
            {"item": "Third item"},
        ],
    }
    _flatten_structural_field_values_in_place(result)
    # All three descriptions joined with '; '
    joined = result["conditions"]
    assert "First condition" in joined
    assert "Second condition" in joined
    assert "Third item" in joined
    assert "conditions__items" in result


def test_dict_of_name_to_number_rendered_as_kv_string() -> None:
    result = {
        "size_breakdown": {
            "Knit T-Shirts": 1000,
            "Denim Trousers": 500,
            "Cotton Dresses": 350,
        },
    }
    _flatten_structural_field_values_in_place(result)
    assert "Knit T-Shirts: 1000" in result["size_breakdown"]
    assert "Denim Trousers: 500" in result["size_breakdown"]
    assert "Cotton Dresses: 350" in result["size_breakdown"]
    assert result["size_breakdown__items"] == {
        "Knit T-Shirts": 1000,
        "Denim Trousers": 500,
        "Cotton Dresses": 350,
    }


def test_structural_party_dict_left_alone() -> None:
    """applicant = {name, address, country} is consumed by the per-field
    unwrap branch in _shape_lc_financial_payload — don't flatten it here."""
    result = {
        "applicant": {
            "name": "GLOBAL IMPORTERS INC.",
            "address": "1250 HUDSON STREET",
            "country": "USA",
        },
        "beneficiary": {
            "name": "DHAKA KNITWEAR LTD.",
            "address": "PLOT 22, SAVAR",
        },
    }
    _flatten_structural_field_values_in_place(result)
    assert result["applicant"]["name"] == "GLOBAL IMPORTERS INC."
    assert result["applicant"]["address"] == "1250 HUDSON STREET"
    assert result["beneficiary"]["name"] == "DHAKA KNITWEAR LTD."
    assert "applicant__items" not in result
    assert "beneficiary__items" not in result


def test_structural_amount_dict_left_alone() -> None:
    """amount = {value, currency} is an intentional structural shape — the
    shape function unwraps ``amount.value`` and ``amount.currency``
    separately.  If we flattened it we'd destroy that contract."""
    result = {"amount": {"value": 250000.0, "currency": "USD"}}
    _flatten_structural_field_values_in_place(result)
    assert result["amount"] == {"value": 250000.0, "currency": "USD"}
    assert "amount__items" not in result


def test_plural_named_field_left_alone() -> None:
    """A field named ``line_items`` / ``goods_items`` should stay as a list
    — the plural name is the schema's contract that the field is a list."""
    items = [
        {"description": "T-Shirts", "qty": 30000},
        {"description": "Trousers", "qty": 12000},
    ]
    result = {
        "line_items": list(items),
        "goods_items": list(items),
        "invoice_lines": list(items),
    }
    _flatten_structural_field_values_in_place(result)
    assert result["line_items"] == items
    assert result["goods_items"] == items
    assert result["invoice_lines"] == items
    assert "line_items__items" not in result


def test_private_underscore_keys_left_alone() -> None:
    result = {
        "_extraction_method": "multimodal_ai_first",
        "_llm_provider": "openrouter",
        "_field_details": {"lc_number": {"value": "X", "confidence": 0.82}},
    }
    snapshot = copy.deepcopy(result)
    _flatten_structural_field_values_in_place(result)
    assert result == snapshot


def test_scalar_fields_pass_through() -> None:
    result = {
        "invoice_number": "INV-001",
        "amount": 50000,
        "currency": "USD",
        "invoice_date": "2026-04-15",
    }
    snapshot = copy.deepcopy(result)
    _flatten_structural_field_values_in_place(result)
    assert result == snapshot


def test_idempotent_second_call_is_noop() -> None:
    """Running the flattener twice on the same dict must not keep adding
    sidecars.  If the __items suffix rule is broken a second pass would
    create ``hs_code__items__items`` and so on."""
    result = {
        "hs_code": ["61091000", "62034200", "61044200"],
        "quantity": [
            {"item": "T-Shirts", "quantity": 30000, "unit": "PCS"},
            {"item": "Trousers", "quantity": 12000, "unit": "PCS"},
        ],
        "size_breakdown": {"Small": 1000, "Medium": 500},
    }
    _flatten_structural_field_values_in_place(result)
    snapshot_after_first = copy.deepcopy(result)
    _flatten_structural_field_values_in_place(result)
    assert result == snapshot_after_first, (
        "flatten is not idempotent — second call produced extra sidecars"
    )


def test_none_values_pass_through() -> None:
    result = {
        "lc_number": None,
        "amount": None,
        "hs_code": None,
    }
    snapshot = copy.deepcopy(result)
    _flatten_structural_field_values_in_place(result)
    assert result == snapshot


def test_list_with_mixed_shape_items_uses_description_join() -> None:
    """List items that aren't all dicts or that don't share a numeric sub-key
    should fall through to the description-join branch, not crash."""
    result = {
        "notes": [
            {"text": "First note"},
            {"text": "Second note"},
        ],
    }
    _flatten_structural_field_values_in_place(result)
    # Neither "text" is in _LINE_ITEM_NUMERIC_KEYS, so the description
    # join branch runs.  "text" isn't in the description keys list so it
    # falls through to the "k: v, k: v" string per item.
    assert isinstance(result["notes"], str)
    assert "notes__items" in result
