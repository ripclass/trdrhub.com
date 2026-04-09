from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.core.lc_types import LCType, LCTypeGuess
from app.services.lc_type_detector import detect_lc_family

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
    request_context: Optional[Dict[str, Any]] = None,
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
    request_hints = request_context or {}

    family_signal = detect_lc_family(lc_context)
    lc_family = family_signal.get("family", "unknown")
    request_user_type = str(
        request_hints.get("user_type") or request_hints.get("userType") or ""
    ).strip().lower()
    request_workflow = str(
        request_hints.get("workflow_type") or request_hints.get("workflowType") or ""
    ).strip().lower()
    company_country = _normalize_country(
        request_hints.get("company_country") or request_hints.get("companyCountry")
    )
    lane_export = request_user_type == "exporter" or request_workflow.startswith("export")
    lane_import = request_user_type == "importer" or request_workflow.startswith("import")

    ports_context = lc_context.get("ports") or {}
    lc_format = (lc_context.get("format") or "").lower()
    loading_hint = ports_context.get("loading") or ports_context.get("port_of_loading")
    discharge_hint = ports_context.get("discharge") or ports_context.get("port_of_discharge")
    if lc_format == "iso20022" and not shipment_context and (loading_hint or discharge_hint):
        # ISO LCs already normalize ports/doc parties, so reuse them as shipment hints.
        shipment_context = {
            "port_of_loading": loading_hint,
            "port_of_discharge": discharge_hint,
        }

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

    pol_country = (
        _normalize_country(shipment_context.get("port_of_loading_country"))
        or _normalize_country(shipment_context.get("port_of_loading_country_name"))
        or _normalize_country(shipment_context.get("port_of_loading_country_code"))
        or _normalize_country(lc_context.get("port_of_loading_country"))
        or _normalize_country(lc_context.get("port_of_loading_country_name"))
        or _normalize_country(lc_context.get("port_of_loading_country_code"))
        or _extract_port_country(shipment_context, "port_of_loading")
        or _extract_port_country(lc_context, "port_of_loading")
        or _normalize_country(ports_context.get("loading") or ports_context.get("port_of_loading"))
        or _extract_port_country(shipment_context, "port_of_shipment")
        or _extract_port_country(lc_context, "port_of_shipment")
    )
    pod_country = (
        _normalize_country(shipment_context.get("port_of_discharge_country"))
        or _normalize_country(shipment_context.get("port_of_discharge_country_name"))
        or _normalize_country(shipment_context.get("port_of_discharge_country_code"))
        or _normalize_country(lc_context.get("port_of_discharge_country"))
        or _normalize_country(lc_context.get("port_of_discharge_country_name"))
        or _normalize_country(lc_context.get("port_of_discharge_country_code"))
        or _extract_port_country(shipment_context, "port_of_discharge")
        or _extract_port_country(lc_context, "port_of_discharge")
        or _normalize_country(ports_context.get("discharge") or ports_context.get("port_of_discharge"))
        or _extract_port_country(shipment_context, "port_of_destination")
        or _extract_port_country(lc_context, "port_of_destination")
    )
    has_loading_country_signal = any(
        (
            shipment_context.get("port_of_loading_country"),
            shipment_context.get("port_of_loading_country_name"),
            shipment_context.get("port_of_loading_country_code"),
            lc_context.get("port_of_loading_country"),
            lc_context.get("port_of_loading_country_name"),
            lc_context.get("port_of_loading_country_code"),
        )
    ) or any(
        _has_explicit_port_country_signal(candidate)
        for candidate in (
            shipment_context.get("port_of_loading"),
            lc_context.get("port_of_loading"),
            ports_context.get("loading"),
            ports_context.get("port_of_loading"),
            shipment_context.get("port_of_shipment"),
        )
    )
    has_discharge_country_signal = any(
        (
            shipment_context.get("port_of_discharge_country"),
            shipment_context.get("port_of_discharge_country_name"),
            shipment_context.get("port_of_discharge_country_code"),
            lc_context.get("port_of_discharge_country"),
            lc_context.get("port_of_discharge_country_name"),
            lc_context.get("port_of_discharge_country_code"),
        )
    ) or any(
        _has_explicit_port_country_signal(candidate)
        for candidate in (
            shipment_context.get("port_of_discharge"),
            lc_context.get("port_of_discharge"),
            ports_context.get("discharge"),
            ports_context.get("port_of_discharge"),
            shipment_context.get("port_of_destination"),
        )
    )

    def _guess(
        lc_type_value: str,
        reason_text: str,
        confidence_value: float,
        *,
        confidence_mode: str = "scored",
        detection_basis: str = "rule_based",
    ) -> LCTypeGuess:
        source = "auto-detected" if lc_family == "unknown" else f"auto-detected:{lc_family}"
        payload: LCTypeGuess = {
            "lc_type": lc_type_value,
            "reason": reason_text,
            "confidence": confidence_value,
            "source": source,
        }
        payload["family"] = lc_family
        payload["family_confidence"] = family_signal.get("confidence", 0.0)
        payload["family_evidence"] = family_signal.get("evidence", [])
        payload["confidence_mode"] = confidence_mode
        payload["detection_basis"] = detection_basis
        return payload

    def _lane_only_confidence(
        *,
        aligned_party_country: str | None,
        other_party_country: str | None,
    ) -> float:
        confidence = 0.5
        if lc_family != "unknown":
            confidence += 0.04
        if aligned_party_country and pol_country and aligned_party_country == pol_country:
            confidence += 0.05
        if other_party_country and pod_country and other_party_country == pod_country:
            confidence += 0.05
        elif pod_country:
            confidence += 0.03
        if issuing_country and aligned_party_country and issuing_country == aligned_party_country:
            confidence += 0.03
        return min(confidence, 0.67)

    flow_export = (
        applicant_country
        and beneficiary_country
        and pol_country
        and pod_country
        and applicant_country != beneficiary_country
        and beneficiary_country == pol_country
        and applicant_country == pod_country
    )

    if flow_export:
        return _guess(
            LCType.EXPORT.value,
            (
                f"Goods load in {pol_country} where the beneficiary resides and discharge in {pod_country} "
                f"where the applicant resides. Shipment flow confirms export LC."
            ),
            0.95,
        )

    flow_import = (
        applicant_country
        and beneficiary_country
        and pol_country
        and pod_country
        and applicant_country != beneficiary_country
        and applicant_country == pol_country
        and beneficiary_country == pod_country
    )

    if flow_import:
        return _guess(
            LCType.IMPORT.value,
            (
                f"Goods load in {pol_country} where the applicant resides and discharge in {pod_country} "
                f"where the beneficiary resides. Shipment flow confirms import LC."
            ),
            0.95,
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
        return _guess(
            LCType.IMPORT.value,
            (
                f"Applicant, issuing bank, and discharge port all in {applicant_country}; "
                f"beneficiary in {beneficiary_country}. Typical import LC."
            ),
            0.95,
        )

    strong_export = (
        beneficiary_country
        and issuing_country
        and pol_country
        and beneficiary_country == issuing_country == pol_country
        and applicant_country
        and applicant_country != beneficiary_country
    )

    if strong_export:
        return _guess(
            LCType.EXPORT.value,
            (
                f"Beneficiary, issuing bank, and loading port all in {beneficiary_country}; "
                f"applicant in {applicant_country}. Typical export LC."
            ),
            0.95,
        )

    weak_import = applicant_country and pod_country and applicant_country == pod_country
    weak_export = beneficiary_country and pol_country and beneficiary_country == pol_country

    # If both weak signals point to different countries, treat as unknown
    if weak_import and weak_export and applicant_country and beneficiary_country and applicant_country != beneficiary_country:
        if pol_country and pod_country:
            if beneficiary_country == pol_country and applicant_country == pod_country:
                return {
                    "lc_type": LCType.EXPORT.value,
                    "reason": (
                        f"Goods load in {pol_country} where beneficiary resides and discharge in {pod_country} "
                        f"where applicant resides. Flow indicates an export LC."
                    ),
                    "confidence": 0.75,
                }
            if applicant_country == pol_country and beneficiary_country == pod_country:
                return {
                    "lc_type": LCType.IMPORT.value,
                    "reason": (
                        f"Goods load in {pol_country} where applicant resides and discharge in {pod_country} "
                        f"where beneficiary resides. Flow indicates an import LC."
                    ),
                    "confidence": 0.75,
                }
        return _guess(
            LCType.UNKNOWN.value,
            (
                "Conflicting port heuristics: applicant/discharge suggest import while "
                "beneficiary/loading suggest export."
            ),
            0.1,
        )

    if weak_import:
        confidence = 0.65 if issuing_country == applicant_country else 0.6
        return _guess(
            LCType.IMPORT.value,
            f"Applicant country matches discharge port ({applicant_country}). Likely import LC.",
            confidence,
        )

    if weak_export:
        confidence = 0.65 if issuing_country == beneficiary_country else 0.6
        return _guess(
            LCType.EXPORT.value,
            f"Beneficiary country matches loading port ({beneficiary_country}). Likely export LC.",
            confidence,
        )

    if issuing_country and applicant_country and issuing_country == applicant_country and not pol_country:
        return _guess(
            LCType.IMPORT.value,
            (
                f"Issuing bank and applicant share the same country ({applicant_country}) with no clear "
                "loading port information."
            ),
            0.55,
        )

    if issuing_country and beneficiary_country and issuing_country == beneficiary_country and not pod_country:
        return _guess(
            LCType.EXPORT.value,
            (
                f"Issuing/advising bank and beneficiary share the same country ({beneficiary_country}) with no clear "
                "discharge port information."
            ),
            0.55,
        )

    exporter_context_export = (
        lane_export
        and company_country
        and pol_country
        and company_country == pol_country
        and lc_context.get("beneficiary")
        and (not applicant_country or applicant_country != company_country)
    )
    if exporter_context_export:
        confidence = 0.72 if pod_country else 0.62
        return _guess(
            LCType.EXPORT.value,
            (
                f"Exporter workflow context aligns with shipment flow: company country {company_country} "
                f"matches the loading port {pol_country} and the LC names a beneficiary."
            ),
            confidence,
        )

    importer_context_import = (
        lane_import
        and company_country
        and pod_country
        and company_country == pod_country
        and lc_context.get("applicant")
        and (not beneficiary_country or beneficiary_country != company_country)
    )
    if importer_context_import:
        confidence = 0.72 if pol_country else 0.62
        return _guess(
            LCType.IMPORT.value,
            (
                f"Importer workflow context aligns with shipment flow: company country {company_country} "
                f"matches the discharge port {pod_country} and the LC names an applicant."
            ),
            confidence,
        )

    lane_only_export = (
        lane_export
        and not company_country
        and lc_context.get("beneficiary")
        and lc_context.get("applicant")
        and has_loading_country_signal
        and has_discharge_country_signal
        and pol_country
        and pod_country
        and pol_country != pod_country
    )
    if lane_only_export:
        return _guess(
            LCType.EXPORT.value,
            (
                "Exporter workflow selected and the LC includes beneficiary/applicant parties with a distinct "
                "loading-to-discharge shipment flow. Treating this as an export LC unless stronger contrary "
                "evidence appears."
            ),
            _lane_only_confidence(
                aligned_party_country=beneficiary_country,
                other_party_country=applicant_country,
            ),
            confidence_mode="estimated",
            detection_basis="lane_only_context",
        )

    lane_only_import = (
        lane_import
        and not company_country
        and lc_context.get("beneficiary")
        and lc_context.get("applicant")
        and has_loading_country_signal
        and has_discharge_country_signal
        and pol_country
        and pod_country
        and pol_country != pod_country
    )
    if lane_only_import:
        return _guess(
            LCType.IMPORT.value,
            (
                "Importer workflow selected and the LC includes applicant/beneficiary parties with a distinct "
                "loading-to-discharge shipment flow. Treating this as an import LC unless stronger contrary "
                "evidence appears."
            ),
            _lane_only_confidence(
                aligned_party_country=applicant_country,
                other_party_country=beneficiary_country,
            ),
            confidence_mode="estimated",
            detection_basis="lane_only_context",
        )

    if lc_family == "iso":
        return _guess(
            LCType.UNKNOWN.value,
            "ISO 20022 / MX documentary-credit structure detected, but country/port flow data is insufficient to classify import vs export.",
            0.25,
        )

    if lc_family == "mt":
        return _guess(
            LCType.UNKNOWN.value,
            "SWIFT MT documentary-credit structure detected, but country/port flow data is insufficient to classify import vs export.",
            0.2,
        )

    return _guess(
        LCType.UNKNOWN.value,
        "Insufficient or conflicting country/port details to determine LC type.",
        0.0,
    )


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


def _has_explicit_port_country_signal(value: Any) -> bool:
    if not value:
        return False
    if isinstance(value, dict):
        if any(value.get(key) for key in ("country", "country_name", "countryCode")):
            return True
        nested = value.get("name") or value.get("port") or value.get("value")
        return _has_explicit_port_country_signal(nested)

    text = str(value).strip()
    if not text:
        return False
    if "," not in text and "|" not in text:
        return False
    return _normalize_country(text) is not None


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


# ---------------------------------------------------------------------------
# LC subtype classification (Sight / Usance / Transferable / Standby / etc.)
#
# detect_lc_type() above decides import vs export.  This helper runs a
# second-level classifier on the MT700 fields to emit more specific labels
# the UI can render as chips:
#
#     "Sight Export LC"
#     "30 Day Usance Import LC"
#     "Transferable Sight LC"
#     "Irrevocable Confirmed Export LC"
#     "Standby LC (ISP98)"
#
# This is deterministic — no LLM calls — based on :40A: / :42C: / :49: /
# :40E: fields that are already on lc_context after extraction.
# ---------------------------------------------------------------------------

_USANCE_DAYS_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:DAYS?|D)\b",
    re.IGNORECASE,
)


def _has_text(value: Any, *needles: str) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        hay = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        hay = " ".join(str(v) for v in value.values())
    else:
        hay = str(value)
    hay = hay.upper()
    return any(needle.upper() in hay for needle in needles)


def _extract_usance_days(drafts_at: Any) -> Optional[int]:
    if drafts_at is None:
        return None
    text = str(drafts_at).upper()
    match = _USANCE_DAYS_PATTERN.search(text)
    if not match:
        return None
    try:
        days = int(match.group(1))
    except ValueError:
        return None
    if 1 <= days <= 360:
        return days
    return None


def detect_lc_subtypes(
    lc_context: Optional[Dict[str, Any]],
    *,
    base_lc_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit a set of secondary labels describing the LC's specific character.

    Returns a dict like::

        {
            "primary_label": "Sight Export LC",
            "labels": ["Sight", "Irrevocable", "Export"],
            "payment_mode": "sight",          # sight | usance | deferred | mixed | unknown
            "usance_days": None,              # int when usance, else None
            "form": "irrevocable",            # irrevocable | transferable | revolving | standby | unknown
            "confirmed": False,               # True when :49: says CONFIRM
            "rule_set": "UCP600",             # UCP600 | ISP98 | URDG758 | EUCP | URC522 | unknown
            "standby": False,
            "transferable": False,
            "revolving": False,
        }

    Every field has a safe default so callers can use it without None checks.
    """
    ctx = lc_context or {}

    form_raw = ctx.get("form_of_documentary_credit") or ctx.get("form_of_doc_credit") or ""
    drafts_at = ctx.get("drafts_at") or (ctx.get("shipment") or {}).get("drafts_at")
    mixed_payment = ctx.get("mixed_payment_details") or ctx.get("mixed_payment")
    deferred_payment = ctx.get("deferred_payment_details") or ctx.get("deferred_payment")
    confirmation = ctx.get("confirmation_instructions") or ""
    applicable_rules = ctx.get("applicable_rules") or ctx.get("ucp_reference") or ""
    additional_conditions = ctx.get("additional_conditions") or []

    # ---- Form (40A) ----
    transferable = _has_text(form_raw, "TRANSFERABLE") or _has_text(additional_conditions, "TRANSFERABLE")
    revolving = _has_text(form_raw, "REVOLVING", "REVOLV") or _has_text(additional_conditions, "REVOLVING")
    standby = (
        _has_text(form_raw, "STANDBY")
        or _has_text(applicable_rules, "ISP98")
        or _has_text(additional_conditions, "STANDBY")
    )
    irrevocable = _has_text(form_raw, "IRREVOCABLE") or not _has_text(form_raw, "REVOCABLE") and bool(form_raw)

    if standby:
        form = "standby"
    elif transferable:
        form = "transferable"
    elif revolving:
        form = "revolving"
    elif irrevocable:
        form = "irrevocable"
    else:
        form = "unknown"

    # ---- Payment mode (42C / 42M / 42P) ----
    drafts_text = str(drafts_at or "").upper()
    mixed_text = str(mixed_payment or "").upper()
    deferred_text = str(deferred_payment or "").upper()

    usance_days = _extract_usance_days(drafts_at) or _extract_usance_days(mixed_payment)
    is_sight = "SIGHT" in drafts_text or "AT SIGHT" in mixed_text or "AT SIGHT" in drafts_text
    is_deferred = bool(deferred_text) or "DEFERRED" in drafts_text
    is_mixed = bool(mixed_text) and not is_sight

    if is_sight and not usance_days:
        payment_mode = "sight"
    elif usance_days is not None:
        payment_mode = "usance"
    elif is_deferred:
        payment_mode = "deferred"
    elif is_mixed:
        payment_mode = "mixed"
    else:
        payment_mode = "unknown"

    # ---- Confirmation (49) ----
    confirmed = _has_text(confirmation, "CONFIRM") and not _has_text(confirmation, "WITHOUT")

    # ---- Applicable rules (40E) ----
    rules_up = str(applicable_rules or "").upper()
    if "ISP98" in rules_up or "ISP 98" in rules_up:
        rule_set = "ISP98"
    elif "URDG758" in rules_up or "URDG 758" in rules_up:
        rule_set = "URDG758"
    elif "EUCP" in rules_up:
        rule_set = "eUCP"
    elif "URC522" in rules_up or "URC 522" in rules_up:
        rule_set = "URC522"
    elif "UCP" in rules_up:
        rule_set = "UCP600"
    else:
        rule_set = "unknown"

    # ---- Assemble labels ----
    labels: list = []

    # Payment mode label
    if payment_mode == "sight":
        labels.append("Sight")
    elif payment_mode == "usance":
        labels.append(f"{usance_days} Day Usance" if usance_days else "Usance")
    elif payment_mode == "deferred":
        labels.append("Deferred Payment")
    elif payment_mode == "mixed":
        labels.append("Mixed Payment")

    # Form label (append AFTER payment mode so "Sight Transferable" reads naturally)
    if form == "transferable":
        labels.append("Transferable")
    elif form == "revolving":
        labels.append("Revolving")
    elif form == "standby":
        labels.append("Standby")
    elif form == "irrevocable" and not standby and not transferable and not revolving:
        labels.append("Irrevocable")

    if confirmed:
        labels.append("Confirmed")

    # Direction label comes last
    direction_label = None
    if base_lc_type == LCType.EXPORT.value:
        direction_label = "Export"
    elif base_lc_type == LCType.IMPORT.value:
        direction_label = "Import"
    if direction_label:
        labels.append(direction_label)

    # Primary chip text — a single short string for the UI to render
    if standby:
        primary_label = f"Standby LC ({rule_set})" if rule_set != "unknown" else "Standby LC"
    elif labels:
        primary_label = " ".join(labels) + " LC"
    else:
        primary_label = "LC"

    return {
        "primary_label": primary_label,
        "labels": labels,
        "payment_mode": payment_mode,
        "usance_days": usance_days,
        "form": form,
        "confirmed": confirmed,
        "rule_set": rule_set,
        "standby": standby,
        "transferable": transferable,
        "revolving": revolving,
    }

