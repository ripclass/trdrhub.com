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
    ],
    "beneficiary_certificate": [
        "beneficiary certificate",
        "beneficiary_certificate",
        "beneficiary cert",
        "beneficiary statement",
    ],
    "manufacturer_certificate": [
        "manufacturer's certificate",
        "manufacturers certificate",
        "manufacturer certificate",
        "manufacturer_certificate",
    ],
    "conformity_certificate": [
        "certificate of conformity",
        "certificate_of_conformity",
        "conformity certificate",
        "conformity_certificate",
    ],
    "non_manipulation_certificate": [
        "non-manipulation certificate",
        "non manipulation certificate",
        "non_manipulation_certificate",
    ],
    "halal_certificate": ["halal certificate", "halal_certificate"],
    "kosher_certificate": ["kosher certificate", "kosher_certificate"],
    "organic_certificate": ["organic certificate", "organic_certificate"],
    "certificate_of_origin": [
        "certificate of origin",
        "coo",
    ],
    "gsp_form_a": ["gsp", "gsp form a", "form a", "gsp_form_a"],
    "eur1_movement_certificate": ["eur.1", "eur1", "movement certificate", "eur1_movement_certificate"],
    "customs_declaration": ["customs declaration", "customs_declaration"],
    "export_license": ["export license", "export_license"],
    "import_license": ["import license", "import_license"],
    "phytosanitary_certificate": ["phytosanitary certificate", "phytosanitary_certificate", "phytosanitary", "phyto"],
    "fumigation_certificate": ["fumigation certificate", "fumigation_certificate", "fumigation"],
    "health_certificate": ["health certificate", "health_certificate"],
    "veterinary_certificate": ["veterinary certificate", "veterinary_certificate", "veterinary", "vet"],
    "sanitary_certificate": ["sanitary certificate", "sanitary_certificate", "sanitary"],
    "radiation_certificate": ["radiation certificate", "radiation_certificate"],
    "inspection_certificate": [
        "inspection",
        "inspection certificate",
    ],
    "pre_shipment_inspection": [
        "pre-shipment inspection",
        "pre shipment inspection",
        "psi",
        "pre_shipment_inspection",
    ],
    "quality_certificate": [
        "quality certificate",
        "quality_certificate",
    ],
    "weight_certificate": [
        "weight certificate",
        "weight_certificate",
    ],
    "weight_list": [
        "weight list",
        "weight_list",
    ],
    "measurement_certificate": [
        "measurement certificate",
        "measurement_certificate",
    ],
    "analysis_certificate": [
        "analysis certificate",
        "analysis_certificate",
        "analysis",
    ],
    "lab_test_report": [
        "lab test report",
        "lab_test_report",
        "laboratory test report",
        "lab test",
    ],
    "sgs_certificate": ["sgs certificate", "sgs_certificate", "sgs"],
    "bureau_veritas_certificate": ["bureau veritas certificate", "bureau_veritas_certificate", "bureau veritas", "bv"],
    "intertek_certificate": ["intertek certificate", "intertek_certificate", "intertek"],
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
        if any(token in lower for token in ("beneficiary certificate", "beneficiary_certificate", "beneficiary cert", "beneficiary statement")):
            return "beneficiary_certificate"
        if any(token in lower for token in ("manufacturer's certificate", "manufacturers certificate", "manufacturer certificate", "manufacturer_certificate")):
            return "manufacturer_certificate"
        if any(token in lower for token in ("certificate of conformity", "certificate_of_conformity", "conformity certificate", "conformity_certificate")):
            return "conformity_certificate"
        if any(token in lower for token in ("non-manipulation certificate", "non manipulation certificate", "non_manipulation_certificate")):
            return "non_manipulation_certificate"
        if any(token in lower for token in ("halal certificate", "halal_certificate", "halal")):
            return "halal_certificate"
        if any(token in lower for token in ("kosher certificate", "kosher_certificate", "kosher")):
            return "kosher_certificate"
        if any(token in lower for token in ("organic certificate", "organic_certificate", "organic")):
            return "organic_certificate"
        if any(token in lower for token in ("insurance", "insurance certificate", "insurance policy", "policy")):
            return "insurance_certificate"
        if any(token in lower for token in ("pre-shipment", "pre shipment", "psi", "pre_shipment_inspection")):
            return "pre_shipment_inspection"
        if any(token in lower for token in ("weight list", "weight_list")):
            return "weight_list"
        if any(token in lower for token in ("weight certificate", "weight_certificate", "weighment")):
            return "weight_certificate"
        if any(token in lower for token in ("measurement certificate", "measurement_certificate", "measurement", "dimension")):
            return "measurement_certificate"
        if any(token in lower for token in ("analysis certificate", "analysis_certificate", "analysis")):
            return "analysis_certificate"
        if any(token in lower for token in ("lab test report", "lab_test_report", "laboratory test report", "lab test")):
            return "lab_test_report"
        if any(token in lower for token in ("quality certificate", "quality_certificate", "quality")):
            return "quality_certificate"
        if any(token in lower for token in ("sgs certificate", "sgs_certificate", "sgs")):
            return "sgs_certificate"
        if any(token in lower for token in ("bureau veritas certificate", "bureau_veritas_certificate", "bureau veritas", "bv")):
            return "bureau_veritas_certificate"
        if any(token in lower for token in ("intertek certificate", "intertek_certificate", "intertek")):
            return "intertek_certificate"
        if any(token in lower for token in ("inspection", "inspection certificate")):
            return "inspection_certificate"
        if any(token in lower for token in ("gsp", "gsp form a", "form a", "gsp_form_a")):
            return "gsp_form_a"
        if any(token in lower for token in ("eur.1", "eur1", "movement certificate", "eur1_movement_certificate")):
            return "eur1_movement_certificate"
        if any(token in lower for token in ("customs declaration", "customs_declaration")):
            return "customs_declaration"
        if any(token in lower for token in ("export license", "export_license")):
            return "export_license"
        if any(token in lower for token in ("import license", "import_license")):
            return "import_license"
        if any(token in lower for token in ("phytosanitary certificate", "phytosanitary_certificate", "phytosanitary", "phyto")):
            return "phytosanitary_certificate"
        if any(token in lower for token in ("fumigation certificate", "fumigation_certificate", "fumigation")):
            return "fumigation_certificate"
        if any(token in lower for token in ("health certificate", "health_certificate")):
            return "health_certificate"
        if any(token in lower for token in ("veterinary certificate", "veterinary_certificate", "veterinary", "vet")):
            return "veterinary_certificate"
        if any(token in lower for token in ("sanitary certificate", "sanitary_certificate", "sanitary")):
            return "sanitary_certificate"
        if any(token in lower for token in ("radiation certificate", "radiation_certificate")):
            return "radiation_certificate"
        if any(token in lower for token in ("certificate_of_origin", "certificate of origin", "coo")):
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
        if any(token in name for token in ("beneficiary certificate", "beneficiary_certificate", "beneficiary cert", "beneficiary statement")):
            return "beneficiary_certificate"
        if any(token in name for token in ("manufacturer's certificate", "manufacturers certificate", "manufacturer certificate", "manufacturer_certificate")):
            return "manufacturer_certificate"
        if any(token in name for token in ("certificate of conformity", "certificate_of_conformity", "conformity certificate", "conformity_certificate")):
            return "conformity_certificate"
        if any(token in name for token in ("non-manipulation certificate", "non manipulation certificate", "non_manipulation_certificate")):
            return "non_manipulation_certificate"
        if any(token in name for token in ("halal certificate", "halal_certificate", "halal")):
            return "halal_certificate"
        if any(token in name for token in ("kosher certificate", "kosher_certificate", "kosher")):
            return "kosher_certificate"
        if any(token in name for token in ("organic certificate", "organic_certificate", "organic")):
            return "organic_certificate"
        if any(token in name for token in ("insurance", "insurance certificate", "insurance policy", "policy")):
            return "insurance_certificate"
        if any(token in name for token in ("pre-shipment", "pre shipment", "psi", "pre_shipment_inspection")):
            return "pre_shipment_inspection"
        if any(token in name for token in ("weight list", "weight_list")):
            return "weight_list"
        if any(token in name for token in ("weight certificate", "weight_certificate", "weighment")):
            return "weight_certificate"
        if any(token in name for token in ("measurement certificate", "measurement_certificate", "measurement", "dimension")):
            return "measurement_certificate"
        if any(token in name for token in ("analysis certificate", "analysis_certificate", "analysis")):
            return "analysis_certificate"
        if any(token in name for token in ("lab test report", "lab_test_report", "laboratory test report", "lab test")):
            return "lab_test_report"
        if any(token in name for token in ("quality certificate", "quality_certificate", "quality")):
            return "quality_certificate"
        if any(token in name for token in ("sgs certificate", "sgs_certificate", "sgs")):
            return "sgs_certificate"
        if any(token in name for token in ("bureau veritas certificate", "bureau_veritas_certificate", "bureau veritas", "bv")):
            return "bureau_veritas_certificate"
        if any(token in name for token in ("intertek certificate", "intertek_certificate", "intertek")):
            return "intertek_certificate"
        if any(token in name for token in ("inspection", "inspection certificate")):
            return "inspection_certificate"
        if any(token in name for token in ("gsp", "gsp form a", "form a", "gsp_form_a")):
            return "gsp_form_a"
        if any(token in name for token in ("eur.1", "eur1", "movement certificate", "eur1_movement_certificate")):
            return "eur1_movement_certificate"
        if any(token in name for token in ("customs declaration", "customs_declaration")):
            return "customs_declaration"
        if any(token in name for token in ("export license", "export_license")):
            return "export_license"
        if any(token in name for token in ("import license", "import_license")):
            return "import_license"
        if any(token in name for token in ("phytosanitary certificate", "phytosanitary_certificate", "phytosanitary", "phyto")):
            return "phytosanitary_certificate"
        if any(token in name for token in ("fumigation certificate", "fumigation_certificate", "fumigation")):
            return "fumigation_certificate"
        if any(token in name for token in ("health certificate", "health_certificate")):
            return "health_certificate"
        if any(token in name for token in ("veterinary certificate", "veterinary_certificate", "veterinary", "vet")):
            return "veterinary_certificate"
        if any(token in name for token in ("sanitary certificate", "sanitary_certificate", "sanitary")):
            return "sanitary_certificate"
        if any(token in name for token in ("radiation certificate", "radiation_certificate")):
            return "radiation_certificate"
        if any(token in name for token in ("certificate_of_origin", "certificate of origin", "coo")):
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
