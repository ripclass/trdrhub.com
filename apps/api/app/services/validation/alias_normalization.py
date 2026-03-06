from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Set


CANONICAL_KEY_ALIASES: Dict[str, Set[str]] = {
    # B/L fields
    "voyage_number": {
        "voyage_number", "voyage", "voyage_no", "voy_no", "voy",
        "vessel_voy", "vessel_voyage", "vessel_voyage_no", "vessel_voyage_number",
        "vessel_voyage_ref", "vessel_voy_no", "vsl_voy", "vsl_voyage",
        "vsl_voy_no", "vsl_voyage_no", "vsl_voyage_number",
        "vessel/voy", "vsl/voy", "vessel/voyage", "vsl/voyage", "vessel&voyage",
        "vessel_and_voyage",
    },
    "gross_weight": {
        "gross_weight", "gross_wt", "gross_wgt", "grosswt", "grosswgt",
        "gw", "g.w.", "g.w", "g_w", "g_wt", "g_wgt",
        "gross_weight_total", "total_gross_weight",
        "gross_net_weight", "gross/net_weight", "gross/net", "gross_net", "gross",
    },
    "net_weight": {
        "net_weight", "net_wt", "net_wgt", "netwt", "netwgt",
        "nw", "n.w.", "n.w", "n_w", "n_wt", "n_wgt",
        "net_weight_total", "total_net_weight",
        "gross_net_weight", "gross/net_weight", "gross/net", "gross_net", "net",
    },
    # Packing list size signal fields
    "size_breakdown": {
        "size", "size_breakdown", "size_distribution", "size_wise", "size-wise",
        "size_ratio", "size_run", "size_matrix", "size_assortment", "assortment",
        "qty_per_size", "qty/size", "size/qty", "size&qty", "size_color",
        "size-colour", "carton_size", "ctn_size", "carton_dimension", "carton_dimensions",
        "package_size", "packing_size", "pre_pack", "prepack", "ratio_pack",
    },
    # 47A exporter identifiers
    "exporter_bin": {
        "bin", "b.i.n", "business_identification", "business_id", "business_identification_number",
        "exporter_bin", "vat_reg", "vat_reg_no", "vat_registration_no", "vat_number", "vat_no",
    },
    "exporter_tin": {
        "tin", "t.i.n", "exporter_tin", "tax_identification", "tax_id",
        "tax_reg", "tax_reg_no", "taxpayer_id", "taxpayer_identification", "etin", "e_tin",
    },
}


BL_RAW_PATTERNS: Dict[str, Iterable[str]] = {
    "voyage_number": [
        r"(?:VOYAGE(?:\s*NO\.?|\s*NUMBER|\s*#|\s*REF(?:ERENCE)?)?|VOY\.?|VSL\s*(?:/|&|AND)\s*VOY|VESSEL\s*(?:/|&|AND)\s*VOY(?:AGE)?)\s*[:\-]?\s*([A-Z0-9\-/\.]+)",
    ],
    "gross_weight": [
        r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GROSS\s*WGT\s*/\s*NET\s*WGT|G\.?\s*W\.?\s*/\s*N\.?\s*W\.?|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:\-]?\s*([0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?)\s*/\s*[0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?",
        r"(?:GROSS\s*(?:WEIGHT|WT|WGT)|G\.?\s*W\.?|G/W|GW)\s*[:\-]?\s*([0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?)",
    ],
    "net_weight": [
        r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GROSS\s*WGT\s*/\s*NET\s*WGT|G\.?\s*W\.?\s*/\s*N\.?\s*W\.?|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:\-]?\s*[0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?\s*/\s*([0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?)",
        r"(?:NET\s*(?:WEIGHT|WT|WGT)|N\.?\s*W\.?|N/W|NW)\s*[:\-]?\s*([0-9.,]+\s*(?:KGS?|KG|LBS?|LB)?)",
    ],
}


SIZE_BREAKDOWN_INDICATORS = {
    "SIZE", "S/M/L", "SMALL", "MEDIUM", "LARGE", "XL", "XXL",
    "SIZE BREAKDOWN", "SIZE DISTRIBUTION", "SIZES PER CARTON", "SIZE WISE", "SIZE-WISE",
    "SIZE/QTY", "SIZE & QTY", "SIZE RATIO", "SIZE RUN", "SIZE MATRIX",
    "SIZE ASSORTMENT", "ASSORTMENT", "PRE-PACK", "PREPACK", "RATIO PACK",
    "QTY PER SIZE", "QTY/SIZE", "SIZE-COLOR", "SIZE COLOR", "SIZE/COLOUR", "SIZE/ COLOR",
    "CARTON SIZE", "CTN SIZE", "CARTON DIMENSION", "CARTON DIMENSIONS", "PACKAGE SIZE", "PACKING SIZE",
}


BIN_REGEX_PATTERNS = [
    r"(?:EXPORTER\s+)?(?:B\.?I\.?N\.?|BIN|VAT\s*REG(?:ISTRATION)?|VAT\s*REG\.?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|VAT\s*REGISTRATION\s*NO\.?|VAT\s*REGISTRATION\s*NUMBER)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
    r"(?:BUSINESS\s+IDENTIFICATION|BUSINESS\s+ID(?:ENTIFICATION)?)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
]

TIN_REGEX_PATTERNS = [
    r"(?:EXPORTER\s+)?(?:T\.?I\.?N\.?|TIN|TAX\s*REG(?:ISTRATION)?|TAX\s*REG\.?|TAXPAYER\s+ID(?:ENTIFICATION)?|E-?TIN|ETIN)\s*(?:NO\.?|NUMBER)?\s*(?:#|:)?\s*([0-9][0-9\-]+)",
    r"(?:TAX\s+IDENTIFICATION|TAX\s+ID(?:ENTIFICATION)?)\s*(?:NO\.?|NUMBER)?\s*(?:#|:)?\s*([0-9][0-9\-]+)",
]


def normalize_alias_key(key: str) -> str:
    if not key:
        return ""
    s = str(key).strip().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[./#()\-]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def canonical_field_key(key: str) -> str:
    normalized = normalize_alias_key(key)
    for canonical, aliases in CANONICAL_KEY_ALIASES.items():
        if normalized in {normalize_alias_key(a) for a in aliases}:
            return canonical
    return normalized


def canonicalize_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for k, v in (data or {}).items():
        if k.startswith("_") or v is None:
            continue
        canonical = canonical_field_key(k)
        if canonical not in result:
            result[canonical] = v
        normalized_key = normalize_alias_key(k)
        result[normalized_key] = v

        # If a combined gross/net value is provided, expose both canonical fields.
        # Example: "gross/net_weight": "1200/1100 KGS"
        if normalized_key in {"gross_net_weight", "gross_net"} and isinstance(v, str) and "/" in v:
            gross_part, net_part = [p.strip() for p in v.split("/", 1)]
            if gross_part and "gross_weight" not in result:
                result["gross_weight"] = gross_part
            if net_part and "net_weight" not in result:
                result["net_weight"] = net_part
    return result


def find_first_pattern_value(text: str, patterns: Iterable[str]) -> Optional[str]:
    if not text:
        return None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(match.lastindex).strip() if match.lastindex else match.group(0).strip()
    return None


def text_has_size_breakdown(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return any(indicator in t for indicator in SIZE_BREAKDOWN_INDICATORS)
