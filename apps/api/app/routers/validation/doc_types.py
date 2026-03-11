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
        "bank guarantee",
        "bank_guarantee",
        "standby letter of credit",
        "standby lc",
        "sblc",
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
        "bill of exchange",
        "draft",
        "promissory note",
        "promissory_note",
        "payment receipt",
        "receipt",
        "debit note",
        "credit note",
    ],
    "bill_of_lading": [
        "bill of lading",
        "bill_of_lading",
        "bill-of-lading",
        "bill",
        "bol",
        "bl",
        "shipping document",
        "transport document",
        "ocean bill of lading",
        "sea waybill",
        "air waybill",
        "awb",
        "multimodal transport document",
        "combined transport document",
        "railway consignment note",
        "road transport document",
        "forwarder's certificate of receipt",
        "fcr",
        "house bill of lading",
        "master bill of lading",
        "delivery order",
        "mate's receipt",
        "mates receipt",
        "shipping company certificate",
    ],
    "packing_list": [
        "packing list",
        "packlist",
        "packing",
    ],
    "insurance_certificate": [
        "insurance",
        "insurance certificate",
        "insurance policy",
        "policy",
        "beneficiary certificate",
        "beneficiary_certificate",
        "manufacturer's certificate",
        "manufacturers certificate",
        "certificate of conformity",
        "certificate_of_conformity",
        "non-manipulation certificate",
        "halal certificate",
        "kosher certificate",
        "organic certificate",
    ],
    "certificate_of_origin": [
        "certificate of origin",
        "coo",
        "gsp",
        "gsp form a",
        "form a",
        "eur.1",
        "eur1",
        "movement certificate",
        "customs declaration",
        "export license",
        "import license",
        "phytosanitary certificate",
        "fumigation certificate",
        "health certificate",
        "veterinary certificate",
        "sanitary certificate",
        "sanitary_certificate",
        "cites permit",
        "radiation certificate",
        "radiation_certificate",
    ],
    "inspection_certificate": [
        "inspection",
        "inspection certificate",
        "pre-shipment inspection",
        "pre shipment inspection",
        "psi",
        "quality certificate",
        "weight certificate",
        "weight_certificate",
        "weight list",
        "measurement certificate",
        "measurement_certificate",
        "analysis certificate",
        "lab test report",
        "lab_test_report",
        "laboratory test report",
        "sgs certificate",
        "bureau veritas certificate",
        "intertek certificate",
        "analysis",
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
        if lower in {"lc.pdf", "lc"} or any(token in lower for token in ("bank guarantee", "bank_guarantee", "standby letter of credit", "standby lc", "sblc")):
            return "letter_of_credit"
        if any(token in lower for token in ("invoice", "inv", "bill of exchange", "draft", "promissory note", "promissory_note", "payment receipt", "receipt", "debit note", "credit note")):
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
            "ocean bill",
            "sea waybill",
            "air waybill",
            "awb",
            "multimodal",
            "combined transport",
            "railway consignment",
            "road transport",
            "forwarder",
            "fcr",
            "house bill",
            "master bill",
            "delivery order",
            "mate",
        )):
            return "bill_of_lading"
        if any(token in lower for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in lower for token in ("insurance", "insurance policy", "policy", "beneficiary certificate", "beneficiary_certificate", "manufacturer's certificate", "manufacturers certificate", "certificate of conformity", "certificate_of_conformity", "non-manipulation certificate", "halal certificate", "kosher certificate", "organic certificate")):
            return "insurance_certificate"
        if any(token in lower for token in ("inspection", "pre-shipment", "pre shipment", "psi", "analysis", "quality", "weight certificate", "weight_certificate", "weight list", "weight_list", "measurement certificate", "measurement_certificate", "lab test", "lab_test_report", "sgs", "bureau veritas", "intertek")):
            return "inspection_certificate"
        if any(token in lower for token in ("certificate_of_origin", "coo", "gsp", "gsp form a", "form a", "eur.1", "eur1", "movement certificate", "customs declaration", "export license", "import license", "phytosanitary", "fumigation", "health certificate", "veterinary certificate", "sanitary certificate", "sanitary_certificate", "cites permit", "radiation certificate", "radiation_certificate")):
            return "certificate_of_origin"
        if any(token in lower for token in ("lc_", "letter_of_credit", "mt700", "bank guarantee", "standby letter of credit", "standby lc", "sblc")) or lower.endswith("_lc.pdf"):
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
        if name in {"lc.pdf", "lc"} or any(token in name for token in ("bank guarantee", "bank_guarantee", "standby letter of credit", "standby lc", "sblc")):
            return "letter_of_credit"
        if any(token in name for token in ("invoice", "inv", "bill of exchange", "draft", "promissory note", "promissory_note", "payment receipt", "receipt", "debit note", "credit note")):
            return "commercial_invoice"
        if any(token in name for token in (
            "bill_of_lading",
            "bill-of-lading",
            "bill",
            "lading",
            "bl",
            "shipping",
            "bol",
            "ocean bill",
            "sea waybill",
            "air waybill",
            "awb",
            "multimodal",
            "combined transport",
            "railway consignment",
            "road transport",
            "forwarder",
            "fcr",
            "house bill",
            "master bill",
            "delivery order",
            "mate",
        )):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in name for token in ("insurance", "insurance policy", "policy", "beneficiary certificate", "beneficiary_certificate", "manufacturer's certificate", "manufacturers certificate", "certificate of conformity", "certificate_of_conformity", "non-manipulation certificate", "halal certificate", "kosher certificate", "organic certificate")):
            return "insurance_certificate"
        if any(token in name for token in ("inspection", "pre-shipment", "pre shipment", "psi", "quality", "analysis", "weight certificate", "weight_certificate", "weight list", "weight_list", "measurement certificate", "measurement_certificate", "lab test", "lab_test_report", "sgs", "bureau veritas", "intertek")):
            return "inspection_certificate"
        if any(token in name for token in ("certificate_of_origin", "coo", "gsp", "gsp form a", "form a", "eur.1", "eur1", "movement certificate", "customs declaration", "export license", "import license", "phytosanitary", "fumigation", "health certificate", "veterinary certificate", "sanitary certificate", "sanitary_certificate", "cites permit", "radiation certificate", "radiation_certificate")):
            return "certificate_of_origin"
        if any(token in name for token in ("lc_", "letter_of_credit", "mt700", "bank guarantee", "standby letter of credit", "standby lc", "sblc")) or name.endswith("_lc.pdf"):
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
