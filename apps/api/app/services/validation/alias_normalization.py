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


def _extract_pattern_with_evidence(
    lines: Iterable[tuple[str, str]],
    label_regex: str,
    patterns: Iterable[str],
    normalize: Optional[Any] = None,
    validate: Optional[Any] = None,
    lookahead: int = 1,
) -> Dict[str, Any]:
    label_seen = False
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    line_items = list(lines)
    for idx, (line, source) in enumerate(line_items):
        if re.search(label_regex, line, re.IGNORECASE):
            label_seen = True
        candidate_windows = [line]
        for offset in range(1, max(1, lookahead) + 1):
            if idx + offset < len(line_items):
                candidate_windows.append(f"{line}: {line_items[idx + offset][0]}")
        for candidate in candidate_windows:
            for pattern in compiled_patterns:
                match = pattern.search(candidate)
                if not match:
                    continue
                value = (match.group(1) if match.lastindex else match.group(0)).strip()
                if normalize:
                    value = normalize(value)
                if validate and not validate(value):
                    return {"value": None, "reason": "parse_failed", "evidence_snippet": candidate, "source": source}
                return {"value": value, "reason": "found", "evidence_snippet": candidate, "source": source}
    return {
        "value": None,
        "reason": "parse_failed" if label_seen else "missing_in_source",
        "evidence_snippet": None,
        "source": None,
    }


def _clean_party_value(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).strip(" :-,")


def _valid_party_value(value: str) -> bool:
    text = _clean_party_value(value)
    if len(text) < 3 or not any(ch.isalpha() for ch in text):
        return False
    word_tokens = [token.upper() for token in re.findall(r"[A-Z]{2,}", text.upper())]
    if not word_tokens:
        return False
    blocked = {"BIN", "TIN", "VAT", "TAX", "DATE", "NO", "NUMBER", "REF", "REFERENCE", "WEIGHT", "GROSS", "NET"}
    if word_tokens[0] in blocked:
        return False
    meaningful = [token for token in word_tokens if token not in blocked]
    return bool(meaningful)


def _extract_party_with_evidence(
    lines: Iterable[tuple[str, str]],
    label_regex: str,
    lookahead: int = 2,
) -> Dict[str, Any]:
    label_seen = False
    line_items = list(lines)
    stop_regex = re.compile(
        r"^(?:BUYER|CONSIGNEE|NOTIFY(?:\s+PARTY)?|SELLER|EXPORTER|SHIPPER|CARRIER|ISSUER|"
        r"DATE(?:\s+OF\s+ISSUE)?|INVOICE(?:\s+DATE)?|B/?L(?:\s+NO)?|LC(?:\s+NO)?|L/C(?:\s+NO)?|"
        r"TOTAL|GROSS|NET|PORT|VESSEL|VOYAGE|PACKING(?:\s+DETAILS)?)\b",
        re.IGNORECASE,
    )

    for idx, (line, source) in enumerate(line_items):
        if not re.search(label_regex, line, re.IGNORECASE):
            continue
        label_seen = True
        inline = re.sub(label_regex, "", line, count=1, flags=re.IGNORECASE)
        inline = re.sub(r"^\s*[:#-]?\s*", "", inline).strip()
        if inline and _valid_party_value(inline):
            return {
                "value": _clean_party_value(inline),
                "reason": "found",
                "evidence_snippet": line,
                "source": source,
            }

        continuation: list[str] = []
        for offset in range(1, max(1, lookahead) + 1):
            if idx + offset >= len(line_items):
                break
            next_line = line_items[idx + offset][0].strip()
            if not next_line:
                continue
            if stop_regex.search(next_line):
                break
            continuation.append(next_line)
            if len(continuation) >= lookahead:
                break

        if continuation:
            value = _clean_party_value(continuation[0])
            if _valid_party_value(value):
                return {
                    "value": value,
                    "reason": "found",
                    "evidence_snippet": " ".join([line] + continuation[:2]).strip(),
                    "source": source,
                }

    return {
        "value": None,
        "reason": "parse_failed" if label_seen else "missing_in_source",
        "evidence_snippet": None,
        "source": None,
    }


def _recovery_confidence(field_name: str, source: Optional[str], reason: str) -> Optional[float]:
    if reason != "found":
        return None
    base = {
        "buyer_po_number": 0.88,
        "exporter_bin": 0.9,
        "exporter_tin": 0.9,
        "invoice_number": 0.9,
        "bl_number": 0.9,
        "voyage_number": 0.86,
        "gross_weight": 0.86,
        "net_weight": 0.86,
        "issue_date": 0.86,
        "issuer": 0.86,
    }.get(field_name, 0.85)
    if source == "spans":
        base = max(0.8, base - 0.02)
    return round(base, 2)


def extract_direct_token_recovery(
    raw_text: str,
    extraction_artifacts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Deterministic token recovery for critical doc tokens with evidence snippets."""
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
    recovered["invoice_number"] = _extract_pattern_with_evidence(
        all_lines,
        label_regex=r"(?:INVOICE\s*(?:NO\.?|NUMBER|#|REF(?:ERENCE)?)|INV(?:OICE)?\s*(?:NO\.?|NUMBER|#))",
        patterns=[
            r"(?:INVOICE\s*(?:NO\.?|NUMBER|#|REF(?:ERENCE)?)|INV(?:OICE)?\s*(?:NO\.?|NUMBER|#))\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/\.]{3,30})",
        ],
        normalize=_norm_id,
        validate=lambda v: bool(re.match(r"^[A-Z0-9][A-Z0-9\-/\.]{3,30}$", v, re.IGNORECASE)),
    )
    recovered["bl_number"] = _extract_pattern_with_evidence(
        all_lines,
        label_regex=r"(?:B/?L|BILL\s+OF\s+LADING|TRANSPORT\s+DOCUMENT)\s*(?:NO\.?|NUMBER|#|REF(?:ERENCE)?)?",
        patterns=[
            r"(?:B/?L|BILL\s+OF\s+LADING|TRANSPORT\s+DOCUMENT)\s*(?:NO\.?|NUMBER|#|REF(?:ERENCE)?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/\.]{3,30})",
        ],
        normalize=_norm_id,
        validate=lambda v: bool(re.match(r"^[A-Z0-9][A-Z0-9\-/\.]{3,30}$", v, re.IGNORECASE)),
    )
    recovered["issue_date"] = _extract_pattern_with_evidence(
        all_lines,
        label_regex=r"(?:^:?31C:?|DATE\s+OF\s+ISSUE|ISSUE\s+DATE|INVOICE\s+DATE|PACKING\s+LIST\s+DATE|BL\s+DATE|SHIPMENT\s+DATE|SHIPPED\s+ON\s+BOARD\s+DATE|ON\s+BOARD\s+DATE|ISSUED\s+ON|DATED|DATE)\b",
        patterns=[
            r"(?:^:?31C:?|DATE\s+OF\s+ISSUE|ISSUE\s+DATE|INVOICE\s+DATE|PACKING\s+LIST\s+DATE|BL\s+DATE|SHIPMENT\s+DATE|SHIPPED\s+ON\s+BOARD\s+DATE|ON\s+BOARD\s+DATE|ISSUED\s+ON|DATED|DATE)\s*[:#-]?\s*([0-9A-Z][0-9A-Z ./-]{4,24})",
        ],
        normalize=lambda v: re.sub(r"\s+", " ", v).strip(" :-"),
        validate=lambda v: bool(re.search(r"\d", v)),
    )
    recovered["issuer"] = _extract_party_with_evidence(
        all_lines,
        label_regex=r"(?:ISSUING\s+BANK|ISSUER|SELLER|EXPORTER|SHIPPER|CARRIER)\s*[:#-]?",
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
        elif voyage_status["value"] is None:
            voyage_candidate = find_first_pattern_value(line, BL_RAW_PATTERNS["voyage_number"])
            voyage_snippet = line
            if not voyage_candidate and idx + 1 < len(all_lines):
                voyage_snippet = f"{line}: {all_lines[idx + 1][0]}"
                voyage_candidate = find_first_pattern_value(voyage_snippet, BL_RAW_PATTERNS["voyage_number"])
            if voyage_candidate and _is_valid_voyage(voyage_candidate):
                voyage_status = {"value": voyage_candidate, "reason": "found", "evidence_snippet": voyage_snippet, "source": source}

        wn = _parse_gross_net_from_line(line)
        if (not wn.get("gross_weight") or not wn.get("net_weight")) and idx + 1 < len(all_lines):
            wn = _parse_gross_net_from_line(f"{line}: {all_lines[idx + 1][0]}")
        if wn.get("gross_weight") and gross_status["value"] is None:
            gross_status = {"value": wn["gross_weight"], "reason": "found", "evidence_snippet": line, "source": source}
        if wn.get("net_weight") and net_status["value"] is None:
            net_status = {"value": wn["net_weight"], "reason": "found", "evidence_snippet": line, "source": source}
        if gross_status["value"] is None:
            gross_candidate = find_first_pattern_value(line, BL_RAW_PATTERNS["gross_weight"])
            gross_snippet = line
            if not gross_candidate and idx + 1 < len(all_lines):
                gross_snippet = f"{line}: {all_lines[idx + 1][0]}"
                gross_candidate = find_first_pattern_value(gross_snippet, BL_RAW_PATTERNS["gross_weight"])
            if gross_candidate and _is_valid_weight_value(gross_candidate):
                gross_status = {"value": gross_candidate, "reason": "found", "evidence_snippet": gross_snippet, "source": source}
        if net_status["value"] is None:
            net_candidate = find_first_pattern_value(line, BL_RAW_PATTERNS["net_weight"])
            net_snippet = line
            if not net_candidate and idx + 1 < len(all_lines):
                net_snippet = f"{line}: {all_lines[idx + 1][0]}"
                net_candidate = find_first_pattern_value(net_snippet, BL_RAW_PATTERNS["net_weight"])
            if net_candidate and _is_valid_weight_value(net_candidate):
                net_status = {"value": net_candidate, "reason": "found", "evidence_snippet": net_snippet, "source": source}

    if voyage_label_seen and voyage_status["value"] is None:
        voyage_status["reason"] = "parse_failed"
    if grossnet_label_seen and gross_status["value"] is None:
        gross_status["reason"] = "parse_failed"
    if grossnet_label_seen and net_status["value"] is None:
        net_status["reason"] = "parse_failed"

    recovered["voyage_number"] = voyage_status
    recovered["gross_weight"] = gross_status
    recovered["net_weight"] = net_status

    for field_name, item in recovered.items():
        if not isinstance(item, dict):
            continue
        confidence = _recovery_confidence(field_name, item.get("source"), str(item.get("reason") or ""))
        if confidence is not None:
            item["confidence"] = confidence

    return recovered
