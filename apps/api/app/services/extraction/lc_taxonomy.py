from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SWIFT_VARIANTS = {
    "mt700", "mt701", "mt705", "mt707", "mt708", "mt710", "mt711", "mt720", "mt721",
    "mt730", "mt732", "mt734", "mt740", "mt742", "mt744", "mt747", "mt750", "mt752",
    "mt754", "mt756", "mt759", "mt760", "mt761", "mt765", "mt767", "mt768", "mt769",
    "mt775", "mt785", "mt786", "mt787", "mt798",
}

LEGACY_WORKFLOW_ALIASES = {"import", "export", "draft", "unknown"}
WORKFLOW_ORIENTATIONS = {"import", "export", "domestic", "intermediary_or_trader", "unknown"}
COUNTRY_SYNONYMS = {
    "u.s.a": "united states",
    "usa": "united states",
    "us": "united states",
    "united states of america": "united states",
    "bd": "bangladesh",
    "bangla desh": "bangladesh",
    "u.k.": "united kingdom",
    "uk": "united kingdom",
}

ISO_VARIANT_RE = re.compile(r"\b((?:tsrv|tsmt|tsin)\.\d{3})\b", re.IGNORECASE)
SWIFT_VARIANT_RE = re.compile(
    r"\b(mt(?:7(?:00|01|05|07|08|10|11|20|21|30|32|34|40|42|44|47|50|52|54|56|59|60|61|65|67|68|69|75|85|86|87)|798))\b",
    re.IGNORECASE,
)
SWIFT_HEADER_RE = re.compile(
    r"\{2:[IO](7(?:00|01|05|07|08|10|11|20|21|30|32|34|40|42|44|47|50|52|54|56|59|60|61|65|67|68|69|75|85|86|87)|798)",
    re.IGNORECASE,
)
MT700_FIELD_HINTS = (
    ":27:",
    ":40A:",
    ":20:",
    ":31C:",
    ":40E:",
    ":32B:",
    ":46A:",
)
TENOR_DAYS_RE = re.compile(r"\b(\d{1,3})\s*DAYS?\b", re.IGNORECASE)

DOCUMENT_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("proforma_invoice", ("pro forma invoice", "proforma invoice")),
    ("commercial_invoice", ("commercial invoice", "signed commercial invoice", "signed invoice", "invoice", "inv")),
    ("draft_bill_of_exchange", ("bill of exchange", "draft drawn", "draft at", "draft", "boe")),
    ("charter_party_bill_of_lading", ("charter party bill of lading", "charter party b/l", "charter party bl")),
    ("ocean_bill_of_lading", ("ocean bill of lading", "marine bill of lading", "clean on board bill of lading")),
    ("bill_of_lading", ("bill of lading", "b/l", "bl")),
    ("air_waybill", ("air waybill", "awb")),
    ("sea_waybill", ("sea waybill",)),
    ("multimodal_transport_document", ("multimodal transport document", "combined transport document")),
    ("road_transport_document", ("road transport document", "cmr")),
    ("railway_consignment_note", ("railway consignment note", "cim", "smgs")),
    ("courier_or_post_receipt_or_certificate_of_posting", ("courier receipt", "post receipt", "certificate of posting", "postal receipt")),
    ("forwarder_certificate_of_receipt", ("forwarder certificate of receipt", "fcr")),
    ("packing_list", ("packing list", "pl")),
    ("weight_list", ("weight list",)),
    ("certificate_of_origin", ("certificate of origin", "country of origin certificate", "coo")),
    ("inspection_certificate", ("inspection certificate", "inspection report")),
    ("quality_certificate", ("quality certificate",)),
    ("analysis_certificate", ("analysis certificate",)),
    ("insurance_policy", ("insurance policy",)),
    ("insurance_certificate", ("insurance certificate", "insurance")),
    ("beneficiary_certificate", ("beneficiary certificate", "beneficiary statement")),
    ("manufacturer_certificate", ("manufacturer certificate",)),
    ("conformity_certificate", ("certificate of conformity", "conformity certificate")),
    ("non_manipulation_certificate", ("non manipulation certificate",)),
    ("shipment_advice", ("shipment advice", "shipping advice", "shipment notice")),
    ("phytosanitary_certificate", ("phytosanitary certificate",)),
    ("fumigation_certificate", ("fumigation certificate",)),
    ("health_certificate", ("health certificate",)),
    ("delivery_note", ("delivery note", "delivery docket", "goods received note")),
    ("warehouse_receipt", ("warehouse receipt",)),
    ("customs_declaration", ("customs declaration",)),
    ("export_license", ("export license", "export licence")),
    ("import_license", ("import license", "import licence")),
)

REQUIREMENT_CONDITION_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\ball documents?\b", re.IGNORECASE),
    re.compile(r"\bdocuments?\s+must\b", re.IGNORECASE),
    re.compile(r"\bmust\s+(?:show|bear|indicate|mention|state|be|not be|be sent|be dated|be authenticated)\b", re.IGNORECASE),
    re.compile(r"\bto be sent\b", re.IGNORECASE),
    re.compile(r"\bwithin\s+\d+\s+days?\b", re.IGNORECASE),
    re.compile(r"\bacceptable\b", re.IGNORECASE),
    re.compile(r"\bnon[-\s]?negotiable documents?\b", re.IGNORECASE),
    re.compile(r"\bdocuments?\s+are discrepant\b", re.IGNORECASE),
    re.compile(r"\bshipment must\b", re.IGNORECASE),
    re.compile(r"\bpayment charge\b", re.IGNORECASE),
)

DOCUMENT_LIKE_REQUIREMENT_KEYWORDS = (
    "certificate",
    "invoice",
    "bill",
    "list",
    "policy",
    "waybill",
    "report",
    "license",
    "licence",
    "permit",
    "declaration",
    "receipt",
    "manifest",
    "statement",
    "advice",
    "note",
    "document",
)

EXPLICIT_OTHER_SPECIFIED_DOCUMENT_ALIASES = (
    "other specified document",
    "other required document",
    "other document",
)

COMPACT_REQUIREMENT_TOKENS: Dict[str, str] = {
    "INVOICE": "commercial_invoice",
    "INV": "commercial_invoice",
    "BL": "bill_of_lading",
    "B/L": "bill_of_lading",
    "AWB": "air_waybill",
    "PL": "packing_list",
    "COO": "certificate_of_origin",
    "INSURANCE": "insurance_certificate",
    "INS": "insurance_certificate",
}

TRANSPORT_DOCUMENT_CODES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "charter_party_bill_of_lading",
    "air_waybill",
    "sea_waybill",
    "multimodal_transport_document",
    "road_transport_document",
    "railway_consignment_note",
    "courier_or_post_receipt_or_certificate_of_posting",
    "forwarder_certificate_of_receipt",
}

INSPECTION_DOCUMENT_CODES = {
    "inspection_certificate",
    "quality_certificate",
    "analysis_certificate",
}

HEALTH_DOCUMENT_CODES = {
    "phytosanitary_certificate",
    "fumigation_certificate",
    "health_certificate",
}

FINANCIAL_DOCUMENT_CODES = {
    "draft_bill_of_exchange",
    "insurance_policy",
    "insurance_certificate",
}

CUSTOMS_DOCUMENT_CODES = {
    "certificate_of_origin",
    "warehouse_receipt",
    "customs_declaration",
    "export_license",
    "import_license",
}


def build_lc_classification(
    source: Optional[Dict[str, Any]],
    legacy_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source = source or {}
    legacy_payload = legacy_payload or {}

    format_variant = detect_format_variant(source, legacy_payload)
    format_family = detect_format_family(source, legacy_payload, format_variant)
    instrument_type = detect_instrument_type(source, format_family, format_variant)
    workflow_orientation = detect_workflow_orientation(source, legacy_payload)
    applicable_rules = detect_applicable_rules(source)
    requirement_contract = extract_requirement_contract(source)
    required_documents = requirement_contract["required_documents"]

    return {
        "format_family": format_family,
        "format_variant": format_variant,
        "embedded_variant": detect_embedded_variant(source, format_variant),
        "instrument_type": instrument_type,
        "workflow_orientation": workflow_orientation,
        "applicable_rules": applicable_rules,
        "attributes": build_attribute_payload(source, applicable_rules, instrument_type, required_documents),
        "required_documents": required_documents,
        "requirement_conditions": requirement_contract["requirement_conditions"],
        "unmapped_requirements": requirement_contract["unmapped_requirements"],
    }


def detect_format_variant(source: Dict[str, Any], legacy_payload: Dict[str, Any]) -> str:
    schema = str(
        source.get("schema")
        or source.get("message_type")
        or source.get("_source_message_type")
        or source.get("format")
        or source.get("_source_format")
        or source.get("format_detected")
        or legacy_payload.get("format")
        or legacy_payload.get("_source_format")
        or legacy_payload.get("format_detected")
        or ""
    ).strip().lower()
    match = ISO_VARIANT_RE.search(schema)
    if match:
        return match.group(1).lower()
    if schema in SWIFT_VARIANTS:
        return schema
    if schema in {"mt", "swift", "swift_mt_fin"} and (source.get("mt700") or source.get("mt700_raw")):
        return "mt700"

    for blob in iter_text_blobs(source, legacy_payload):
        lowered = blob.lower()
        iso_match = ISO_VARIANT_RE.search(lowered)
        if iso_match:
            return iso_match.group(1).lower()
        header_match = SWIFT_HEADER_RE.search(blob)
        if header_match:
            return f"mt{header_match.group(1).lower()}"
        swift_match = SWIFT_VARIANT_RE.search(lowered)
        if swift_match:
            return swift_match.group(1).lower().replace(" ", "")
    if source.get("mt700") or source.get("mt700_raw"):
        return "mt700"
    raw_text = str(source.get("raw_text") or source.get("text") or source.get("content") or "")
    if sum(1 for hint in MT700_FIELD_HINTS if hint in raw_text.upper()) >= 3:
        return "mt700"

    explicit_format = str(
        source.get("format")
        or source.get("_source_format")
        or source.get("format_detected")
        or legacy_payload.get("format")
        or legacy_payload.get("_source_format")
        or legacy_payload.get("format_detected")
        or ""
    ).strip().lower()
    if explicit_format == "xml_other":
        return "xml_other"
    if explicit_format in {"mt700", "mt", "swift", "swift_mt_fin"}:
        return "mt700"
    if explicit_format in {"pdf_text", "pdf_narrative", "pdf_ocr", "pdf_scanned_ocr", "unknown"}:
        return "narrative_other"
    return "unknown"


def detect_format_family(source: Dict[str, Any], legacy_payload: Dict[str, Any], format_variant: str) -> str:
    explicit_format = str(
        source.get("format")
        or source.get("_source_format")
        or source.get("format_detected")
        or legacy_payload.get("format")
        or legacy_payload.get("_source_format")
        or legacy_payload.get("format_detected")
        or ""
    ).strip().lower()
    extraction_method = str(source.get("_extraction_method") or "").strip().lower()

    if format_variant in SWIFT_VARIANTS:
        return "swift_mt_fin"
    if ISO_VARIANT_RE.fullmatch(format_variant):
        return "iso20022_xml_trade_services"
    if format_variant == "xml_other" or explicit_format in {"xml_other", "generic_xml"}:
        return "other_structured"
    if explicit_format in {"iso20022", "iso", "mx"}:
        return "iso20022_xml_trade_services"
    if explicit_format in {"mt700", "mt", "swift"}:
        return "swift_mt_fin"
    if explicit_format in {"pdf_text", "pdf_narrative"}:
        return "pdf_narrative"
    if extraction_method.startswith("ocr") or explicit_format in {"pdf_ocr", "pdf_scanned_ocr"}:
        return "pdf_scanned_ocr"
    if any(isinstance(value, str) and value.strip() for value in (source.get("raw_text"), source.get("text"), source.get("content"))):
        return "plain_text"
    return "unknown_or_unsupported"


def detect_embedded_variant(source: Dict[str, Any], format_variant: str) -> Optional[str]:
    if format_variant != "mt798":
        return None
    for blob in iter_text_blobs(source):
        lowered = blob.lower()
        for candidate in sorted(SWIFT_VARIANTS - {"mt798"}):
            if candidate in lowered:
                return candidate
    return None


def detect_workflow_orientation(source: Dict[str, Any], legacy_payload: Dict[str, Any]) -> str:
    existing = source.get("lc_classification")
    if isinstance(existing, dict):
        workflow = str(existing.get("workflow_orientation") or "").strip().lower()
        if workflow in WORKFLOW_ORIENTATIONS - {"unknown"}:
            return workflow

    for raw in (legacy_payload.get("lc_type"), source.get("workflow_orientation"), source.get("lc_type")):
        candidate = str(raw or "").strip().lower()
        if candidate in {"import", "export"}:
            return candidate

    text = " ".join(iter_text_blobs(source, legacy_payload)).lower()
    if "domestic lc" in text or "domestic letter of credit" in text:
        return "domestic"
    if any(token in text for token in ("second beneficiary", "transferred credit", "intermediary", "trader")):
        return "intermediary_or_trader"
    inferred_trade_lane = _detect_trade_lane_workflow(source, legacy_payload)
    if inferred_trade_lane in {"import", "export"}:
        return inferred_trade_lane
    return "unknown"


def _detect_trade_lane_workflow(source: Dict[str, Any], legacy_payload: Dict[str, Any]) -> str:
    if not _has_trade_lane_evidence(source, legacy_payload):
        return ""

    detector = _load_lc_type_detector()
    shipment_context: Dict[str, Any] = {}
    shipment = source.get("shipment")
    if isinstance(shipment, dict):
        shipment_context.update(shipment)
    ports = source.get("ports")
    if isinstance(ports, dict):
        if ports.get("loading") and not shipment_context.get("port_of_loading"):
            shipment_context["port_of_loading"] = ports.get("loading")
        if ports.get("discharge") and not shipment_context.get("port_of_discharge"):
            shipment_context["port_of_discharge"] = ports.get("discharge")

    for key in (
        "port_of_loading",
        "port_of_discharge",
        "port_of_loading_country",
        "port_of_loading_country_name",
        "port_of_loading_country_code",
        "port_of_discharge_country",
        "port_of_discharge_country_name",
        "port_of_discharge_country_code",
        "port_of_shipment",
        "port_of_destination",
    ):
        value = source.get(key)
        if value not in (None, "") and key not in shipment_context:
            shipment_context[key] = value

    request_context: Dict[str, Any] = {}
    for source_dict in (legacy_payload, source):
        if not isinstance(source_dict, dict):
            continue
        for legacy_key, request_key in (
            ("user_type", "user_type"),
            ("userType", "user_type"),
            ("workflow_type", "workflow_type"),
            ("workflowType", "workflow_type"),
            ("company_country", "company_country"),
            ("companyCountry", "company_country"),
        ):
            value = source_dict.get(legacy_key)
            if value not in (None, "") and request_key not in request_context:
                request_context[request_key] = value

    if detector is not None:
        guess = detector(source, shipment_context, request_context=request_context)
        candidate = str((guess or {}).get("lc_type") or "").strip().lower()
        if candidate in {"import", "export"}:
            return candidate

    return _infer_trade_lane_workflow_locally(source, shipment_context)


def _load_lc_type_detector():
    try:
        from app.services.lc_classifier import detect_lc_type

        return detect_lc_type
    except Exception:
        classifier_path = Path(__file__).resolve().parents[1] / "lc_classifier.py"
        try:
            package_root = classifier_path.parents[2]
            if str(package_root) not in sys.path:
                sys.path.insert(0, str(package_root))
            spec = importlib.util.spec_from_file_location("lc_taxonomy_lc_classifier", classifier_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, "detect_lc_type", None)
        except Exception:
            return None


def _has_trade_lane_evidence(source: Dict[str, Any], legacy_payload: Dict[str, Any]) -> bool:
    party_signals = (
        source.get("applicant"),
        source.get("beneficiary"),
        source.get("applicant_country"),
        source.get("beneficiary_country"),
        legacy_payload.get("company_country"),
        legacy_payload.get("companyCountry"),
    )
    port_signals = (
        source.get("port_of_loading"),
        source.get("port_of_discharge"),
        source.get("port_of_loading_country"),
        source.get("port_of_discharge_country"),
        (source.get("ports") or {}).get("loading") if isinstance(source.get("ports"), dict) else None,
        (source.get("ports") or {}).get("discharge") if isinstance(source.get("ports"), dict) else None,
    )
    has_party_signal = any(value not in (None, "", [], {}) for value in party_signals)
    has_port_signal = any(value not in (None, "", [], {}) for value in port_signals)
    return has_party_signal and has_port_signal


def _infer_trade_lane_workflow_locally(source: Dict[str, Any], shipment_context: Dict[str, Any]) -> str:
    applicant_country = _extract_country_hint(
        source.get("applicant"),
        source.get("applicant_country"),
        source.get("applicantCountry"),
    )
    beneficiary_country = _extract_country_hint(
        source.get("beneficiary"),
        source.get("beneficiary_country"),
        source.get("beneficiaryCountry"),
    )
    port_of_loading_country = _extract_country_hint(
        shipment_context.get("port_of_loading_country"),
        shipment_context.get("port_of_loading_country_name"),
        shipment_context.get("port_of_loading_country_code"),
        source.get("port_of_loading_country"),
        source.get("port_of_loading_country_name"),
        source.get("port_of_loading_country_code"),
        shipment_context.get("port_of_loading"),
        shipment_context.get("port_of_shipment"),
        (source.get("ports") or {}).get("loading") if isinstance(source.get("ports"), dict) else None,
        source.get("port_of_loading"),
    )
    port_of_discharge_country = _extract_country_hint(
        shipment_context.get("port_of_discharge_country"),
        shipment_context.get("port_of_discharge_country_name"),
        shipment_context.get("port_of_discharge_country_code"),
        source.get("port_of_discharge_country"),
        source.get("port_of_discharge_country_name"),
        source.get("port_of_discharge_country_code"),
        shipment_context.get("port_of_discharge"),
        shipment_context.get("port_of_destination"),
        (source.get("ports") or {}).get("discharge") if isinstance(source.get("ports"), dict) else None,
        source.get("port_of_discharge"),
    )

    if (
        applicant_country
        and beneficiary_country
        and port_of_loading_country
        and port_of_discharge_country
        and applicant_country != beneficiary_country
    ):
        if beneficiary_country == port_of_loading_country and applicant_country == port_of_discharge_country:
            return "export"
        if applicant_country == port_of_loading_country and beneficiary_country == port_of_discharge_country:
            return "import"

    return ""


def _extract_country_hint(*values: Any) -> str:
    for value in values:
        country = _extract_country_from_value(value)
        if country:
            return country
    return ""


def _extract_country_from_value(value: Any) -> str:
    if value in (None, "", [], {}, ()):
        return ""
    if isinstance(value, dict):
        for key in ("country", "country_name", "countryName", "address", "name", "value"):
            country = _extract_country_from_value(value.get(key))
            if country:
                return country
        return ""
    if isinstance(value, (list, tuple, set)):
        for item in value:
            country = _extract_country_from_value(item)
            if country:
                return country
        return ""

    text = str(value).strip()
    if not text:
        return ""
    segments = [segment.strip(" .,-") for segment in re.split(r"[\n,;/]+", text) if segment.strip(" .,-")]
    candidates = list(reversed(segments)) + [text]
    for candidate in candidates:
        normalized = _normalize_country_name(candidate)
        if normalized:
            return normalized
    return ""


def _normalize_country_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s.]", " ", text)).strip()
    return COUNTRY_SYNONYMS.get(text, text)


def detect_instrument_type(source: Dict[str, Any], format_family: str, format_variant: str) -> str:
    text = " ".join(iter_text_blobs(source)).lower()
    legacy_lc_type = str(source.get("lc_type") or "").strip().lower()
    if legacy_lc_type in LEGACY_WORKFLOW_ALIASES:
        legacy_lc_type = ""
    combined = " ".join(filter(None, [text, legacy_lc_type]))

    if any(token in combined for token in ("counter guarantee", "counter-guarantee", "counter undertaking", "counter-undertaking")):
        return "counter_undertaking_or_counter_guarantee"
    if "documentary collection" in combined or "collection instruction" in combined:
        return "documentary_collection"
    if any(token in combined for token in ("demand guarantee", "bank guarantee", "guarantee")) and "standby" not in combined:
        return "demand_guarantee"
    if any(token in combined for token in ("standby", "sblc", "isp98", "isp 98")):
        return "standby_letter_of_credit"
    if format_family == "iso20022_xml_trade_services" and format_variant.startswith("tsrv."):
        return "standby_letter_of_credit"
    if format_family == "iso20022_xml_trade_services" and (format_variant.startswith("tsin.") or format_variant.startswith("tsmt.")):
        return "documentary_credit"
    if format_variant in {"mt700", "mt701", "mt705", "mt707", "mt708", "mt710", "mt711", "mt720", "mt721", "mt730", "mt732", "mt734", "mt740", "mt742", "mt744", "mt747", "mt750", "mt752", "mt754", "mt756", "mt775", "mt785", "mt786", "mt787"}:
        return "documentary_credit"
    if any(token in combined for token in ("documentary credit", "documentary letter of credit", "doc credit", "irrevocable", "revocable", "transferable", "revolving", "clean credit")):
        return "documentary_credit"
    return "other_or_unknown_undertaking"


def detect_applicable_rules(source: Dict[str, Any]) -> str:
    text = " ".join(iter_text_blobs(source)).lower()
    if "isp98" in text or "isp 98" in text:
        return "isp98"
    if "urdg758" in text or "urdg 758" in text:
        return "urdg758"
    if "urc522" in text or "urc 522" in text:
        return "urc522"
    if "ucp600" in text or "ucp 600" in text or "ucp latest" in text:
        return "ucp600"
    return "unknown"


def build_attribute_payload(
    source: Dict[str, Any],
    applicable_rules: str,
    instrument_type: str,
    required_documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    text = " ".join(iter_text_blobs(source)).upper()
    latest_shipment_date = clean_string(source.get("latest_shipment_date")) or clean_string((source.get("dates") or {}).get("latest_shipment")) or clean_string((source.get("timeline") or {}).get("latest_shipment"))
    expiry_date = clean_string(source.get("expiry_date")) or clean_string((source.get("dates") or {}).get("expiry")) or clean_string((source.get("timeline") or {}).get("expiry_date"))
    expiry_place = clean_string(source.get("expiry_place")) or clean_string(source.get("place_of_expiry")) or clean_string((source.get("dates") or {}).get("place_of_expiry"))
    shipment = source.get("shipment") if isinstance(source.get("shipment"), dict) else {}
    mt700 = source.get("mt700") if isinstance(source.get("mt700"), dict) else {}
    tenor_days = extract_int(source.get("tenor_days") or source.get("deferred_days") or source.get("usance_days") or source.get("drafts_at"))
    if tenor_days is None:
        tenor_match = TENOR_DAYS_RE.search(text)
        tenor_days = int(tenor_match.group(1)) if tenor_match else None

    return {
        "revocability": "irrevocable" if "IRREVOCABLE" in text else "revocable" if "REVOCABLE" in text else "unknown",
        "availability": detect_availability(source, text),
        "available_with_scope": detect_available_with_scope(source, text),
        "confirmation": detect_confirmation(source, text),
        "transferability": "transferable" if "TRANSFERABLE" in text else "unknown",
        "assignment_of_proceeds": "assigned" if "ASSIGNMENT OF PROCEEDS" in text else "not_assigned" if "ASSIGNMENT PROHIBITED" in text else "unknown",
        "revolving": "revolving" if "REVOLV" in text else "unknown",
        "revolving_mode": "automatic" if "AUTOMATICALLY REINSTATED" in text or "AUTOMATIC REINSTATEMENT" in text else "non_cumulative" if "NON-CUMULATIVE" in text or "NON CUMULATIVE" in text else "cumulative" if "CUMULATIVE" in text else None,
        "red_clause": "present" if "RED CLAUSE" in text else "unknown",
        "green_clause": "present" if "GREEN CLAUSE" in text else "unknown",
        "back_to_back": "present" if "BACK TO BACK" in text or "BACK-TO-BACK" in text else "unknown",
        "documentation_basis": "clean" if "CLEAN CREDIT" in text else "documentary" if required_documents or instrument_type == "documentary_credit" else "unknown",
        "partial_shipments": normalize_permission(
            source.get("partial_shipments")
            or mt700.get("partial_shipments")
            or shipment.get("partial_shipments")
        ),
        "transshipment": normalize_permission(
            source.get("transshipment")
            or mt700.get("transshipment")
            or shipment.get("transshipment")
        ),
        "latest_shipment_date": latest_shipment_date,
        "expiry_date": expiry_date,
        "expiry_place": expiry_place,
        "presentation_period_days": extract_int(
            source.get("presentation_period_days")
            or source.get("period_for_presentation")
            or mt700.get("period_for_presentation")
        ),
        "tenor_kind": detect_availability(source, text),
        "tenor_days": tenor_days,
        "tolerance_min_pct": None,
        "tolerance_max_pct": None,
        "reimbursement_present": "present" if any(token in text for token in ("REIMBURSE", "REIMBURSING BANK")) else "unknown",
    }


def detect_availability(source: Dict[str, Any], text: str) -> str:
    legacy = str(source.get("lc_type") or "").strip().lower()
    if legacy in {"sight", "at_sight"} or "AT SIGHT" in text or "SIGHT PAYMENT" in text:
        return "sight"
    if legacy in {"deferred", "deferred_payment"} or "DEFERRED PAYMENT" in text:
        return "deferred_payment"
    if legacy == "usance" or "USANCE" in text:
        return "usance"
    if "ACCEPTANCE" in text:
        return "acceptance"
    if "NEGOTIATION" in text or "AVAILABLE BY NEGOTIATION" in text:
        return "negotiation"
    if source.get("mixed_payment_details") or "MIXED PAYMENT" in text:
        return "mixed"
    return "unknown"


def detect_available_with_scope(source: Dict[str, Any], text: str) -> str:
    available_with = clean_string((source.get("available_with") or {}).get("details") if isinstance(source.get("available_with"), dict) else source.get("available_with"))
    upper = (available_with or "").upper()
    if "ANY BANK" in upper or "ANY BANK" in text:
        return "any_bank"
    if "ISSUING BANK" in upper or "ISSUING BANK" in text:
        return "issuing_bank"
    if "ADVISING BANK" in upper or "ADVISING BANK" in text:
        return "advising_bank"
    if "CONFIRMING BANK" in upper or "CONFIRMING BANK" in text:
        return "confirming_bank"
    return "specified_bank" if available_with else "unknown"


def detect_confirmation(source: Dict[str, Any], text: str) -> str:
    value = clean_string(source.get("confirmation") or source.get("confirmation_instructions")) or ""
    upper = value.upper()
    if "CONFIRM" in upper or "CONFIRMED" in text:
        return "confirmed"
    if "MAY ADD" in upper or "MAY ADD" in text:
        return "may_add"
    if "WITHOUT" in upper or ("WITHOUT" in text and "CONFIRM" in text):
        return "without"
    return "unknown"


def extract_requirement_contract(source: Dict[str, Any]) -> Dict[str, List[Any]]:
    items: List[Dict[str, Any]] = []
    requirement_conditions: List[str] = []
    unmapped_requirements: List[str] = []
    for raw_code in coerce_text_sequence(source.get("required_document_types")):
        code = normalize_document_code(raw_code)
        if code:
            items.append(required_document_item(code, str(raw_code), [str(raw_code)], "required_document_types", 0.98))
    for raw in (
        source.get("required_documents"),
        source.get("documents_required"),
        ((source.get("mt700") or {}).get("blocks") or {}).get("46A") if isinstance(source.get("mt700"), dict) else None,
    ):
        lines_source: Any = raw
        if isinstance(raw, list):
            simple_entries: List[Any] = []
            for entry in raw:
                normalized_entry = normalize_required_document_entry(entry)
                if normalized_entry:
                    items.append(normalized_entry)
                    continue
                simple_entries.append(entry)
            lines_source = simple_entries
        elif isinstance(raw, dict):
            normalized_entry = normalize_required_document_entry(raw)
            if normalized_entry:
                items.append(normalized_entry)
                lines_source = []
        for line in coerce_text_sequence(lines_source):
            normalized_line = line.strip()
            if not normalized_line:
                continue
            matches = match_required_document_codes(normalized_line)
            if matches:
                for code, alias in matches:
                    items.append(required_document_item(code, normalized_line, [alias], "documents_required_text", 0.84))
                continue
            if _is_non_document_requirement_condition(normalized_line):
                requirement_conditions.append(normalized_line)
                continue
            if _mentions_explicit_other_specified_document(normalized_line):
                items.append(
                    required_document_item(
                        "other_specified_document",
                        normalized_line,
                        [normalized_line],
                        "documents_required_fallback",
                        0.72,
                    )
                )
                continue
            if _looks_like_document_requirement(normalized_line):
                unmapped_requirements.append(normalized_line)
                continue
            requirement_conditions.append(normalized_line)
    return {
        "required_documents": dedupe_required_documents(items),
        "requirement_conditions": _dedupe_text_sequence(requirement_conditions),
        "unmapped_requirements": _dedupe_text_sequence(unmapped_requirements),
    }


def normalize_required_documents(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    return extract_requirement_contract(source)["required_documents"]


def extract_requirement_conditions(source: Dict[str, Any]) -> List[str]:
    return extract_requirement_contract(source)["requirement_conditions"]


def extract_unmapped_requirements(source: Dict[str, Any]) -> List[str]:
    return extract_requirement_contract(source)["unmapped_requirements"]


def required_document_item(code: str, raw_text: str, aliases_matched: Sequence[str], detection_source: str, confidence: float) -> Dict[str, Any]:
    return {
        "code": code,
        "display_name": humanize(code),
        "category": categorize_document_code(code),
        "raw_text": raw_text,
        "aliases_matched": [alias for alias in aliases_matched if alias],
        "originals": None,
        "copies": None,
        "signed": None,
        "negotiable": None,
        "issuer": None,
        "exact_wording": None,
        "legalized": None,
        "transport_mode": None,
        "detection_source": detection_source,
        "confidence": round(confidence, 2),
        "evidence": [raw_text] if raw_text else [],
    }


def normalize_required_document_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    code = normalize_document_code(
        raw.get("code")
        or raw.get("document_code")
        or raw.get("document_type")
        or raw.get("type")
        or raw.get("display_name")
        or raw.get("raw_text")
        or raw.get("name")
    )
    if not code:
        return None

    aliases_matched = raw.get("aliases_matched")
    if isinstance(aliases_matched, list):
        aliases = [str(alias).strip() for alias in aliases_matched if str(alias).strip()]
    else:
        aliases = []

    raw_text = clean_string(raw.get("raw_text") or raw.get("exact_wording") or raw.get("display_name") or raw.get("name")) or humanize(code)
    evidence_raw = raw.get("evidence")
    if isinstance(evidence_raw, list):
        evidence = [str(item).strip() for item in evidence_raw if str(item).strip()]
    else:
        evidence = [raw_text]

    category = clean_string(raw.get("category")) or categorize_document_code(code)
    display_name = clean_string(raw.get("display_name") or raw.get("name")) or humanize(code)

    return {
        "code": code,
        "display_name": display_name,
        "category": category,
        "raw_text": raw_text,
        "aliases_matched": aliases,
        "originals": extract_int(raw.get("originals")),
        "copies": extract_int(raw.get("copies")),
        "signed": raw.get("signed") if isinstance(raw.get("signed"), bool) else None,
        "negotiable": raw.get("negotiable") if isinstance(raw.get("negotiable"), bool) else None,
        "issuer": clean_string(raw.get("issuer")),
        "exact_wording": clean_string(raw.get("exact_wording")),
        "legalized": raw.get("legalized") if isinstance(raw.get("legalized"), bool) else None,
        "transport_mode": clean_string(raw.get("transport_mode")),
        "detection_source": clean_string(raw.get("detection_source")) or "structured_payload",
        "confidence": float(raw.get("confidence") or 0.99),
        "evidence": evidence,
    }


def match_required_document_codes(line: str) -> List[Tuple[str, str]]:
    lowered = line.lower()
    matches: List[Tuple[str, str]] = []
    seen_codes: set[str] = set()
    for token in _extract_compact_requirement_tokens(line):
        code = COMPACT_REQUIREMENT_TOKENS.get(token)
        if code and code not in seen_codes:
            matches.append((code, token.lower()))
            seen_codes.add(code)
    for code, aliases in DOCUMENT_PATTERNS:
        if code in seen_codes:
            continue
        for alias in aliases:
            if _contains_alias(lowered, alias):
                matches.append((code, alias))
                seen_codes.add(code)
                break
    return matches


def _is_non_document_requirement_condition(line: str) -> bool:
    lowered = line.lower()
    return any(pattern.search(lowered) for pattern in REQUIREMENT_CONDITION_PATTERNS)


def _mentions_explicit_other_specified_document(line: str) -> bool:
    lowered = line.lower()
    return any(alias in lowered for alias in EXPLICIT_OTHER_SPECIFIED_DOCUMENT_ALIASES)


def _looks_like_document_requirement(line: str) -> bool:
    lowered = line.lower()
    if _is_non_document_requirement_condition(line):
        return False
    return any(keyword in lowered for keyword in DOCUMENT_LIKE_REQUIREMENT_KEYWORDS)


def _dedupe_text_sequence(values: Sequence[str]) -> List[str]:
    deduped: List[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _contains_alias(lowered_line: str, alias: str) -> bool:
    normalized_alias = alias.lower().strip()
    if not normalized_alias:
        return False
    if re.search(r"[^a-z0-9]", normalized_alias):
        return normalized_alias in lowered_line
    pattern = re.compile(rf"(^|[^a-z0-9]){re.escape(normalized_alias)}([^a-z0-9]|$)")
    return bool(pattern.search(lowered_line))


def _extract_compact_requirement_tokens(line: str) -> List[str]:
    tokens = re.findall(r"[A-Z0-9/]+", (line or "").upper())
    return [token for token in tokens if token in COMPACT_REQUIREMENT_TOKENS]


def dedupe_required_documents(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for item in items:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        if code not in deduped:
            deduped[code] = item
            order.append(code)
            continue
        existing = deduped[code]
        existing["confidence"] = max(float(existing.get("confidence") or 0.0), float(item.get("confidence") or 0.0))
        existing["aliases_matched"] = sorted(set(existing.get("aliases_matched") or []).union(item.get("aliases_matched") or []))
        for evidence in item.get("evidence") or []:
            if evidence not in (existing.get("evidence") or []):
                existing.setdefault("evidence", []).append(evidence)
    return [deduped[code] for code in order]


def normalize_document_code(raw: Any) -> Optional[str]:
    value = clean_string(raw)
    if not value:
        return None
    lowered = value.lower().strip()
    for code, aliases in DOCUMENT_PATTERNS:
        if lowered == code or any(alias == lowered for alias in aliases):
            return code
    return lowered.replace(" ", "_").replace("-", "_")


def categorize_document_code(code: str) -> str:
    if code in TRANSPORT_DOCUMENT_CODES:
        return "transport"
    if code in INSPECTION_DOCUMENT_CODES:
        return "inspection"
    if code in HEALTH_DOCUMENT_CODES:
        return "health"
    if code in FINANCIAL_DOCUMENT_CODES:
        return "financial"
    if code in CUSTOMS_DOCUMENT_CODES:
        return "customs"
    if code in {"commercial_invoice", "proforma_invoice", "packing_list", "weight_list"}:
        return "core"
    return "other"


def iter_text_blobs(*contexts: Dict[str, Any]) -> Iterable[str]:
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for key in (
            "format", "schema", "message_type", "_source_format", "_source_message_type", "lc_type",
            "lc_type_reason", "form_of_doc_credit", "ucp_reference", "applicable_rules", "goods_description", "additional_conditions",
            "documents_required", "required_documents", "raw_text", "text", "content", "narrative",
        ):
            for value in coerce_text_sequence(context.get(key)):
                yield value
        mt700 = context.get("mt700")
        if isinstance(mt700, dict):
            for key in (
                "form_of_doc_credit", "applicable_rules", "additional_conditions", "docs_required",
                "description_of_goods", "mixed_payment_details", "deferred_payment_details",
                "period_for_presentation",
            ):
                for value in coerce_text_sequence(mt700.get(key)):
                    yield value
            blocks = mt700.get("blocks")
            if isinstance(blocks, dict):
                for value in blocks.values():
                    for item in coerce_text_sequence(value):
                        yield item


def coerce_text_sequence(value: Any) -> List[str]:
    if value in (None, "", [], {}, ()):
        return []
    if isinstance(value, (list, tuple, set)):
        items: List[str] = []
        for item in value:
            items.extend(coerce_text_sequence(item))
        return items
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                parsed = ast.literal_eval(trimmed)
            except Exception:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        if "\n" in trimmed:
            return [line.strip(" -\t") for line in trimmed.splitlines() if line.strip(" -\t")]
        return [trimmed]
    return [str(value).strip()] if str(value).strip() else []


def clean_string(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def extract_int(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    match = re.search(r"(\d+)", str(raw))
    return int(match.group(1)) if match else None


def normalize_permission(raw: Any) -> str:
    value = clean_string(raw)
    upper = (value or "").upper()
    if not upper:
        return "unknown"
    if any(token in upper for token in ("NOT ALLOWED", "PROHIBITED", "FORBIDDEN")):
        return "prohibited"
    if any(token in upper for token in ("ALLOWED", "PERMITTED", "YES")):
        return "allowed"
    return "unknown"


def humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()
