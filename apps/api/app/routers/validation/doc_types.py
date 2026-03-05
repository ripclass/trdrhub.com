"""
Document type inference and normalization helpers.
"""

from typing import Any, Dict, Optional

from app.services.crossdoc import DEFAULT_LABELS


DOCUMENT_TYPE_ALIASES: Dict[str, list[str]] = {
    "letter_of_credit": [
        "letter of credit",
        "lc",
        "l/c",
        "mt700",
        "lc document",
        "lc_document",
        "draft lc",
        "draft_lc",
    ],
    # Importer Draft LC document types
    "swift_message": [
        "swift",
        "swift message",
        "mt 700",
        "mt700",
        "mt 710",
        "mt710",
        "mt 760",
        "mt760",
        "swift mt",
    ],
    "lc_application": [
        "application",
        "lc application",
        "lc application form",
        "application form",
    ],
    "proforma_invoice": [
        "proforma",
        "proforma invoice",
        "pi",
        "pro forma",
        "pro-forma",
    ],
    "commercial_invoice": [
        "invoice",
        "commercial invoice",
        "ci",
        "inv",
    ],
    "bill_of_lading": [
        "bill of lading",
        "bill_of_lading",
        "bill-of-lading",
        "bill",
        "bol",
        "bl",
        "shipping document",
        "awb",
    ],
    "packing_list": [
        "packing list",
        "packlist",
        "packing",
    ],
    "insurance_certificate": [
        "insurance",
        "insurance certificate",
        "policy",
    ],
    "certificate_of_origin": [
        "certificate of origin",
        "coo",
        "gsp",
    ],
    "inspection_certificate": [
        "inspection",
        "analysis",
        "quality certificate",
    ],
    "supporting_document": [
        "supporting",
        "misc",
        "other",
    ],
}


def canonical_document_tag(raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip().lower()
    if not normalized:
        return None
    normalized = normalized.replace("-", " ").replace("_", " ")
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if normalized == canonical.replace("_", " "):
            return canonical
        if normalized in aliases:
            return canonical
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return canonical
    return normalized.replace(" ", "_")


def resolve_document_type(
    filename: Optional[str],
    index: int,
    document_tags: Optional[Dict[str, str]] = None,
) -> str:
    if filename and document_tags:
        lower_name = filename.lower()
        base_name = lower_name.rsplit(".", 1)[0]
        tag_value = document_tags.get(lower_name) or document_tags.get(base_name)
        if tag_value:
            return tag_value
    return infer_document_type(filename, index)


def infer_document_type(filename: Optional[str], index: int) -> str:
    """Guess document type using filename hints or position."""
    if filename:
        lower = filename.lower()
        if any(token in lower for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in lower for token in (
            "bill of lading",
            "bill_of_lading",
            "bill-of-lading",
            "bill",
            "lading",
            "bl",
            "shipping",
            "bol",
        )):
            return "bill_of_lading"
        if any(token in lower for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in lower for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in lower for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in lower for token in ("inspection", "analysis", "quality")):
            return "inspection_certificate"
        if any(token in lower for token in ("lc_", "letter_of_credit", "mt700")) or lower.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in lower:
            return "letter_of_credit"

    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
    }
    return mapping.get(index, "letter_of_credit")


def infer_document_type_from_name(filename: Optional[str], index: int) -> str:
    """Infer the document type using filename patterns."""
    if filename:
        name = filename.lower()
        if any(token in name for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in name for token in (
            "bill_of_lading",
            "bill-of-lading",
            "bill",
            "lading",
            "bl",
            "shipping",
            "bol",
        )):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in name for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in name for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in name for token in ("inspection", "quality", "analysis")):
            return "inspection_certificate"
        if any(token in name for token in ("lc_", "letter_of_credit", "mt700")) or name.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in name:
            return "letter_of_credit"

    return fallback_doc_type(index)


def fallback_doc_type(index: int) -> str:
    """Fallback ordering for document types when hints are unavailable."""
    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
        3: "packing_list",
        4: "certificate_of_origin",
        5: "insurance_certificate",
        6: "inspection_certificate",
    }
    return mapping.get(index, "supporting_document")


def label_to_doc_type(label: Optional[str]) -> Optional[str]:
    if not label:
        return None
    normalized = str(label).strip().lower()
    for canonical, friendly in DEFAULT_LABELS.items():
        if normalized == friendly.lower():
            return canonical
        if normalized.replace(" ", "_") == canonical:
            return canonical
    return None


def doc_type_to_display_name(doc_type: Optional[str]) -> Optional[str]:
    """Convert document type (e.g., 'invoice') to display name (e.g., 'Commercial Invoice')."""
    if not doc_type:
        return None
    normalized = str(doc_type).strip().lower().replace(" ", "_")

    # Common mappings from doc types to display names
    type_to_display = {
        "invoice": "Commercial Invoice",
        "commercial_invoice": "Commercial Invoice",
        "bill_of_lading": "Bill of Lading",
        "bl": "Bill of Lading",
        "certificate_of_origin": "Certificate of Origin",
        "coo": "Certificate of Origin",
        "packing_list": "Packing List",
        "insurance": "Insurance Certificate",
        "insurance_certificate": "Insurance Certificate",
        "lc": "Letter of Credit",
        "letter_of_credit": "Letter of Credit",
    }

    if normalized in type_to_display:
        return type_to_display[normalized]

    # Try DEFAULT_LABELS
    if normalized in DEFAULT_LABELS:
        return DEFAULT_LABELS[normalized]

    return None


def normalize_doc_type_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower()
    normalized_snake = normalized.replace(" ", "_")
    if normalized_snake in DEFAULT_LABELS:
        return normalized_snake
    if normalized in DEFAULT_LABELS:
        return normalized
    return normalized_snake


def humanize_doc_type(doc_type: Optional[str]) -> str:
    if not doc_type:
        return "Supporting Document"
    return DEFAULT_LABELS.get(doc_type, doc_type.replace("_", " ").title())
