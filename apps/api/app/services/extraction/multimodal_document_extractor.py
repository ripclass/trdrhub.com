from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image

from app.services.extraction.ai_first_extractor import (
    _build_default_field_details_from_wrapped_result,
    _derive_overall_status_from_field_details,
    _flatten_structural_field_values_in_place,
    _parse_llm_json_with_repair,
    _summarize_field_detail_statuses,
    _unwrap_confidence_scalars_in_place,
    _wrap_ai_result_with_default_confidence,
)
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


# Per-request diagnostic channel for vision tier attempts.  Populated by
# extract_document_multimodal_first on every call — including when all tiers
# fail and the function returns None.  Callers that need to surface "which
# tier ran and why did it fail" to the user can read this after the call
# even when multimodal produced nothing.
_last_tier_attempts: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "_last_tier_attempts", default=None
)


def get_last_tier_attempts() -> List[Dict[str, Any]]:
    """Return the list of tier attempts from the most recent call to
    ``extract_document_multimodal_first`` in the current async context.
    Returns an empty list if no call has been made yet.
    """
    value = _last_tier_attempts.get()
    return list(value or [])


@dataclass
class MultimodalExtractionResult:
    success: bool
    fields: Dict[str, Any]
    provider: str
    model: str
    pages_used: int
    source_mode: str
    error: Optional[str] = None


TRANSPORT_TYPES = {
    "bill_of_lading",
    "air_waybill",
    "sea_waybill",
    "ocean_bill_of_lading",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "multimodal_transport_document",
    "railway_consignment_note",
    "road_transport_document",
    "forwarder_certificate_of_receipt",
    "forwarders_certificate_of_receipt",
    "shipping_company_certificate",
    "delivery_order",
    "mates_receipt",
}
REGULATORY_TYPES = {
    "certificate_of_origin",
    "gsp_form_a",
    "eur1_movement_certificate",
    "customs_declaration",
    "export_license",
    "import_license",
    "phytosanitary_certificate",
    "fumigation_certificate",
    "health_certificate",
    "veterinary_certificate",
    "sanitary_certificate",
    "cites_permit",
    "radiation_certificate",
}
INSURANCE_TYPES = {
    "insurance_certificate",
    "insurance_policy",
    "marine_insurance_policy",
    "marine_insurance_certificate",
}
# Compliance attestation / beneficiary-statement family. These are NOT
# insurance policies — they're free-text attestations the exporter signs
# (goods are brand new, goods meet safety standards, etc.). They use the
# attestation_document schema instead.
ATTESTATION_TYPES = {
    "beneficiary_certificate",
    "beneficiary_statement",
    "beneficiarys_certificate",
    "manufacturer_certificate",
    "manufacturers_certificate",
    "conformity_certificate",
    "certificate_of_conformity",
    "non_manipulation_certificate",
    "halal_certificate",
    "kosher_certificate",
    "organic_certificate",
    "compliance_certificate",
}
INSPECTION_TYPES = {
    "inspection_certificate",
    "pre_shipment_inspection",
    "quality_certificate",
    "weight_certificate",
    "weight_list",
    "measurement_certificate",
    "analysis_certificate",
    "lab_test_report",
    "sgs_certificate",
    "bureau_veritas_certificate",
    "intertek_certificate",
}


DOC_TYPE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "letter_of_credit": {
        "family": "lc",
        "title": "Letter of Credit / SWIFT documentary credit (MT700)",
        # Field list aligned with the MT700 mandatory + important-optional spec.
        # Anything tagged "MT700 Field <NN>" in the comments is the SWIFT field
        # the vision LLM should be looking for on the LC pages.
        "fields": [
            # MT700 mandatory fields
            "sequence_of_total",        # Field 27 — e.g. "1/1"; tells us if MT701 continuations exist
            "form_of_documentary_credit",  # Field 40A — Irrevocable / Irrevocable Transferable / etc.
            "lc_number",                # Field 20 — unique LC reference
            "issue_date",               # Field 31C — date of issue
            "expiry_date",              # Field 31D — hard deadline
            "expiry_place",             # Field 31D place
            "applicable_rules",         # Field 40E — UCP LATEST VERSION / EUCP LATEST VERSION
            "applicant",                # Field 50 — buyer / importer
            "beneficiary",              # Field 59 — seller / exporter
            "amount",                   # Field 32B — credit amount
            "currency",                 # Field 32B — currency code
            "available_with",           # Field 41a — bank credit is available with
            "available_by",             # Field 41a — payment / acceptance / negotiation / deferred
            "port_of_loading",          # Field 44E — must match B/L
            "port_of_discharge",        # Field 44F — must match B/L
            "latest_shipment_date",     # Field 44C — B/L on-board date must not exceed
            "goods_description",        # Field 45A — invoice goods must "correspond"
            "documents_required",       # Field 46A — list of required docs (parser drives validation)
            "additional_conditions",    # Field 47A — supplemental rules
            "period_for_presentation",  # Field 48 — overrides 21-day default

            # MT700 important-optional fields
            "amount_tolerance",         # Field 39A — "ABOUT" / ±10%
            "partial_shipments",        # Field 43P — ALLOWED / NOT ALLOWED / CONDITIONAL
            "transshipment",            # Field 43T — ALLOWED / NOT ALLOWED / CONDITIONAL
            "drafts_at",                # Field 42C — tenor (sight / 30 days / etc.)
            "drawee",                   # Field 42a — who the draft is drawn on
            "confirmation_instructions",# Field 49 — CONFIRM / MAY ADD / WITHOUT
            "instructions_to_paying_bank", # Field 78 — bank-to-bank instructions
            "charges",                  # Field 71D — who pays the bank charges

            # Existing fields kept for backwards compat with structured_lc_builder etc.
            "lc_type",
            "issuing_bank",             # extracted from Field 52a (issuer of LC)
            "advising_bank",            # extracted from Field 57a
            "confirming_bank",          # may be inferred from Field 49 or banks list
            "incoterm",
            "ucp_reference",            # alias for applicable_rules (kept for compat)
            "payment_terms",            # synthesized from 41a/42C/42a if structured fields not available
        ],
        "notes": [
            "Treat the actual document pages as primary evidence — never invent SWIFT fields.",
            "documents_required (Field 46A) and additional_conditions (Field 47A) MUST be arrays when present.",
            "If you can read field 32B, ALWAYS split it into `amount` (number) and `currency` (3-letter code).",
            "If field 31D shows '261015USA' style format, parse `expiry_date` as ISO (2026-10-15) and put 'USA' in `expiry_place`.",
            "If field 27 is missing or shows anything other than '1/1', flag it — there may be MT701 continuation messages.",
            "If field 40E says 'UCP LATEST VERSION', set applicable_rules to 'UCP600'. Same for EUCP / ISP / URDG variants.",
        ],
    },
    "commercial_invoice": {
        "family": "invoice",
        "title": "Commercial / Proforma Invoice",
        # Schema lists ONLY fields intrinsic to a commercial invoice —
        # i.e., what defines an invoice regardless of any specific trade
        # context.  Cross-transaction artifacts (LC number, buyer PO,
        # exporter tax IDs) are NOT in this list.  If they happen to be
        # printed on the doc, the "transcribe any other printed field"
        # instruction in the prompt captures them under whatever key the
        # LLM picks.  Validation decides whether they "should" be there.
        "fields": [
            "invoice_number", "invoice_date", "amount", "currency",
            "seller", "buyer", "applicant", "beneficiary",
            "consignee", "notify_party",
            "goods_description", "hs_code", "quantity", "unit_price",
            "incoterm", "country_of_origin",
            "port_of_loading", "port_of_discharge",
            "gross_weight", "net_weight", "total_packages",
            "payment_terms",
        ],
        "notes": [
            "Return EXACTLY these key names. `seller` NOT `seller_name`, `buyer` NOT `buyer_name`.",
            "Extract the invoice party names exactly as written.",
            "Do not guess HS codes or Incoterms.",
            "quantity / unit_price / amount should be numbers when possible (multi-line-item invoices may return comma-separated strings).",
        ],
    },
    "packing_list": {
        "family": "packing",
        "title": "Packing List",
        "fields": [
            "packing_list_number", "packing_list_date",
            "seller", "buyer", "shipper", "consignee",
            "goods_description", "marks_and_numbers",
            "total_packages", "package_type", "size_breakdown",
            "gross_weight", "net_weight", "measurement_value",
            "port_of_loading", "port_of_discharge",
        ],
        "notes": [
            "Return EXACTLY these key names. `size_breakdown` NOT `packing_size_breakdown`, `total_packages` NOT `number_of_packages`.",
            "Prioritize package counts, weights, dimensions, and marks/numbers.",
            "size_breakdown should be a structured object when possible — e.g. {\"S\": 100, \"M\": 200, \"L\": 300}.",
        ],
    },
    "transport_document": {
        "family": "transport",
        "title": "Transport document (B/L, AWB, waybill, multimodal, rail, road, forwarder receipt)",
        "fields": [
            "bl_number", "transport_reference_number", "airway_bill_number", "consignment_reference",
            "shipper", "consignee", "notify_party", "applicant",
            "port_of_loading", "port_of_discharge",
            "airport_of_departure", "airport_of_destination",
            "vessel_name", "voyage_number",
            "carriage_vessel_name", "carriage_voyage_number",
            "shipped_on_board_date", "issue_date",
            "goods_description", "gross_weight", "net_weight",
            "container_number", "seal_number",
            "marks_and_numbers", "transport_mode_chain",
            "freight_terms",
        ],
        "notes": [
            "Return EXACTLY these key names. `bl_number` NOT `bill_of_lading_number`.",
            "Use the correct field family for the visible transport mode.",
            "If it is AWB, prefer airway_bill_number / airport fields.",
            "`applicant` — include ONLY if the document itself has a field labeled Applicant / Buyer / Importer with a value. Do NOT copy the notify party into applicant. Do NOT invent this field from other information.",
        ],
    },
    "regulatory_document": {
        "family": "regulatory",
        "title": "Origin / customs / regulatory / sanitary certificate document",
        "fields": [
            "certificate_number", "license_number", "declaration_reference", "permit_number",
            "country_of_origin", "issuing_authority",
            "issue_date", "expiry_date",
            "goods_description", "hs_code",
            "exporter", "importer",
        ],
        "notes": [
            "Return EXACTLY these key names. `exporter` NOT `exporter_name`, `importer` NOT `importer_name`, `issuing_authority` NOT `certifying_authority`.",
            "Use certificate_number for most certificates, license_number for licenses, declaration_reference for customs declarations.",
            "issuing_authority — for Bangladesh COOs this is usually 'EPB' / 'Export Promotion Bureau' or 'Chamber of Commerce'.",
        ],
    },
    "insurance_document": {
        "family": "insurance",
        "title": "Insurance policy or certificate",
        "fields": [
            "policy_number", "certificate_number",
            "insured_amount", "coverage_amount", "currency",
            "issuer", "insurer",
            "issue_date", "expiry_date",
            "goods_description", "risks_covered",
            "beneficiary", "applicant", "insured_party",
            "vessel_name", "voyage_details",
            "claims_payable_at", "survey_agent",
        ],
        "notes": [
            "Use policy_number for marine insurance policies, certificate_number for insurance certificates.",
            "`issuer` is the underwriter / insurance company name.",
            "insured_amount should be the full coverage value — typically 110% of the invoice value per UCP600 Art 28.",
            "This schema is ONLY for real insurance documents. Beneficiary certificates, compliance attestations, manufacturer certs go through the attestation_document schema.",
        ],
    },
    "attestation_document": {
        "family": "attestation",
        "title": "Beneficiary certificate, manufacturer certificate, or compliance attestation",
        "fields": [
            "certificate_number", "issuer", "issue_date",
            "goods_description", "attestation_text",
            "manufacture_year", "brand_new",
        ],
        "notes": [
            "This is NOT an insurance policy. Beneficiary certificates are compliance attestations where the exporter certifies something about the goods (e.g., 'goods are brand new and manufactured in 2026').",
            "`issuer` is the exporter / beneficiary — the party signing the certificate.",
            "`attestation_text` is the main statement the certificate is making (verbatim or a concise paraphrase).",
            "Return EXACTLY these key names.",
        ],
    },
    "inspection_document": {
        "family": "inspection",
        "title": "Inspection / testing / quality / weight / measurement document",
        "fields": [
            "certificate_number", "inspection_agency",
            "inspection_date", "issue_date",
            "inspection_result", "quality_finding", "analysis_result",
            "quantity", "gross_weight", "net_weight", "measurement_value",
            "goods_description", "issuer",
        ],
        "notes": [
            "Return EXACTLY these key names. `certificate_number` NOT `inspection_number`, `inspection_agency` NOT `inspector`.",
            "`inspection_agency` is SGS / Intertek / Bureau Veritas / etc.",
            "`inspection_date` is when the inspection happened; `issue_date` is when the cert was issued.",
            "Use inspection_result / quality_finding / analysis_result based on the visible document type.",
        ],
    },
    "supporting_document": {
        "family": "supporting",
        "title": "Supporting trade document",
        "fields": [
            "document_title", "document_reference", "issuing_authority", "issue_date",
            "expiry_date", "goods_description", "shipper", "consignee", "country_of_origin",
            "summary",
        ],
        "notes": [
            "If the subtype is unclear, extract a safe reference + summary and leave uncertain fields null.",
        ],
    },
}


def _resolve_schema_key(document_type: str) -> str:
    doc_type = str(document_type or "").strip().lower()
    if doc_type in {"letter_of_credit", "swift_message", "lc_application", "standby_letter_of_credit", "bank_guarantee"}:
        return "letter_of_credit"
    if doc_type in {"commercial_invoice", "proforma_invoice"}:
        return "commercial_invoice"
    if doc_type in TRANSPORT_TYPES:
        return "transport_document"
    if doc_type == "packing_list":
        return "packing_list"
    if doc_type in REGULATORY_TYPES:
        return "regulatory_document"
    if doc_type in INSURANCE_TYPES:
        return "insurance_document"
    if doc_type in ATTESTATION_TYPES:
        return "attestation_document"
    if doc_type in INSPECTION_TYPES:
        return "inspection_document"
    return "supporting_document"


def _resolve_multimodal_config() -> Tuple[str, str, int]:
    """Legacy single-provider config — kept for backwards compat. The tiered
    resolver below (`_resolve_vision_tier_config`) is the preferred path.
    """
    provider = (
        os.getenv("EXTRACTION_MULTIMODAL_PROVIDER")
        or os.getenv("EXTRACTION_PRIMARY_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or LLMProvider.OPENROUTER.value
    )
    model = (
        os.getenv("EXTRACTION_MULTIMODAL_MODEL")
        or os.getenv("EXTRACTION_PRIMARY_MODEL")
        or os.getenv("OPENROUTER_MODEL_VERSION")
        or os.getenv("LLM_PRIMARY_MODEL")
        or os.getenv("LLM_MODEL_VERSION")
        or "openai/gpt-4o-mini"
    )
    max_pages = int(os.getenv("EXTRACTION_MULTIMODAL_MAX_PAGES") or "4")
    return provider, model, max(1, max_pages)


# Vision-tier escalation configuration. L1 is the cheap default, L2 is the
# mid-tier escalation when L1 returns nothing or misses critical fields, L3 is
# the top-tier model used only in extreme cases. Each tier has its own provider
# and model env vars; if a tier-specific env var is unset it falls back to the
# legacy EXTRACTION_MULTIMODAL_* vars (L1) or to a sensible default.
_VISION_TIER_DEFAULTS: Dict[str, Tuple[str, str]] = {
    "L1": (LLMProvider.OPENAI.value, "gpt-4.1"),
    "L2": (LLMProvider.ANTHROPIC.value, "claude-sonnet-4-6"),
    "L3": (LLMProvider.ANTHROPIC.value, "claude-opus-4-6"),
}


def _resolve_vision_tier_config(tier: str) -> Tuple[str, str]:
    """Return (provider, model) for a vision tier (L1/L2/L3).

    Resolution order for each tier:
    1. EXTRACTION_VISION_{tier}_PROVIDER + EXTRACTION_VISION_{tier}_MODEL
       (explicit vision-tier override — highest priority)
    2. AI_ROUTER_{tier}_PRIMARY_MODEL
       - If OPENROUTER_API_KEY is set: treat the whole slash-delimited
         value as an OpenRouter model slug (e.g. "anthropic/claude-sonnet-4.6"
         IS the OpenRouter model ID, not a provider/model split).  This is
         the common case for operators running on OpenRouter.
       - Otherwise: legacy behavior — split on "/" so "anthropic/claude-..."
         routes to the direct Anthropic SDK.
    3. Legacy EXTRACTION_MULTIMODAL_PROVIDER/MODEL and EXTRACTION_PRIMARY_PROVIDER/MODEL
       env vars.  Honored for L1/L2 so "set sonnet as the primary/fallback"
       via the text-extractor vars works for vision too.
    4. Hardcoded default in _VISION_TIER_DEFAULTS.
    """
    tier_upper = tier.upper()
    provider_env = os.getenv(f"EXTRACTION_VISION_{tier_upper}_PROVIDER")
    model_env = os.getenv(f"EXTRACTION_VISION_{tier_upper}_MODEL")
    if provider_env and model_env:
        return provider_env, model_env

    router_model = os.getenv(f"AI_ROUTER_{tier_upper}_PRIMARY_MODEL")
    if router_model and "/" in router_model:
        # OpenRouter gateway mode: slash-delimited slugs are OpenRouter
        # model IDs, NOT direct-provider overrides.  When the operator has
        # OPENROUTER_API_KEY set we pass the whole slug through.
        if os.getenv("OPENROUTER_API_KEY"):
            return LLMProvider.OPENROUTER.value, router_model
        # Legacy path: split on "/" for direct-SDK routing.  Kept for
        # operators who actually have ANTHROPIC_API_KEY / OPENAI_API_KEY
        # set and want the resolver to dispatch to the provider-specific
        # SDK instead of OpenRouter.
        provider_part, _, model_part = router_model.partition("/")
        return provider_part, model_part

    if tier_upper in ("L1", "L2"):
        legacy_provider = os.getenv("EXTRACTION_MULTIMODAL_PROVIDER") or os.getenv("EXTRACTION_PRIMARY_PROVIDER")
        legacy_model = os.getenv("EXTRACTION_MULTIMODAL_MODEL") or os.getenv("EXTRACTION_PRIMARY_MODEL")
        if legacy_provider and legacy_model:
            return legacy_provider, legacy_model

    return _VISION_TIER_DEFAULTS.get(tier_upper, _VISION_TIER_DEFAULTS["L1"])


# Critical fields that must be present for an extraction to be considered
# "strong enough" not to escalate. If the L1 result is missing all of these
# for a doc type, escalate to L2.
#
# For LC-family documents we use the MT700 "skeleton" — the 5 absolute
# minimums you cannot validate without: Field 20 (lc_number), Field 32B
# (amount + currency), Field 45A (goods_description), Field 46A
# (documents_required), Field 31D (expiry_date). If any of these are missing,
# downstream validation has nothing to anchor on and we MUST escalate.
_VISION_CRITICAL_FIELDS: Dict[str, Tuple[str, ...]] = {
    "letter_of_credit": (
        "lc_number",          # MT700 Field 20
        "amount",             # MT700 Field 32B
        "currency",           # MT700 Field 32B
        "goods_description",  # MT700 Field 45A
        "documents_required", # MT700 Field 46A
        "expiry_date",        # MT700 Field 31D
        "applicant",          # MT700 Field 50
        "beneficiary",        # MT700 Field 59
    ),
    "swift_message": (
        "lc_number", "amount", "currency", "applicant", "beneficiary",
        "documents_required", "expiry_date",
    ),
    "lc_application": (
        "lc_number", "amount", "currency", "applicant", "beneficiary",
    ),
    "commercial_invoice": ("invoice_number", "amount", "seller", "buyer"),
    "proforma_invoice": ("invoice_number", "amount", "seller", "buyer"),
    "bill_of_lading": ("bl_number", "shipper", "consignee"),
    "ocean_bill_of_lading": ("bl_number", "shipper", "consignee"),
    "air_waybill": ("awb_number", "shipper", "consignee"),
    "packing_list": ("packing_list_number", "shipper", "consignee"),
    "certificate_of_origin": ("certificate_number", "exporter", "country_of_origin"),
    "insurance_certificate": ("insurance_number", "insured_amount"),
    "inspection_certificate": ("inspection_number", "inspection_date"),
}


def _vision_result_is_strong(
    result: Optional[Dict[str, Any]],
    document_type: str,
) -> bool:
    """Check if a vision extraction result is strong enough to skip escalation.

    A result is strong when:
    - It is non-None
    - Its `_status` is not "failed" / "error"
    - At least HALF of the critical fields for this doc type are non-empty
    """
    if not isinstance(result, dict):
        return False
    if result.get("_status") in ("failed", "error"):
        return False

    critical = _VISION_CRITICAL_FIELDS.get(document_type)
    if not critical:
        # Unknown doc type — accept anything that returned without error
        return True

    present = 0
    for field_name in critical:
        value = result.get(field_name)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            continue
        present += 1

    return present >= max(1, len(critical) // 2)


def _is_supported_content_type(content_type: Optional[str], filename: Optional[str]) -> bool:
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or ctype == "application/pdf":
        return True
    lower_name = (filename or "").lower()
    return lower_name.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp"))


async def _attempt_vision_tier(
    *,
    tier: str,
    document_type: str,
    filename: str,
    image_parts: Sequence[Dict[str, str]],
    source_mode: str,
    subtype_hint: Optional[str],
    extracted_text: str,
    attempt_record: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Run a single vision extraction attempt at a given tier (L1/L2/L3).

    When ``attempt_record`` is provided, the function will populate it with
    ``error`` / ``error_type`` keys on failure so callers can surface the
    actual failure reason instead of a silent None.
    """
    provider, model = _resolve_vision_tier_config(tier)

    schema_key = _resolve_schema_key(document_type)
    schema = DOC_TYPE_SCHEMAS[schema_key]
    prompt = _build_multimodal_prompt(
        document_type=document_type,
        schema=schema,
        subtype_hint=subtype_hint,
        extracted_text=extracted_text,
    )
    system_prompt = (
        "You are a senior trade-finance document examiner extracting "
        "structured data from a Letter of Credit presentation. "
        "Read the attached page images carefully — you have both the rendered "
        "PDF pages AND the raw text content. Cross-check both. "
        "Return EVERY field you can see, in canonical JSON form. Don't be "
        "lazy — if a value is on the page anywhere, return it. "
        "Output ONLY a JSON object, no prose."
    )

    try:
        response_text, provider_used = await _generate_multimodal(
            provider=provider,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            image_parts=image_parts,
        )
    except Exception as exc:
        logger.warning(
            "Multimodal extraction call failed for %s via tier=%s %s/%s: %s",
            filename, tier, provider, model, exc,
        )
        if attempt_record is not None:
            attempt_record["error"] = str(exc)[:300]
            attempt_record["error_type"] = type(exc).__name__
        return None

    if not response_text:
        if attempt_record is not None:
            attempt_record["error"] = "empty_response"
            attempt_record["error_type"] = "EmptyResponse"
        return None

    try:
        from app.services.llm_provider import LLMProviderFactory
        repair_provider = LLMProviderFactory.create_provider(provider)
    except Exception:
        repair_provider = None

    parsed = await _parse_llm_json_with_repair(repair_provider, response_text)
    if not parsed:
        logger.warning("Multimodal extraction JSON parse failed for %s tier=%s", filename, tier)
        return None

    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    field_details = _build_default_field_details_from_wrapped_result(
        wrapped,
        source=f"multimodal:{source_mode}",
        raw_text=extracted_text,
    )
    # The sidecar field_details dict now carries confidence metadata.  Unwrap
    # the main payload so downstream shaping code (_shape_lc_financial_payload,
    # build_lc_intake_summary, the Extract & Review screen) sees scalar values
    # instead of {value, confidence} dicts leaking into the UI as jsonish strings.
    _unwrap_confidence_scalars_in_place(wrapped)
    # Collapse legitimately-multi-item structured values (list-of-dict line
    # items, dict-of-number breakdowns, list-of-scalar HS-code arrays) into
    # scalar + _breakdown sidecar.  The LLM returns these for real multi-SKU
    # invoices / multi-size packing lists; the review form expects scalars.
    _flatten_structural_field_values_in_place(wrapped)
    wrapped["_extraction_method"] = "multimodal_ai_first"
    wrapped["_source_mode"] = source_mode
    wrapped["_llm_provider"] = provider_used
    wrapped["_llm_model"] = model
    wrapped["_llm_tier"] = tier
    wrapped["_multimodal_pages_used"] = len(image_parts)
    wrapped["_field_details"] = field_details
    wrapped["_status_counts"] = _summarize_field_detail_statuses(field_details)
    wrapped["_status"] = _derive_overall_status_from_field_details(field_details)
    if subtype_hint:
        wrapped["_multimodal_subtype_hint"] = subtype_hint
    logger.info(
        "validate.extraction.multimodal file=%s doc_type=%s tier=%s provider=%s model=%s pages=%s source_mode=%s",
        filename,
        document_type,
        tier,
        provider_used,
        model,
        len(image_parts),
        source_mode,
    )
    return wrapped


_LC_DOCUMENT_TYPES = {
    "letter_of_credit",
    "swift_message",
    "lc_application",
    "standby_letter_of_credit",
    "bank_guarantee",
}


def _tier_chain_for_document(document_type: str) -> Tuple[str, ...]:
    """Pick the tier escalation order based on document type.

    LC-family documents start at L2 (Sonnet) because the MT700 structure
    needs careful parsing. Supporting docs start at L1 (GPT-4.1) and
    escalate to L2→L3 if critical fields are missing.

    Respects EXTRACTION_VISION_L1_MODEL env var — if set, the operator
    wants L1 in the chain.
    """
    lc_types = {"letter_of_credit", "swift_message", "lc_application", "standby_letter_of_credit"}
    if document_type in lc_types:
        return ("L2", "L3")
    return ("L1", "L2", "L3")


async def extract_document_multimodal_first(
    *,
    document_type: str,
    filename: str,
    file_bytes: Optional[bytes],
    content_type: Optional[str],
    extracted_text: str = "",
    subtype_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Vision LLM extraction with tier escalation.

    Blind per-document OCR. Each call sees exactly one document —
    no cross-referencing to the LC or other documents. That separation
    is enforced at the extraction boundary so validation (Part 2) can
    judge what's actually present on each doc, not a cross-mixed view.

    `extracted_text` is the raw PDF text (from pdfminer/pypdf or OCR) — when
    present, it's sent alongside the page images so the LLM has both
    visual layout AND character-perfect text content. Empty string means
    vision-only.
    """
    if not file_bytes or not _is_supported_content_type(content_type, filename):
        return None

    _, _, max_pages = _resolve_multimodal_config()
    try:
        image_parts, source_mode = await _build_visual_parts(
            file_bytes=file_bytes,
            content_type=content_type,
            filename=filename,
            max_pages=max_pages,
        )
    except Exception as exc:
        logger.warning("Multimodal visual preparation failed for %s: %s", filename, exc)
        return None

    if not image_parts:
        return None

    tier_chain = _tier_chain_for_document(document_type)
    last_result: Optional[Dict[str, Any]] = None
    tier_attempts: List[Dict[str, Any]] = []
    # Reset the per-request diagnostic channel so stale attempts from a
    # previous call don't leak into this one.
    _last_tier_attempts.set(tier_attempts)
    for tier in tier_chain:
        provider, model = _resolve_vision_tier_config(tier)
        attempt_record: Dict[str, Any] = {
            "tier": tier,
            "provider": provider,
            "model": model,
        }
        result = await _attempt_vision_tier(
            tier=tier,
            document_type=document_type,
            filename=filename,
            image_parts=image_parts,
            source_mode=source_mode,
            subtype_hint=subtype_hint,
            extracted_text=extracted_text,
            attempt_record=attempt_record,
        )
        if result is None:
            attempt_record.setdefault("outcome", "no_result")
        elif _vision_result_is_strong(result, document_type):
            attempt_record["outcome"] = "strong"
        else:
            attempt_record["outcome"] = "weak_missing_critical"
        tier_attempts.append(attempt_record)

        if _vision_result_is_strong(result, document_type):
            # Attach the full attempt trace so downstream consumers can see
            # which tier(s) ran and what provider/model each used.
            if isinstance(result, dict):
                result["_tier_attempts"] = tier_attempts
            return result
        last_result = result or last_result
        if result is None:
            logger.info(
                "Vision tier=%s returned no result for %s (provider=%s model=%s) — escalating",
                tier, filename, provider, model,
            )
        else:
            logger.info(
                "Vision tier=%s result missing critical fields for %s (doc_type=%s provider=%s model=%s) — escalating",
                tier, filename, document_type, provider, model,
            )

    # All tiers were tried — return whatever the last attempt produced
    # (which may be a weak result with some fields populated, or None).
    # Attach the full attempt trace either way so diagnostics survive.
    if isinstance(last_result, dict):
        last_result["_tier_attempts"] = tier_attempts
    return last_result


_MT700_ONE_SHOT_EXAMPLE = """
EXAMPLE — for an MT700 LC the page would look like:
  27: 1/1
  40A: IRREVOCABLE
  20: ABCD2026123
  31C: 260315
  40E: UCP LATEST VERSION
  31D: 260920NEW YORK
  50: ACME IMPORTERS LLC
      123 5TH AVE, NEW YORK, NY, USA
  59: GLOBAL EXPORT CO LTD
      45 INDUSTRIAL ROAD, DHAKA, BANGLADESH
  32B: USD 250,000.00
  39A: 5/5
  41D: ANY BANK BY NEGOTIATION
  43P: ALLOWED
  43T: NOT ALLOWED
  44E: CHITTAGONG, BANGLADESH
  44F: NEW YORK, USA
  44C: 260830
  45A: <goods description...>
  46A: <documents required list...>
  47A: <additional conditions list...>
  48: 21 DAYS FROM SHIPMENT DATE
  49: WITHOUT
  71D: ALL CHARGES OUTSIDE BANGLADESH FOR APPLICANT ACCOUNT

You should return EXACTLY:
{
  "lc_number": "ABCD2026123",
  "sequence_of_total": "1/1",
  "form_of_documentary_credit": "IRREVOCABLE",
  "issue_date": "2026-03-15",
  "applicable_rules": "UCP LATEST VERSION",
  "expiry_date": "2026-09-20",
  "expiry_place": "NEW YORK",
  "applicant": "ACME IMPORTERS LLC, 123 5TH AVE, NEW YORK, NY, USA",
  "beneficiary": "GLOBAL EXPORT CO LTD, 45 INDUSTRIAL ROAD, DHAKA, BANGLADESH",
  "amount": 250000.00,
  "currency": "USD",
  "amount_tolerance": "5/5",
  "available_with": "ANY BANK",
  "available_by": "NEGOTIATION",
  "partial_shipments": "ALLOWED",
  "transshipment": "NOT ALLOWED",
  "port_of_loading": "CHITTAGONG, BANGLADESH",
  "port_of_discharge": "NEW YORK, USA",
  "latest_shipment_date": "2026-08-30",
  "goods_description": "<full text of 45A>",
  "documents_required": ["<each line of 46A as a separate array entry>"],
  "additional_conditions": ["<each line of 47A as a separate array entry>"],
  "period_for_presentation": 21,
  "confirmation_instructions": "WITHOUT",
  "charges": "ALL CHARGES OUTSIDE BANGLADESH FOR APPLICANT ACCOUNT"
}

Notice: dates parsed to ISO format, amount as a number (not a string), 41D split
into available_with + available_by, 31D split into expiry_date + expiry_place,
documents_required and additional_conditions as ARRAYS not strings.

Notice also: this example LC has every field populated, so every canonical
key appears in the output.  On a real LC, if a field is NOT present
(e.g. the LC doesn't mention transshipment at all) then OMIT that key
entirely.  Don't return `transshipment: null`.  Don't invent a value.
Only include keys for fields that are actually on the document.
"""


def _build_multimodal_prompt(
    *,
    document_type: str,
    schema: Dict[str, Any],
    subtype_hint: Optional[str],
    extracted_text: str,
) -> str:
    fields = schema.get("fields") or []
    notes = schema.get("notes") or []
    support_text = (extracted_text or "").strip()
    # Don't truncate text for the LC — we need every clause and every field.
    is_lc = document_type.lower() in _LC_DOCUMENT_TYPES
    text_cap = 16000 if is_lc else 4000
    support_text = support_text[:text_cap] if support_text else ""

    # Header / role
    header = (
        f"You are extracting structured data from this {schema['title']}.\n"
        f"Declared document type: {document_type}\n"
    )
    if subtype_hint:
        header += f"Subtype hint: {subtype_hint}\n"

    # The "see everything" instruction.  Three-case rule for whether a
    # key should appear in the output JSON:
    #
    #   1. Field is on the document AND you can read the value →
    #      include the key with the value.
    #   2. Field label is on the document but the value is blank,
    #      smudged, or unclear → include the key with an empty
    #      string ``""``.  The reviewer can type it in.
    #   3. Field is NOT on the document at all → OMIT the key
    #      entirely from your output.  Do NOT return ``null``.
    #
    # This lets the reviewer distinguish "the extractor saw a label but
    # couldn't read the value" (fillable empty slot) from "this field
    # was never on the document" (no slot at all — the document simply
    # doesn't have that field).
    instruction = (
        "\n\nYour task: read the page images and the raw text, transcribe "
        "EVERY printed labeled field you see on the document, and return a "
        "JSON object.  You are a BLIND TRANSCRIBER — you do not know what "
        "the LC, customs, or any other external rule demands.  You do not "
        "care whether a field 'should' be there.  You only care about what "
        "is PHYSICALLY PRINTED on this one document right now.\n\n"
        "CRITICAL — what to include in the JSON output:\n"
        "  1. If a field is on the document AND you can read the value: "
        "include the key with the value.\n"
        "  2. If the field label is on the document but the value is "
        "blank, smudged, or unclear: include the key with an empty "
        "string \"\".  The reviewer will type the value in.\n"
        "  3. If the field is NOT on the document at all: OMIT the key "
        "entirely from your output.  Do NOT include it with null.  Do "
        "NOT invent placeholder values.  Do NOT 'remember' values from "
        "other documents in the presentation.  If it isn't there, it "
        "simply does not appear in the output JSON.\n\n"
        "The canonical key list below is a NAMING CONVENTION for the "
        "common fields intrinsic to this document type.  It is NOT an "
        "exhaustive list of what the document should carry.\n\n"
        "  - If a canonical field is printed: return it under the "
        "canonical key name (map synonyms — e.g., 'Shipper Name' → "
        "'shipper').\n"
        "  - If a canonical field is NOT printed: OMIT that key entirely "
        "(rule 3 above).\n"
        "  - If ANY OTHER printed labeled field is on the document that "
        "is not in the canonical list (e.g., 'LC No: ABC123', 'Order "
        "Ref: PO-9001', 'Exporter BIN: 1234-5678', 'Tax ID', 'Incoterms', "
        "'Bank Reference', etc.): STILL INCLUDE IT.  Use a sensible "
        "snake_case key name derived from the printed label.  Do not "
        "skip printed fields just because they are not in the canonical "
        "list.\n\n"
        "Canonical keys intrinsic to this document type "
        "(use these names when you find the values, per rule above):\n"
        + "\n".join(f"  - {field}" for field in fields)
    )

    # Doc-type-specific notes from the schema.
    if notes:
        instruction += "\n\nFormatting rules:\n" + "\n".join(f"  - {note}" for note in notes)

    instruction += (
        "\n  - Preserve arrays as arrays for documents_required, "
        "additional_conditions, and any other obviously-multi-valued field.\n"
        "  - Dates: return ISO format YYYY-MM-DD when possible.\n"
        "  - Amounts: return numbers, not strings (no commas, no currency).\n"
        "  - Output ONLY a JSON object. No markdown, no prose, no explanations."
    )

    # MT700 one-shot ONLY for LC documents — gives the LLM a worked example
    # of the field-tag-to-canonical-key mapping it always gets wrong.
    one_shot = _MT700_ONE_SHOT_EXAMPLE if is_lc else ""

    # Raw text. We send this for ALL doc types when available — pdfminer
    # gives us character-perfect text content directly from the PDF, which
    # is more reliable than reading text out of a JPEG.
    text_block = ""
    if support_text:
        text_block = (
            "\n\nRAW PDF TEXT CONTENT (extracted via pdfminer/pypdf — "
            "use as the authoritative source for text values; use the page "
            "images to understand layout and confirm formatting):\n"
            f"```\n{support_text}\n```"
        )

    return header + one_shot + instruction + text_block


async def _build_visual_parts(*, file_bytes: bytes, content_type: Optional[str], filename: str, max_pages: int) -> Tuple[List[Dict[str, str]], str]:
    ctype = (content_type or "").lower()
    lower_name = (filename or "").lower()
    if ctype.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        media_type = ctype if ctype.startswith("image/") else _guess_image_media_type(lower_name)
        return ([{"media_type": media_type, "data": base64.b64encode(file_bytes).decode("ascii")}], "image" )
    if ctype == "application/pdf" or lower_name.endswith(".pdf"):
        return await _render_pdf_to_images(file_bytes, max_pages=max_pages)
    return ([], "unsupported")


async def _render_pdf_to_images(file_bytes: bytes, *, max_pages: int) -> Tuple[List[Dict[str, str]], str]:
    def _convert() -> List[Dict[str, str]]:
        from pdf2image import convert_from_bytes

        # 220 DPI + JPEG quality 90 — enough resolution for the LLM to read
        # MT700 small print and SWIFT field codes. Was 170 / 82 which lost
        # detail on dense LC pages.
        images = convert_from_bytes(file_bytes, dpi=220, first_page=1, last_page=max_pages, fmt="jpeg")
        result: List[Dict[str, str]] = []
        for img in images[:max_pages]:
            buf = io.BytesIO()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=90, optimize=True)
            result.append({
                "media_type": "image/jpeg",
                "data": base64.b64encode(buf.getvalue()).decode("ascii"),
            })
        return result

    images = await asyncio.to_thread(_convert)
    return images, "pdf_pages"


async def _generate_multimodal(*, provider: str, model: str, prompt: str, system_prompt: str, image_parts: Sequence[Dict[str, str]]) -> Tuple[str, str]:
    provider_name = (provider or "").lower()

    # OpenRouter gateway mode: when OPENROUTER_API_KEY is configured and the
    # direct-provider key is NOT, route the call through OpenRouter using
    # the "<provider>/<model>" model ID format that OpenRouter expects.
    #
    # This is the path for operators who set
    #   AI_ROUTER_L2_PRIMARY_MODEL=anthropic/claude-sonnet-4-6
    # and only have OPENROUTER_API_KEY in their env.  Previously the
    # resolver would split that into (anthropic, claude-sonnet-4-6) and
    # route to the direct Anthropic SDK, which fails with "ANTHROPIC_API_KEY
    # not configured" — a silent failure that fell through to the
    # text-based extractor (GPT-4o-mini) without surfacing any error.
    has_openrouter_key = bool(os.getenv("OPENROUTER_API_KEY"))
    if has_openrouter_key:
        if provider_name == LLMProvider.ANTHROPIC.value and not os.getenv("ANTHROPIC_API_KEY"):
            openrouter_model = model if "/" in model else f"anthropic/{model}"
            return await _generate_openai_compatible(
                provider=LLMProvider.OPENROUTER.value,
                model=openrouter_model,
                prompt=prompt,
                system_prompt=system_prompt,
                image_parts=image_parts,
            )
        if provider_name == LLMProvider.OPENAI.value and not os.getenv("OPENAI_API_KEY"):
            openrouter_model = model if "/" in model else f"openai/{model}"
            return await _generate_openai_compatible(
                provider=LLMProvider.OPENROUTER.value,
                model=openrouter_model,
                prompt=prompt,
                system_prompt=system_prompt,
                image_parts=image_parts,
            )

    if provider_name in {LLMProvider.OPENAI.value, LLMProvider.OPENROUTER.value}:
        return await _generate_openai_compatible(
            provider=provider_name,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            image_parts=image_parts,
        )
    if provider_name == LLMProvider.ANTHROPIC.value:
        return await _generate_anthropic(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            image_parts=image_parts,
        )
    # fall back to openrouter/openai style for unknown compatible providers
    return await _generate_openai_compatible(
        provider=LLMProvider.OPENROUTER.value,
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        image_parts=image_parts,
    )


async def _generate_openai_compatible(*, provider: str, model: str, prompt: str, system_prompt: str, image_parts: Sequence[Dict[str, str]]) -> Tuple[str, str]:
    import httpx
    import openai

    api_key: Optional[str]
    base_url: Optional[str] = None
    if provider == LLMProvider.OPENAI.value:
        api_key = os.getenv("OPENAI_API_KEY")
    else:
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if not api_key:
        raise ValueError(f"{provider} API key not configured")

    timeout = httpx.Timeout(30.0, read=120.0)
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for part in image_parts:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{part['media_type']};base64,{part['data']}"},
        })
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=int(os.getenv("EXTRACTION_MULTIMODAL_MAX_TOKENS") or "8000"),
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return (response.choices[0].message.content or "", provider)


async def _generate_anthropic(*, model: str, prompt: str, system_prompt: str, image_parts: Sequence[Dict[str, str]]) -> Tuple[str, str]:
    import anthropic
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    timeout = httpx.Timeout(30.0, read=120.0)
    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for part in image_parts:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": part["media_type"],
                "data": part["data"],
            },
        })
    response = await client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
        max_tokens=int(os.getenv("EXTRACTION_MULTIMODAL_MAX_TOKENS") or "8000"),
        temperature=0.1,
    )
    chunks: List[str] = []
    for block in response.content or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return ("".join(chunks), LLMProvider.ANTHROPIC.value)


def _guess_image_media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"
