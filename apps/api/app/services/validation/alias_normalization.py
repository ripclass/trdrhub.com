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
        "vessel_and_voyage", "vvd", "vvd_no", "vvd_number", "vessel_voyage_details",
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
        r"(?:VOYAGE(?:\s*NO\.?|\s*NUMBER|\s*#|\s*REF(?:ERENCE)?)?|VOY\.?|VSL\s*(?:/|&|AND)\s*VOY|VESSEL\s*(?:/|&|AND)\s*VOY(?:AGE)?|VVD(?:\s*(?:NO\.?|NUMBER|#))?)\s*[:\-]?\s*([A-Z0-9\-/\.]+)",
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


def _is_valid_voyage(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    if len(v) < 2 or len(v) > 30:
        return False
    if not re.search(r"\d", v):
        return False
    return bool(re.match(r"^[A-Z0-9][A-Z0-9\-\./]*$", v, re.IGNORECASE))


def _is_valid_weight_value(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    return bool(re.match(r"^[0-9][0-9,\.]*\s*(?:KGS?|KG|LBS?|LB)?$", v, re.IGNORECASE))


def _parse_vessel_voyage_from_line(text: str) -> Dict[str, str]:
    line = (text or "").strip()
    if not line:
        return {}

    match = re.search(
        r"(?:VSL|VESSEL)(?:\s*(?:/|&|AND)\s*VOY(?:AGE)?)?\s*[:\-]?\s*([A-Z0-9 .\-]{2,80}?)\s*(?:/|\s{2,}|\s+-\s+)\s*([A-Z0-9\-\./]{2,30})\b",
        line,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"(?:V(?:ESSEL)?\s*/\s*VOY(?:AGE)?|VVD(?:\s*(?:NO\.?|NUMBER|#))?)\s*[:\-]?\s*([A-Z0-9 .\-]{2,80}?)\s*(?:/|\s{2,}|\s+-\s+)\s*([A-Z0-9\-\./]{2,30})\b",
            line,
            re.IGNORECASE,
        )

    if not match:
        return {}

    vessel = match.group(1).strip(" .:-")
    voyage = match.group(2).strip(" .:-")
    if not vessel or not _is_valid_voyage(voyage):
        return {}
    return {"vessel_name": vessel, "voyage_number": voyage}


def _parse_gross_net_from_line(text: str) -> Dict[str, str]:
    line = (text or "").strip()
    if not line:
        return {}

    match = re.search(
        r"(?:GROSS\s*/\s*NET|GROSS\s*WT\s*/\s*NET\s*WT|GROSS\s*WGT\s*/\s*NET\s*WGT|G\.?\s*W\.?\s*/\s*N\.?\s*W\.?|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:\-]?\s*([0-9][0-9,\.]*(?:\s*(?:KGS?|KG|LBS?|LB))?)\s*/\s*([0-9][0-9,\.]*(?:\s*(?:KGS?|KG|LBS?|LB))?)",
        line,
        re.IGNORECASE,
    )
    if not match:
        return {}

    gross = match.group(1).strip()
    net = match.group(2).strip()
    if not (_is_valid_weight_value(gross) and _is_valid_weight_value(net)):
        return {}
    return {"gross_weight": gross, "net_weight": net}


def _iter_artifact_lines(extraction_artifacts: Dict[str, Any]) -> Iterable[str]:
    if not isinstance(extraction_artifacts, dict):
        return []

    spans = extraction_artifacts.get("spans")
    if not isinstance(spans, list):
        return []

    collected = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        text = str(span.get("text") or "").strip()
        if not text:
            continue
        bbox = span.get("bbox") or {}
        page = bbox.get("page") if isinstance(bbox, dict) else None
        y1 = bbox.get("y1") if isinstance(bbox, dict) else None
        x1 = bbox.get("x1") if isinstance(bbox, dict) else None
        try:
            page_val = float(page) if page is not None else 0.0
        except Exception:
            page_val = 0.0
        try:
            y_val = float(y1) if y1 is not None else 0.0
        except Exception:
            y_val = 0.0
        try:
            x_val = float(x1) if x1 is not None else 0.0
        except Exception:
            x_val = 0.0
        collected.append((page_val, y_val, x_val, text))

    if not collected:
        return []

    collected.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in collected]


def extract_bl_required_field_candidates(
    raw_text: str,
    extraction_artifacts: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Best-effort, conservative recovery for BL voyage/gross/net from text + OCR spans."""
    candidates: Dict[str, str] = {}

    text_lines = [ln.strip() for ln in (raw_text or "").splitlines() if ln and ln.strip()]
    artifact_lines = [ln.strip() for ln in _iter_artifact_lines(extraction_artifacts) if ln and ln.strip()]

    # Scan raw lines first, then artifact lines (artifact lines may preserve layout/header zones).
    all_lines = text_lines + artifact_lines

    for idx, line in enumerate(all_lines):
        if "voyage_number" not in candidates:
            vv = _parse_vessel_voyage_from_line(line)
            if vv.get("voyage_number"):
                candidates.setdefault("voyage_number", vv["voyage_number"])

        if "gross_weight" not in candidates or "net_weight" not in candidates:
            wn = _parse_gross_net_from_line(line)
            if wn.get("gross_weight"):
                candidates.setdefault("gross_weight", wn["gross_weight"])
            if wn.get("net_weight"):
                candidates.setdefault("net_weight", wn["net_weight"])

        # Label+value split across consecutive lines in OCR/layout blocks.
        if idx + 1 < len(all_lines):
            nxt = all_lines[idx + 1]
            lowered = line.lower()
            if "voyage_number" not in candidates and (("vessel" in lowered and "voy" in lowered) or ("vsl" in lowered and "voy" in lowered)):
                vv = _parse_vessel_voyage_from_line(f"{line}: {nxt}") or _parse_vessel_voyage_from_line(nxt)
                if vv.get("voyage_number"):
                    candidates.setdefault("voyage_number", vv["voyage_number"])
            if ("gross_weight" not in candidates or "net_weight" not in candidates) and ("gross" in lowered and "net" in lowered):
                wn = _parse_gross_net_from_line(f"{line}: {nxt}") or _parse_gross_net_from_line(nxt)
                if wn.get("gross_weight"):
                    candidates.setdefault("gross_weight", wn["gross_weight"])
                if wn.get("net_weight"):
                    candidates.setdefault("net_weight", wn["net_weight"])

        if {"voyage_number", "gross_weight", "net_weight"}.issubset(set(candidates.keys())):
            break

    return candidates


def text_has_size_breakdown(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return any(indicator in t for indicator in SIZE_BREAKDOWN_INDICATORS)


def _iter_text_evidence_lines(raw_text: str, extraction_artifacts: Optional[Dict[str, Any]]) -> Iterable[tuple[str, str]]:
    """Yield (line, source) pairs from merged raw text then OCR spans."""
    for line in [ln.strip() for ln in (raw_text or "").splitlines() if ln and ln.strip()]:
        yield line, "raw_text"
    for line in [ln.strip() for ln in _iter_artifact_lines(extraction_artifacts) if ln and ln.strip()]:
        yield line, "spans"


def _extract_identifier_with_evidence(
    lines: Iterable[tuple[str, str]],
    label_regex: str,
    value_regex: str,
    normalize: Optional[Any] = None,
    validate: Optional[Any] = None,
) -> Dict[str, Any]:
    label_seen = False
    for line, source in lines:
        upper = line.upper()
        if re.search(label_regex, upper, re.IGNORECASE):
            label_seen = True
            match = re.search(value_regex, upper, re.IGNORECASE)
            if not match:
                continue
            value = (match.group(1) if match.lastindex else match.group(0)).strip()
            if normalize:
                value = normalize(value)
            if validate and not validate(value):
                return {"value": None, "reason": "parse_failed", "evidence_snippet": line, "source": source}
            return {"value": value, "reason": "found", "evidence_snippet": line, "source": source}
    return {
        "value": None,
        "reason": "parse_failed" if label_seen else "missing_in_source",
        "evidence_snippet": None,
        "source": None,
    }


def extract_direct_token_recovery(
    raw_text: str,
    extraction_artifacts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Deterministic token recovery for PO/BIN/TIN + B/L voyage/gross/net with evidence snippets."""
    all_lines = list(_iter_text_evidence_lines(raw_text, extraction_artifacts))

    def _norm_id(v: str) -> str:
        return re.sub(r"\s+", "", v).strip(" :-")

    def _valid_po(v: str) -> bool:
        return bool(re.match(r"^[A-Z0-9]{2,}(?:[-/][A-Z0-9]{2,})+$", v, re.IGNORECASE))

    def _valid_bin(v: str) -> bool:
        digits = re.sub(r"\D", "", v)
        return 9 <= len(digits) <= 14

    def _valid_tin(v: str) -> bool:
        digits = re.sub(r"\D", "", v)
        return 10 <= len(digits) <= 15

    recovered: Dict[str, Dict[str, Any]] = {}

    recovered["buyer_po_number"] = _extract_identifier_with_evidence(
        all_lines,
        label_regex=r"(?:BUYER\s+)?(?:PURCHASE\s+ORDER|P\.?\s*O\.?|PO)\b",
        value_regex=r"(?:PURCHASE\s+ORDER\s*(?:NO\.?|NUMBER)?|P\.?\s*O\.?\s*(?:NO\.?|NUMBER)?|PO\s*(?:NO\.?|NUMBER)?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{4,})",
        normalize=_norm_id,
        validate=_valid_po,
    )
    recovered["exporter_bin"] = _extract_identifier_with_evidence(
        all_lines,
        label_regex=r"(?:\bBIN\b|B\.?I\.?N\.?|VAT\s*REG|BUSINESS\s+IDENTIFICATION)",
        value_regex=r"(?:\bBIN\b|B\.?I\.?N\.?|VAT\s*REG(?:ISTRATION)?(?:\s*NO\.?|\s*NUMBER)?|BUSINESS\s+IDENTIFICATION(?:\s*NO\.?|\s*NUMBER)?)\s*[:#-]?\s*([0-9][0-9\s\-]{7,})",
        normalize=_norm_id,
        validate=_valid_bin,
    )
    recovered["exporter_tin"] = _extract_identifier_with_evidence(
        all_lines,
        label_regex=r"(?:\bTIN\b|T\.?I\.?N\.?|E-?TIN|ETIN|TAX\s*(?:ID|REG|IDENTIFICATION|PAYER\s+ID))",
        value_regex=r"(?:\bTIN\b|T\.?I\.?N\.?|E-?TIN|ETIN|TAX\s*(?:ID|REG(?:ISTRATION)?|IDENTIFICATION|PAYER\s+ID))\s*(?:NO\.?|NUMBER)?\s*[:#-]?\s*([0-9][0-9\s\-]{8,})",
        normalize=lambda v: re.sub(r"\D", "", v),
        validate=_valid_tin,
    )

    # BL fields: use line-level parsing so evidence snippets are carried.
    voyage_status = {"value": None, "reason": "missing_in_source", "evidence_snippet": None, "source": None}
    gross_status = {"value": None, "reason": "missing_in_source", "evidence_snippet": None, "source": None}
    net_status = {"value": None, "reason": "missing_in_source", "evidence_snippet": None, "source": None}
    voyage_label_seen = False
    grossnet_label_seen = False

    for idx, (line, source) in enumerate(all_lines):
        lowered = line.lower()
        if any(tok in lowered for tok in ("voy", "voyage", "vvd")):
            voyage_label_seen = True
        if "gross" in lowered or "net" in lowered or "g/w" in lowered or "n/w" in lowered:
            grossnet_label_seen = True

        vv = _parse_vessel_voyage_from_line(line)
        if not vv.get("voyage_number") and idx + 1 < len(all_lines):
            vv = _parse_vessel_voyage_from_line(f"{line}: {all_lines[idx + 1][0]}")
        if vv.get("voyage_number") and voyage_status["value"] is None:
            voyage_status = {"value": vv["voyage_number"], "reason": "found", "evidence_snippet": line, "source": source}

        wn = _parse_gross_net_from_line(line)
        if (not wn.get("gross_weight") or not wn.get("net_weight")) and idx + 1 < len(all_lines):
            wn = _parse_gross_net_from_line(f"{line}: {all_lines[idx + 1][0]}")
        if wn.get("gross_weight") and gross_status["value"] is None:
            gross_status = {"value": wn["gross_weight"], "reason": "found", "evidence_snippet": line, "source": source}
        if wn.get("net_weight") and net_status["value"] is None:
            net_status = {"value": wn["net_weight"], "reason": "found", "evidence_snippet": line, "source": source}

    if voyage_label_seen and voyage_status["value"] is None:
        voyage_status["reason"] = "parse_failed"
    if grossnet_label_seen and gross_status["value"] is None:
        gross_status["reason"] = "parse_failed"
    if grossnet_label_seen and net_status["value"] is None:
        net_status["reason"] = "parse_failed"

    recovered["voyage_number"] = voyage_status
    recovered["gross_weight"] = gross_status
    recovered["net_weight"] = net_status

    return recovered
