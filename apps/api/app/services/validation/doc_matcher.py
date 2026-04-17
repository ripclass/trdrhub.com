"""
Per-document Field Matcher for Validation (Part 2).

For each parsed 46A/47A clause, walks the relevant document's extracted
fields (using the canonical alias map) and produces a Finding if a
required field is missing or mismatched.

Also contains deterministic cross-document consistency checks:
- Insurance coverage >= 110% CIF (UCP600 Art 28(f)(ii))
- BL vs Packing List weight consistency
- Late shipment / stale documents / LC expiry date checks
- Goods description keyword matching (LC vs invoice/BL)

Extraction (Part 1) is a blind transcriber. This module is the examiner.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.validation.clause_parser import ParsedClause

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The unified field alias map — canonical → known aliases.
#
# Copied from launch_pipeline._FIELD_NAME_ALIASES (inverted) +
# ExtractionReview.FIELD_ALIAS_MAP. This is the single authoritative
# source for validation matching. When a new alias is added to either
# extraction source, it must also land here.
# ---------------------------------------------------------------------------

_CANONICAL_ALIASES: Dict[str, List[str]] = {
    # Parties
    "seller": ["seller_name", "exporter", "exporter_name", "shipper"],
    "buyer": ["buyer_name", "importer", "importer_name", "consignee", "applicant"],
    "applicant": ["buyer", "buyer_name", "importer"],
    "beneficiary": ["seller", "seller_name", "exporter", "exporter_name", "insured_party"],
    "exporter": ["exporter_name", "seller", "seller_name"],
    "notify_party": ["notify", "notify_name", "notify_applicant"],
    # Cross-transaction references
    "lc_number": ["lc_no", "lc_reference", "lc_ref", "credit_number", "letter_of_credit_number", "reference_lc_no"],
    "buyer_purchase_order_number": ["buyer_po_number", "purchase_order_number", "purchase_order_no", "po_number", "po_no", "order_reference", "order_ref", "buyer_purchase_order_no", "reference_to_po", "po_reference"],
    "exporter_bin": ["exporter_bin_number", "bin_number", "bin", "bin_no", "seller_bin"],
    "exporter_tin": ["exporter_tin_number", "tin_number", "tin", "tin_no", "seller_tin"],
    # Transport / BL
    "vessel_name": ["vessel", "ship_name", "carrying_vessel"],
    "voyage_number": ["voyage_no", "voyage"],
    "container_number": ["container_no", "container"],
    "seal_number": ["seal_no", "seal"],
    "bl_number": ["bill_of_lading_number", "bl_no"],
    "port_of_loading": ["loading_port", "pol"],
    "port_of_discharge": ["discharge_port", "pod", "destination_port"],
    "on_board_date": ["shipped_on_board_date", "onboard_date"],
    # freight_terms is the canonical BL-schema key the multimodal extractor
    # emits (see multimodal_document_extractor DOC_TYPE_SCHEMAS). Without
    # this alias, every BL with "FREIGHT COLLECT"/"FREIGHT PREPAID" clauses
    # produced a Cluster-B false-positive "Freight Status missing" finding.
    "freight_status": ["freight", "freight_prepaid", "freight_collect", "freight_terms", "freight_payment"],
    "carrier_name": ["carrier", "shipping_line"],
    "gross_weight": ["gross_wt", "total_gross_weight"],
    "net_weight": ["net_wt", "total_net_weight"],
    "issue_date": ["bl_date", "date_of_issue", "issuance_date"],
    # Invoice
    "goods_description": ["description_of_goods", "goods", "merchandise"],
    "total_amount": ["invoice_amount", "total_value", "amount"],
    "unit_price": ["price_per_unit", "rate"],
    "quantity": ["qty", "total_quantity", "quantities", "total_qty"],
    "hs_code": ["hs_codes", "tariff_code"],
    # Insurance
    "coverage_percentage": ["insurance_coverage", "coverage"],
    "coverage_basis": ["insured_value_basis"],
    "risk_coverage": ["coverage_type", "risks_covered"],
    "war_risk_coverage": ["war_risk", "war_clause"],
    # COO
    "country_of_origin": ["origin_country", "country"],
    "issuing_authority": ["certifying_authority", "authority", "issuer"],
    # Packing
    "total_packages": ["number_of_packages", "total_cartons", "carton_count", "packages"],
    "size_breakdown": ["packing_size_breakdown", "sizes", "size_distribution"],
    # Inspection
    "certificate_number": ["inspection_number", "cert_number"],
    "inspection_agency": ["inspector", "inspection_company"],
    # LC MT700 aliases
    "form_of_documentary_credit": ["lc_type", "form_of_doc_credit", "credit_form"],
    "applicable_rules": ["ucp_reference", "rules", "applicable_uniform_rules"],
    "drafts_at": ["payment_terms", "tenor", "usance"],
}


# Arrays the LLM uses to hold per-line-item structure on multi-SKU docs
# (commercial invoice with 3 HS codes, inspection cert with 3 quantities,
# packing list with per-carton rows, …). When a canonical field is absent
# at the top level but every row of one of these arrays carries it, treat
# the field as "present" — otherwise a clean invoice with line items
# produces false-positive "quantity not found" / "hs_code not found" rows.
_LINE_ITEM_KEYS: Tuple[str, ...] = (
    "line_items",
    "goods_items",
    "items",
    "shipment_items",
    "invoice_items",
    "product_items",
)

# Fields that legitimately live per-row on multi-SKU docs. Drilling into
# line_items for `beneficiary` or `port_of_loading` would be nonsense, so
# the array scan only fires for these.
_PER_ROW_FIELDS: Set[str] = {
    "quantity",
    "unit_price",
    "hs_code",
    "hs_codes",
    "goods_description",
    "total_amount",
    "gross_weight",
    "net_weight",
    "item_description",
    "measurement_value",
}


def _is_field_value_present(val: Any) -> bool:
    """A field is considered present only if it's not empty. Confidence-wrapped
    dicts (``{"value": "...", "confidence": 0.9}``) count as present when the
    inner ``value`` is non-empty."""
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip() != ""
    if isinstance(val, (list, tuple, set)):
        return len(val) > 0
    if isinstance(val, dict):
        if not val:
            return False
        # confidence-wrapper pattern: {"value": ..., "confidence": ...}
        if "value" in val and "confidence" in val:
            return _is_field_value_present(val.get("value"))
        return True
    return True


# Verbs that signal a clause requirement is satisfied by a text statement
# on the document. An inspection certificate that says "Quantity confirmed."
# satisfies an LC clause "CONFIRMING ... QUANTITY" even when the extractor
# didn't carve out a dedicated ``quantity`` field — the qty is embedded in
# the finding statement, not stored as a separate scalar. Without this
# fallback we fire "Quantity not found on document" on a perfectly valid
# inspection cert and look broken to the operator.
_CONFIRMATION_VERB_RE = re.compile(
    r"\b(?:"
    r"confirm(?:ed|ing|s)?|certify(?:ing|ies|ied)?|verif(?:y|ied|ying|ies)|"
    r"stat(?:e|ed|ing|es)|attest(?:ed|ing|s)?|declar(?:ed|ing|es)|"
    r"find(?:ing|ings)?|satisfactory|found\s+to\s+be|ok|correct"
    r")\b",
    re.IGNORECASE,
)


def _clause_satisfied_by_text_evidence(
    canonical_field: str,
    extracted_fields: Dict[str, Any],
) -> bool:
    """Scan string values on a document for a confirmation statement about
    the canonical field. Returns True if the document's text clearly states
    the field's condition was satisfied — which is how inspection certs,
    beneficiary certs, and quality reports usually report on the items the
    LC asks them to confirm.

    We deliberately accept fairly loose phrasing ("Quality confirmed.",
    "Quantity confirmed.", "Packing confirmed to export standard.") because
    this is what real documents look like. False positives here would be
    clauses satisfied when they're not; in practice the opposite — firing
    a "not found" finding on a cert that clearly stated the fact — is the
    noisier failure mode.
    """
    if not canonical_field or not isinstance(extracted_fields, dict):
        return False

    field_human = canonical_field.replace("_", " ").strip()
    if not field_human:
        return False
    # Regex: field word(s) within ~40 chars of a confirmation verb, either order.
    pattern = re.compile(
        rf"(?:\b{re.escape(field_human)}\b[\s\S]{{0,40}}{_CONFIRMATION_VERB_RE.pattern}"
        rf"|{_CONFIRMATION_VERB_RE.pattern}[\s\S]{{0,40}}\b{re.escape(field_human)}\b)",
        re.IGNORECASE,
    )

    def _scan(val: Any) -> bool:
        if isinstance(val, str):
            return bool(pattern.search(val))
        if isinstance(val, list):
            return any(_scan(item) for item in val)
        if isinstance(val, dict):
            # Check the 'value' first (common confidence-wrap shape), then
            # recursively scan nested dict values for multi-line cert text.
            if "value" in val and _scan(val["value"]):
                return True
            return any(_scan(v) for v in val.values())
        return False

    return _scan(extracted_fields)


def _find_field_value(
    extracted_fields: Dict[str, Any],
    canonical_name: str,
) -> Optional[Any]:
    """
    Look up a field in extracted_fields by canonical name, then aliases.

    Search order:
      1. Direct lookup on canonical name.
      2. Direct lookup on each known alias.
      3. Case-insensitive lookup over all keys (catches ``Freight_Terms``
         vs ``freight_terms`` drift between extractor output shapes).
      4. For per-row fields (``quantity``, ``hs_code``, ``unit_price``, …),
         drill into ``line_items`` / ``goods_items`` / ``items`` arrays
         and return the collected per-row values if present.

    Returns the value if found and non-empty, else None.
    """
    if not isinstance(extracted_fields, dict):
        return None

    aliases = _CANONICAL_ALIASES.get(canonical_name, [])
    candidate_keys = (canonical_name, *aliases)

    # 1 + 2. Exact-case direct lookups on canonical + aliases.
    for key in candidate_keys:
        if key in extracted_fields:
            val = extracted_fields[key]
            if _is_field_value_present(val):
                return val

    # 3. Case-insensitive lookup over all extractor keys. Multiple extractor
    # paths (MT700 regex, multimodal LLM, ai_first text) normalize casing
    # differently, so the validator shouldn't care about it either.
    lowered = {str(k).lower(): v for k, v in extracted_fields.items()}
    for key in candidate_keys:
        val = lowered.get(key.lower())
        if _is_field_value_present(val):
            return val

    # 4. Drill into line-item arrays for per-row fields.
    if canonical_name in _PER_ROW_FIELDS:
        for li_key in _LINE_ITEM_KEYS:
            items = extracted_fields.get(li_key) or lowered.get(li_key)
            if not isinstance(items, list) or not items:
                continue
            collected: List[Any] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_lower = {str(k).lower(): v for k, v in item.items()}
                for key in candidate_keys:
                    candidate = item.get(key)
                    if not _is_field_value_present(candidate):
                        candidate = item_lower.get(key.lower())
                    if _is_field_value_present(candidate):
                        collected.append(candidate)
                        break
            if collected:
                return collected

    return None


# ---------------------------------------------------------------------------
# Finding shape (matches the plan spec)
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One validation finding — a discrepancy, advisory, or info note."""

    severity: str  # "discrepancy" | "advisory" | "info"
    document: str  # doc_type, e.g. "bill_of_lading"
    field: str  # canonical field name
    lc_clause: str  # raw 46A/47A clause text (truncated for display)
    expected: str
    found: str
    rule: str  # UCP600/ISBP745 reference
    explanation: str
    suggested_fix: str
    impact: str
    source_layer: str  # "clause_matcher"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "document": self.document,
            "field": self.field,
            "lc_clause": self.lc_clause,
            "expected": self.expected,
            "found": self.found,
            "rule": self.rule,
            "explanation": self.explanation,
            "suggested_fix": self.suggested_fix,
            "impact": self.impact,
            "source_layer": self.source_layer,
        }


# ---------------------------------------------------------------------------
# UCP600 rule references by doc type
# ---------------------------------------------------------------------------

_UCP_RULES: Dict[str, str] = {
    "bill_of_lading": "UCP600 Art 20",
    "air_waybill": "UCP600 Art 23",
    "commercial_invoice": "UCP600 Art 18",
    "insurance_certificate": "UCP600 Art 28",
    "insurance_policy": "UCP600 Art 28",
    "certificate_of_origin": "UCP600 Art 14",
    "packing_list": "UCP600 Art 14",
    "inspection_certificate": "UCP600 Art 14",
    "beneficiary_certificate": "UCP600 Art 14",
    "draft": "UCP600 Art 7",
}

_FIELD_EXPLANATIONS: Dict[str, str] = {
    "vessel_name": "A bill of lading must indicate the name of the carrying vessel per UCP600 Art 20(a)(ii).",
    "voyage_number": "The voyage number identifies the specific sailing; its absence may cause rejection.",
    "container_number": "Container number is required for containerized cargo per ISBP745.",
    "seal_number": "Seal number provides cargo integrity evidence.",
    "port_of_loading": "Port of loading must match the LC stipulation per UCP600 Art 20(a)(ii).",
    "port_of_discharge": "Port of discharge must match the LC stipulation per UCP600 Art 20(a)(ii).",
    "on_board_date": "On-board notation with date is required for shipped bills of lading per UCP600 Art 20(a)(ii).",
    "notify_party": "Notify party must match LC stipulation if specified.",
    "gross_weight": "Gross weight must appear on the BL when required by the LC.",
    "net_weight": "Net weight must appear on the BL when required by the LC.",
    "goods_description": "Goods description on the invoice must correspond to the LC description per UCP600 Art 18(c).",
    "lc_number": "LC reference number must appear on the document when the LC requires it.",
    "buyer_purchase_order_number": "PO number must appear on the document when the LC requires it.",
    "exporter_bin": "BIN must appear on the document when the LC requires it.",
    "exporter_tin": "TIN must appear on the document when the LC requires it.",
    "country_of_origin": "Country of origin must be stated on the certificate of origin.",
    "coverage_percentage": "Insurance coverage must be at least 110% of CIF value per UCP600 Art 28(f)(ii).",
    "total_packages": "Total package count must match across documents.",
}


# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------

def match_clauses_to_documents(
    clauses: List[ParsedClause],
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Walk each parsed clause and compare its requirements against the
    matching extracted document's fields.

    Args:
        clauses: Output from clause_parser.parse_lc_clauses().
        extracted_documents: List of dicts from the extraction snapshot,
            each with at least {"document_type": "...", "extracted_fields": {...}}.

    Returns:
        List of Finding for all missing/mismatched fields.
    """
    # Index documents by type for O(1) lookup
    docs_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        if dt:
            docs_by_type.setdefault(dt, []).append(doc)

    findings: List[Finding] = []

    for clause in clauses:
        if not clause.document_type:
            # Can't match clause without a doc type — skip
            continue

        matching_docs = docs_by_type.get(clause.document_type, [])

        if not matching_docs:
            # Document required by LC but not in the submission
            findings.append(Finding(
                severity="discrepancy",
                document=clause.document_type,
                field="",
                lc_clause=_truncate(clause.raw_text, 200),
                expected=f"{_humanize(clause.document_type)} required by LC",
                found="Document not submitted",
                rule=_UCP_RULES.get(clause.document_type, "UCP600 Art 14"),
                explanation=f"The LC requires a {_humanize(clause.document_type)} but none was found in the submission.",
                suggested_fix=f"Obtain and submit the required {_humanize(clause.document_type)}.",
                impact="Bank will reject. Missing required document.",
                source_layer="clause_matcher",
            ))
            continue

        # Check each required field against each matching document
        for req_field in clause.required_fields:
            for doc in matching_docs:
                fields = doc.get("extracted_fields") or doc.get("fields") or {}
                value = _find_field_value(fields, req_field)

                if value is None:
                    # Before raising "not found", check whether the document
                    # *verbally confirms* the field. Inspection certs and
                    # beneficiary certs routinely satisfy clauses like
                    # "CERTIFICATE CONFIRMING QUALITY, QUANTITY & PACKING"
                    # via a free-text finding statement ("Quantity confirmed.")
                    # rather than a structured scalar field. Skip the finding
                    # when such a statement is clearly present — otherwise
                    # we fire false positives on clean inspection / beneficiary
                    # docs and the operator stops trusting the tool.
                    if _clause_satisfied_by_text_evidence(req_field, fields):
                        logger.debug(
                            "Clause requirement %s on %s satisfied by text evidence",
                            req_field, clause.document_type,
                        )
                        continue

                    findings.append(Finding(
                        severity="discrepancy",
                        document=clause.document_type,
                        field=req_field,
                        lc_clause=_truncate(clause.raw_text, 200),
                        expected=f"{_humanize(req_field)} present on {_humanize(clause.document_type)}",
                        found="Not found on document",
                        rule=_UCP_RULES.get(clause.document_type, "UCP600 Art 14"),
                        explanation=_FIELD_EXPLANATIONS.get(
                            req_field,
                            f"The LC requires {_humanize(req_field)} on the {_humanize(clause.document_type)}."
                        ),
                        suggested_fix=f"Obtain an amended {_humanize(clause.document_type)} showing the {_humanize(req_field)}.",
                        impact="Bank may reject. Required field missing per LC clause.",
                        source_layer="clause_matcher",
                    ))

    # Deduplicate findings (same doc + field)
    seen = set()
    unique: List[Finding] = []
    for f in findings:
        key = (f.document, f.field)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    logger.info(
        "Clause matcher produced %d findings (%d before dedup) from %d clauses against %d documents",
        len(unique), len(findings), len(clauses), len(extracted_documents or []),
    )

    return unique


# ---------------------------------------------------------------------------
# Cross-document field consistency checks
# ---------------------------------------------------------------------------

def check_cross_document_consistency(
    lc_fields: Dict[str, Any],
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Check that key fields are consistent across documents:
    - Amount on invoice <= LC amount
    - Party names match across docs
    - Ports match LC stipulation
    - Insurance coverage >= 110% CIF (UCP600 Art 28(f)(ii))
    - BL vs Packing List weight consistency (ISBP745 L4)
    - Late shipment / stale documents / LC expiry (UCP600 Art 14(c), 6(d))
    - Goods description correspondence (UCP600 Art 18(c), 14(e))
    """
    findings: List[Finding] = []

    lc_amount = _extract_amount(lc_fields)
    lc_beneficiary = _normalize_party(lc_fields.get("beneficiary"))
    lc_applicant = _normalize_party(lc_fields.get("applicant"))
    lc_pol = _normalize_text(lc_fields.get("port_of_loading"))
    lc_pod = _normalize_text(lc_fields.get("port_of_discharge"))

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or ""
        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        # Amount check (invoice vs LC)
        if dt == "commercial_invoice" and lc_amount is not None:
            inv_amount = _extract_amount(fields)
            if inv_amount is not None and inv_amount > lc_amount:
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="total_amount",
                    lc_clause="LC Field 32B (Amount)",
                    expected=f"Invoice amount <= LC amount ({lc_amount})",
                    found=f"Invoice amount: {inv_amount}",
                    rule="UCP600 Art 18(b)",
                    explanation="The amount of the commercial invoice must not exceed the amount permitted by the credit.",
                    suggested_fix="Issue an amended invoice with amount not exceeding the LC value.",
                    impact="Bank will reject. Invoice exceeds credit amount.",
                    source_layer="crossdoc_matcher",
                ))

        # Port checks (BL vs LC)
        if dt == "bill_of_lading":
            doc_pol = _normalize_text(_find_field_value(fields, "port_of_loading"))
            doc_pod = _normalize_text(_find_field_value(fields, "port_of_discharge"))

            if lc_pol and doc_pol and not _ports_equivalent(lc_pol, doc_pol):
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="port_of_loading",
                    lc_clause="LC Field 44E (Port of Loading)",
                    expected=f"Port of loading: {lc_pol}",
                    found=f"BL shows: {doc_pol}",
                    rule="UCP600 Art 20(a)(ii)",
                    explanation="The port of loading on the bill of lading must match the LC stipulation.",
                    suggested_fix="Obtain an amended BL with the correct port of loading.",
                    impact="Bank will reject. Port mismatch.",
                    source_layer="crossdoc_matcher",
                ))

            if lc_pod and doc_pod and not _ports_equivalent(lc_pod, doc_pod):
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="port_of_discharge",
                    lc_clause="LC Field 44F (Port of Discharge)",
                    expected=f"Port of discharge: {lc_pod}",
                    found=f"BL shows: {doc_pod}",
                    rule="UCP600 Art 20(a)(ii)",
                    explanation="The port of discharge on the bill of lading must match the LC stipulation.",
                    suggested_fix="Obtain an amended BL with the correct port of discharge.",
                    impact="Bank will reject. Port mismatch.",
                    source_layer="crossdoc_matcher",
                ))

        # Beneficiary name check (all docs should name the beneficiary consistently)
        if lc_beneficiary:
            doc_beneficiary = _normalize_party(
                _find_field_value(fields, "beneficiary")
                or _find_field_value(fields, "seller")
                or _find_field_value(fields, "exporter")
            )
            if doc_beneficiary and not _fuzzy_match(lc_beneficiary, doc_beneficiary):
                findings.append(Finding(
                    severity="advisory",
                    document=dt,
                    field="beneficiary",
                    lc_clause="LC Field 59 (Beneficiary)",
                    expected=f"Beneficiary: {lc_beneficiary}",
                    found=f"Document shows: {doc_beneficiary}",
                    rule="UCP600 Art 14(d)",
                    explanation="Data in documents must not conflict with data in the LC or other stipulated documents.",
                    suggested_fix="Verify the beneficiary name matches across all documents.",
                    impact="May cause rejection if the discrepancy is material.",
                    source_layer="crossdoc_matcher",
                ))

    # --- Deterministic checks (delegated to specialized functions) ---
    findings.extend(check_insurance_coverage(lc_fields, extracted_documents))
    findings.extend(check_weight_consistency(extracted_documents))
    findings.extend(check_date_compliance(lc_fields, extracted_documents))
    findings.extend(check_goods_description_correspondence(lc_fields, extracted_documents))

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _humanize(snake: str) -> str:
    """Convert snake_case to Title Case for display."""
    return snake.replace("_", " ").title()


def _extract_amount(fields: Dict[str, Any]) -> Optional[float]:
    """Try to extract a numeric amount from various field shapes."""
    for key in ("amount", "total_amount", "invoice_amount"):
        val = fields.get(key)
        if val is None:
            continue
        if isinstance(val, dict):
            val = val.get("value") or val.get("amount")
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                cleaned = val.replace(",", "").replace(" ", "")
                # Strip currency prefix
                import re
                cleaned = re.sub(r"^[A-Z]{3}\s*", "", cleaned)
                return float(cleaned)
            except (ValueError, TypeError):
                pass
    return None


def _normalize_text(val: Any) -> Optional[str]:
    """Normalize a text value for comparison."""
    if val is None:
        return None
    if isinstance(val, dict):
        val = val.get("name") or val.get("value") or ""
    text = str(val).strip().upper()
    return text if text else None


def _normalize_party(val: Any) -> Optional[str]:
    """Normalize a party name for comparison."""
    if val is None:
        return None
    if isinstance(val, dict):
        val = val.get("name") or val.get("value") or ""
    text = str(val).strip().upper()
    # Remove common suffixes that vary across documents
    import re
    text = re.sub(r"\b(?:LTD|LIMITED|INC|CORP|LLC|PLC|GMBH|CO)\b\.?", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def _fuzzy_match(a: str, b: str) -> bool:
    """Simple fuzzy match — one string contains the other, or high overlap."""
    if not a or not b:
        return False
    a_upper = a.upper().strip()
    b_upper = b.upper().strip()
    if a_upper == b_upper:
        return True
    if a_upper in b_upper or b_upper in a_upper:
        return True
    # Token overlap: if 80%+ of tokens match
    a_tokens = set(a_upper.split())
    b_tokens = set(b_upper.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
    return overlap >= 0.75


def _strip_port_noise(port: str) -> str:
    """Strip country suffix and port qualifiers before UN/LOCODE resolution.

    Real-world extracted values look like ``"CHITTAGONG SEA PORT, BANGLADESH"``
    or ``"Port of Chattogram, Bangladesh"``. The UN/LOCODE resolver needs just
    the city token (``"Chittagong"`` / ``"Chattogram"``) — the surrounding
    country + qualifier words block alias matching.
    """
    if not port:
        return ""
    text = port.strip()
    # Drop everything after the first comma — usually the country name.
    if "," in text:
        text = text.split(",", 1)[0].strip()
    # Strip trailing port-qualifier words (order matters: multi-word first).
    text = re.sub(
        r"\s*\b(?:SEA\s*PORT|CONTAINER\s*PORT|AIRPORT|HARBOU?R|SEAPORT|PORT)\b\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    # Strip leading "Port of " prefix.
    text = re.sub(r"^\s*PORT\s+OF\s+", "", text, flags=re.IGNORECASE).strip()
    return text


def _ports_equivalent(port_a: Optional[str], port_b: Optional[str]) -> bool:
    """True when two extracted port strings refer to the same UN/LOCODE port.

    Tries the cheap fuzzy match first (handles simple spelling variants and
    substring cases), then falls back to the UN/LOCODE registry with noise
    stripped off both sides so aliases like ``CHITTAGONG`` / ``CHATTOGRAM`` and
    qualified forms like ``"CHITTAGONG SEA PORT, BANGLADESH"`` resolve
    correctly. Doing this inside ``doc_matcher`` means the crossdoc port
    checks no longer raise MAJOR/ADVISORY discrepancies for Bangladesh's 2018
    renaming (or any other registry alias).
    """
    if not port_a or not port_b:
        return False
    if _fuzzy_match(port_a, port_b):
        return True
    try:
        from app.reference_data.ports import get_port_registry
        registry = get_port_registry()
        if registry.same_port(_strip_port_noise(port_a), _strip_port_noise(port_b)):
            return True
    except Exception:  # noqa: BLE001 — never let the registry fail the validator
        logger.debug("Port registry lookup failed for %r vs %r", port_a, port_b, exc_info=True)
    return False


# ---------------------------------------------------------------------------
# Date parsing helper
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y%m%d",
]


def _parse_date(val: Any) -> Optional[date]:
    """Try to parse a date from various formats."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, dict):
        val = val.get("value") or val.get("date") or ""
    text = str(val).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # ISO-like with T
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Weight parsing helper
# ---------------------------------------------------------------------------

_WEIGHT_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:kgs?|kilograms?|kg\.?)?", re.IGNORECASE)


def _parse_weight(val: Any) -> Optional[float]:
    """Extract a numeric weight value, stripping units."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        val = val.get("value") or val.get("weight") or ""
    text = str(val).strip()
    if not text:
        return None
    m = _WEIGHT_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    # Plain number
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Insurance coverage helper
# ---------------------------------------------------------------------------

def _parse_coverage_percentage(val: Any) -> Optional[float]:
    """Parse a coverage percentage like '110%' or '110' into 110.0."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        val = val.get("value") or val.get("percentage") or ""
    text = str(val).strip().rstrip("%").strip()
    # Handle "110% of invoice value" free-text form.
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(val))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    try:
        return float(text)
    except ValueError:
        return None


def _parse_insured_amount(fields: Dict[str, Any]) -> Optional[float]:
    """Backwards-compatible wrapper around ``_parse_insured_amount_raw``
    that drops the raw form and returns only the numeric value.
    """
    parsed = _parse_insured_amount_raw(fields)
    return parsed[1] if parsed else None


def _parse_insured_amount_raw(fields: Dict[str, Any]) -> Optional[Tuple[Any, float]]:
    """Extract the insured/coverage amount from insurance fields, returning
    both the **raw** source value and its numeric form so callers can decide
    whether the value is actually dollars or a percentage mis-stored in an
    amount field.
    """
    for key in ("insured_amount", "coverage_amount", "sum_insured", "insured_value", "amount"):
        val = fields.get(key)
        if val is None:
            continue
        raw = val
        if isinstance(val, dict):
            val = val.get("value") or val.get("amount")
            raw = val
        if isinstance(val, (int, float)):
            return raw, float(val)
        if isinstance(val, str):
            try:
                cleaned = val.replace(",", "").replace(" ", "")
                cleaned = re.sub(r"^[A-Z]{3}\s*", "", cleaned)
                return raw, float(cleaned)
            except (ValueError, TypeError):
                pass
    return None


# Words that, when they appear in 46A `documents_required` or 47A
# `additional_conditions`, signal that the credit calls for an insurance
# document and therefore UCP600 Art 28 coverage rules apply. The list is
# trade-finance vocabulary, not jurisdictional hardcoding — any LC that
# requires insurance will use one of these phrases somewhere.
_INSURANCE_REQUIREMENT_KEYWORDS = re.compile(
    r"\b("
    r"insurance|marine\s+insurance|cargo\s+insurance|"
    r"insurance\s+(?:certificate|policy|document)|"
    r"all[\s-]*risks?|war\s+risks?|strikes?\s+clause|"
    r"institute\s+cargo\s+clauses|icc\s*\([abc]\)|"
    r"wa\b|fpa\b"
    r")\b",
    re.IGNORECASE,
)


def _flatten_clause_text(val: Any) -> str:
    """Flatten an arbitrary LC clause value (string / list of strings / list
    of dicts / dict) to a single searchable text blob."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts: List[str] = []
        for item in val:
            if isinstance(item, dict):
                # Prefer the raw clause text when the extractor wraps clauses.
                parts.append(
                    str(item.get("text") or item.get("clause") or item.get("value") or "")
                )
                # Also include the whole dict as a fallback so nothing is lost.
                parts.append(json.dumps(item, default=str))
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p)
    if isinstance(val, dict):
        return json.dumps(val, default=str)
    return str(val)


def _lc_requires_insurance(lc_fields: Dict[str, Any]) -> bool:
    """Does this LC require an insurance document?

    Per UCP600 Art 28(a) the coverage check only applies when the credit
    calls for an insurance document. Per Art 14(g), a document presented
    but not required by the credit is disregarded. So the right gate is
    "does 46A / 47A / the requirements graph mention insurance?" — NOT
    the Incoterm (which is only a correlated signal).

    Returns True when any of:
      - 46A ``documents_required`` clause mentions an insurance keyword.
      - 47A ``additional_conditions`` clause mentions an insurance keyword.
      - ``requirements_graph_v1.required_document_types`` includes an
        insurance family.
    """
    if not isinstance(lc_fields, dict):
        return False

    # Structured clause fields (46A / 47A and their aliases).
    for key in (
        "documents_required",
        "documents_required_detailed",
        "additional_conditions",
        "46A", "47A",
    ):
        text = _flatten_clause_text(lc_fields.get(key))
        if text and _INSURANCE_REQUIREMENT_KEYWORDS.search(text):
            return True

    # Fact-graph signal: the requirements graph carries normalized doc
    # families extracted from the clauses. If it contains any insurance
    # family, the LC requires an insurance document.
    graph = lc_fields.get("requirements_graph_v1") or lc_fields.get("requirementsGraphV1")
    if isinstance(graph, dict):
        required_types = graph.get("required_document_types") or []
        if isinstance(required_types, list):
            for dt in required_types:
                token = str(dt or "").strip().lower()
                if "insurance" in token:
                    return True
        # Some graph builds nest the list under required_documents[].
        for entry in graph.get("required_documents") or []:
            if isinstance(entry, dict):
                entry_type = str(entry.get("document_type") or "").lower()
                if "insurance" in entry_type:
                    return True
            elif isinstance(entry, str) and "insurance" in entry.lower():
                return True

    return False


def _value_is_dollar_amount(raw: Any, numeric: float, lc_amount: float) -> bool:
    """Tell apart a dollar amount from a percentage value mis-stored in
    an amount field.

    Signals (in order of authority, no absolute thresholds):
      1. The raw textual form contains a ``%`` sign → it's a percentage.
      2. The raw textual form carries a currency code (USD, EUR, …) or
         typical numeric formatting (thousands separator) → it's dollars.
      3. Falling back to magnitude comparison against the LC amount:
         genuine insured amounts on an LC are at least 1% of the LC
         amount (usually 100%+). A naked small number that's < 1% of the
         LC amount is almost certainly the percentage mis-stored in the
         amount slot.
    """
    if isinstance(raw, str):
        text = raw.strip()
        if "%" in text:
            return False
        if re.search(r"\b[A-Z]{3}\b", text.upper()):
            return True
        # A string with thousands separators or a decimal point almost
        # always came off an amount field on a real document.
        if "," in text or re.search(r"\d+\.\d{2}\b", text):
            return True

    # Magnitude-based fallback: proportion against the LC amount.
    if lc_amount > 0:
        ratio = abs(numeric) / lc_amount
        if ratio < 0.01:   # value is < 1% of LC amount
            return False   # almost certainly a percentage, not dollars

    return True


# ---------------------------------------------------------------------------
# Goods description keyword matching
# ---------------------------------------------------------------------------

# Noise words to exclude from keyword matching
_GOODS_STOPWORDS: Set[str] = {
    "THE", "A", "AN", "AND", "OR", "OF", "IN", "TO", "FOR", "ON", "AT",
    "BY", "AS", "IS", "ARE", "WITH", "FROM", "PER", "ALL", "ANY", "EACH",
    "NO", "NOT", "BE", "BEEN", "BEING", "HAVE", "HAS", "HAD", "DO", "DOES",
    "DID", "WILL", "SHALL", "SHOULD", "WOULD", "COULD", "MAY", "MIGHT",
    "MUST", "THAT", "THIS", "THESE", "THOSE", "WHICH", "WHO", "WHOM",
    "WHAT", "WHERE", "WHEN", "HOW", "IF", "THAN", "THEN", "SO", "SUCH",
    "ONLY", "ALSO", "ABOUT", "ABOVE", "AFTER", "BEFORE", "BETWEEN",
    "UNDER", "OVER", "THROUGH", "DURING", "UNTIL", "INTO", "UPON",
    # Trade-finance boilerplate
    "LC", "CREDIT", "DOCUMENTARY", "REQUIRED", "DOCUMENTS", "DOCUMENT",
    "FOLLOWING", "MENTIONED", "STATED", "SPECIFIED", "ACCORDANCE",
    "HEREWITH", "THEREOF", "THEREIN", "HEREIN", "HEREBY",
}


def _extract_goods_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from a goods description."""
    if not text:
        return set()
    # Normalize
    upper = text.upper()
    # Split on non-alpha (keep numbers for quantities)
    tokens = re.findall(r"[A-Z0-9]+(?:[./%-][A-Z0-9]+)*", upper)
    # Filter stopwords and very short tokens
    return {t for t in tokens if len(t) > 2 and t not in _GOODS_STOPWORDS}


# HS codes are 6 to 10 digits. Matching all LC HS codes on the invoice is
# the most authoritative correspondence signal UCP600 Art 18(c) recognises
# — the description doesn't have to be word-for-word, but it must not
# conflict, and matching classification codes is about as unambiguous as it
# gets. Quantity numbers (e.g. 30,000) are a strong secondary signal.
_HS_CODE_RE = re.compile(r"\b(\d{6,10})\b")
_QUANTITY_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d{4,})\b")  # 3,000 / 30,000 / 12000


def _extract_hs_codes(text: str) -> Set[str]:
    """Pull all HS-code-shaped numbers out of a goods description."""
    if not text:
        return set()
    # Accept HS codes with separators too: "6109.1000", "6109 1000"
    normalized = re.sub(r"[.\s]+", "", text)
    return set(_HS_CODE_RE.findall(normalized))


def _extract_quantities(text: str) -> Set[str]:
    """Pull quantity-shaped numbers (normalized without thousands separators)."""
    if not text:
        return set()
    raw = _QUANTITY_RE.findall(text)
    return {q.replace(",", "") for q in raw}


def check_goods_description_correspondence(
    lc_fields: Dict[str, Any],
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Check that the goods description on invoice and BL corresponds to the
    LC goods description per UCP600 Art 18(c) / Art 14(e).

    The invoice description must NOT be inconsistent with the LC.
    Other documents may use general terms (ISBP745 D1).
    """
    lc_goods = _normalize_text(
        lc_fields.get("goods_description")
        or lc_fields.get("description_of_goods")
        or (lc_fields.get("mt700") or {}).get("goods_description")
        or (lc_fields.get("mt700") or {}).get("45A")
    )
    if not lc_goods:
        return []

    lc_keywords = _extract_goods_keywords(lc_goods)
    lc_hs_codes = _extract_hs_codes(lc_goods)
    lc_quantities = _extract_quantities(lc_goods)
    if len(lc_keywords) < 2 and not lc_hs_codes:
        return []

    findings: List[Finding] = []

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        # Build a joined text blob of the fields that plausibly carry goods
        # info on this doc (description + line-item arrays + HS/quantity
        # scalars). This way we correspond on what's actually printed, not
        # on whether the extractor happened to nail the exact key name.
        doc_goods_parts: List[str] = []
        primary = _normalize_text(_find_field_value(fields, "goods_description"))
        if primary:
            doc_goods_parts.append(primary)
        for key in ("hs_code", "hs_codes", "quantity", "total_quantity",
                    "line_items", "goods_items", "items", "inspected_goods"):
            v = fields.get(key)
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                doc_goods_parts.append(" ".join(str(x) for x in v))
            elif isinstance(v, dict):
                doc_goods_parts.append(json.dumps(v, default=str))
            else:
                doc_goods_parts.append(str(v))
        doc_goods = " ".join(doc_goods_parts).upper() if doc_goods_parts else None
        if not doc_goods:
            continue

        doc_keywords = _extract_goods_keywords(doc_goods)
        doc_hs_codes = _extract_hs_codes(doc_goods)
        doc_quantities = _extract_quantities(doc_goods)

        # Overlap ratio (secondary signal, now used only when HS/qty are absent)
        overlap = len(lc_keywords & doc_keywords)
        lc_coverage = overlap / len(lc_keywords) if lc_keywords else 0

        # Authoritative signals (UCP600 Art 18(c) — "correspond to"):
        #   1. If the LC lists HS codes and the invoice lists them all, the
        #      goods are classified the same and the description corresponds
        #      in the sense the regulation cares about.
        #   2. If the LC lists quantities and the invoice shows them all,
        #      strong secondary confirmation of the same goods.
        #   3. Otherwise fall back to keyword overlap, but at a realistic
        #      threshold (25% for an invoice, not 40%) — LC text contains
        #      packaging/marking prose the invoice legitimately omits.
        hs_match = bool(lc_hs_codes) and lc_hs_codes.issubset(doc_hs_codes)
        qty_match = bool(lc_quantities) and lc_quantities.issubset(doc_quantities)

        if dt == "commercial_invoice":
            # If HS codes all match OR (HS + qty) both match, it
            # corresponds — no finding regardless of keyword overlap.
            if hs_match or (lc_hs_codes and lc_quantities and hs_match and qty_match):
                continue
            # Fallback keyword threshold — lowered from 40% to 25%.
            if lc_coverage < 0.25:
                missing_kw = lc_keywords - doc_keywords
                sample = ", ".join(sorted(missing_kw)[:5])
                expected = "Invoice goods description must correspond to LC"
                if lc_hs_codes:
                    expected += f" (LC HS codes: {', '.join(sorted(lc_hs_codes))})"
                findings.append(Finding(
                    severity="advisory" if lc_coverage >= 0.15 else "discrepancy",
                    document=dt,
                    field="goods_description",
                    lc_clause="LC Field 45A (Goods Description)",
                    expected=expected,
                    found=(
                        f"Invoice keywords overlap {overlap}/{len(lc_keywords)} "
                        f"({lc_coverage:.0%}). Missing: {sample}"
                    ),
                    rule="UCP600 Art 18(c)",
                    explanation="The description of goods in the commercial invoice must correspond to the description in the credit. "
                                "Key product terms from the LC are not reflected in the invoice.",
                    suggested_fix="Amend the commercial invoice to include the goods description as stated in the LC.",
                    impact="Bank will reject. Goods description on invoice does not correspond to LC.",
                    source_layer="crossdoc_matcher",
                ))
        elif dt == "bill_of_lading":
            # BL may use general terms, but should not conflict (Art 14(e))
            if lc_coverage < 0.25:
                findings.append(Finding(
                    severity="advisory",
                    document=dt,
                    field="goods_description",
                    lc_clause="LC Field 45A (Goods Description)",
                    expected=f"BL goods description should not conflict with LC",
                    found=f"Low keyword overlap: {overlap}/{len(lc_keywords)} ({lc_coverage:.0%})",
                    rule="UCP600 Art 14(e)",
                    explanation="Transport documents may use general terms for goods not inconsistent with the LC, "
                                "but very low overlap may indicate a conflict.",
                    suggested_fix="Verify that the BL goods description is not inconsistent with the LC.",
                    impact="May cause rejection if the bank considers it inconsistent.",
                    source_layer="crossdoc_matcher",
                ))

    return findings


# ---------------------------------------------------------------------------
# Insurance coverage check — UCP600 Art 28(f)(ii)
# ---------------------------------------------------------------------------

def check_insurance_coverage(
    lc_fields: Dict[str, Any],
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Verify insurance covers at least 110% of CIF/CIP value.

    UCP600 Art 28(a) + Art 14(g):
      - The coverage check only applies when the credit calls for an
        insurance document. If 46A / 47A / the requirements graph don't
        ask for one, any insurance cert in the presentation is
        disregarded (Art 14(g)) — so firing a coverage finding against
        it would be noise.

    UCP600 Art 28(f)(ii):
      - When the credit does call for insurance and no percentage is
        specified, coverage must be >= 110% of the CIF or CIP value.

    Two layers of truth:
      1. If the certificate states a coverage percentage, that's
         authoritative per Art 28(f)(ii) — don't fall through to the
         amount-based check (the amount field on a percentage-denominated
         certificate is often the percent itself mis-stored).
      2. Otherwise, check insured amount vs 110% of the LC amount — but
         only if the value genuinely looks like dollars, not a percentage
         that landed in an amount slot.
    """
    lc_amount = _extract_amount(lc_fields)
    if lc_amount is None or lc_amount <= 0:
        return []

    # Art 28(a) gate: does the credit require an insurance document at all?
    # Driven by the LC text (46A / 47A / requirements graph), not by the
    # Incoterm. An FOB LC that explicitly asks for an insurance certificate
    # still needs the coverage check; a CIF LC that doesn't mention
    # insurance (vanishingly rare but possible) doesn't.
    if not _lc_requires_insurance(lc_fields):
        logger.info(
            "Skipping insurance coverage check — LC does not require an "
            "insurance document (46A/47A silent, requirements graph has no "
            "insurance family). Per UCP600 Art 14(g), extra docs are disregarded."
        )
        return []

    findings: List[Finding] = []

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        if dt not in ("insurance_certificate", "insurance_policy", "insurance"):
            continue

        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        # Layer 1 — percentage is authoritative per Art 28(f)(ii).
        coverage_pct = _parse_coverage_percentage(
            _find_field_value(fields, "coverage_percentage")
        )
        if coverage_pct is not None:
            if coverage_pct < 110:
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="coverage_percentage",
                    lc_clause="UCP600 Art 28(f)(ii)",
                    expected="Insurance coverage >= 110% of CIF/CIP value",
                    found=f"Coverage: {coverage_pct}%",
                    rule="UCP600 Art 28(f)(ii)",
                    explanation="Insurance must cover at least 110% of the CIF or CIP value of the goods. "
                                "If the credit does not specify a percentage, 110% is the minimum.",
                    suggested_fix=f"Obtain amended insurance with coverage of at least 110% (i.e., {lc_amount * 1.1:,.2f}).",
                    impact="Bank will reject. Insurance coverage below minimum 110%.",
                    source_layer="crossdoc_matcher",
                ))
            # Percentage is authoritative — don't also fire on the amount.
            continue

        # Layer 2 — amount-based check. Only meaningful if the extracted
        # value IS a dollar amount, not a percentage mis-stored in the
        # amount slot. The classifier looks at the raw form (%, currency
        # code, formatting) AND compares magnitude to the LC amount, so
        # there's no absolute threshold: a tiny insured amount on a large
        # LC is recognised as unit-less regardless of the LC size.
        parsed = _parse_insured_amount_raw(fields)
        if parsed is None:
            continue
        raw_value, insured_amount = parsed

        if not _value_is_dollar_amount(raw_value, insured_amount, lc_amount):
            logger.info(
                "Skipping insurance amount check — value %r on %s doesn't "
                "classify as a dollar amount (likely a percentage in the "
                "amount slot). LC amount %.2f.",
                raw_value, dt, lc_amount,
            )
            continue

        min_required = lc_amount * 1.10
        if insured_amount < min_required:
            actual_pct = (insured_amount / lc_amount) * 100
            findings.append(Finding(
                severity="discrepancy",
                document=dt,
                field="insured_amount",
                lc_clause="UCP600 Art 28(f)(ii)",
                expected=f"Insured amount >= {min_required:,.2f} (110% of LC amount {lc_amount:,.2f})",
                found=f"Insured amount: {insured_amount:,.2f} ({actual_pct:.1f}% of LC amount)",
                rule="UCP600 Art 28(f)(ii)",
                explanation="The insured amount must be at least 110% of the CIF or CIP value.",
                suggested_fix=f"Obtain amended insurance covering at least {min_required:,.2f}.",
                impact="Bank will reject. Insured amount below 110% of credit value.",
                source_layer="crossdoc_matcher",
            ))

    return findings


# ---------------------------------------------------------------------------
# BL vs Packing List weight consistency
# ---------------------------------------------------------------------------

def check_weight_consistency(
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Check that gross weight on the BL matches the packing list.
    ISBP745 para L4: weight on transport document must match packing list.
    """
    bl_gross: Optional[float] = None
    pl_gross: Optional[float] = None
    bl_net: Optional[float] = None
    pl_net: Optional[float] = None

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        if dt == "bill_of_lading":
            bl_gross = _parse_weight(_find_field_value(fields, "gross_weight"))
            bl_net = _parse_weight(_find_field_value(fields, "net_weight"))
        elif dt == "packing_list":
            pl_gross = _parse_weight(_find_field_value(fields, "gross_weight"))
            pl_net = _parse_weight(_find_field_value(fields, "net_weight"))

    findings: List[Finding] = []

    if bl_gross is not None and pl_gross is not None:
        # Allow 1% tolerance for rounding
        diff = abs(bl_gross - pl_gross)
        tolerance = max(bl_gross, pl_gross) * 0.01
        if diff > tolerance:
            findings.append(Finding(
                severity="discrepancy",
                document="bill_of_lading",
                field="gross_weight",
                lc_clause="Packing List gross weight",
                expected=f"BL gross weight should match Packing List: {pl_gross:,.2f} kg",
                found=f"BL shows: {bl_gross:,.2f} kg (difference: {diff:,.2f} kg)",
                rule="ISBP745 L4",
                explanation="The gross weight stated on the bill of lading must be consistent "
                            "with the gross weight on the packing list.",
                suggested_fix="Reconcile the gross weight between the BL and packing list. "
                              "Obtain amended documents if needed.",
                impact="Bank may reject. Weight discrepancy between transport document and packing list.",
                source_layer="crossdoc_matcher",
            ))

    if bl_net is not None and pl_net is not None:
        diff = abs(bl_net - pl_net)
        tolerance = max(bl_net, pl_net) * 0.01
        if diff > tolerance:
            findings.append(Finding(
                severity="advisory",
                document="bill_of_lading",
                field="net_weight",
                lc_clause="Packing List net weight",
                expected=f"BL net weight should match Packing List: {pl_net:,.2f} kg",
                found=f"BL shows: {bl_net:,.2f} kg (difference: {diff:,.2f} kg)",
                rule="ISBP745 L4",
                explanation="The net weight on the bill of lading should be consistent "
                            "with the net weight on the packing list.",
                suggested_fix="Verify the net weight figures and reconcile if necessary.",
                impact="May cause rejection if the discrepancy is material.",
                source_layer="crossdoc_matcher",
            ))

    return findings


# ---------------------------------------------------------------------------
# Date validation — late shipment, stale docs, LC expiry
# ---------------------------------------------------------------------------

def check_date_compliance(
    lc_fields: Dict[str, Any],
    extracted_documents: List[Dict[str, Any]],
) -> List[Finding]:
    """
    Check date-related compliance:
    1. Late shipment — BL on-board date > LC latest shipment date (UCP600 Art 14(c))
    2. Stale documents — presentation > 21 days after shipment (UCP600 Art 14(c))
    3. LC expired — current date or BL date > LC expiry date (UCP600 Art 6(d))
    """
    lc_latest_shipment = _parse_date(
        lc_fields.get("latest_shipment_date")
        or lc_fields.get("latest_date_of_shipment")
        or (lc_fields.get("mt700") or {}).get("latest_shipment_date")
        or (lc_fields.get("mt700") or {}).get("44C")
    )
    lc_expiry = _parse_date(
        lc_fields.get("expiry_date")
        or lc_fields.get("date_of_expiry")
        or (lc_fields.get("mt700") or {}).get("expiry_date")
        or (lc_fields.get("mt700") or {}).get("31D")
    )
    lc_presentation_period = None
    pp_val = (
        lc_fields.get("presentation_period")
        or lc_fields.get("period_for_presentation")
        or (lc_fields.get("mt700") or {}).get("48")
    )
    if pp_val:
        # Try to extract number of days
        pp_str = str(pp_val).strip()
        m = re.search(r"(\d+)\s*(?:days?|calendar days?)", pp_str, re.IGNORECASE)
        if m:
            lc_presentation_period = int(m.group(1))
    # Default per UCP600 Art 14(c): 21 calendar days
    if lc_presentation_period is None:
        lc_presentation_period = 21

    findings: List[Finding] = []
    bl_on_board: Optional[date] = None

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        if dt == "bill_of_lading":
            bl_on_board = _parse_date(
                _find_field_value(fields, "on_board_date")
                or _find_field_value(fields, "issue_date")
            )
            if bl_on_board is None:
                continue

            # 1. Late shipment check
            if lc_latest_shipment and bl_on_board > lc_latest_shipment:
                days_late = (bl_on_board - lc_latest_shipment).days
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="on_board_date",
                    lc_clause=f"LC Field 44C (Latest Shipment Date: {lc_latest_shipment.isoformat()})",
                    expected=f"Shipment on or before {lc_latest_shipment.isoformat()}",
                    found=f"BL on-board date: {bl_on_board.isoformat()} ({days_late} days late)",
                    rule="UCP600 Art 14(c)",
                    explanation="The shipment date on the bill of lading exceeds the latest date "
                                "of shipment specified in the credit.",
                    suggested_fix="Late shipment cannot be cured by amendment after the fact. "
                                  "Request an LC amendment extending the latest shipment date, "
                                  "or negotiate with the issuing bank.",
                    impact="Bank will reject. Late shipment is a non-waivable discrepancy.",
                    source_layer="crossdoc_matcher",
                ))

            # 2. Stale documents check
            today = date.today()
            deadline = bl_on_board + timedelta(days=lc_presentation_period)
            if lc_expiry:
                deadline = min(deadline, lc_expiry)
            if today > deadline:
                days_stale = (today - deadline).days
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="presentation_deadline",
                    lc_clause=f"UCP600 Art 14(c) — {lc_presentation_period} days from shipment",
                    expected=f"Documents presented by {deadline.isoformat()} "
                             f"({lc_presentation_period} days from shipment {bl_on_board.isoformat()})",
                    found=f"Today is {today.isoformat()} — {days_stale} days past deadline",
                    rule="UCP600 Art 14(c)",
                    explanation="Documents must be presented within the period specified in the LC "
                                f"(or 21 days after shipment if not specified). "
                                f"The presentation deadline was {deadline.isoformat()}.",
                    suggested_fix="Contact the issuing bank urgently to discuss late presentation. "
                                  "Request an LC amendment if possible.",
                    impact="Bank will reject. Stale documents (late presentation).",
                    source_layer="crossdoc_matcher",
                ))

    # 3. LC expiry check (independent of BL)
    if lc_expiry:
        today = date.today()
        if today > lc_expiry:
            days_past = (today - lc_expiry).days
            findings.append(Finding(
                severity="discrepancy",
                document="letter_of_credit",
                field="expiry_date",
                lc_clause=f"LC Field 31D (Expiry Date: {lc_expiry.isoformat()})",
                expected=f"LC valid until {lc_expiry.isoformat()}",
                found=f"LC expired {days_past} days ago (today: {today.isoformat()})",
                rule="UCP600 Art 6(d)(i)",
                explanation="The credit has expired. No presentation can be made under an expired credit.",
                suggested_fix="Do not present documents under this LC. Contact the issuing bank "
                              "to request an extension or a new credit.",
                impact="Bank will reject. Credit has expired.",
                source_layer="crossdoc_matcher",
            ))

    return findings
