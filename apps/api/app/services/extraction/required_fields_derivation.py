"""Derive per-document required field lists from a parsed LC context.

The MT700 LC's clauses 45A (goods description), 46A (documents required),
and 47A (additional conditions) are the SOURCE OF TRUTH for what must be
extracted from each supporting document. This module reads the
already-parsed LC context (no LLM calls — pure keyword scanning) and
produces both a flat per-doc field-name map (legacy, for consumers that
only need "is this field required"), AND a per-doc annotated record map
that explains **WHY** each field is required so the Extract & Review UI
can cite the specific clause:

    {
        "lc_self_required": [...],             # MT700 mandatory field names (flat)
        "lc_self_required_annotated": [        # same, with provenance per field
            {
                "field": "lc_number",
                "source_type": "mt700_mandatory",
                "source_refs": ["MT700 Field 20"],
                "clause_texts": [],
                "severity": "required",
            },
            ...
        ],
        "by_document_type": {                  # flat field-name lists (legacy)
            "commercial_invoice": ["amount", "buyer", ...],
            ...
        },
        "by_document_type_annotated": {        # annotated records per doc type
            "commercial_invoice": [
                {
                    "field": "lc_number",
                    "source_type": "47a",
                    "source_refs": ["47A-6"],
                    "clause_texts": ["EXPORTER BIN: ... MUST APPEAR ON ALL DOCUMENTS"],
                    "severity": "required",
                },
                {
                    "field": "invoice_number",
                    "source_type": "doc_standard",
                    "source_refs": [],
                    "clause_texts": [],
                    "severity": "conventional",
                },
                ...
            ],
            ...
        },
        "applies_to_all_supporting_docs": [...],  # flat cross-doc field names
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

## Provenance semantics

Each annotated record has one of four ``source_type`` values, which maps
1:1 to how the frontend renders the missing-field badge:

- ``"46a"`` — field was found keyword-matched inside a clause 46A entry
  (the LC's documents-required list).  Red badge, high severity.
- ``"47a"`` — field was found inside a clause 47A condition.  Red badge.
- ``"mt700_mandatory"`` — the LC itself must carry this field per SWIFT
  MT700 spec.  Only applies to the ``letter_of_credit`` doc type and is
  independent of whether the clause mentions the field.  Red badge.
- ``"doc_standard"`` — the field comes from ``DOC_TYPE_BASELINE`` below.
  These are conventional fields a bank examiner expects on a given doc
  type (e.g. every B/L has a BL Number, every CoO has a Certificate
  Number) but are NOT explicitly demanded by this particular LC.  Amber
  badge, lower severity — not a UCP600/LC breach, just a convention.

A field can have MULTIPLE sources (e.g. ``lc_number`` on an invoice may
be demanded by 47A condition #6 AND by 46A clause #1 that says "INVOICE
INDICATING LC NO.").  When that happens we keep ``source_type`` at the
highest-severity entry and accumulate all source refs and clause texts.
The severity order (highest first) is:
``46a > 47a > mt700_mandatory > doc_standard``.

## Design notes

- No regexes spanning multiple lines if we can avoid it. Each clause text
  is treated as a self-contained sentence.
- Field name normalization is centralized in ``FIELD_KEYWORDS`` so adding
  new keywords is a one-line change.
- Doc-type detection looks for explicit keywords ("BILL OF LADING",
  "COMMERCIAL INVOICE", etc.) at the start of each 46A line, then in the
  body of each 47A condition.
- The "applies to all" fields detected from 47A conditions are filtered
  through each destination doc's schema before being merged into that
  doc's required list.  This prevents a clause like "DOCUMENTS PRESENTED
  LATER THAN 21 DAYS AFTER SHIPMENT DATE" (which trips the 'shipment date'
  keyword) from adding ``shipped_on_board_date`` as a phantom field on
  Invoice / COO / Packing List where it doesn't belong.
- The baseline list (``DOC_TYPE_BASELINE``) is NOT dropped when a clause
  doesn't mention a field — we still emit it with ``source_type="doc_standard"``
  so the frontend can render it with amber-advisory severity.  Dropping it
  would hide conventional fields from the review screen entirely, which
  makes it harder for the user to spot a genuinely missing BL Number.
"""

from __future__ import annotations

import re
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple


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
    # The LC itself — the full MT700 mandatory set. We list every mandatory
    # field even if the LC clauses don't mention them, because the LC IS the
    # source document that imposes those requirements on everything else.
    "letter_of_credit": (
        "sequence_of_total",
        "form_of_documentary_credit",
        "lc_number",
        "issue_date",
        "expiry_date",
        "expiry_place",
        "applicable_rules",
        "applicant",
        "beneficiary",
        "amount",
        "currency",
        "available_with",
        "available_by",
        "port_of_loading",
        "port_of_discharge",
        "latest_shipment_date",
        "goods_description",
        "documents_required",
        "additional_conditions",
        "period_for_presentation",
    ),
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
    # NOTE: the old pattern here also matched "inspection certificate" as a
    # keyword for certificate_number, but "INSPECTION CERTIFICATE" in a
    # 46A clause is the NAME of the required document, not a field label
    # — it erroneously upgraded certificate_number from doc_standard to
    # 46a-required on every inspection-cert bearing LC.  We now only
    # match "inspection no." / "inspection number".  The generic
    # ``certificate number`` pattern above still catches legitimate
    # "inspection certificate number" phrasings.
    (re.compile(r"\binspection\s+(?:no\.?|number)\b", re.I), "certificate_number"),

    # Parties — only match when the clause is referring to the party as a
    # FIELD on a document, not as an incidental mention. Bare `\bapplicant\b`
    # was catching "notify applicant" / "sent to applicant" / "by applicant"
    # etc. which are unrelated instructions.
    (re.compile(r"\bshipper\b", re.I), "shipper"),
    (re.compile(r"\bconsignee\b", re.I), "consignee"),
    (re.compile(r"\bnotify\s+party\b", re.I), "notify_party"),
    (
        re.compile(
            r"\bbeneficiary(?:'s|s)?\s+(?:name|address|details)\b|\bname\s+of\s+(?:the\s+)?beneficiary\b",
            re.I,
        ),
        "beneficiary",
    ),
    (
        re.compile(
            r"\bapplicant(?:'s|s)?\s+(?:name|address|details)\b|\bname\s+of\s+(?:the\s+)?applicant\b|\bmade\s+out\s+(?:in\s+)?(?:the\s+)?name\s+of\s+(?:the\s+)?applicant\b",
            re.I,
        ),
        "applicant",
    ),
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


# Patterns that mean the clause is about physical carton/box markings, not
# fields on any document. Clauses like "COUNTRY OF ORIGIN MUST BE PRINTED ON
# ALL CARTONS IN INDELIBLE INK" or "MARKING: EXPORTER NAME" should NOT
# produce field requirements — they're packaging instructions for the goods
# themselves, not data fields the bank examiner checks on documents.
CARTON_MARKING_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:on|upon)\s+(?:all\s+)?(?:the\s+)?cartons?\b", re.I),
    re.compile(r"\bprinted\s+on\b", re.I),
    re.compile(r"\bmarking\s*:", re.I),
    re.compile(r"\bshipping\s+marks?\b", re.I),
    re.compile(r"\bin\s+indelible\s+ink\b", re.I),
    re.compile(r"\bstenci[lr]led\b", re.I),
]


def _is_carton_marking_clause(clause_text: str) -> bool:
    if not clause_text:
        return False
    return any(p.search(clause_text) for p in CARTON_MARKING_PATTERNS)


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


# ---------------------------------------------------------------------------
# Per-doc schema field lookup.  We defer the import of DOC_TYPE_SCHEMAS to
# function-call time to avoid a circular import at module load, and cache the
# resolved sets so repeated derivations are cheap.
# ---------------------------------------------------------------------------

_DOC_TYPE_TO_SCHEMA_KEY: Dict[str, str] = {
    # LC family
    "letter_of_credit": "letter_of_credit",
    "swift_message": "letter_of_credit",
    "lc_application": "letter_of_credit",
    "standby_letter_of_credit": "letter_of_credit",
    "bank_guarantee": "letter_of_credit",
    # Invoice family
    "commercial_invoice": "commercial_invoice",
    "proforma_invoice": "commercial_invoice",
    # Packing family
    "packing_list": "packing_list",
    # Transport family (all go through transport_document schema)
    "bill_of_lading": "transport_document",
    "ocean_bill_of_lading": "transport_document",
    "house_bill_of_lading": "transport_document",
    "master_bill_of_lading": "transport_document",
    "air_waybill": "transport_document",
    "sea_waybill": "transport_document",
    "road_transport_document": "transport_document",
    "railway_consignment_note": "transport_document",
    "forwarder_certificate_of_receipt": "transport_document",
    "forwarders_certificate_of_receipt": "transport_document",
    "multimodal_transport_document": "transport_document",
    # Regulatory family
    "certificate_of_origin": "regulatory_document",
    "gsp_form_a": "regulatory_document",
    "eur1_movement_certificate": "regulatory_document",
    "customs_declaration": "regulatory_document",
    "export_license": "regulatory_document",
    "import_license": "regulatory_document",
    "phytosanitary_certificate": "regulatory_document",
    # Insurance family
    "insurance_certificate": "insurance_document",
    "insurance_policy": "insurance_document",
    "marine_insurance_policy": "insurance_document",
    "marine_insurance_certificate": "insurance_document",
    # Attestation family
    "beneficiary_certificate": "attestation_document",
    "manufacturer_certificate": "attestation_document",
    "conformity_certificate": "attestation_document",
    "non_manipulation_certificate": "attestation_document",
    "halal_certificate": "attestation_document",
    "kosher_certificate": "attestation_document",
    "organic_certificate": "attestation_document",
    # Inspection family
    "inspection_certificate": "inspection_document",
    "pre_shipment_inspection": "inspection_document",
    "quality_certificate": "inspection_document",
    "weight_certificate": "inspection_document",
    "weight_list": "inspection_document",
    "measurement_certificate": "inspection_document",
    "analysis_certificate": "inspection_document",
    "lab_test_report": "inspection_document",
    "sgs_certificate": "inspection_document",
    "bureau_veritas_certificate": "inspection_document",
    "intertek_certificate": "inspection_document",
}

_SCHEMA_FIELD_CACHE: Dict[str, FrozenSet[str]] = {}


# ---------------------------------------------------------------------------
# Annotated required-field records — the source-cited provenance shape the
# Extract & Review screen reads to decide how to render each missing-field
# badge (red "46A clause #2" vs amber "doc-standard").
# ---------------------------------------------------------------------------

# Severity ordering — used when the same field has multiple sources and we
# need to pick the "primary" source_type for UI rendering.  Higher rank =
# stronger requirement = red-blocking badge.
_SOURCE_TYPE_RANK: Dict[str, int] = {
    "doc_standard": 1,
    "mt700_mandatory": 2,
    "47a": 3,
    "46a": 4,
}


def _severity_for_source_type(source_type: str) -> str:
    """Return the UI severity label for a provenance source type."""
    if source_type == "doc_standard":
        return "conventional"
    return "required"


def _merge_field_record(
    records: Dict[str, Dict[str, Any]],
    *,
    field: str,
    source_type: str,
    source_ref: Optional[str] = None,
    clause_text: Optional[str] = None,
) -> None:
    """Add or upgrade a required-field record in-place.

    If the field is already recorded at a lower severity, the existing
    record is upgraded to the new source_type (its source_refs and
    clause_texts are preserved and the new provenance is appended).  If
    the field is already recorded at the SAME source_type, the new
    source_ref and clause_text are appended to the existing lists so the
    UI can cite multiple supporting clauses.  If the existing record
    already dominates, the new source is still appended (so the frontend
    can show a full audit trail) but the primary source_type stays put.
    """
    existing = records.get(field)
    new_rank = _SOURCE_TYPE_RANK.get(source_type, 0)
    if existing is None:
        record: Dict[str, Any] = {
            "field": field,
            "source_type": source_type,
            "source_refs": [source_ref] if source_ref else [],
            "clause_texts": [clause_text] if clause_text else [],
            "severity": _severity_for_source_type(source_type),
        }
        records[field] = record
        return

    existing_rank = _SOURCE_TYPE_RANK.get(existing.get("source_type") or "", 0)
    if new_rank > existing_rank:
        existing["source_type"] = source_type
        existing["severity"] = _severity_for_source_type(source_type)
    if source_ref and source_ref not in existing["source_refs"]:
        existing["source_refs"].append(source_ref)
    if clause_text and clause_text not in existing["clause_texts"]:
        existing["clause_texts"].append(clause_text)


def _build_lc_self_annotated_records() -> List[Dict[str, Any]]:
    """Build annotated records for the LC's own MT700 mandatory fields.

    These are required by the SWIFT MT700 spec regardless of whether the
    LC's own clauses reference them — see the ``lc_self_required`` list
    in the return value of ``derive_required_fields``.
    """
    records: Dict[str, Dict[str, Any]] = {}
    field_to_tag = {
        "sequence_of_total": "Field 27",
        "form_of_documentary_credit": "Field 40A",
        "lc_number": "Field 20",
        "issue_date": "Field 31C",
        "expiry_date": "Field 31D",
        "expiry_place": "Field 31D",
        "applicable_rules": "Field 40E",
        "applicant": "Field 50",
        "beneficiary": "Field 59",
        "amount": "Field 32B",
        "currency": "Field 32B",
        "available_with": "Field 41a",
        "available_by": "Field 41a",
        "port_of_loading": "Field 44E",
        "port_of_discharge": "Field 44F",
        "latest_shipment_date": "Field 44C",
        "goods_description": "Field 45A",
        "documents_required": "Field 46A",
        "additional_conditions": "Field 47A",
        "period_for_presentation": "Field 48",
    }
    for field_name in MT700_MANDATORY_FIELDS:
        tag = field_to_tag.get(field_name) or field_name
        _merge_field_record(
            records,
            field=field_name,
            source_type="mt700_mandatory",
            source_ref=f"MT700 {tag}",
        )
    return list(records.values())


def _schema_fields_for_doc_type(doc_type: str) -> FrozenSet[str]:
    """Return the set of canonical field names declared by the extraction
    schema for ``doc_type``.  Returns an empty frozenset when the doc type
    isn't mapped or the schemas module can't be imported (the caller then
    skips the filter and falls back to the unfiltered behavior).
    """
    if not doc_type:
        return frozenset()
    schema_key = _DOC_TYPE_TO_SCHEMA_KEY.get(doc_type.lower())
    if not schema_key:
        return frozenset()
    cached = _SCHEMA_FIELD_CACHE.get(schema_key)
    if cached is not None:
        return cached
    try:
        from app.services.extraction.multimodal_document_extractor import (
            DOC_TYPE_SCHEMAS,
        )
    except ImportError:
        _SCHEMA_FIELD_CACHE[schema_key] = frozenset()
        return frozenset()
    schema = DOC_TYPE_SCHEMAS.get(schema_key) or {}
    fields = schema.get("fields") or []
    resolved = frozenset(str(f) for f in fields if isinstance(f, str))
    _SCHEMA_FIELD_CACHE[schema_key] = resolved
    return resolved


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

    # 1. Per-doc annotated records and cross-doc applies-to-all records.
    #
    # ``per_doc_annotated`` maps doc_type -> field_name -> annotated record.
    # ``applies_to_all_annotated`` maps field_name -> annotated record.
    # The flat ``per_doc_required`` (field-name sets) is derived from
    # ``per_doc_annotated`` at emission time — we don't maintain two
    # parallel data structures during the walk.
    per_doc_annotated: Dict[str, Dict[str, Dict[str, Any]]] = {}
    applies_to_all_annotated: Dict[str, Dict[str, Any]] = {}
    evidence: List[Dict[str, Any]] = []

    # Apply baselines for every doc type the user uploaded.  Baseline
    # fields are recorded with ``source_type="doc_standard"`` so the UI
    # can render them as conventional / amber severity.  If a later
    # clause also demands the field, the record is upgraded to the
    # stronger source_type via ``_merge_field_record``.
    for doc_type in document_types_present or []:
        canonical = DOC_TYPE_ALIASES.get(doc_type.lower(), doc_type.lower())
        baseline = DOC_TYPE_BASELINE.get(canonical, ())
        if canonical == "letter_of_credit":
            # LC self-fields are recorded as mt700_mandatory, not doc_standard.
            bucket = per_doc_annotated.setdefault(canonical, {})
            for field_name in MT700_MANDATORY_FIELDS:
                _merge_field_record(
                    bucket,
                    field=field_name,
                    source_type="mt700_mandatory",
                    source_ref=f"MT700 Field ({field_name})",
                )
            continue
        if not baseline:
            continue
        bucket = per_doc_annotated.setdefault(canonical, {})
        for field_name in baseline:
            _merge_field_record(
                bucket,
                field=field_name,
                source_type="doc_standard",
            )

    # 2. Walk clause 46A entries (each is a description of one required doc).
    for idx, clause in enumerate(documents_required, start=1):
        if _is_carton_marking_clause(clause):
            # Packaging instruction, not a data-field requirement.
            continue
        doc_type = _detect_doc_type(clause)
        fields = _detect_fields_in_text(clause)
        if not fields:
            continue
        source_ref = f"46A-{idx}"
        clause_text = clause[:300]
        if doc_type:
            bucket = per_doc_annotated.setdefault(doc_type, {})
            for field_name in fields:
                _merge_field_record(
                    bucket,
                    field=field_name,
                    source_type="46a",
                    source_ref=source_ref,
                    clause_text=clause_text,
                )
            evidence.append(
                {
                    "source": source_ref,
                    "scope": doc_type,
                    "fields": fields,
                    "text": clause_text,
                }
            )
        else:
            # Could not pin down a doc type — treat as a soft hint shared
            # across all uploaded docs.
            for field_name in fields:
                _merge_field_record(
                    applies_to_all_annotated,
                    field=field_name,
                    source_type="46a",
                    source_ref=source_ref,
                    clause_text=clause_text,
                )
            evidence.append(
                {
                    "source": source_ref,
                    "scope": "all",
                    "fields": fields,
                    "text": clause_text,
                }
            )

    # 3. Walk clause 47A entries (each is a free-text additional condition).
    for idx, condition in enumerate(additional_conditions, start=1):
        if _is_carton_marking_clause(condition):
            continue
        fields = _detect_fields_in_text(condition)
        if not fields:
            continue
        source_ref = f"47A-{idx}"
        clause_text = condition[:300]
        if _applies_to_all(condition):
            for field_name in fields:
                _merge_field_record(
                    applies_to_all_annotated,
                    field=field_name,
                    source_type="47a",
                    source_ref=source_ref,
                    clause_text=clause_text,
                )
            evidence.append(
                {
                    "source": source_ref,
                    "scope": "all",
                    "fields": fields,
                    "text": clause_text,
                }
            )
            continue
        # Otherwise: try to detect a doc-type scope inline.
        doc_type = _detect_doc_type(condition)
        if doc_type:
            bucket = per_doc_annotated.setdefault(doc_type, {})
            for field_name in fields:
                _merge_field_record(
                    bucket,
                    field=field_name,
                    source_type="47a",
                    source_ref=source_ref,
                    clause_text=clause_text,
                )
            evidence.append(
                {
                    "source": source_ref,
                    "scope": doc_type,
                    "fields": fields,
                    "text": clause_text,
                }
            )
        else:
            # No scope detected — fall back to "applies to all". This keeps
            # the requirement visible to the user rather than silently
            # dropping it.
            for field_name in fields:
                _merge_field_record(
                    applies_to_all_annotated,
                    field=field_name,
                    source_type="47a",
                    source_ref=source_ref,
                    clause_text=clause_text,
                )
            evidence.append(
                {
                    "source": source_ref,
                    "scope": "all",
                    "fields": fields,
                    "text": clause_text,
                }
            )

    # 4. Merge cross-doc applies-to-all records into every SUPPORTING doc,
    # FILTERED through the destination doc's own extraction schema.
    #
    # Without this filter, a 47A condition like "DOCUMENTS PRESENTED LATER
    # THAN 21 DAYS AFTER SHIPMENT DATE ARE NOT ACCEPTABLE" (which trips the
    # 'shipment date' keyword because of clause D on a typical MT700) would
    # dump `shipped_on_board_date` into applies_to_all and then spray it
    # onto Invoice / COO / Packing List, turning them into phantom-field
    # factories on the Extract & Review screen.
    def _filter_applies_to_all_for(doc_type: str) -> Set[str]:
        schema_fields = _schema_fields_for_doc_type(doc_type)
        if not schema_fields:
            return set(applies_to_all_annotated.keys())
        return {f for f in applies_to_all_annotated.keys() if f in schema_fields}

    def _merge_applies_to_all_into(doc_type: str) -> None:
        bucket = per_doc_annotated.setdefault(doc_type, {})
        for field_name in _filter_applies_to_all_for(doc_type):
            cross_record = applies_to_all_annotated[field_name]
            for source_ref in cross_record.get("source_refs") or []:
                _merge_field_record(
                    bucket,
                    field=field_name,
                    source_type=cross_record.get("source_type") or "47a",
                    source_ref=source_ref,
                    clause_text=(cross_record.get("clause_texts") or [None])[0],
                )

    # The LC itself does NOT get cross-doc requirements merged in — it's
    # the SOURCE of those requirements, not a doc that must satisfy them.
    for doc_type in list(per_doc_annotated.keys()):
        if doc_type == "letter_of_credit":
            continue
        _merge_applies_to_all_into(doc_type)

    # Make sure every uploaded supporting doc type has an entry.
    for doc_type in document_types_present or []:
        canonical = DOC_TYPE_ALIASES.get(doc_type.lower(), doc_type.lower())
        if canonical == "letter_of_credit":
            per_doc_annotated.setdefault(canonical, {})
            continue
        per_doc_annotated.setdefault(canonical, {})
        _merge_applies_to_all_into(canonical)

    # 5. The LC's own required field list — MT700 mandatory (flat) + annotated.
    lc_self_required = list(MT700_MANDATORY_FIELDS)
    lc_self_required_annotated = _build_lc_self_annotated_records()

    # 6. Emit both the flat and annotated per-doc maps.
    by_document_type_sorted: Dict[str, List[str]] = {}
    by_document_type_annotated: Dict[str, List[Dict[str, Any]]] = {}
    for doc_type, records in per_doc_annotated.items():
        sorted_field_names = sorted(records.keys())
        by_document_type_sorted[doc_type] = sorted_field_names
        by_document_type_annotated[doc_type] = [
            records[name] for name in sorted_field_names
        ]

    return {
        "lc_self_required": lc_self_required,
        "lc_self_required_annotated": lc_self_required_annotated,
        "lc_skeleton_required": list(MT700_SKELETON_FIELDS),
        "by_document_type": by_document_type_sorted,
        "by_document_type_annotated": by_document_type_annotated,
        "applies_to_all_supporting_docs": sorted(applies_to_all_annotated.keys()),
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
