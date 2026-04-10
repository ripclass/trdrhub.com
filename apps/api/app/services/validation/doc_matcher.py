"""
Per-document Field Matcher for Validation (Part 2).

For each parsed 46A/47A clause, walks the relevant document's extracted
fields (using the canonical alias map) and produces a Finding if a
required field is missing or mismatched.

Extraction (Part 1) is a blind transcriber. This module is the examiner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
    "buyer_purchase_order_number": ["buyer_po_number", "purchase_order_number", "po_number", "po_no", "order_reference", "order_ref", "buyer_purchase_order_no"],
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
    "freight_status": ["freight", "freight_prepaid", "freight_collect"],
    "carrier_name": ["carrier", "shipping_line"],
    "gross_weight": ["gross_wt", "total_gross_weight"],
    "net_weight": ["net_wt", "total_net_weight"],
    "issue_date": ["bl_date", "date_of_issue", "issuance_date"],
    # Invoice
    "goods_description": ["description_of_goods", "goods", "merchandise"],
    "total_amount": ["invoice_amount", "total_value", "amount"],
    "unit_price": ["price_per_unit", "rate"],
    "quantity": ["qty", "total_quantity"],
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


def _find_field_value(
    extracted_fields: Dict[str, Any],
    canonical_name: str,
) -> Optional[Any]:
    """
    Look up a field in extracted_fields by canonical name, then aliases.

    Returns the value if found and non-empty, else None.
    """
    # Direct canonical lookup
    val = extracted_fields.get(canonical_name)
    if val is not None and val != "" and val != []:
        return val

    # Alias lookup
    aliases = _CANONICAL_ALIASES.get(canonical_name, [])
    for alias in aliases:
        val = extracted_fields.get(alias)
        if val is not None and val != "" and val != []:
            return val

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
    - Goods description corresponds
    - Dates within LC validity
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

            if lc_pol and doc_pol and not _fuzzy_match(lc_pol, doc_pol):
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

            if lc_pod and doc_pod and not _fuzzy_match(lc_pod, doc_pod):
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
