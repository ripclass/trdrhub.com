from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image

from app.services.extraction.ai_first_extractor import (
    _parse_llm_json_with_repair,
    _wrap_ai_result_with_default_confidence,
)
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


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
    "beneficiary_certificate",
    "beneficiary_statement",
    "manufacturer_certificate",
    "conformity_certificate",
    "non_manipulation_certificate",
    "halal_certificate",
    "kosher_certificate",
    "organic_certificate",
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
        "title": "Letter of Credit / SWIFT documentary credit",
        "fields": [
            "lc_number", "lc_type", "amount", "currency", "applicant", "beneficiary",
            "issuing_bank", "advising_bank", "confirming_bank", "port_of_loading",
            "port_of_discharge", "expiry_date", "latest_shipment_date", "issue_date",
            "incoterm", "ucp_reference", "partial_shipments", "transshipment",
            "goods_description", "documents_required", "additional_conditions",
            "payment_terms", "available_with",
        ],
        "notes": [
            "Treat the actual document pages as primary evidence.",
            "Do not invent SWIFT fields that are not visible.",
            "documents_required and additional_conditions should be arrays when present.",
        ],
    },
    "commercial_invoice": {
        "family": "invoice",
        "title": "Commercial / Proforma Invoice",
        "fields": [
            "invoice_number", "invoice_date", "amount", "currency", "seller", "buyer",
            "applicant", "beneficiary", "consignee", "notify_party", "goods_description",
            "hs_code", "incoterm", "country_of_origin", "port_of_loading",
            "port_of_discharge", "gross_weight", "net_weight", "total_packages",
            "payment_terms",
        ],
        "notes": [
            "Extract the invoice party names exactly as written.",
            "Do not guess HS codes or Incoterms.",
        ],
    },
    "packing_list": {
        "family": "packing",
        "title": "Packing List",
        "fields": [
            "packing_list_number", "packing_list_date", "seller", "buyer", "consignee",
            "goods_description", "marks_and_numbers", "total_packages", "package_type",
            "gross_weight", "net_weight", "measurement_value", "port_of_loading",
            "port_of_discharge",
        ],
        "notes": [
            "Prioritize package counts, weights, dimensions, and marks/numbers.",
        ],
    },
    "transport_document": {
        "family": "transport",
        "title": "Transport document (B/L, AWB, waybill, multimodal, rail, road, forwarder receipt)",
        "fields": [
            "bl_number", "transport_reference_number", "airway_bill_number", "consignment_reference",
            "shipper", "consignee", "notify_party", "port_of_loading", "port_of_discharge",
            "airport_of_departure", "airport_of_destination", "vessel_name", "voyage_number",
            "carriage_vessel_name", "carriage_voyage_number", "shipped_on_board_date",
            "issue_date", "goods_description", "gross_weight", "net_weight", "marks_and_numbers",
            "transport_mode_chain",
        ],
        "notes": [
            "Use the correct field family for the visible transport mode.",
            "If it is AWB, prefer airway_bill_number / airport fields.",
        ],
    },
    "regulatory_document": {
        "family": "regulatory",
        "title": "Origin / customs / regulatory / sanitary certificate document",
        "fields": [
            "certificate_number", "license_number", "declaration_reference", "permit_number",
            "country_of_origin", "origin_country", "issuing_authority", "certifying_authority",
            "issue_date", "expiry_date", "goods_description", "exporter", "importer",
        ],
        "notes": [
            "Use certificate_number for most certificates, license_number for licenses, declaration_reference for customs declarations.",
        ],
    },
    "insurance_document": {
        "family": "insurance",
        "title": "Insurance / compliance / special certificate",
        "fields": [
            "policy_number", "certificate_number", "insured_amount", "coverage_amount",
            "currency", "issuer_name", "insurer", "issue_date", "expiry_date",
            "goods_description", "risks_covered", "beneficiary", "applicant",
        ],
        "notes": [
            "Use policy_number or certificate_number exactly as visible.",
        ],
    },
    "inspection_document": {
        "family": "inspection",
        "title": "Inspection / testing / quality / weight / measurement document",
        "fields": [
            "certificate_number", "inspection_agency", "inspection_result", "quality_finding",
            "analysis_result", "gross_weight", "net_weight", "measurement_value",
            "issue_date", "goods_description",
        ],
        "notes": [
            "Use inspection_result / quality_finding / analysis_result based on the visible document type.",
        ],
    },
    "supporting_document": {
        "family": "supporting",
        "title": "Supporting trade document",
        "fields": [
            "document_title", "document_reference", "issuing_authority", "issue_date",
            "expiry_date", "goods_description", "shipper", "consignee", "origin_country",
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
    if doc_type in INSPECTION_TYPES:
        return "inspection_document"
    return "supporting_document"


def _resolve_multimodal_config() -> Tuple[str, str, int]:
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


def _is_supported_content_type(content_type: Optional[str], filename: Optional[str]) -> bool:
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or ctype == "application/pdf":
        return True
    lower_name = (filename or "").lower()
    return lower_name.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp"))


async def extract_document_multimodal_first(
    *,
    document_type: str,
    filename: str,
    file_bytes: Optional[bytes],
    content_type: Optional[str],
    extracted_text: str = "",
    subtype_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not file_bytes or not _is_supported_content_type(content_type, filename):
        return None

    provider, model, max_pages = _resolve_multimodal_config()
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

    schema_key = _resolve_schema_key(document_type)
    schema = DOC_TYPE_SCHEMAS[schema_key]
    prompt = _build_multimodal_prompt(
        document_type=document_type,
        schema=schema,
        subtype_hint=subtype_hint,
        extracted_text=extracted_text,
    )
    system_prompt = (
        "You are an expert trade-finance document extractor. "
        "Use the attached document pages as primary evidence. "
        "Extract ONLY what is explicitly visible. Return valid JSON object only."
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
        logger.warning("Multimodal extraction call failed for %s via %s/%s: %s", filename, provider, model, exc)
        return None

    if not response_text:
        return None

    try:
        from app.services.llm_provider import LLMProviderFactory
        repair_provider = LLMProviderFactory.create_provider(provider)
    except Exception:
        repair_provider = None

    parsed = await _parse_llm_json_with_repair(repair_provider, response_text)
    if not parsed:
        logger.warning("Multimodal extraction JSON parse failed for %s", filename)
        return None

    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    wrapped["_extraction_method"] = "multimodal_ai_first"
    wrapped["_source_mode"] = source_mode
    wrapped["_llm_provider"] = provider_used
    wrapped["_llm_model"] = model
    wrapped["_multimodal_pages_used"] = len(image_parts)
    if subtype_hint:
        wrapped["_multimodal_subtype_hint"] = subtype_hint
    logger.info(
        "validate.extraction.multimodal file=%s doc_type=%s provider=%s model=%s pages=%s source_mode=%s",
        filename,
        document_type,
        provider_used,
        model,
        len(image_parts),
        source_mode,
    )
    return wrapped


def _build_multimodal_prompt(*, document_type: str, schema: Dict[str, Any], subtype_hint: Optional[str], extracted_text: str) -> str:
    fields = schema.get("fields") or []
    notes = schema.get("notes") or []
    support_text = (extracted_text or "").strip()
    support_text = support_text[:4000] if support_text else ""
    return (
        f"Extract structured data from this {schema['title']}\n"
        f"Declared document type: {document_type}\n"
        f"Subtype hint: {subtype_hint or 'none'}\n\n"
        "Return one JSON object with EXACTLY these top-level keys (use null when absent):\n"
        + "\n".join(f"- {field}" for field in fields)
        + "\n\nRules:\n"
        + "\n".join(f"- {note}" for note in notes)
        + "\n- Preserve arrays as arrays when the field obviously contains multiple items."
        + "\n- Do not add markdown. Do not add explanation. JSON only."
        + (f"\n\nFallback OCR/native text context (secondary evidence only):\n{support_text}" if support_text else "")
    )


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

        images = convert_from_bytes(file_bytes, dpi=170, first_page=1, last_page=max_pages, fmt="jpeg")
        result: List[Dict[str, str]] = []
        for img in images[:max_pages]:
            buf = io.BytesIO()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=82, optimize=True)
            result.append({
                "media_type": "image/jpeg",
                "data": base64.b64encode(buf.getvalue()).decode("ascii"),
            })
        return result

    images = await asyncio.to_thread(_convert)
    return images, "pdf_pages"


async def _generate_multimodal(*, provider: str, model: str, prompt: str, system_prompt: str, image_parts: Sequence[Dict[str, str]]) -> Tuple[str, str]:
    provider_name = (provider or "").lower()
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
        max_tokens=int(os.getenv("EXTRACTION_MULTIMODAL_MAX_TOKENS") or "2000"),
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
        max_tokens=int(os.getenv("EXTRACTION_MULTIMODAL_MAX_TOKENS") or "2000"),
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
