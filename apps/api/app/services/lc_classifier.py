from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.core.lc_types import LCType, LCTypeGuess

COUNTRY_SYNONYMS = {
    "u.s.a": "united states",
    "usa": "united states",
    "us": "united states",
    "united states of america": "united states",
    "united states america": "united states",
    "u.k.": "united kingdom",
    "uk": "united kingdom",
    "great britain": "united kingdom",
    "p.r. china": "china",
    "pr china": "china",
    "people's republic of china": "china",
    "peoples republic of china": "china",
    "srilanka": "sri lanka",
    "bangla desh": "bangladesh",
    "bd": "bangladesh",
}


def detect_lc_type(
    lc_data: Optional[Dict[str, Any]],
    shipment_data: Optional[Dict[str, Any]] = None,
) -> LCTypeGuess:
    """
    Attempt to detect whether an LC context represents an import or export workflow.

    Heuristics:
        - Import LC: applicant + issuing bank + discharge port match, beneficiary differs.
        - Export LC: beneficiary + issuing bank + loading port match, applicant differs.
        - Fallback to weaker hints (applicant vs discharge, beneficiary vs loading).
        - Otherwise unknown.
    """

    lc_context = lc_data or {}
    shipment_context = shipment_data or {}

    applicant_country = _extract_party_country(lc_context.get("applicant")) or _normalize_country(
        lc_context.get("applicant_country") or lc_context.get("applicantCountry")
    )
    beneficiary_country = _extract_party_country(lc_context.get("beneficiary")) or _normalize_country(
        lc_context.get("beneficiary_country") or lc_context.get("beneficiaryCountry")
    )
    issuing_country = _extract_party_country(lc_context.get("issuing_bank")) or _normalize_country(
        lc_context.get("issuing_bank_country")
        or lc_context.get("issuingBankCountry")
        or lc_context.get("issuing_bank_branch_country")
    )
    advising_country = _extract_party_country(lc_context.get("advising_bank")) or _normalize_country(
        lc_context.get("advising_bank_country") or lc_context.get("advisingBankCountry")
    )

    ports_context = lc_context.get("ports") or {}
    pol_country = (
        _extract_port_country(shipment_context, "port_of_loading")
        or _normalize_country(shipment_context.get("port_of_loading_country"))
        or _normalize_country(ports_context.get("loading") or ports_context.get("port_of_loading"))
        or _normalize_country(shipment_context.get("port_of_shipment"))
    )
    pod_country = (
        _extract_port_country(shipment_context, "port_of_discharge")
        or _normalize_country(shipment_context.get("port_of_discharge_country"))
        or _normalize_country(ports_context.get("discharge") or ports_context.get("port_of_discharge"))
        or _normalize_country(shipment_context.get("port_of_destination"))
    )

    strong_import = (
        applicant_country
        and issuing_country
        and pod_country
        and applicant_country == issuing_country == pod_country
        and beneficiary_country
        and beneficiary_country != applicant_country
    )

    if strong_import:
        return {
            "lc_type": LCType.IMPORT.value,
            "reason": (
                f"Applicant, issuing bank, and discharge port all in {applicant_country}; "
                f"beneficiary in {beneficiary_country}. Typical import LC."
            ),
            "confidence": 0.95,
        }

    strong_export = (
        beneficiary_country
        and issuing_country
        and pol_country
        and beneficiary_country == issuing_country == pol_country
        and applicant_country
        and applicant_country != beneficiary_country
    )

    if strong_export:
        return {
            "lc_type": LCType.EXPORT.value,
            "reason": (
                f"Beneficiary, issuing bank, and loading port all in {beneficiary_country}; "
                f"applicant in {applicant_country}. Typical export LC."
            ),
            "confidence": 0.95,
        }

    weak_import = applicant_country and pod_country and applicant_country == pod_country
    weak_export = beneficiary_country and pol_country and beneficiary_country == pol_country

    # If both weak signals point to different countries, treat as unknown
    if weak_import and weak_export and (applicant_country != beneficiary_country):
        return {
            "lc_type": LCType.UNKNOWN.value,
            "reason": (
                "Conflicting port heuristics: applicant/discharge suggest import while "
                "beneficiary/loading suggest export."
            ),
            "confidence": 0.1,
        }

    if weak_import:
        confidence = 0.65 if issuing_country == applicant_country else 0.6
        return {
            "lc_type": LCType.IMPORT.value,
            "reason": f"Applicant country matches discharge port ({applicant_country}). Likely import LC.",
            "confidence": confidence,
        }

    if weak_export:
        confidence = 0.65 if issuing_country == beneficiary_country else 0.6
        return {
            "lc_type": LCType.EXPORT.value,
            "reason": f"Beneficiary country matches loading port ({beneficiary_country}). Likely export LC.",
            "confidence": confidence,
        }

    if issuing_country and applicant_country and issuing_country == applicant_country and not pol_country:
        return {
            "lc_type": LCType.IMPORT.value,
            "reason": (
                f"Issuing bank and applicant share the same country ({applicant_country}) with no clear "
                "loading port information."
            ),
            "confidence": 0.55,
        }

    if issuing_country and beneficiary_country and issuing_country == beneficiary_country and not pod_country:
        return {
            "lc_type": LCType.EXPORT.value,
            "reason": (
                f"Issuing/advising bank and beneficiary share the same country ({beneficiary_country}) with no clear "
                "discharge port information."
            ),
            "confidence": 0.55,
        }

    return {
        "lc_type": LCType.UNKNOWN.value,
        "reason": "Insufficient or conflicting country/port details to determine LC type.",
        "confidence": 0.0,
    }


def _extract_party_country(party: Any) -> Optional[str]:
    if not party:
        return None
    if isinstance(party, dict):
        direct_candidate = (
            party.get("country")
            or party.get("country_name")
            or party.get("countryCode")
            or party.get("nation")
        )
        if direct_candidate:
            normalized = _normalize_country(direct_candidate)
            if normalized:
                return normalized
        address = party.get("address") or {}
        if isinstance(address, dict):
            for key in ("country", "country_name", "countryCode", "nation"):
                if address.get(key):
                    normalized = _normalize_country(address.get(key))
                    if normalized:
                        return normalized
            if address.get("full"):
                normalized = _normalize_country(address["full"])
                if normalized:
                    return normalized
        if party.get("value"):
            normalized = _normalize_country(party.get("value"))
            if normalized:
                return normalized
        if party.get("description"):
            return _normalize_country(party.get("description"))
    elif isinstance(party, str):
        return _normalize_country(party)
    return None


def _extract_port_country(shipment: Dict[str, Any], port_key: str) -> Optional[str]:
    port_value = shipment.get(port_key)
    if not port_value:
        return None
    if isinstance(port_value, dict):
        for key in ("country", "country_name", "countryCode"):
            if port_value.get(key):
                normalized = _normalize_country(port_value.get(key))
                if normalized:
                    return normalized
        if port_value.get("name"):
            return _normalize_country(port_value.get("name"))
    return _normalize_country(port_value)


def _normalize_country(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, dict):
        # Attempt to pull nested country values
        for nested_key in ("country", "country_name", "countryCode", "value", "name"):
            if value.get(nested_key):
                normalized = _normalize_country(value[nested_key])
                if normalized:
                    return normalized
        return None
    text = str(value).strip()
    if not text:
        return None

    lower = text.casefold()
    # Split on comma or dash to catch "City, Country"
    for separator in (",", "|"):
        if separator in lower:
            lower = lower.split(separator)[-1].strip()
    # Remove descriptive terms
    lower = re.sub(r"\b(port|any|city|state|province|of|the)\b", "", lower, flags=re.IGNORECASE).strip()
    lower = re.sub(r"\s+", " ", lower)
    normalized = COUNTRY_SYNONYMS.get(lower, lower)
    if not normalized:
        return None
    return normalized

