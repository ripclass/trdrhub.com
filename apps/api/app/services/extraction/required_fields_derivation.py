"""Derive per-document required field lists from a parsed LC context.

The MT700 LC's clauses 45A (goods description), 46A (documents required),
and 47A (additional conditions) are the SOURCE OF TRUTH for what must be
extracted from each supporting document. This module reads the
already-parsed LC context (no LLM calls — pure keyword scanning) and
produces a map of:

    {
        "lc_self_required": [...],            # MT700 mandatory + skeleton fields
        "by_document_type": {
            "commercial_invoice": [...],
            "bill_of_lading": [...],
            "packing_list": [...],
            ...
        },
        "applies_to_all_supporting_docs": [...],  # rules that apply to every doc
        "evidence": [
            {
                "source": "47A-6",
                "scope": "all",                  # or a doc_type
                "fields": ["exporter_bin", "exporter_tin"],
                "text": "EXPORTER BIN: ... MUST APPEAR ON ALL DOCUMENTS",
            },
            ...
        ],
    }

This is the input the Extraction Review screen uses to decide which fields
to surface for user confirmation per document.

Design notes
------------
- No regexes spanning multiple lines if we can avoid it. Each clause text is
  treated as a self-contained sentence.
- Field name normalization is centralized in `FIELD_KEYWORDS` so adding
  new keywords is a one-line change.
- Doc-type detection looks for explicit keywords ("BILL OF LADING",
  "COMMERCIAL INVOICE", etc.) at the start of each 46A line, then in the
  body of each 47A condition.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# MT700 baselines (from the canonical mandatory / important-optional spec)
# ---------------------------------------------------------------------------

# The 5 absolute minimums — without these the system cannot validate at all.
MT700_SKELETON_FIELDS: Tuple[str, ...] = (
    "lc_number",          # Field 20
    "amount",             # Field 32B
    "currency",           # Field 32B
    "goods_description",  # Field 45A
    "documents_required", # Field 46A
    "expiry_date",        # Field 31D
)

# Full MT700 mandatory list — every LC MUST carry these.
MT700_MANDATORY_FIELDS: Tuple[str, ...] = (
    "sequence_of_total",            # Field 27
    "form_of_documentary_credit",   # Field 40A
    "lc_number",                    # Field 20
    "issue_date",                   # Field 31C
    "expiry_date",                  # Field 31D
    "expiry_place",                 # Field 31D
    "applicable_rules",             # Field 40E
    "applicant",                    # Field 50
    "beneficiary",                  # Field 59
    "amount",                       # Field 32B
    "currency",                     # Field 32B
    "available_with",               # Field 41a
    "available_by",                 # Field 41a
    "port_of_loading",              # Field 44E
    "port_of_discharge",            # Field 44F
    "latest_shipment_date",         # Field 44C
    "goods_description",            # Field 45A
    "documents_required",           # Field 46A
    "additional_conditions",        # Field 47A
    "period_for_presentation",      # Field 48
)

# Optional MT700 fields the engine should still parse when present.
MT700_OPTIONAL_FIELDS: Tuple[str, ...] = (
    "amount_tolerance",             # Field 39A
    "partial_shipments",            # Field 43P
    "transshipment",                # Field 43T
    "drafts_at",                    # Field 42C
    "drawee",                       # Field 42a
    "confirmation_instructions",    # Field 49
    "instructions_to_paying_bank",  # Field 78
    "charges",                      # Field 71D
)


# ---------------------------------------------------------------------------
# Per-document baseline requirements (what the bank examiner expects on each
# document type, independent of any specific LC clauses).
# ---------------------------------------------------------------------------

DOC_TYPE_BASELINE: Dict[str, Tuple[str, ...]] = {
    "commercial_invoice": (
        "invoice_number",
        "invoice_date",
        "amount",
        "currency",
        "seller",       # must match LC beneficiary (Art 18(a)(i))
        "buyer",        # must match LC applicant (Art 18(a)(ii))
        "goods_description",
        "lc_number",
    ),
    "bill_of_lading": (
        "bl_number",
        "shipper",
        "consignee",
        "notify_party",
        "port_of_loading",
        "port_of_discharge",
        "vessel_name",
        "shipped_on_board_date",  # vs LC field 44C
        "lc_number",
    ),
    "ocean_bill_of_lading": (
        "bl_number", "shipper", "consignee", "notify_party",
        "port_of_loading", "port_of_discharge", "vessel_name",
        "shipped_on_board_date", "lc_number",
    ),
    "air_waybill": (
        "awb_number", "shipper", "consignee",
        "airport_of_departure", "airport_of_destination",
        "shipped_on_board_date", "lc_number",
    ),
    "packing_list": (
        "packing_list_number",
        "total_packages",
        "gross_weight",
        "net_weight",
        "lc_number",
    ),
    "certificate_of_origin": (
        "certificate_number",
        "country_of_origin",
        "issuing_authority",
        "exporter",
        "lc_number",
    ),
    "insurance_certificate": (
        "policy_number",
        "insured_amount",   # must be >= 110% of LC 32B (Art 28(f)(ii))
        "currency",
        "issue_date",
        "lc_number",
    ),
    "insurance_policy": (
        "policy_number", "insured_amount", "currency", "issue_date", "lc_number",
    ),
    "inspection_certificate": (
        "certificate_number",
        "inspection_agency",
        "inspection_date",
        "lc_number",
    ),
    "beneficiary_certificate": (
        "certificate_number", "issuer", "issue_date", "lc_number",
    ),
}


# Doc-type aliases — used to canonicalize a doc type detected from clause text.
DOC_TYPE_ALIASES: Dict[str, str] = {
    "commercial_invoice": "commercial_invoice",
    "invoice": "commercial_invoice",
    "signed commercial invoice": "commercial_invoice",
    "proforma_invoice": "commercial_invoice",
    "proforma invoice": "commercial_invoice",
    "bill_of_lading": "bill_of_lading",
    "bill of lading": "bill_of_lading",
    "b/l": "bill_of_lading",
    "bl": "bill_of_lading",
    "ocean bill of lading": "ocean_bill_of_lading",
    "on board bill of lading": "bill_of_lading",
    "clean on-board bill of lading": "bill_of_lading",
    "clean on board bill of lading": "bill_of_lading",
    "air waybill": "air_waybill",
    "airway bill": "air_waybill",
    "awb": "air_waybill",
    "packing_list": "packing_list",
    "packing list": "packing_list",
    "detailed packing list": "packing_list",
    "certificate_of_origin": "certificate_of_origin",
    "certificate of origin": "certificate_of_origin",
    "coo": "certificate_of_origin",
    "country of origin certificate": "certificate_of_origin",
    "insurance_certificate": "insurance_certificate",
    "insurance certificate": "insurance_certificate",
    "marine insurance certificate": "insurance_certificate",
    "insurance policy": "insurance_policy",
    "marine insurance policy": "insurance_policy",
    "inspection certificate": "inspection_certificate",
    "sgs certificate": "inspection_certificate",
    "intertek certificate": "inspection_certificate",
    "pre-shipment inspection certificate": "inspection_certificate",
    "psi certificate": "inspection_certificate",
    "beneficiary certificate": "beneficiary_certificate",
    "beneficiary's certificate": "beneficiary_certificate",
}


# ---------------------------------------------------------------------------
# Field keyword detection — keywords are matched case-insensitive against
# clause text and produce canonical field names.
# ---------------------------------------------------------------------------

# Order matters: more specific phrases first so "lc no." doesn't accidentally
# get caught by a generic "no." matcher.
FIELD_KEYWORDS: List[Tuple[re.Pattern, str]] = [
    # Identifiers / cross-references
    (re.compile(r"\blc\s*(?:no\.?|number|ref(?:erence)?)\b", re.I), "lc_number"),
    (re.compile(r"\bdocumentary\s+credit\s+(?:number|no\.?)\b", re.I), "lc_number"),
    (re.compile(r"\bcredit\s+(?:number|no\.?)\b", re.I), "lc_number"),
    (re.compile(r"\b(?:buyer\s+)?purchase\s+order\s+(?:no\.?|number)\b", re.I), "buyer_purchase_order_number"),
    (re.compile(r"\bp\.?o\.?\s*(?:no\.?|number)\b", re.I), "buyer_purchase_order_number"),

    # Tax / business identifiers (Bangladesh-specific seen in many LCs)
    (re.compile(r"\bexporter\s+bin\b", re.I), "exporter_bin"),
    (re.compile(r"\bbin\s*(?:no\.?|number)?\b", re.I), "exporter_bin"),
    (re.compile(r"\bexporter\s+tin\b", re.I), "exporter_tin"),
    (re.compile(r"\btin\s*(?:no\.?|number)?\b", re.I), "exporter_tin"),
    (re.compile(r"\bvat\s+registration\b", re.I), "vat_registration"),

    # Invoice fields
    (re.compile(r"\bhs\s*code\b", re.I), "hs_code"),
    (re.compile(r"\bunit\s+price\b", re.I), "unit_price"),
    (re.compile(r"\bquantity\b|\bqty\b", re.I), "quantity"),
    # "TOTAL" / "TOTAL AMOUNT" / "TOTAL VALUE" all map to canonical `amount`
    # so we don't fragment the same concept across two field names.
    (re.compile(r"\b(?:grand\s+)?total(?:\s+(?:amount|value))?\b", re.I), "amount"),
    (re.compile(r"\binvoice\s+(?:no\.?|number)\b", re.I), "invoice_number"),
    (re.compile(r"\binvoice\s+date\b", re.I), "invoice_date"),

    # Bill of Lading fields
    (re.compile(r"\bvessel\s+name\b", re.I), "vessel_name"),
    (re.compile(r"\bvoy(?:age)?\s*(?:no\.?|number)?\b", re.I), "voyage_number"),
    (re.compile(r"\bcontainer\s+(?:no\.?|number)\b", re.I), "container_number"),
    (re.compile(r"\bseal\s+(?:no\.?|number)\b", re.I), "seal_number"),
    (re.compile(r"\bb/?l\s+(?:no\.?|number)\b", re.I), "bl_number"),
    (re.compile(r"\bbill\s+of\s+lading\s+(?:no\.?|number)\b", re.I), "bl_number"),
    (re.compile(r"\bon[\s\-]?board\s+date\b", re.I), "shipped_on_board_date"),
    (re.compile(r"\bshipment\s+date\b", re.I), "shipped_on_board_date"),

    # Weights / packaging — also catch "GROSS AND NET WEIGHT" / "G.W. AND N.W."
    # phrasings where both fields are listed in a single shared sentence.
    (re.compile(r"\bgross\s+(?:and\s+net\s+)?weight\b|\bg\.?w\.?\b", re.I), "gross_weight"),
    (re.compile(r"\b(?:gross\s+and\s+)?net\s+weight\b|\bn\.?w\.?\b", re.I), "net_weight"),
    (re.compile(r"\bcarton[\s\-]wise\b|\bcarton\s+breakdown\b|\btotal\s+cartons?\b", re.I), "total_packages"),
    (re.compile(r"\bsize\s+breakdown\b|\bsizes?\b", re.I), "size_breakdown"),
    (re.compile(r"\bpacking\s+list\s+(?:no\.?|number)\b", re.I), "packing_list_number"),

    # Certificate of origin
    (re.compile(r"\bcountry\s+of\s+origin\b", re.I), "country_of_origin"),
    (re.compile(r"\bissuing\s+authority\b|\bchamber\s+of\s+commerce\b|\bepb\b", re.I), "issuing_authority"),
    (re.compile(r"\bcertificate\s+(?:no\.?|number)\b", re.I), "certificate_number"),

    # Insurance
    (re.compile(r"\bpolicy\s+(?:no\.?|number)\b", re.I), "policy_number"),
    (re.compile(r"\binsured\s+amount\b|\bsum\s+insured\b", re.I), "insured_amount"),
    (re.compile(r"\b110\s*%|\b110\s*percent\b", re.I), "insured_amount"),

    # Inspection
    (re.compile(r"\bsgs|intertek|bureau\s+veritas\b", re.I), "inspection_agency"),
    (re.compile(r"\binspection\s+(?:no\.?|number|certificate)\b", re.I), "certificate_number"),

    # Parties
    (re.compile(r"\bshipper\b", re.I), "shipper"),
    (re.compile(r"\bconsignee\b", re.I), "consignee"),
    (re.compile(r"\bnotify\s+party\b|\bnotify\b", re.I), "notify_party"),
    (re.compile(r"\bbeneficiary\b", re.I), "beneficiary"),
    (re.compile(r"\bapplicant\b", re.I), "applicant"),
    (re.compile(r"\bissuer\b", re.I), "issuer"),

    # Ports
    (re.compile(r"\bport\s+of\s+loading\b", re.I), "port_of_loading"),
    (re.compile(r"\bport\s+of\s+discharge\b", re.I), "port_of_discharge"),
]


# Patterns indicating a clause applies to ALL documents in the presentation.
APPLIES_TO_ALL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\ball\s+documents?\b", re.I),
    re.compile(r"\bevery\s+document\b", re.I),
    re.compile(r"\beach\s+document\b", re.I),
    re.compile(r"\bon\s+all\s+documents?\b", re.I),
    re.compile(r"\bmust\s+appear\s+on\s+all\b", re.I),
    re.compile(r"\bdocuments\s+must\s+show\b", re.I),
    re.compile(r"\bdocuments\s+to\s+show\b", re.I),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_doc_type(clause_text: str) -> Optional[str]:
    """Return the canonical doc type if the clause clearly references one."""
    if not clause_text:
        return None
    haystack = clause_text.lower()
    # Check long aliases first so "marine insurance certificate" wins over
    # "insurance certificate" when both could match.
    sorted_aliases = sorted(DOC_TYPE_ALIASES.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in haystack:
            return DOC_TYPE_ALIASES[alias]
    return None


def _detect_fields_in_text(clause_text: str) -> List[str]:
    """Return the canonical field names referenced anywhere in the clause."""
    if not clause_text:
        return []
    found: List[str] = []
    seen: Set[str] = set()
    for pattern, field_name in FIELD_KEYWORDS:
        if pattern.search(clause_text):
            if field_name not in seen:
                found.append(field_name)
                seen.add(field_name)
    return found


def _applies_to_all(clause_text: str) -> bool:
    if not clause_text:
        return False
    return any(p.search(clause_text) for p in APPLIES_TO_ALL_PATTERNS)


def _coerce_string_list(value: Any) -> List[str]:
    """Accept a list/tuple/string and return a flat list of trimmed strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                if item.strip():
                    out.append(item.strip())
            elif isinstance(item, dict):
                # documents_required entries are sometimes dicts with
                # raw_text / text / display_name fields. Pull the most
                # informative one.
                text = (
                    item.get("raw_text")
                    or item.get("text")
                    or item.get("display_name")
                    or item.get("description")
                    or item.get("id")
                    or ""
                )
                if isinstance(text, str) and text.strip():
                    out.append(text.strip())
        return out
    return []


def _extract_clauses_from_lc(lc_context: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Pull the 46A documents-required entries and 47A conditions out of
    whatever shape the LC context happens to use.
    """
    if not isinstance(lc_context, dict):
        return [], []

    documents_required = (
        lc_context.get("documents_required")
        or lc_context.get("required_documents_detailed")
        or lc_context.get("documentsRequired")
        or []
    )
    additional_conditions = (
        lc_context.get("additional_conditions")
        or lc_context.get("conditions")
        or lc_context.get("clauses")
        or lc_context.get("clauses_47a")
        or lc_context.get("additionalConditions")
        or []
    )
    return _coerce_string_list(documents_required), _coerce_string_list(additional_conditions)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def derive_required_fields(
    *,
    lc_context: Optional[Dict[str, Any]],
    document_types_present: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Build the required-fields map for the Extraction Review screen.

    Parameters
    ----------
    lc_context : dict
        The parsed LC context (already extracted by the vision LLM and
        normalized in launch_pipeline._shape_lc_financial_payload). Should
        contain `documents_required` and `additional_conditions` arrays
        from clauses 46A and 47A.
    document_types_present : sequence of str, optional
        The doc types that were actually uploaded by the user. We always
        emit per-doc requirements for these doc types so the review screen
        can render every uploaded document, even if the LC clauses don't
        mention them by name.

    Returns
    -------
    dict
        See module docstring for shape.
    """
    documents_required, additional_conditions = _extract_clauses_from_lc(lc_context or {})

    # 1. Per-doc requirements collected as sets so we don't duplicate fields.
    per_doc_required: Dict[str, Set[str]] = {}
    applies_to_all: Set[str] = set()
    evidence: List[Dict[str, Any]] = []

    # Apply baselines for every doc type the user uploaded.
    for doc_type in document_types_present or []:
        canonical = DOC_TYPE_ALIASES.get(doc_type.lower(), doc_type.lower())
        baseline = DOC_TYPE_BASELINE.get(canonical, ())
        if baseline:
            per_doc_required.setdefault(canonical, set()).update(baseline)

    # 2. Walk clause 46A entries (each is a description of one required doc).
    for idx, clause in enumerate(documents_required, start=1):
        doc_type = _detect_doc_type(clause)
        fields = _detect_fields_in_text(clause)
        if not fields:
            continue
        if doc_type:
            per_doc_required.setdefault(doc_type, set()).update(fields)
            evidence.append(
                {
                    "source": f"46A-{idx}",
                    "scope": doc_type,
                    "fields": fields,
                    "text": clause[:300],
                }
            )
        else:
            # Could not pin down a doc type — treat as a soft hint shared
            # across all uploaded docs (still better than dropping the info).
            applies_to_all.update(fields)
            evidence.append(
                {
                    "source": f"46A-{idx}",
                    "scope": "all",
                    "fields": fields,
                    "text": clause[:300],
                }
            )

    # 3. Walk clause 47A entries (each is a free-text additional condition).
    for idx, condition in enumerate(additional_conditions, start=1):
        fields = _detect_fields_in_text(condition)
        if not fields:
            continue
        if _applies_to_all(condition):
            applies_to_all.update(fields)
            evidence.append(
                {
                    "source": f"47A-{idx}",
                    "scope": "all",
                    "fields": fields,
                    "text": condition[:300],
                }
            )
            continue
        # Otherwise: try to detect a doc-type scope inline.
        doc_type = _detect_doc_type(condition)
        if doc_type:
            per_doc_required.setdefault(doc_type, set()).update(fields)
            evidence.append(
                {
                    "source": f"47A-{idx}",
                    "scope": doc_type,
                    "fields": fields,
                    "text": condition[:300],
                }
            )
        else:
            # No scope detected — fall back to "applies to all". This keeps
            # the requirement visible to the user rather than silently
            # dropping it.
            applies_to_all.update(fields)
            evidence.append(
                {
                    "source": f"47A-{idx}",
                    "scope": "all",
                    "fields": fields,
                    "text": condition[:300],
                }
            )

    # 4. Apply the cross-doc requirements to every per-doc list, and ALSO
    #    return them as their own list so the UI can render them once at
    #    the top of the page if it wants to.
    for doc_type in list(per_doc_required.keys()):
        per_doc_required[doc_type].update(applies_to_all)

    # Make sure every uploaded doc type has an entry, even if empty.
    for doc_type in document_types_present or []:
        canonical = DOC_TYPE_ALIASES.get(doc_type.lower(), doc_type.lower())
        per_doc_required.setdefault(canonical, set()).update(applies_to_all)

    # 5. The LC's own required field list — MT700 mandatory + skeleton.
    lc_self_required = list(MT700_MANDATORY_FIELDS)

    # 6. Sort and emit.
    by_document_type_sorted: Dict[str, List[str]] = {
        doc_type: sorted(fields)
        for doc_type, fields in per_doc_required.items()
    }

    return {
        "lc_self_required": lc_self_required,
        "lc_skeleton_required": list(MT700_SKELETON_FIELDS),
        "by_document_type": by_document_type_sorted,
        "applies_to_all_supporting_docs": sorted(applies_to_all),
        "evidence": evidence,
    }


__all__ = [
    "derive_required_fields",
    "DOC_TYPE_ALIASES",
    "DOC_TYPE_BASELINE",
    "FIELD_KEYWORDS",
    "MT700_MANDATORY_FIELDS",
    "MT700_OPTIONAL_FIELDS",
    "MT700_SKELETON_FIELDS",
]
