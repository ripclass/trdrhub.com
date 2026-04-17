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
    """Extract the insured/coverage amount from insurance fields."""
    for key in ("insured_amount", "coverage_amount", "sum_insured", "insured_value", "amount"):
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
                cleaned = re.sub(r"^[A-Z]{3}\s*", "", cleaned)
                return float(cleaned)
            except (ValueError, TypeError):
                pass
    return None


# Incoterms under which the BUYER arranges insurance. When the LC uses one
# of these, UCP600 Art 28 doesn't require the seller to present insurance —
# the seller-side insurance-coverage check is a no-op, not a discrepancy.
# (Art 28 only governs "insurance documents when required by the credit".)
_BUYER_ARRANGES_INSURANCE_INCOTERMS: Set[str] = {
    "FOB", "FCA", "EXW", "FAS",   # buyer arranges carriage + insurance
    "CFR", "CPT",                  # seller arranges carriage but NOT insurance
}


def _extract_incoterm(lc_fields: Dict[str, Any]) -> Optional[str]:
    """Pull the Incoterm abbreviation out of the LC. Accepts the field under
    multiple common keys; handles free-text forms like 'FOB Chittagong' by
    taking the 3-letter prefix.
    """
    if not isinstance(lc_fields, dict):
        return None
    for key in ("incoterm", "terms_of_delivery", "delivery_terms", "trade_terms"):
        val = lc_fields.get(key)
        if val is None:
            continue
        if isinstance(val, dict):
            val = val.get("value") or val.get("code") or ""
        text = str(val).strip().upper()
        if not text:
            continue
        m = re.match(r"(FOB|FCA|EXW|FAS|CFR|CPT|CIF|CIP|DAP|DPU|DDP)\b", text)
        if m:
            return m.group(1)
        return text  # return raw when we can't pattern-match — caller handles
    return None


# A coverage/insured amount below this floor is treated as unit-less (almost
# certainly the percentage value mis-stored in the amount slot: "Coverage:
# 110% of invoice value" → LLM wrote 110 into coverage_amount). Small real-
# world insurance amounts exist (e.g. courier policies) but in the LC trade-
# finance context the insured amount is always at least invoice-sized. If
# the LC amount is under 1 000 we don't apply this heuristic at all — the
# test set might be a unit test or a malformed extraction.
_INSURED_AMOUNT_UNITLESS_FLOOR = 1000.0


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
    if len(lc_keywords) < 2:
        return []

    findings: List[Finding] = []

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        doc_goods = _normalize_text(
            _find_field_value(fields, "goods_description")
        )
        if not doc_goods:
            continue

        doc_keywords = _extract_goods_keywords(doc_goods)
        if not doc_keywords:
            continue

        # Overlap ratio: what fraction of LC keywords appear in the doc
        overlap = len(lc_keywords & doc_keywords)
        lc_coverage = overlap / len(lc_keywords) if lc_keywords else 0

        if dt == "commercial_invoice":
            # Invoice must correspond to LC description — stricter threshold
            if lc_coverage < 0.40:
                missing_kw = lc_keywords - doc_keywords
                sample = ", ".join(sorted(missing_kw)[:5])
                findings.append(Finding(
                    severity="discrepancy",
                    document=dt,
                    field="goods_description",
                    lc_clause="LC Field 45A (Goods Description)",
                    expected=f"Invoice goods description must correspond to LC. LC keywords: {', '.join(sorted(lc_keywords)[:8])}",
                    found=f"Invoice keywords overlap {overlap}/{len(lc_keywords)} ({lc_coverage:.0%}). Missing: {sample}",
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
    UCP600 Art 28(f)(ii): If no percentage is specified in the credit,
    insurance must cover at least 110% of the CIF or CIP value.

    Skipped entirely when the LC's Incoterm (FOB / FCA / EXW / FAS / CFR /
    CPT) leaves insurance to the buyer — UCP600 Art 28 only governs
    insurance documents the credit calls for, and none of these Incoterms
    require the seller to present one.
    """
    lc_amount = _extract_amount(lc_fields)
    if lc_amount is None or lc_amount <= 0:
        return []

    # Short-circuit on buyer-arranges-insurance Incoterms. Firing this check
    # against an FOB LC used to produce a MAJOR false-positive that read
    # "insured amount 110.00" on a certificate the LC never required.
    incoterm = _extract_incoterm(lc_fields)
    if incoterm and incoterm.upper() in _BUYER_ARRANGES_INSURANCE_INCOTERMS:
        logger.info(
            "Skipping insurance coverage check — LC Incoterm %s leaves insurance to buyer.",
            incoterm,
        )
        return []

    findings: List[Finding] = []

    for doc in (extracted_documents or []):
        dt = doc.get("document_type") or doc.get("doc_type") or ""
        if dt not in ("insurance_certificate", "insurance_policy", "insurance"):
            continue

        fields = doc.get("extracted_fields") or doc.get("fields") or {}

        # Check via explicit coverage percentage. When a percentage is
        # stated on the certificate that IS the authoritative answer
        # per UCP600 Art 28(f)(ii); never fall through to the amount
        # check for the same document — the amount field on a percentage-
        # denominated certificate is often the percent itself mis-stored.
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
            # Percentage is authoritative — skip the amount-based check.
            continue

        # Check via insured amount vs LC amount.
        insured_amount = _parse_insured_amount(fields)
        if insured_amount is None or lc_amount <= 0:
            continue

        # Detect the percent-in-amount-slot trap. If the certificate reads
        # "Coverage: 110% of invoice value" and the LLM stored the 110 in
        # coverage_amount instead of coverage_percentage, treating it as
        # dollars compares $110 to $504 625 and fires a garbage finding.
        # Heuristic: an insured amount far below any realistic insurance
        # figure (< $1 000), on an LC that is clearly commercial-scale,
        # is almost certainly the percentage value misplaced.
        if (
            insured_amount < _INSURED_AMOUNT_UNITLESS_FLOOR
            and lc_amount >= _INSURED_AMOUNT_UNITLESS_FLOOR
        ):
            logger.info(
                "Skipping insurance amount check — value %.2f on %s looks like "
                "a percentage mis-stored in the amount slot (LC amount %.2f).",
                insured_amount, dt, lc_amount,
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
