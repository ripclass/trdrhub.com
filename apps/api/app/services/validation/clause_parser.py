"""
46A/47A Clause Parser for Validation (Part 2).

Takes the extracted LC's `documents_required` and `additional_conditions`,
splits concatenated text into individual clauses, and tags each with:
  - expected document type
  - required fields the clause demands on that document
  - the raw clause text (for display in findings)

This is a VALIDATION concern — it reads the LC to understand what the
examiner should check. Extraction (Part 1) is blind and doesn't know
about any of this.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ParsedClause:
    """One clause from 46A or 47A, tagged for validation matching."""

    raw_text: str
    source_field: str  # "46A" or "47A"
    clause_index: int  # 0-based within its source field
    document_type: Optional[str] = None  # canonical doc type or None if undetectable
    required_fields: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # free-text conditions (e.g. "MADE OUT TO ORDER OF ISSUING BANK")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "source_field": self.source_field,
            "clause_index": self.clause_index,
            "document_type": self.document_type,
            "required_fields": self.required_fields,
            "conditions": self.conditions,
        }


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

# Order matters — more specific patterns first to avoid "INVOICE" matching
# inside "COMMERCIAL INVOICE" after "COMMERCIAL" was already consumed.
_DOC_TYPE_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\bFULL\s+SET\b.*?\bBILL\s+OF\s+LADING\b", re.I), "bill_of_lading"),
    (re.compile(r"\bBILL\s+OF\s+LADING\b", re.I), "bill_of_lading"),
    (re.compile(r"\bOCEAN\s+B/?L\b", re.I), "bill_of_lading"),
    (re.compile(r"\bMARINE\s+B/?L\b", re.I), "bill_of_lading"),
    (re.compile(r"\bB/?L\b(?:\s+(?:TO|SHOWING|MARKED|ISSUED))", re.I), "bill_of_lading"),
    (re.compile(r"\bAIRWAY\s*BILL\b", re.I), "air_waybill"),
    (re.compile(r"\bAWB\b", re.I), "air_waybill"),
    (re.compile(r"\bCOMMERCIAL\s+INVOICE\b", re.I), "commercial_invoice"),
    (re.compile(r"\bSIGNED\s+INVOICE\b", re.I), "commercial_invoice"),
    (re.compile(r"\bINVOICE\b(?!\s+INSURANCE)", re.I), "commercial_invoice"),
    (re.compile(r"\bPACKING\s+LIST\b", re.I), "packing_list"),
    (re.compile(r"\bPACKING\s+AND\s+WEIGHT\s+LIST\b", re.I), "packing_list"),
    (re.compile(r"\bWEIGHT\s+LIST\b", re.I), "packing_list"),
    (re.compile(r"\bCERTIFICATE\s+OF\s+ORIGIN\b", re.I), "certificate_of_origin"),
    (re.compile(r"\bC/?O/?O\b", re.I), "certificate_of_origin"),
    (re.compile(r"\bINSURANCE\s+POLICY\b", re.I), "insurance_policy"),
    (re.compile(r"\bINSURANCE\s+CERTIFICATE\b", re.I), "insurance_certificate"),
    (re.compile(r"\bINSURANCE\b.*?\b(?:COVERING|COVER)\b", re.I), "insurance_certificate"),
    (re.compile(r"\bINSPECTION\s+CERTIFICATE\b", re.I), "inspection_certificate"),
    (re.compile(r"\bSGS\b.*?\bCERTIFICATE\b", re.I), "inspection_certificate"),
    (re.compile(r"\bPRE[\-\s]?SHIPMENT\s+INSPECTION\b", re.I), "inspection_certificate"),
    (re.compile(r"\bBENEFICIARY\S*S?\s+CERTIFICATE\b", re.I), "beneficiary_certificate"),
    (re.compile(r"\bDRAFT\b(?:\s+(?:AT|DRAWN))", re.I), "draft"),
    (re.compile(r"\bBILL\s+OF\s+EXCHANGE\b", re.I), "draft"),
    (re.compile(r"\bPHYTOSANITARY\s+CERTIFICATE\b", re.I), "phytosanitary_certificate"),
    (re.compile(r"\bHEALTH\s+CERTIFICATE\b", re.I), "health_certificate"),
    (re.compile(r"\bFUMIGATION\s+CERTIFICATE\b", re.I), "fumigation_certificate"),
    (re.compile(r"\bWEIGHT\s+CERTIFICATE\b", re.I), "weight_certificate"),
    (re.compile(r"\bQUALITY\s+CERTIFICATE\b", re.I), "quality_certificate"),
    (re.compile(r"\bANALYSIS\s+CERTIFICATE\b", re.I), "analysis_certificate"),
]


def detect_document_type(text: str) -> Optional[str]:
    """Detect the canonical document type from a 46A clause."""
    for pattern, doc_type in _DOC_TYPE_PATTERNS:
        if pattern.search(text):
            return doc_type
    return None


# ---------------------------------------------------------------------------
# Field requirement extraction
# ---------------------------------------------------------------------------

# Phrases in 46A clauses that map to canonical field names.
# "BL TO SHOW VESSEL NAME, VOYAGE NO., CONTAINER NO." → [vessel_name, voyage_number, container_number]
_FIELD_PATTERNS: List[tuple[re.Pattern, str]] = [
    # Transport fields (BL)
    (re.compile(r"\bVESSEL\s+NAME\b", re.I), "vessel_name"),
    (re.compile(r"\bVOYAGE\s+(?:NO\.?|NUMBER)\b", re.I), "voyage_number"),
    (re.compile(r"\bCONTAINER\s+(?:NO\.?|NUMBER)\b", re.I), "container_number"),
    (re.compile(r"\bSEAL\s+(?:NO\.?|NUMBER)\b", re.I), "seal_number"),
    (re.compile(r"\bGROSS\s+WEIGHT\b", re.I), "gross_weight"),
    (re.compile(r"\bNET\s+WEIGHT\b", re.I), "net_weight"),
    (re.compile(r"\bPORT\s+OF\s+LOADING\b", re.I), "port_of_loading"),
    (re.compile(r"\bPORT\s+OF\s+DISCHARGE\b", re.I), "port_of_discharge"),
    (re.compile(r"\bNOTIFY\s+(?:PARTY|APPLICANT)\b", re.I), "notify_party"),
    (re.compile(r"\bSHIPPED\s+ON\s+BOARD\b", re.I), "on_board_date"),
    (re.compile(r"\bON[\s\-]?BOARD\s+(?:DATE|NOTATION)\b", re.I), "on_board_date"),
    (re.compile(r"\bFREIGHT\s+(?:PREPAID|COLLECT)\b", re.I), "freight_status"),
    (re.compile(r"\bCARRIER(?:'?S)?\s+NAME\b", re.I), "carrier_name"),
    # Invoice fields
    (re.compile(r"\bGOODS\s+DESCRIPTION\b", re.I), "goods_description"),
    (re.compile(r"\bDESCRIPTION\s+OF\s+GOODS\b", re.I), "goods_description"),
    (re.compile(r"\bHS\s+CODE\b", re.I), "hs_code"),
    (re.compile(r"\bUNIT\s+PRICE\b", re.I), "unit_price"),
    (re.compile(r"\bTOTAL\s+AMOUNT\b", re.I), "total_amount"),
    (re.compile(r"\bQUANTITY\b", re.I), "quantity"),
    # Insurance fields
    (re.compile(r"\b110\s*%\b", re.I), "coverage_percentage"),
    (re.compile(r"\bCIF\s+VALUE\b", re.I), "coverage_basis"),
    (re.compile(r"\bALL\s+RISKS?\b", re.I), "risk_coverage"),
    (re.compile(r"\bINSTITUTE\s+(?:CARGO|WAR)\s+CLAUSE\b", re.I), "risk_coverage"),
    (re.compile(r"\bWAR\s+(?:RISK|CLAUSE)\b", re.I), "war_risk_coverage"),
    # COO fields
    (re.compile(r"\bCOUNTRY\s+OF\s+ORIGIN\b", re.I), "country_of_origin"),
    # Cross-transaction identifiers the LC requires on docs
    (re.compile(r"\bL/?C\s+(?:NO\.?|NUMBER|REF)\b", re.I), "lc_number"),
    (re.compile(r"\bCREDIT\s+(?:NO\.?|NUMBER)\b", re.I), "lc_number"),
    (re.compile(r"\bP/?O\s+(?:NO\.?|NUMBER)\b", re.I), "buyer_purchase_order_number"),
    (re.compile(r"\bPURCHASE\s+ORDER\s+(?:NO\.?|NUMBER)\b", re.I), "buyer_purchase_order_number"),
    (re.compile(r"\bBIN\s+(?:NO\.?|NUMBER)\b", re.I), "exporter_bin"),
    (re.compile(r"\bTIN\s+(?:NO\.?|NUMBER)\b", re.I), "exporter_tin"),
]


def extract_required_fields(text: str) -> List[str]:
    """Extract canonical field names demanded by a 46A clause."""
    found = []
    seen = set()
    for pattern, field_name in _FIELD_PATTERNS:
        if field_name not in seen and pattern.search(text):
            found.append(field_name)
            seen.add(field_name)
    return found


# ---------------------------------------------------------------------------
# Condition extraction (free-text conditions on the document)
# ---------------------------------------------------------------------------

_CONDITION_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\bMADE\s+OUT\s+TO\s+(?:THE\s+)?ORDER\s+OF\b[^.;]*", re.I), "consignment_order"),
    (re.compile(r"\bMARKED\s+(?:FREIGHT\s+)?(?:PREPAID|COLLECT)\b", re.I), "freight_marking"),
    (re.compile(r"\bCLEAN\s+ON[\s\-]?BOARD\b", re.I), "clean_on_board"),
    (re.compile(r"\bENDORSED\s+(?:IN\s+BLANK|TO\s+THE\s+ORDER)\b", re.I), "endorsement"),
    (re.compile(r"\bIN\s+(?:TRIPLICATE|DUPLICATE|ORIGINAL)\b", re.I), "copy_requirement"),
    (re.compile(r"\b(\d+)\s*/\s*(\d+)\s+(?:ORIGINAL|SET)\b", re.I), "copy_requirement"),
    (re.compile(r"\bFULL\s+SET\b", re.I), "full_set"),
    (re.compile(r"\bSIGNED\s+(?:AND\s+)?(?:STAMPED|SEALED)\b", re.I), "signature_requirement"),
    (re.compile(r"\bIN\s+ENGLISH\b", re.I), "language_requirement"),
    (re.compile(r"\bNOTARIZED\b|\bLEGALIZED\b|\bATTESTED\b", re.I), "legalization"),
]


def extract_conditions(text: str) -> List[str]:
    """Extract free-text conditions from a 46A clause."""
    found = []
    for pattern, label in _CONDITION_PATTERNS:
        m = pattern.search(text)
        if m:
            found.append(m.group(0).strip())
    return found


# ---------------------------------------------------------------------------
# Clause splitting — break concatenated 46A text
# ---------------------------------------------------------------------------

# Some LCs concatenate all 46A clauses into one blob. We split on patterns
# like numbered items, "PLUS", or document-type transitions.
_CLAUSE_SPLIT_RE = re.compile(
    r"""
    (?:                                       # Numbered: "1) ...", "1. ...", "(1) ..."
      (?:^|\n)\s*(?:\d+[.)]\s|\(\d+\)\s)
    )
    |(?:                                      # "+PLUS" or "AND" between doc types
      \n\s*(?:\+|PLUS|AND)\s*\n
    )
    """,
    re.I | re.X,
)


def _split_concatenated_clauses(text: str) -> List[str]:
    """Split a concatenated 46A / 47A blob into individual clause strings.

    Real extraction outputs both newline-separated numbered clauses
    ("1) X\\n2) Y\\n...") and inline-comma-separated ones
    ("1) X., 2) Y., 3) Z."). The inline form is especially common from
    LLM extractors that flatten whitespace. Both must split correctly,
    otherwise downstream ``detect_document_type`` scans the whole blob
    and matches on noise words — e.g. the literal "INVOICE" in clause 3
    "THIRD-PARTY DOCUMENTS ACCEPTABLE EXCEPT BILL OF EXCHANGE AND
    INVOICE" gets attributed to the clause about cartons & country-of-
    origin, producing a false-positive finding.
    """
    if not text or len(text.strip()) < 10:
        return []

    # Numbered: try inline + newline forms together. The pattern matches
    # "1) ", "1. ", "(1) " at either the start of the string, after a
    # newline, OR after a sentence-terminal (``.`` / ``;`` / ``,`` +
    # whitespace) — which is how LLM extractors typically return them.
    numbered = re.split(
        r"(?:^|\n|(?<=[.;,])\s+)(?:\(?\d+\)?[.)])\s+",
        text,
    )
    numbered = [c.strip() for c in numbered if c and c.strip() and len(c.strip()) > 10]
    if len(numbered) > 1:
        return numbered

    # Letter bullets: A) ... B) ..., same extended separator rules.
    letters = re.split(
        r"(?:^|\n|(?<=[.;,])\s+)[A-Z][.)]\s+",
        text,
    )
    letters = [c.strip() for c in letters if c and c.strip() and len(c.strip()) > 10]
    if len(letters) > 1:
        return letters

    # "+PLUS" / "AND" separators between doc blocks (newline-delimited
    # only; these tokens are too ambiguous inline).
    plus_split = re.split(r"\n\s*(?:\+|PLUS)\s*\n", text, flags=re.I)
    plus_split = [c.strip() for c in plus_split if c and c.strip() and len(c.strip()) > 10]
    if len(plus_split) > 1:
        return plus_split

    # Heuristic: split on transitions between doc types.
    # If the text mentions 2+ doc types, split at each doc type mention.
    type_positions = []
    for pattern, doc_type in _DOC_TYPE_PATTERNS:
        for m in pattern.finditer(text):
            type_positions.append((m.start(), doc_type))
    type_positions.sort()

    if len(type_positions) >= 2:
        clauses = []
        for i, (pos, _) in enumerate(type_positions):
            end = type_positions[i + 1][0] if i + 1 < len(type_positions) else len(text)
            chunk = text[pos:end].strip().rstrip("+").strip()
            if chunk and len(chunk) > 10:
                clauses.append(chunk)
        if len(clauses) >= 2:
            return clauses

    # Can't split — return as single clause
    return [text.strip()]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_lc_clauses(
    documents_required: List[Any],
    additional_conditions: List[str],
) -> List[ParsedClause]:
    """
    Parse all 46A and 47A clauses from an extracted LC into tagged clauses.

    Args:
        documents_required: List of LCDocumentRequirement dicts or raw strings
                           (from LCDocument.documents_required or extracted_context).
        additional_conditions: List of strings from Field 47A.

    Returns:
        List of ParsedClause, each tagged with doc_type + required_fields.
    """
    clauses: List[ParsedClause] = []

    # --- 46A: Documents Required ---
    clause_idx = 0
    for item in (documents_required or []):
        # Accept both LCDocumentRequirement dicts and raw strings
        if isinstance(item, str):
            raw_text = item
            pre_tagged_type = None
            pre_tagged_fields: List[str] = []
        elif isinstance(item, dict):
            raw_text = item.get("raw_text") or item.get("text") or ""
            pre_tagged_type = item.get("document_type")
            pre_tagged_fields = item.get("field_requirements") or []
        elif hasattr(item, "raw_text"):
            raw_text = item.raw_text or ""
            pre_tagged_type = getattr(item, "document_type", None)
            pre_tagged_fields = list(getattr(item, "field_requirements", []) or [])
        else:
            continue

        if not raw_text or len(raw_text.strip()) < 5:
            continue

        # Split concatenated clauses
        sub_clauses = _split_concatenated_clauses(raw_text)

        for sub_text in sub_clauses:
            doc_type = pre_tagged_type or detect_document_type(sub_text)
            req_fields = pre_tagged_fields if pre_tagged_fields else extract_required_fields(sub_text)
            conditions = extract_conditions(sub_text)

            clauses.append(ParsedClause(
                raw_text=sub_text,
                source_field="46A",
                clause_index=clause_idx,
                document_type=doc_type,
                required_fields=req_fields,
                conditions=conditions,
            ))
            clause_idx += 1

    # --- 47A: Additional Conditions ---
    # Like 46A, 47A often arrives as a single concatenated string with
    # numbered sub-clauses. Scanning the whole blob at once produces
    # catastrophic false-positive targeting: e.g. "THIRD-PARTY DOCUMENTS
    # ACCEPTABLE EXCEPT BILL OF EXCHANGE AND INVOICE" in clause 3 makes
    # detect_document_type return "commercial_invoice", then the
    # country-of-origin requirement from clause 4 ("PRINTED ON ALL
    # CARTONS IN INDELIBLE INK") gets attached to the invoice, and the
    # validator raises "Country of Origin present on Commercial Invoice"
    # even though the clause was about cartons. Split first, then detect.
    sub_clause_idx = 0
    for cond_text in (additional_conditions or []):
        if not cond_text or len(cond_text.strip()) < 5:
            continue

        for sub_text in _split_concatenated_clauses(cond_text):
            if not sub_text or len(sub_text.strip()) < 5:
                continue
            doc_type = detect_document_type(sub_text)
            req_fields = extract_required_fields(sub_text)
            conditions = extract_conditions(sub_text)

            clauses.append(ParsedClause(
                raw_text=sub_text,
                source_field="47A",
                clause_index=sub_clause_idx,
                document_type=doc_type,
                required_fields=req_fields,
                conditions=conditions,
            ))
            sub_clause_idx += 1

    logger.info(
        "Parsed %d clauses from LC (46A: %d, 47A: %d), %d with detected doc types",
        len(clauses),
        sum(1 for c in clauses if c.source_field == "46A"),
        sum(1 for c in clauses if c.source_field == "47A"),
        sum(1 for c in clauses if c.document_type),
    )

    return clauses
