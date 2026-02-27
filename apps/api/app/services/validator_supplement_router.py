from __future__ import annotations

from typing import Any, Dict, List, Tuple
import logging
import re

logger = logging.getLogger(__name__)

ICC_TEXT_KEYS = [
    "applicable_rules",
    "applicable_rules_text",
    "lc_text",
    "raw_text",
    "mt700_40e",
    "mt700_field_40e",
    "narrative",
    "notes",
    "clauses",
    "terms",
    "instructions",
    "reimbursement_text",
]

ICC_META_KEYS = [
    "lc_type",
    "instrument_type",
    "product",
    "product_type",
    "product_category",
    "transaction_type",
    "facility_type",
]

ICC_RULE_PATTERN = re.compile(
    r"(isp\s*98|isp98|ucp\s*600|ucp600|e[-\s]?ucp\s*(?:v?\s*2\.1|latest)|urr\s*725|urr725|urdg\s*758|urdg758|urc\s*522|urc522)",
    re.IGNORECASE,
)


def resolve_domain_sequence(document_data: Dict[str, Any], *, default_domain: str = "icc.ucp600") -> List[str]:
    requested_domain = document_data.get("domain")
    jurisdiction = document_data.get("jurisdiction", "global")
    extra_supplements = document_data.get("supplement_domains", []) or []

    if requested_domain:
        domain_sequence = _unique_preserve(
            [requested_domain, *[d for d in extra_supplements if isinstance(d, str)]]
        )
    else:
        base_domain, detected_supplements = detect_icc_ruleset_domains(document_data)
        domain_sequence = _unique_preserve(
            [base_domain, *detected_supplements, *[d for d in extra_supplements if isinstance(d, str)]]
        )

    domain_sequence = [d for d in domain_sequence if isinstance(d, str) and d.strip()]
    if not domain_sequence:
        domain_sequence = [default_domain]

    if any(d.startswith("icc.") for d in domain_sequence):
        crossdoc_domain = "icc.lcopilot.crossdoc"
        if crossdoc_domain not in domain_sequence:
            domain_sequence.append(crossdoc_domain)

    logger.info(
        "Resolved validator domain routing",
        extra={
            "domain_sequence": domain_sequence,
            "requested_domain": requested_domain,
            "jurisdiction": jurisdiction,
            "supplement_count": max(0, len(domain_sequence) - 1),
        },
    )
    return domain_sequence


def detect_icc_ruleset_domains(document_data: Dict[str, Any]) -> Tuple[str, List[str]]:
    text_blob = _gather_text_blob(document_data).lower()
    meta_blob = _gather_meta_blob(document_data).lower()

    hits = {
        match.group(0).lower().replace(" ", "").replace("-", "")
        for match in ICC_RULE_PATTERN.finditer(text_blob)
    }

    has_isp = any("isp98" in token for token in hits)
    has_ucp = any("ucp600" in token for token in hits) or "ucp 600" in text_blob
    has_eucp = ("eucp" in text_blob and ("2.1" in text_blob or "latest" in text_blob)) or any("eucp" in token for token in hits)
    has_urr = any("urr725" in token for token in hits)
    has_urdg = any("urdg758" in token for token in hits)
    has_urc = any("urc522" in token for token in hits)

    is_standby = bool(document_data.get("is_standby")) or "standby" in meta_blob or "sblc" in meta_blob
    is_guarantee = bool(document_data.get("is_guarantee")) or "guarantee" in meta_blob
    is_collection = bool(document_data.get("is_collection")) or "collection" in meta_blob or has_urc

    supplements: List[str] = []

    if has_isp and has_ucp:
        logger.warning("Detected both ISP98 and UCP600 references; prioritising ISP98.")

    if has_urdg and has_isp:
        logger.warning("Detected URDG text alongside ISP98; using URDG for guarantee context.")

    if has_isp:
        base_domain = "icc.isp98"
    elif has_urdg or is_guarantee:
        base_domain = "icc.urdg758"
    elif has_ucp:
        base_domain = "icc.ucp600"
    elif is_collection:
        base_domain = "icc.urc522"
    elif is_standby:
        base_domain = "icc.isp98"
    else:
        base_domain = "icc.ucp600"

    if base_domain == "icc.ucp600" and has_eucp:
        supplements.append("icc.eucp2.1")

    if has_urr:
        supplements.append("icc.urr725")

    if is_collection and base_domain != "icc.urc522":
        base_domain = "icc.urc522"

    return base_domain, _unique_preserve(supplements)


def _gather_text_blob(document_data: Dict[str, Any]) -> str:
    def _append_value(value: Any, parts: List[str]) -> None:
        if value is None:
            return
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                parts.append(stripped)
        elif isinstance(value, dict):
            for nested in value.values():
                _append_value(nested, parts)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                _append_value(item, parts)
        else:
            parts.append(str(value))

    fragments: List[str] = []
    for key in ICC_TEXT_KEYS:
        _append_value(document_data.get(key), fragments)

    return " ".join(fragments)


def _gather_meta_blob(document_data: Dict[str, Any]) -> str:
    fragments: List[str] = []
    for key in ICC_META_KEYS:
        value = document_data.get(key)
        if isinstance(value, str) and value.strip():
            fragments.append(value.strip())
    if document_data.get("is_standby"):
        fragments.append("standby")
    if document_data.get("is_guarantee"):
        fragments.append("guarantee")
    if document_data.get("is_collection"):
        fragments.append("collection")
    return " ".join(fragments)


def _unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered
