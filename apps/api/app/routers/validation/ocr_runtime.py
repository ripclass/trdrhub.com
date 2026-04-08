"""OCR/runtime extraction helpers for validation routes."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.utils.logger import TRACE_LOG_LEVEL


logger = logging.getLogger(__name__)


def _empty_extraction_artifacts_v1(
    raw_text: str = "",
    ocr_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "version": "extraction_artifacts_v1",
        "raw_text": raw_text or "",
        "tables": [],
        "key_value_candidates": [],
        "spans": [],
        "bbox": [],
        "ocr_confidence": ocr_confidence,
        "attempted_stages": [],
        "text_length_by_stage": {},
        "stage_errors": {},
        "reason_codes": [],
        "provider_attempts": [],
        "fallback_activated": False,
        "final_stage": None,
        "final_text_length": len((raw_text or "").strip()),
        "stage_scores": {},
        "selected_stage": None,
        "rejected_stages": {},
    }


def _extraction_fallback_hotfix_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ocr_compatibility_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_OCR_COMPATIBILITY_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _stage_promotion_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_STAGE_PROMOTION_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ocr_adapter_runtime_payload_fix_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_OCR_ADAPTER_RUNTIME_PAYLOAD_FIX_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _stage_threshold_tuning_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_STAGE_THRESHOLD_TUNING_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _record_extraction_reason_code(artifacts: Dict[str, Any], reason_code: Optional[str]) -> None:
    if not reason_code:
        return
    reasons = artifacts.setdefault("reason_codes", [])
    if reason_code not in reasons:
        reasons.append(reason_code)


def _record_extraction_stage(
    artifacts: Dict[str, Any],
    *,
    filename: str,
    stage: str,
    text: str = "",
    error_code: Optional[str] = None,
    error: Optional[str] = None,
    fallback: bool = False,
) -> None:
    attempted = artifacts.setdefault("attempted_stages", [])
    if stage not in attempted:
        attempted.append(stage)

    text_length = len((text or "").strip())
    artifacts.setdefault("text_length_by_stage", {})[stage] = text_length

    if fallback:
        artifacts["fallback_activated"] = True

    if error_code or error:
        stage_errors = artifacts.setdefault("stage_errors", {})
        entries = stage_errors.setdefault(stage, [])
        if error_code and error_code not in entries:
            entries.append(error_code)
        if error:
            error_text = str(error)
            if error_text and error_text not in entries:
                entries.append(error_text)

    if error_code:
        _record_extraction_reason_code(artifacts, error_code)

    logger.info(
        "validate.extraction.stage file=%s stage=%s text_len=%s fallback=%s error_code=%s",
        filename,
        stage,
        text_length,
        bool(artifacts.get("fallback_activated")),
        error_code,
    )


def _merge_extraction_artifacts(base: Dict[str, Any], overlay: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = dict(base or {})
    if not isinstance(overlay, dict):
        return result

    for key, value in overlay.items():
        if key in {"attempted_stages", "reason_codes"}:
            merged = list(result.get(key) or [])
            for item in value or []:
                if item not in merged:
                    merged.append(item)
            result[key] = merged
        elif key in {"text_length_by_stage"}:
            merged_map = dict(result.get(key) or {})
            merged_map.update(value or {})
            result[key] = merged_map
        elif key in {"stage_errors"}:
            merged_errors = dict(result.get(key) or {})
            for stage_name, errors in (value or {}).items():
                existing = list(merged_errors.get(stage_name) or [])
                for entry in errors or []:
                    if entry not in existing:
                        existing.append(entry)
                merged_errors[stage_name] = existing
            result[key] = merged_errors
        elif key in {"provider_attempts"}:
            existing_attempts = list(result.get(key) or [])
            existing_attempts.extend(value or [])
            result[key] = existing_attempts
        elif value not in (None, "", [], {}):
            result[key] = value

    return result


def _finalize_text_extraction_result(
    artifacts: Dict[str, Any],
    *,
    stage: str,
    text: str,
) -> Dict[str, Any]:
    artifacts["final_stage"] = stage
    artifacts["selected_stage"] = artifacts.get("selected_stage") or stage
    artifacts["final_text_length"] = len((text or "").strip())
    artifacts["raw_text"] = text or ""
    return {"text": text or "", "artifacts": artifacts}


def _merge_text_sources(*texts: Optional[str]) -> str:
    """Merge text sources into a deduplicated line stream while preserving order."""
    merged_lines: List[str] = []
    seen: set[str] = set()
    for text in texts:
        if not text:
            continue
        for line in str(text).splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged_lines.append(normalized)
    return "\n".join(merged_lines)


def _build_extraction_artifacts_from_ocr(
    raw_text: str,
    provider_result: Optional[Any] = None,
    ocr_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    artifacts = _empty_extraction_artifacts_v1(raw_text=raw_text, ocr_confidence=ocr_confidence)

    if not provider_result:
        return artifacts

    confidence = provider_result.overall_confidence
    if isinstance(confidence, (int, float)):
        artifacts["ocr_confidence"] = float(confidence)

    metadata = provider_result.metadata if isinstance(provider_result.metadata, dict) else {}
    artifacts["tables"] = metadata.get("tables") or []
    artifacts["key_value_candidates"] = (
        metadata.get("key_value_candidates")
        or metadata.get("key_value_pairs")
        or metadata.get("entities")
        or []
    )

    spans: List[Dict[str, Any]] = []
    bboxes: List[Dict[str, Any]] = []
    for element in provider_result.elements or []:
        span_entry: Dict[str, Any] = {
            "text": element.text,
            "confidence": element.confidence,
            "element_type": element.element_type,
        }
        bbox_entry: Optional[Dict[str, Any]] = None
        if element.bounding_box:
            bbox_entry = {
                "x1": element.bounding_box.x1,
                "y1": element.bounding_box.y1,
                "x2": element.bounding_box.x2,
                "y2": element.bounding_box.y2,
                "page": element.bounding_box.page,
            }
            span_entry["bbox"] = bbox_entry

        spans.append(span_entry)
        if bbox_entry:
            bboxes.append(bbox_entry)

    artifacts["spans"] = spans
    artifacts["bbox"] = bboxes
    return artifacts


def _scrape_binary_text_metadata(file_bytes: bytes) -> str:
    """Best-effort printable-text scrape from binary payloads as a final recovery stage."""
    if not file_bytes:
        return ""

    decoded = file_bytes.decode("latin-1", errors="ignore")
    text_segments = re.findall(r"\(([^()]{6,200})\)", decoded)
    if not text_segments:
        text_segments = re.findall(r"[A-Za-z0-9][A-Za-z0-9:/,.\-() ]{5,}", decoded)

    candidates: List[str] = []
    seen: set[str] = set()
    for segment in text_segments:
        normalized = re.sub(r"\s+", " ", segment).strip()
        if len(normalized) < 6:
            continue
        lower = normalized.lower()
        if lower in seen:
            continue
        if lower in {"obj", "endobj", "stream", "endstream", "xref", "trailer"}:
            continue
        noise_count = sum(1 for ch in normalized if ch in "<>{}[]\\")
        if noise_count > max(3, len(normalized) // 6):
            continue
        seen.add(lower)
        candidates.append(normalized)
        if len(candidates) >= 80:
            break

    return "\n".join(candidates)


_STAGE_FIELD_PATTERNS = {
    "issue_date": [r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"],
    "bin_tin": [
        r"\b(?:bin|tin|vat\s*reg(?:istration)?|tax\s*id|etin)\b",
        r"\b[0-9OISBL][0-9OISBL\-\s]{9,18}\b",
    ],
    "gross_weight": [
        r"\bgross(?:\s+weight|\s+wt|\s+wgt)?\b",
        r"\bgross\s*/\s*net\b",
        r"\b[0-9OISBL]+(?:[.,][0-9OISBL]+)?\s?(kg|kgs|kilograms?|lb|lbs|mt|ton|tonne)\b",
    ],
    "net_weight": [
        r"\bnet(?:\s+weight|\s+wt|\s+wgt)?\b",
        r"\bgross\s*/\s*net\b",
        r"\b[0-9OISBL]+(?:[.,][0-9OISBL]+)?\s?(kg|kgs|kilograms?|lb|lbs|mt|ton|tonne)\b",
    ],
    "issuer": [r"\bissuer\b", r"\bissuing bank\b", r"\bseller\b", r"\bexporter\b", r"\bcarrier\b", r"\bauthority\b"],
    "voyage": [r"\bvoyage\b", r"\bvessel\b", r"\bvsl\b"],
}

_STAGE_CRITICAL_FIELD_TO_ANCHOR_FIELD = {
    "bin_tin": "bin",
    "voyage": "voyage",
    "gross_weight": "gross_weight",
    "net_weight": "net_weight",
    "issue_date": "doc_date",
    "issuer": "issuer",
}


def _detect_input_mime_type(file_bytes: bytes, filename: str, content_type: Optional[str]) -> str:
    detected = str(content_type or "").strip().lower()
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if file_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if file_bytes[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if _looks_like_plaintext_bytes(file_bytes):
        return "text/plain"
    if detected and detected != "application/octet-stream":
        return detected
    lowered_name = (filename or "").lower()
    if lowered_name.endswith(".pdf"):
        return "application/pdf"
    if lowered_name.endswith(".png"):
        return "image/png"
    if lowered_name.endswith(".jpg") or lowered_name.endswith(".jpeg"):
        return "image/jpeg"
    if lowered_name.endswith(".tif") or lowered_name.endswith(".tiff"):
        return "image/tiff"
    return "application/octet-stream"


def _looks_like_plaintext_bytes(file_bytes: bytes) -> bool:
    sample = bytes(file_bytes[:4096] or b"")
    if not sample:
        return False
    if sample.startswith(b"%PDF") or sample[:8] == b"\x89PNG\r\n\x1a\n" or sample[:2] == b"\xff\xd8" or sample[:4] in (b"II*\x00", b"MM\x00*"):
        return False
    if b"\x00" in sample:
        return False
    printable = 0
    alpha = 0
    for byte in sample:
        if byte in (9, 10, 13) or 32 <= byte <= 126:
            printable += 1
            if 65 <= byte <= 90 or 97 <= byte <= 122:
                alpha += 1
    ratio = float(printable) / float(len(sample))
    return ratio >= 0.92 and alpha >= 8


def _extract_plaintext_bytes(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded = file_bytes.decode(encoding)
        except Exception:
            continue
        cleaned = decoded.replace("\x00", "").strip()
        if cleaned:
            return cleaned
    return ""


def _normalize_ocr_input(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    provider_name: Optional[str] = None,
) -> Dict[str, Any]:
    detected_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))
    if not getattr(settings, "OCR_NORMALIZATION_SHIM_ENABLED", True):
        return {
            "content": file_bytes,
            "content_type": detected_mime,
            "original_content_type": detected_mime,
            "page_count": 1,
            "dpi": dpi,
            "error_code": None,
            "error": None,
        }

    if detected_mime == "application/pdf":
        page_count = 0
        try:
            from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]

            page_count = len(PdfReader(BytesIO(file_bytes)).pages)
        except Exception:
            page_count = 0

        if (
            page_count and page_count > int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
        ) or len(file_bytes) > int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024)):
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": page_count,
                "dpi": dpi,
                "error_code": None,
                "error": "normalization_guardrail_skip",
            }

        try:
            from pdf2image import convert_from_bytes  # type: ignore
            from PIL import ImageOps  # type: ignore

            rendered_pages = convert_from_bytes(file_bytes, dpi=dpi, fmt="png", thread_count=1)
            if not rendered_pages:
                raise ValueError("pdf_render_empty")
            normalized_pages = []
            for image in rendered_pages:
                normalized = ImageOps.exif_transpose(image)
                if normalized.mode != "RGB":
                    normalized = normalized.convert("RGB")
                normalized_pages.append(normalized)

            buffer = BytesIO()
            normalized_pages[0].save(
                buffer,
                format="TIFF",
                save_all=True,
                append_images=normalized_pages[1:],
                compression="tiff_deflate",
                dpi=(dpi, dpi),
            )
            return {
                "content": buffer.getvalue(),
                "content_type": "image/tiff",
                "original_content_type": detected_mime,
                "page_count": len(normalized_pages),
                "dpi": dpi,
                "provider": provider_name,
                "error_code": None,
                "error": None,
            }
        except Exception as exc:
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": page_count or 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": "OCR_UNSUPPORTED_FORMAT",
                "error": str(exc),
            }

    if detected_mime.startswith("image/"):
        try:
            from PIL import Image, ImageOps  # type: ignore

            image = Image.open(BytesIO(file_bytes))
            normalized = ImageOps.exif_transpose(image)
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")

            buffer = BytesIO()
            normalized.save(buffer, format="PNG", dpi=(dpi, dpi))
            return {
                "content": buffer.getvalue(),
                "content_type": "image/png",
                "original_content_type": detected_mime,
                "page_count": 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": None,
                "error": None,
            }
        except Exception as exc:
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": "OCR_UNSUPPORTED_FORMAT",
                "error": str(exc),
            }

    return {
        "content": file_bytes,
        "content_type": detected_mime,
        "original_content_type": detected_mime,
        "page_count": 1,
        "dpi": dpi,
        "provider": provider_name,
        "error_code": "OCR_UNSUPPORTED_FORMAT",
        "error": "unsupported_input_mime",
    }


def _prepare_provider_ocr_payload(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    normalized_input = _normalize_ocr_input(file_bytes, filename, content_type, provider_name)
    original_mime = _detect_input_mime_type(file_bytes, filename, content_type)

    compat_enabled = _ocr_compatibility_v1_enabled()
    if not compat_enabled:
        normalized_input["bytes_sent"] = len(normalized_input.get("content") or b"")
        normalized_input["payload_source"] = "normalized"
        return normalized_input

    provider_key = str(provider_name or "").strip().lower()
    max_bytes_default = int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024))
    max_pages_default = int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
    preferences = {
        "google_documentai": {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
            "max_pages": max_pages_default,
        },
        "aws_textract": {
            "preferred_pdf_mimes": ("image/tiff", "application/pdf", "image/png"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 10 * 1024 * 1024),
            "max_pages": min(max_pages_default, 20),
        },
        "ocr_service": {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
            "max_pages": max_pages_default,
        },
        "deepseek_ocr": {
            "preferred_pdf_mimes": ("image/tiff", "image/png"),
            "supported_mimes": {"image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 10 * 1024 * 1024),
            "max_pages": min(max_pages_default, 10),
        },
    }.get(
        provider_key,
        {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": max_bytes_default,
            "max_pages": max_pages_default,
        },
    )

    page_count = int(normalized_input.get("page_count") or 1)
    if page_count > int(preferences.get("max_pages") or max_pages_default):
        return {
            "content": b"",
            "content_type": normalized_input.get("content_type") or original_mime,
            "original_content_type": original_mime,
            "page_count": page_count,
            "dpi": normalized_input.get("dpi"),
            "provider": provider_name,
            "bytes_sent": 0,
            "payload_source": "guardrail_rejected",
            "error_code": "OCR_UNSUPPORTED_FORMAT",
            "error": f"page_limit_exceeded:{page_count}",
        }

    preferred_pdf_mimes = tuple(preferences.get("preferred_pdf_mimes") or ())
    supported_mimes = set(preferences.get("supported_mimes") or set())
    max_bytes = int(preferences.get("max_bytes") or max_bytes_default)

    candidates: List[Tuple[bytes, str, str]] = []
    if original_mime == "application/pdf":
        if normalized_input.get("error_code") is None:
            candidates.append(
                (
                    normalized_input.get("content") or b"",
                    str(normalized_input.get("content_type") or ""),
                    "normalized",
                )
            )
        elif "application/pdf" in supported_mimes:
            candidates.append((file_bytes, original_mime, "original"))
        candidates = sorted(
            candidates,
            key=lambda item: preferred_pdf_mimes.index(item[1])
            if item[1] in preferred_pdf_mimes
            else len(preferred_pdf_mimes),
        )
    elif normalized_input.get("error_code") is None:
        candidates.append(
            (
                normalized_input.get("content") or b"",
                str(normalized_input.get("content_type") or ""),
                "normalized",
            )
        )
        if original_mime != str(normalized_input.get("content_type") or ""):
            candidates.append((file_bytes, original_mime, "original"))
    else:
        candidates.append((file_bytes, original_mime, "original"))

    for content_bytes, payload_mime, payload_source in candidates:
        if payload_mime not in supported_mimes:
            continue
        if not content_bytes:
            continue
        if len(content_bytes) > max_bytes:
            continue
        return {
            "content": content_bytes,
            "content_type": payload_mime,
            "original_content_type": original_mime,
            "page_count": page_count,
            "dpi": normalized_input.get("dpi"),
            "provider": provider_name,
            "bytes_sent": len(content_bytes),
            "payload_source": payload_source,
            "error_code": None,
            "error": None,
        }

    return {
        "content": b"",
        "content_type": normalized_input.get("content_type") or original_mime,
        "original_content_type": original_mime,
        "page_count": page_count,
        "dpi": normalized_input.get("dpi"),
        "provider": provider_name,
        "bytes_sent": 0,
        "payload_source": "unsupported",
        "error_code": normalized_input.get("error_code") or "OCR_UNSUPPORTED_FORMAT",
        "error": normalized_input.get("error") or "provider_payload_incompatible",
    }


def _provider_runtime_limits(provider_name: str) -> Dict[str, Any]:
    provider_key = str(provider_name or "").strip().lower()
    max_pages_default = int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
    max_bytes_default = int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024))
    limits = {
        "google_documentai": {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
        },
        "ocr_service": {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
        },
        "aws_textract": {
            "supported_mimes": {"image/png", "image/jpeg"},
            "max_pages": min(max_pages_default, 15),
            "max_bytes": min(max_bytes_default, 5 * 1024 * 1024),
        },
    }
    return limits.get(
        provider_key,
        {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": max_bytes_default,
        },
    )


def _pdf_page_count(file_bytes: bytes) -> int:
    try:
        from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]

        return len(PdfReader(BytesIO(file_bytes)).pages)
    except Exception:
        return 0


def _render_pdf_runtime_images(
    file_bytes: bytes,
    *,
    dpi: int,
    output_format: str,
) -> List[bytes]:
    from pdf2image import convert_from_bytes  # type: ignore
    from PIL import ImageOps  # type: ignore

    fmt = output_format.upper()
    save_format = "JPEG" if fmt == "JPEG" else "PNG"
    rendered_pages = convert_from_bytes(file_bytes, dpi=dpi, fmt=save_format.lower(), thread_count=1)
    page_payloads: List[bytes] = []
    for image in rendered_pages:
        normalized = ImageOps.exif_transpose(image)
        if fmt == "JPEG":
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")
        elif normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
        buffer = BytesIO()
        save_kwargs: Dict[str, Any] = {"format": save_format, "dpi": (dpi, dpi)}
        if save_format == "JPEG":
            save_kwargs["quality"] = 90
        normalized.save(buffer, **save_kwargs)
        page_payloads.append(buffer.getvalue())
    return page_payloads


def _normalize_runtime_image_bytes(
    file_bytes: bytes,
    *,
    dpi: int,
    output_format: str,
) -> bytes:
    from PIL import Image, ImageOps  # type: ignore

    image = Image.open(BytesIO(file_bytes))
    normalized = ImageOps.exif_transpose(image)
    save_format = "JPEG" if output_format.upper() == "JPEG" else "PNG"
    if save_format == "JPEG":
        if normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
    elif normalized.mode != "RGB":
        normalized = normalized.convert("RGB")
    buffer = BytesIO()
    save_kwargs: Dict[str, Any] = {"format": save_format, "dpi": (dpi, dpi)}
    if save_format == "JPEG":
        save_kwargs["quality"] = 90
    normalized.save(buffer, **save_kwargs)
    return buffer.getvalue()


def _build_runtime_payload_entry(
    *,
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    input_mime: str,
    normalized_mime: str,
    page_count: int,
    bytes_sent: int,
    payload_source: str,
    retry_used: bool,
    dpi: Optional[int] = None,
    page_index: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "provider": provider_name,
        "content": file_bytes,
        "filename": filename,
        "content_type": normalized_mime,
        "input_mime": input_mime,
        "normalized_mime": normalized_mime,
        "page_count": int(page_count or 1),
        "page_index": int(page_index or 1),
        "dpi": dpi,
        "bytes_sent": int(bytes_sent),
        "payload_source": payload_source,
        "retry_used": bool(retry_used),
    }


def _build_google_docai_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    input_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    limits = _provider_runtime_limits(provider_name)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))
    page_count = _pdf_page_count(file_bytes) if input_mime == "application/pdf" else 1

    if page_count and page_count > int(limits["max_pages"]):
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"page_limit_exceeded:{page_count}"}
    if len(file_bytes) > int(limits["max_bytes"]):
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"byte_limit_exceeded:{len(file_bytes)}"}

    groups: List[List[Dict[str, Any]]] = []
    if input_mime == "application/pdf":
        primary = _build_runtime_payload_entry(
            provider_name=provider_name,
            file_bytes=file_bytes,
            filename=filename,
            input_mime=input_mime,
            normalized_mime="application/pdf",
            page_count=max(1, page_count),
            bytes_sent=len(file_bytes),
            payload_source="runtime_pdf_direct",
            retry_used=False,
            dpi=dpi,
        )
        fallback_groups = [primary]
        try:
            normalized = _normalize_ocr_input(file_bytes, filename, content_type, provider_name)
            if normalized.get("error_code") is None and normalized.get("content"):
                fallback_groups.append(
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=normalized.get("content") or b"",
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime=str(normalized.get("content_type") or "image/tiff"),
                        page_count=int(normalized.get("page_count") or page_count or 1),
                        bytes_sent=len(normalized.get("content") or b""),
                        payload_source="runtime_pdf_retry_image",
                        retry_used=True,
                        dpi=int(normalized.get("dpi") or dpi),
                    )
                )
        except Exception:
            pass
        groups.append(fallback_groups)
    elif input_mime.startswith("image/"):
        try:
            primary_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="PNG")
            group = [
                _build_runtime_payload_entry(
                    provider_name=provider_name,
                    file_bytes=primary_bytes,
                    filename=filename,
                    input_mime=input_mime,
                    normalized_mime="image/png",
                    page_count=1,
                    bytes_sent=len(primary_bytes),
                    payload_source="runtime_image_png",
                    retry_used=False,
                    dpi=dpi,
                )
            ]
            if input_mime != "image/png":
                group.append(
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=file_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime=input_mime,
                        page_count=1,
                        bytes_sent=len(file_bytes),
                        payload_source="runtime_image_original",
                        retry_used=True,
                        dpi=dpi,
                    )
                )
            groups.append(group)
        except Exception as exc:
            return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": str(exc)}
    else:
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported_input_mime"}

    return {"groups": groups, "aggregate_pages": False, "error_code": None, "error": None}


def _build_textract_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    input_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    limits = _provider_runtime_limits(provider_name)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))

    groups: List[List[Dict[str, Any]]] = []
    try:
        if input_mime == "application/pdf":
            png_pages = _render_pdf_runtime_images(file_bytes, dpi=dpi, output_format="PNG")
            jpeg_pages = _render_pdf_runtime_images(file_bytes, dpi=dpi, output_format="JPEG")
            page_count = len(png_pages)
            if page_count > int(limits["max_pages"]):
                return {"groups": [], "aggregate_pages": True, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"page_limit_exceeded:{page_count}"}
            for page_index, page_bytes in enumerate(png_pages, start=1):
                if len(page_bytes) > int(limits["max_bytes"]):
                    return {"groups": [], "aggregate_pages": True, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"byte_limit_exceeded:{len(page_bytes)}"}
                group = [
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=page_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/png",
                        page_count=page_count,
                        page_index=page_index,
                        bytes_sent=len(page_bytes),
                        payload_source="runtime_pdf_page_png",
                        retry_used=False,
                        dpi=dpi,
                    )
                ]
                if page_index <= len(jpeg_pages):
                    group.append(
                        _build_runtime_payload_entry(
                            provider_name=provider_name,
                            file_bytes=jpeg_pages[page_index - 1],
                            filename=filename,
                            input_mime=input_mime,
                            normalized_mime="image/jpeg",
                            page_count=page_count,
                            page_index=page_index,
                            bytes_sent=len(jpeg_pages[page_index - 1]),
                            payload_source="runtime_pdf_page_jpeg_retry",
                            retry_used=True,
                            dpi=dpi,
                        )
                    )
                groups.append(group)
        elif input_mime.startswith("image/"):
            png_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="PNG")
            jpeg_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="JPEG")
            groups.append(
                [
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=png_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/png",
                        page_count=1,
                        bytes_sent=len(png_bytes),
                        payload_source="runtime_image_png",
                        retry_used=False,
                        dpi=dpi,
                    ),
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=jpeg_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/jpeg",
                        page_count=1,
                        bytes_sent=len(jpeg_bytes),
                        payload_source="runtime_image_jpeg_retry",
                        retry_used=True,
                        dpi=dpi,
                    ),
                ]
            )
        else:
            return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported_input_mime"}
    except Exception as exc:
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": str(exc)}

    return {"groups": groups, "aggregate_pages": True, "error_code": None, "error": None}


def _build_provider_runtime_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    if not _ocr_adapter_runtime_payload_fix_v1_enabled():
        payload = _prepare_provider_ocr_payload(provider_name, file_bytes, filename, content_type)
        if payload.get("error_code"):
            return {
                "groups": [],
                "aggregate_pages": False,
                "error_code": payload.get("error_code"),
                "error": payload.get("error"),
            }
        return {
            "groups": [[
                _build_runtime_payload_entry(
                    provider_name=provider_name,
                    file_bytes=payload.get("content") or b"",
                    filename=filename,
                    input_mime=str(payload.get("original_content_type") or payload.get("content_type") or content_type),
                    normalized_mime=str(payload.get("content_type") or content_type),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or len(payload.get("content") or b"")),
                    payload_source=str(payload.get("payload_source") or "normalized"),
                    retry_used=False,
                    dpi=payload.get("dpi"),
                )
            ]],
            "aggregate_pages": False,
            "error_code": None,
            "error": None,
        }

    provider_key = str(provider_name or "").strip().lower()
    if provider_key in {"google_documentai", "ocr_service"}:
        return _build_google_docai_payload_plan(provider_name, file_bytes, filename, content_type)
    if provider_key == "aws_textract":
        return _build_textract_payload_plan(provider_name, file_bytes, filename, content_type)
    return _build_google_docai_payload_plan(provider_name, file_bytes, filename, content_type)


def _build_provider_attempt_record(
    *,
    stage: str,
    provider_name: str,
    payload: Dict[str, Any],
    text: str,
    status: str,
    error_code: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "stage": stage,
        "provider": provider_name,
        "attempt_number": int(payload.get("attempt_number") or 1),
        "status": status,
        "text_len": len((text or "").strip()),
        "error_code": error_code,
        "error": error,
        "input_mime": payload.get("input_mime"),
        "normalized_mime": payload.get("normalized_mime"),
        "retry_used": bool(payload.get("retry_used")),
        "page_index": int(payload.get("page_index") or 1),
        "page_count": int(payload.get("page_count") or 1),
        "bytes_sent": int(payload.get("bytes_sent") or 0),
        "payload_source": payload.get("payload_source"),
    }


def _map_ocr_provider_error_code(error: Optional[str]) -> Optional[str]:
    if not error:
        return None
    lowered = str(error).strip().lower()
    if not lowered:
        return None
    if any(
        token in lowered
        for token in (
            "unsupported",
            "invalid mime",
            "content type",
            "content-type",
            "mime type",
            "bad format",
            "invalid document format",
            "unsupporteddocumentexception",
            "unsupported document",
            "unsupported file type",
            "format",
        )
    ):
        return "OCR_UNSUPPORTED_FORMAT"
    if any(
        token in lowered
        for token in (
            "empty_output",
            "empty output",
            "empty result",
            "empty_result",
            "no text",
            "no_ocr_provider_returned_text",
            "no text extracted",
            "no output",
            "blank document",
        )
    ):
        return "OCR_EMPTY_RESULT"
    if any(token in lowered for token in ("processor not found", "processor_not_found", "document ai processor not found")):
        return "OCR_PROCESSOR_NOT_FOUND"
    if "processor" in lowered and "not found" in lowered:
        return "OCR_PROCESSOR_NOT_FOUND"
    if any(
        token in lowered
        for token in (
            "permission denied",
            "forbidden",
            "access denied",
            "not authorized",
            "not allowed",
            "insufficient permissions",
            "status code 403",
        )
    ):
        return "OCR_PERMISSION_DENIED"
    if any(
        token in lowered
        for token in (
            "unauthenticated",
            "authentication failed",
            "auth failed",
            "auth failure",
            "invalid credentials",
            "invalid api key",
            "api key",
            "credential",
            "credentials",
            "expiredtoken",
            "signaturedoesnotmatch",
            "could not load default credentials",
            "status code 401",
        )
    ):
        return "OCR_AUTH_FAILURE"
    if any(
        token in lowered
        for token in (
            "timeout",
            "timed out",
            "deadline exceeded",
            "read timed out",
            "connect timeout",
            "request timeout",
        )
    ):
        return "OCR_TIMEOUT"
    if any(
        token in lowered
        for token in (
            "connection reset",
            "connection error",
            "connection refused",
            "connection aborted",
            "connection closed",
            "network",
            "dns",
            "temporary failure in name resolution",
            "name or service not known",
            "failed to establish a new connection",
            "service unavailable",
            "ssl",
            "tls",
            "unreachable",
            "proxyerror",
            "remote disconnected",
        )
    ):
        return "OCR_NETWORK_ERROR"
    return "OCR_UNKNOWN_PROVIDER_ERROR"


def _get_viable_ocr_providers() -> List[str]:
    try:
        from app.ocr.factory import get_ocr_factory
        from app.services.ocr_diagnostics import get_ocr_diagnostics, resolve_ocr_provider_name

        factory = get_ocr_factory()
        configured = [resolve_ocr_provider_name(name) for name in list(getattr(factory, "configured_providers", None) or []) if name]
        initialized = {
            resolve_ocr_provider_name(adapter.provider_name)
            for adapter in list(getattr(factory, "get_all_adapters", lambda: [])() or [])
            if getattr(adapter, "provider_name", None)
        }
        diagnostics = get_ocr_diagnostics()
        states = {
            str(entry.get("provider_name") or ""): entry
            for entry in diagnostics.ordered_states(configured)
            if entry.get("provider_name")
        }
    except Exception:
        return []

    fatal_error_codes = {"OCR_AUTH_FAILURE", "OCR_PERMISSION_DENIED", "OCR_PROCESSOR_NOT_FOUND"}
    viable: List[str] = []
    for provider_name in configured:
        if provider_name not in initialized:
            continue
        state = states.get(provider_name) or {}
        last_error_code = str(state.get("last_error_code") or "")
        if last_error_code in fatal_error_codes:
            continue
        if state.get("healthy") is False:
            continue
        viable.append(provider_name)
    return viable


def _score_stage_candidate(stage: str, text: str, document_type: Optional[str]) -> Dict[str, Any]:
    stripped = str(text or "").strip()
    total_chars = len(stripped)
    non_space_chars = sum(1 for ch in stripped if not ch.isspace())
    alnum_chars = sum(1 for ch in stripped if ch.isalnum())
    target_chars = max(100, int(getattr(settings, "OCR_MIN_TEXT_CHARS_FOR_SKIP", 1200) or 1200))
    text_len_score = min(1.0, float(total_chars) / float(target_chars))
    alnum_ratio_score = min(1.0, float(alnum_chars) / float(max(1, non_space_chars)))

    critical_fields: List[str] = []
    stage_tuning: Dict[str, Any] = {}
    anchor_hit_score = 0.0
    try:
        from app.services.extraction_core.profiles import load_profile
        from app.services.validation.day1_retrieval_guard import evaluate_anchor_evidence

        if document_type:
            profile = load_profile(document_type) or {}
            critical_fields = list(profile.get("critical_fields") or [])
            stage_tuning = profile.get("stage_tuning") if isinstance(profile.get("stage_tuning"), dict) else {}
        anchor_checks = evaluate_anchor_evidence(stripped, min_score=0.0)
        relevant_anchor_scores = [
            anchor_checks[anchor_field].score
            for field_name in critical_fields
            for anchor_field in [_STAGE_CRITICAL_FIELD_TO_ANCHOR_FIELD.get(field_name)]
            if anchor_field and anchor_field in anchor_checks
        ]
        if relevant_anchor_scores:
            anchor_hit_score = sum(relevant_anchor_scores) / float(len(relevant_anchor_scores))
    except Exception:
        critical_fields = critical_fields or []
        anchor_hit_score = 0.0

    field_pattern_hits = 0
    field_pattern_total = 0
    for field_name in critical_fields:
        patterns = _STAGE_FIELD_PATTERNS.get(field_name) or []
        if not patterns:
            continue
        field_pattern_total += 1
        if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in patterns):
            field_pattern_hits += 1
    field_pattern_score = (
        float(field_pattern_hits) / float(field_pattern_total)
        if field_pattern_total
        else 0.0
    )

    weights = {
        "text_len_score": float(getattr(settings, "OCR_STAGE_WEIGHT_TEXT_LEN", 0.30) or 0.30),
        "alnum_ratio_score": float(getattr(settings, "OCR_STAGE_WEIGHT_ALNUM_RATIO", 0.20) or 0.20),
        "anchor_hit_score": float(getattr(settings, "OCR_STAGE_WEIGHT_ANCHOR_HIT", 0.25) or 0.25),
        "field_pattern_score": float(getattr(settings, "OCR_STAGE_WEIGHT_FIELD_PATTERN", 0.25) or 0.25),
    }
    weight_total = sum(weights.values()) or 1.0
    overall_score = (
        (text_len_score * weights["text_len_score"])
        + (alnum_ratio_score * weights["alnum_ratio_score"])
        + (anchor_hit_score * weights["anchor_hit_score"])
        + (field_pattern_score * weights["field_pattern_score"])
    ) / weight_total

    target_field_hits = 0
    top3_anchor_hits = 0
    top3_numeric_hits = 0
    top3_quality_score = 0.0
    if document_type:
        try:
            from app.services.extraction_core.review_metadata import _preparse_document_fields

            parsed = _preparse_document_fields(stripped, document_type)
            top3_fields = [field_name for field_name in critical_fields if field_name in {"bin_tin", "gross_weight", "net_weight"}]
            target_field_hits = sum(
                1
                for field_name in ("bin_tin", "gross_weight", "net_weight")
                if getattr(parsed.get(field_name), "state", None) == "found"
            )
            top3_anchor_hits = sum(
                1
                for field_name in top3_fields
                if bool(getattr(parsed.get(field_name), "anchor_hit", False))
            )
            top3_numeric_hits = sum(
                1
                for field_name in top3_fields
                if getattr(parsed.get(field_name), "state", None) == "found"
                and getattr(parsed.get(field_name), "value_normalized", None) not in (None, "", [], {})
            )
            if top3_fields:
                numeric_weight = float(stage_tuning.get("top3_numeric_weight", 0.7) or 0.7)
                anchor_weight = float(stage_tuning.get("top3_anchor_weight", 0.3) or 0.3)
                weight_sum = max(0.1, numeric_weight + anchor_weight)
                top3_quality_score = min(
                    1.0,
                    (
                        (float(top3_numeric_hits) * numeric_weight)
                        + (float(top3_anchor_hits) * anchor_weight)
                    ) / (float(len(top3_fields)) * weight_sum),
                )
        except Exception:
            target_field_hits = 0
            top3_anchor_hits = 0
            top3_numeric_hits = 0
            top3_quality_score = 0.0

    source_preference_bonus = 0.0
    if stage != "binary_metadata_scrape" and (anchor_hit_score > 0 or field_pattern_score > 0):
        source_preference_bonus += 0.08
    if target_field_hits:
        source_preference_bonus += min(0.18, 0.06 * float(target_field_hits))
    if _stage_threshold_tuning_v1_enabled() and stage != "binary_metadata_scrape" and top3_quality_score > 0:
        source_preference_bonus += min(0.12, 0.10 * float(top3_quality_score))

    selection_score = overall_score + source_preference_bonus

    return {
        "stage": stage,
        "overall_score": round(overall_score, 6),
        "selection_score": round(selection_score, 6),
        "text_len_score": round(text_len_score, 6),
        "alnum_ratio_score": round(alnum_ratio_score, 6),
        "anchor_hit_score": round(anchor_hit_score, 6),
        "field_pattern_score": round(field_pattern_score, 6),
        "source_preference_bonus": round(source_preference_bonus, 6),
        "target_field_hits": int(target_field_hits),
        "top3_anchor_hits": int(top3_anchor_hits),
        "top3_numeric_hits": int(top3_numeric_hits),
        "top3_quality_score": round(top3_quality_score, 6),
        "text_length": total_chars,
    }


def _select_best_extraction_stage(
    stage_candidates: Dict[str, str],
    artifacts: Dict[str, Any],
    document_type: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not stage_candidates:
        artifacts["stage_scores"] = {}
        artifacts["selected_stage"] = None
        artifacts["rejected_stages"] = {}
        return None

    profile: Dict[str, Any] = {}
    critical_fields: List[str] = []
    stage_tuning: Dict[str, Any] = {}
    if document_type:
        try:
            from app.services.extraction_core.profiles import load_profile

            profile = load_profile(document_type) or {}
            critical_fields = list(profile.get("critical_fields") or [])
            stage_tuning = profile.get("stage_tuning") if isinstance(profile.get("stage_tuning"), dict) else {}
        except Exception:
            profile = {}
            critical_fields = []
            stage_tuning = {}

    stage_scores = {
        stage: _score_stage_candidate(stage, text, document_type)
        for stage, text in stage_candidates.items()
    }
    priorities = list(getattr(settings, "OCR_STAGE_SELECTION_PRIORITY", []) or [])
    priority_index = {stage: index for index, stage in enumerate(priorities)}
    top3_fields = [field_name for field_name in critical_fields if field_name in {"bin_tin", "gross_weight", "net_weight"}]
    threshold_tuning_enabled = _stage_threshold_tuning_v1_enabled() and bool(top3_fields)
    binary_min_quality = float(stage_tuning.get("top3_binary_min_quality", 0.58) or 0.58)
    binary_min_target_hits = int(stage_tuning.get("top3_binary_min_target_hits", 1) or 1)
    promotion_min_quality = float(stage_tuning.get("top3_promotion_min_quality", 0.34) or 0.34)
    promotion_min_target_hits = int(stage_tuning.get("top3_promotion_min_target_hits", 1) or 1)

    selection_reason = "highest_selection_score"
    binary_penalty_applied = False
    binary_rejected_for_top3 = False
    promoted_from_stage: Optional[str] = None
    promotion_candidates: List[str] = []
    if _stage_promotion_v1_enabled() and "binary_metadata_scrape" in stage_scores:
        binary_score = stage_scores.get("binary_metadata_scrape") or {}
        binary_low_quality_for_top3 = bool(
            threshold_tuning_enabled
            and (
                float(binary_score.get("top3_quality_score", 0.0) or 0.0) < binary_min_quality
                or int(binary_score.get("target_field_hits", 0) or 0) < binary_min_target_hits
            )
        )
        promotion_candidates = [
            stage
            for stage, score in stage_scores.items()
            if stage != "binary_metadata_scrape"
            and (
                (
                    threshold_tuning_enabled
                    and (
                        int(score.get("target_field_hits", 0) or 0) >= promotion_min_target_hits
                        or (
                            float(score.get("top3_quality_score", 0.0) or 0.0) >= promotion_min_quality
                            and int(score.get("top3_anchor_hits", 0) or 0) > 0
                            and float(score.get("field_pattern_score", 0.0) or 0.0) > 0.0
                        )
                    )
                )
                or score.get("target_field_hits", 0) > 0
                or (
                    score.get("anchor_hit_score", 0.0) > 0
                    and score.get("field_pattern_score", 0.0) > 0
                )
            )
        ]
        if promotion_candidates:
            binary_penalty_applied = True
            binary_rejected_for_top3 = binary_low_quality_for_top3
            penalty = 0.38 if binary_low_quality_for_top3 else 0.24
            stage_scores["binary_metadata_scrape"]["binary_scrape_penalty"] = round(penalty, 6)
            stage_scores["binary_metadata_scrape"]["selection_score"] = round(
                stage_scores["binary_metadata_scrape"].get("selection_score", stage_scores["binary_metadata_scrape"].get("overall_score", 0.0)) - penalty,
                6,
            )
            selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_low_quality_for_top3 else "binary_scrape_penalized"
        else:
            stage_scores["binary_metadata_scrape"]["binary_scrape_penalty"] = 0.0

    if getattr(settings, "OCR_STAGE_SCORER_ENABLED", True):
        ordered_candidates = sorted(
            stage_candidates.items(),
            key=lambda item: (
                stage_scores[item[0]].get("selection_score", stage_scores[item[0]].get("overall_score", 0.0)),
                -priority_index.get(item[0], len(priority_index)),
            ),
            reverse=True,
        )
    else:
        ordered_candidates = sorted(
            stage_candidates.items(),
            key=lambda item: priority_index.get(item[0], len(priority_index)),
        )

    selected_stage, selected_text = ordered_candidates[0]
    if (
        _stage_promotion_v1_enabled()
        and selected_stage == "binary_metadata_scrape"
        and promotion_candidates
    ):
        promoted_stage, _ = max(
            (
                (stage, stage_scores[stage])
                for stage in promotion_candidates
            ),
            key=lambda item: (
                item[1].get("target_field_hits", 0),
                item[1].get("anchor_hit_score", 0.0),
                item[1].get("field_pattern_score", 0.0),
                item[1].get("selection_score", item[1].get("overall_score", 0.0)),
                -priority_index.get(item[0], len(priority_index)),
            ),
        )
        promoted_from_stage = selected_stage
        selected_stage = promoted_stage
        selected_text = stage_candidates[promoted_stage]
        selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_rejected_for_top3 else "anchor_promoted_over_binary_scrape"
    elif (
        _stage_promotion_v1_enabled()
        and binary_penalty_applied
        and selected_stage in promotion_candidates
    ):
        selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_rejected_for_top3 else "anchor_promoted_over_binary_scrape"
    elif (
        threshold_tuning_enabled
        and selected_stage == "binary_metadata_scrape"
        and float(stage_scores[selected_stage].get("top3_quality_score", 0.0) or 0.0) < binary_min_quality
    ):
        selection_reason = "binary_scrape_only_available"

    selected_score = stage_scores[selected_stage].get("selection_score", stage_scores[selected_stage].get("overall_score", 0.0))
    rejected_stages = {}
    for stage, _text in ordered_candidates:
        if stage == selected_stage:
            continue
        rejected_stages[stage] = {
            "reason": (
                "lower_score"
                if stage_scores[stage].get("selection_score", stage_scores[stage].get("overall_score", 0.0)) < selected_score
                else "tie_break_priority"
            ),
            "score": stage_scores[stage].get("selection_score", stage_scores[stage].get("overall_score", 0.0)),
        }

    artifacts["stage_scores"] = stage_scores
    artifacts["selected_stage"] = selected_stage
    artifacts["rejected_stages"] = rejected_stages
    artifacts["stage_selection_rationale"] = {
        "selected_stage": selected_stage,
        "reason": selection_reason,
        "binary_scrape_penalty_applied": binary_penalty_applied,
        "binary_rejected_for_top3": binary_rejected_for_top3,
        "promoted_from_stage": promoted_from_stage,
        "promotion_candidates": promotion_candidates[:6],
        "binary_min_quality": round(binary_min_quality, 4),
        "binary_quality_score": round(float((stage_scores.get("binary_metadata_scrape") or {}).get("top3_quality_score", 0.0) or 0.0), 4),
        "selected_stage_quality_score": round(float(stage_scores[selected_stage].get("top3_quality_score", 0.0) or 0.0), 4),
    }
    return {"stage": selected_stage, "text": selected_text}


async def _extract_text_from_upload(upload_file: Any, document_type: Optional[str] = None) -> Dict[str, Any]:
    """Extract text + normalized OCR artifacts from an uploaded file."""
    filename = getattr(upload_file, "filename", "unknown")
    content_type = getattr(upload_file, "content_type", "unknown")
    hotfix_enabled = _extraction_fallback_hotfix_enabled()

    logger.log(TRACE_LOG_LEVEL, "Starting text extraction for %s (type=%s)", filename, content_type)

    try:
        file_bytes = await upload_file.read()
        await upload_file.seek(0)
        logger.info(f"? Read {len(file_bytes)} bytes from {filename}")
    except Exception as e:
        logger.error(f"? Failed to read file {filename}: {e}", exc_info=True)
        artifacts = _empty_extraction_artifacts_v1()
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="read_upload",
            error="file_read_failed",
        )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="read_upload", text="")

    if not file_bytes:
        logger.warning(f"? Empty file content for {filename}")
        artifacts = _empty_extraction_artifacts_v1()
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="read_upload",
            error="file_bytes_empty",
        )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="read_upload", text="")

    artifacts = _empty_extraction_artifacts_v1()
    text_output = ""
    pypdf_text = ""
    stage_candidates: Dict[str, str] = {}
    detected_input_mime = _detect_input_mime_type(file_bytes, filename, content_type)

    def _choose_stage() -> Optional[Dict[str, Any]]:
        selector = globals().get("_select_best_extraction_stage")
        if callable(selector):
            return selector(stage_candidates, artifacts, document_type)
        if not stage_candidates:
            return None
        stage_name, stage_text = next(iter(stage_candidates.items()))
        artifacts["selected_stage"] = stage_name
        artifacts["stage_scores"] = artifacts.get("stage_scores") or {}
        artifacts["rejected_stages"] = artifacts.get("rejected_stages") or {}
        return {"stage": stage_name, "text": stage_text}

    min_chars_for_skip = max(1, int(getattr(settings, "OCR_MIN_TEXT_CHARS_FOR_SKIP", 1200) or 1200))
    native_text_soft_skip_chars = max(1, int(getattr(settings, "OCR_NATIVE_TEXT_SOFT_SKIP_CHARS", 250) or 250))

    if detected_input_mime == "text/plain":
        logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "plaintext_native")
        text_output = _extract_plaintext_bytes(file_bytes)
        _record_extraction_stage(artifacts, filename=filename, stage="plaintext_native", text=text_output)
    else:
        logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "pdfminer_native")
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            text_output = extract_text(BytesIO(file_bytes))
            _record_extraction_stage(artifacts, filename=filename, stage="pdfminer_native", text=text_output)
        except Exception as exc:
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="pdfminer_native",
                error=str(exc),
            )

        # Fallback plain-text extraction pass if pdfminer is empty/weak
        if len((text_output or "").strip()) < min_chars_for_skip:
            logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "pypdf_native")
            try:
                from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
                reader = PdfReader(BytesIO(file_bytes))
                pieces = []
                for page in reader.pages:
                    try:
                        pieces.append(page.extract_text() or "")
                    except Exception:
                        continue
                pypdf_text = "\n".join(pieces)
                _record_extraction_stage(artifacts, filename=filename, stage="pypdf_native", text=pypdf_text)
                if len((pypdf_text or "").strip()) > len((text_output or "").strip()):
                    text_output = pypdf_text
            except Exception as exc:
                _record_extraction_stage(
                    artifacts,
                    filename=filename,
                    stage="pypdf_native",
                    error=str(exc),
                )

    text_output_clean = (text_output or "").strip()
    if text_output_clean:
        stage_candidates["plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"] = text_output

    # If direct/native text is already sufficient support evidence, do not spend time on OCR.
    native_text_is_usable = len(text_output_clean) >= native_text_soft_skip_chars
    if len(text_output_clean) >= min_chars_for_skip or (
        detected_input_mime == "application/pdf" and native_text_is_usable
    ):
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or ("plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"),
            text=(selection or {}).get("text") or text_output,
        )

    if not text_output_clean:
        _record_extraction_reason_code(artifacts, "PARSER_EMPTY_OUTPUT")

    if not settings.OCR_ENABLED:
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or ("plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"),
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(
            artifacts,
            stage="plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text",
            text="",
        )

    if detected_input_mime == "text/plain":
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "plaintext_native",
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="plaintext_native", text="")

    page_count = 0
    try:
        from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
        page_count = len(PdfReader(BytesIO(file_bytes)).pages)
    except Exception:
        page_count = 1 if detected_input_mime.startswith("image/") else 0

    if page_count > settings.OCR_MAX_PAGES or len(file_bytes) > settings.OCR_MAX_BYTES:
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "native_pdf_text",
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="native_pdf_text", text="")

    viable_ocr_providers = _get_viable_ocr_providers()
    if not viable_ocr_providers:
        _record_extraction_reason_code(artifacts, "OCR_SKIPPED_NO_VIABLE_PROVIDER")
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "native_pdf_text",
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            binary_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=binary_text,
                fallback=True,
            )
            if (binary_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = binary_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or binary_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="native_pdf_text", text="")

    ocr_result = await _try_ocr_providers(file_bytes, filename, content_type)
    ocr_text = ocr_result.get("text") or ""
    ocr_artifacts = ocr_result.get("artifacts") or _empty_extraction_artifacts_v1(raw_text=ocr_text)
    artifacts = _merge_extraction_artifacts(artifacts, ocr_artifacts)
    ocr_text_clean = (ocr_text or "").strip()

    _record_extraction_stage(
        artifacts,
        filename=filename,
        stage="ocr_provider_primary",
        text=ocr_text,
        error_code=ocr_artifacts.get("error_code") if not ocr_text_clean else None,
        error=ocr_artifacts.get("error") if not ocr_text_clean else None,
        fallback=not bool(text_output_clean),
    )

    merged_text = _merge_text_sources(text_output_clean, ocr_text_clean, pypdf_text)

    # If OCR is available, prefer merged evidence to maximize deterministic token recall.
    if ocr_text_clean:
        if not text_output_clean:
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
        stage_candidates["ocr_provider_primary"] = merged_text or ocr_text
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or "ocr_provider_primary",
            text=(selection or {}).get("text") or (merged_text or ocr_text),
        )

    if hotfix_enabled:
        secondary_result = await _try_secondary_ocr_adapter(file_bytes, filename, content_type)
        secondary_text = secondary_result.get("text") or ""
        secondary_artifacts = secondary_result.get("artifacts") or _empty_extraction_artifacts_v1(raw_text=secondary_text)
        artifacts = _merge_extraction_artifacts(artifacts, secondary_artifacts)
        secondary_text_clean = (secondary_text or "").strip()

        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="ocr_secondary",
            text=secondary_text,
            error_code=secondary_artifacts.get("error_code") if not secondary_text_clean else None,
            error=secondary_artifacts.get("error") if not secondary_text_clean else None,
            fallback=True,
        )

        if secondary_text_clean:
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
            stage_candidates["ocr_secondary"] = _merge_text_sources(text_output_clean, secondary_text_clean, ocr_text_clean)
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "ocr_secondary",
                text=(selection or {}).get("text") or _merge_text_sources(text_output_clean, secondary_text_clean, ocr_text_clean),
            )

        binary_text = _scrape_binary_text_metadata(file_bytes)
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="binary_metadata_scrape",
            text=binary_text,
            fallback=True,
        )
        if (binary_text or "").strip():
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
            stage_candidates["binary_metadata_scrape"] = _merge_text_sources(text_output_clean, binary_text)
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                text=(selection or {}).get("text") or _merge_text_sources(text_output_clean, binary_text),
            )

    # No OCR available: return best extracted direct text.
    if text_output_clean:
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or "native_pdf_text",
            text=(selection or {}).get("text") or text_output,
        )

    _record_extraction_reason_code(
        artifacts,
        ocr_artifacts.get("error_code") or "OCR_PROVIDER_UNAVAILABLE",
    )
    _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
    return _finalize_text_extraction_result(artifacts, stage="ocr_provider_primary", text="")


async def _try_secondary_ocr_adapter(file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Attempt a deterministic secondary OCR path that bypasses the factory adapter chain."""
    artifacts = _empty_extraction_artifacts_v1()
    provider_attempts: List[Dict[str, Any]] = []
    plan = _build_provider_runtime_payload_plan("ocr_service", file_bytes, filename, content_type)
    first_group = (plan.get("groups") or [[]])[0] if isinstance(plan.get("groups"), list) else []
    first_payload = first_group[0] if first_group else {}
    artifacts["normalization"] = {
        "original_mime": first_payload.get("input_mime"),
        "normalized_mime": first_payload.get("normalized_mime"),
        "page_count": first_payload.get("page_count"),
        "dpi": first_payload.get("dpi"),
        "bytes_sent": first_payload.get("bytes_sent"),
        "payload_source": first_payload.get("payload_source"),
    }

    record_runtime_failure = None
    record_runtime_success = None
    try:
        from app.services.ocr_diagnostics import record_ocr_runtime_failure, record_ocr_runtime_success
    except Exception:
        record_ocr_runtime_failure = None
        record_ocr_runtime_success = None

    def _record_runtime(
        *,
        provider_name: str,
        error_code: Optional[str],
        error_message: Optional[str],
        stage: str,
        attempt_number: int,
        payload: Dict[str, Any],
        success: bool = False,
    ) -> None:
        if success:
            if callable(record_runtime_success):
                try:
                    record_runtime_success(provider_name, stage=stage)
                except Exception:
                    return
            return
        if callable(record_runtime_failure) and error_code:
            try:
                record_runtime_failure(
                    provider_name,
                    error_code=error_code,
                    error_message=error_message,
                    stage=stage,
                    attempt_number=attempt_number,
                    normalized_mime=payload.get("normalized_mime"),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or 0),
                )
            except Exception:
                return

    if plan.get("error_code"):
        artifacts["provider_attempts"] = [
            {
                "stage": "ocr_secondary",
                "provider": "ocr_service",
                "status": "guardrail_rejected",
                "text_len": 0,
                "error": plan.get("error"),
                "error_code": plan.get("error_code"),
                "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                "normalized_mime": None,
                "retry_used": False,
                "page_index": 1,
                "page_count": 1,
                "bytes_sent": 0,
                "payload_source": "plan_error",
            }
        ]
        artifacts["error_code"] = plan.get("error_code")
        artifacts["error"] = plan.get("error")
        return {"text": "", "artifacts": artifacts}

    try:
        from app.services.ocr_service import get_ocr_service

        service = get_ocr_service()
        if not await service.health_check():
            first_attempt_number = len(provider_attempts) + 1
            unhealthy_payload = dict(first_payload)
            unhealthy_payload["attempt_number"] = first_attempt_number
            provider_attempts.append(
                _build_provider_attempt_record(
                    stage="ocr_secondary",
                    provider_name="ocr_service",
                    payload=unhealthy_payload,
                    text="",
                    status="unhealthy",
                    error_code="OCR_PROVIDER_UNAVAILABLE",
                    error="service_unhealthy",
                )
            )
            _record_runtime(
                provider_name="ocr_service",
                error_code="OCR_PROVIDER_UNAVAILABLE",
                error_message="service_unhealthy",
                stage="ocr_secondary",
                attempt_number=first_attempt_number,
                payload=unhealthy_payload,
            )
            artifacts["provider_attempts"] = provider_attempts
            artifacts["error_code"] = "OCR_PROVIDER_UNAVAILABLE"
            artifacts["error"] = "service_unhealthy"
            return {"text": "", "artifacts": artifacts}

        collected_texts: List[str] = []
        confidences: List[float] = []
        selected_payload = first_payload

        for group in plan.get("groups") or []:
            group_success = False
            for payload in group:
                attempt_number = len(provider_attempts) + 1
                payload = dict(payload)
                payload["attempt_number"] = attempt_number
                logger.info(
                    "validate.extraction.provider_input provider=%s attempt=%s original_mime=%s normalized_mime=%s page_count=%s dpi=%s bytes_sent=%s payload_source=%s retry_used=%s",
                    "ocr_service",
                    attempt_number,
                    payload.get("input_mime"),
                    payload.get("normalized_mime"),
                    payload.get("page_count"),
                    payload.get("dpi"),
                    payload.get("bytes_sent"),
                    payload.get("payload_source"),
                    payload.get("retry_used"),
                )
                result = await asyncio.wait_for(
                    service.extract_text(
                        payload.get("content") or file_bytes,
                        filename=payload.get("filename") or filename,
                        content_type=payload.get("normalized_mime") or content_type,
                    ),
                    timeout=settings.OCR_TIMEOUT_SEC,
                )
                text = result.get("text") or ""
                error = result.get("error")
                success = bool((text or "").strip()) and not error
                error_code = None if success else (result.get("error_code") or (_map_ocr_provider_error_code(error) if error else "OCR_EMPTY_RESULT"))
                provider_attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_secondary",
                        provider_name="ocr_service",
                        payload=payload,
                        text=text,
                        status="success" if success else "empty_output" if not error else "error",
                        error_code=error_code,
                        error=error,
                    )
                )
                logger.info(
                    "validate.extraction.provider_response provider=%s attempt=%s status=%s error_code=%s error=%s text_len=%s retry_used=%s",
                    "ocr_service",
                    attempt_number,
                    provider_attempts[-1]["status"],
                    error_code,
                    error,
                    provider_attempts[-1]["text_len"],
                    provider_attempts[-1]["retry_used"],
                )
                if success:
                    _record_runtime(
                        provider_name="ocr_service",
                        error_code=None,
                        error_message=None,
                        stage="ocr_secondary",
                        attempt_number=attempt_number,
                        payload=payload,
                        success=True,
                    )
                    selected_payload = payload
                    collected_texts.append(text)
                    confidence = result.get("confidence")
                    if isinstance(confidence, (int, float)):
                        confidences.append(float(confidence))
                    group_success = True
                    break
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    "ocr_service",
                    attempt_number,
                    payload.get("normalized_mime"),
                    payload.get("page_count"),
                    payload.get("bytes_sent"),
                    error_code,
                )
                _record_runtime(
                    provider_name="ocr_service",
                    error_code=error_code,
                    error_message=error,
                    stage="ocr_secondary",
                    attempt_number=attempt_number,
                    payload=payload,
                )
                should_retry_normalized_pdf = (
                    str(payload.get("payload_source") or "") == "runtime_pdf_direct"
                    and str(error_code or "") in {"OCR_UNSUPPORTED_FORMAT", "OCR_EMPTY_RESULT"}
                )
                if error_code != "OCR_UNSUPPORTED_FORMAT" and not should_retry_normalized_pdf:
                    break
            if group_success and not plan.get("aggregate_pages"):
                break
    except asyncio.TimeoutError as exc:
        timeout_attempt_number = len(provider_attempts) + 1
        timeout_payload = dict(first_payload)
        timeout_payload["attempt_number"] = timeout_attempt_number
        provider_attempts.append(
            _build_provider_attempt_record(
                stage="ocr_secondary",
                provider_name="ocr_service",
                payload=timeout_payload,
                text="",
                status="timeout",
                error_code="OCR_TIMEOUT",
                error="timeout",
            )
        )
        _record_runtime(
            provider_name="ocr_service",
            error_code="OCR_TIMEOUT",
            error_message=str(exc),
            stage="ocr_secondary",
            attempt_number=timeout_attempt_number,
            payload=timeout_payload,
        )
        artifacts["provider_attempts"] = provider_attempts
        artifacts["error_code"] = "OCR_TIMEOUT"
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}
    except Exception as exc:
        error_attempt_number = len(provider_attempts) + 1
        error_payload = dict(first_payload)
        error_payload["attempt_number"] = error_attempt_number
        error_code = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
        provider_attempts.append(
            _build_provider_attempt_record(
                stage="ocr_secondary",
                provider_name="ocr_service",
                payload=error_payload,
                text="",
                status="error",
                error_code=error_code,
                error=str(exc),
            )
        )
        _record_runtime(
            provider_name="ocr_service",
            error_code=error_code,
            error_message=str(exc),
            stage="ocr_secondary",
            attempt_number=error_attempt_number,
            payload=error_payload,
        )
        artifacts["provider_attempts"] = provider_attempts
        artifacts["error_code"] = error_code
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}

    if collected_texts:
        merged_text = _merge_text_sources(*collected_texts)
        success_artifacts = _empty_extraction_artifacts_v1(
            raw_text=merged_text,
            ocr_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )
        success_artifacts["provider_attempts"] = provider_attempts
        success_artifacts["provider"] = "ocr_service"
        success_artifacts["normalization"] = {
            "original_mime": selected_payload.get("input_mime"),
            "normalized_mime": selected_payload.get("normalized_mime"),
            "page_count": selected_payload.get("page_count"),
            "dpi": selected_payload.get("dpi"),
            "bytes_sent": selected_payload.get("bytes_sent"),
            "payload_source": selected_payload.get("payload_source"),
        }
        return {"text": merged_text, "artifacts": success_artifacts}

    artifacts["provider_attempts"] = provider_attempts
    artifacts["error_code"] = next((attempt.get("error_code") for attempt in provider_attempts if attempt.get("error_code")), None) or "OCR_EMPTY_RESULT"
    artifacts["error"] = next((attempt.get("error") for attempt in provider_attempts if attempt.get("error")), None) or "secondary_ocr_empty_result"
    return {"text": "", "artifacts": artifacts}


async def _try_ocr_providers(file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Try OCR providers in configured order; return text + normalized artifacts."""
    from uuid import uuid4
    from app.ocr.factory import get_ocr_factory

    provider_map = {
        "gdocai": "google_documentai",
        "textract": "aws_textract",
    }
    # Google DocAI is suspended; default fallback is Textract only.
    provider_order = settings.OCR_PROVIDER_ORDER or ["textract"]
    attempts: List[Dict[str, Any]] = []
    record_runtime_failure = None
    record_runtime_success = None

    try:
        from app.services.ocr_diagnostics import record_ocr_runtime_failure, record_ocr_runtime_success
    except Exception:
        record_runtime_failure = None
        record_runtime_success = None

    def _record_runtime(
        *,
        provider_name: str,
        error_code: Optional[str],
        error_message: Optional[str],
        stage: str,
        attempt_number: int,
        payload: Dict[str, Any],
        success: bool = False,
    ) -> None:
        if success:
            if callable(record_runtime_success):
                try:
                    record_runtime_success(provider_name, stage=stage)
                except Exception:
                    return
            return
        if callable(record_runtime_failure) and error_code:
            try:
                record_runtime_failure(
                    provider_name,
                    error_code=error_code,
                    error_message=error_message,
                    stage=stage,
                    attempt_number=attempt_number,
                    normalized_mime=payload.get("normalized_mime"),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or 0),
                )
            except Exception:
                return

    try:
        factory = get_ocr_factory()
        provider_order = list(getattr(factory, "configured_providers", None) or provider_order)
        all_adapters = factory.get_all_adapters()
        adapter_map = {adapter.provider_name: adapter for adapter in all_adapters}

        for provider_name in provider_order:
            full_provider_name = provider_map.get(provider_name, provider_name)
            adapter = adapter_map.get(full_provider_name)
            if not adapter:
                attempt_number = len(attempts) + 1
                attempts.append(
                    {
                        "stage": "ocr_provider_primary",
                        "provider": full_provider_name,
                        "attempt_number": attempt_number,
                        "status": "missing_adapter",
                        "text_len": 0,
                        "error": "missing_adapter",
                        "error_code": "OCR_PROVIDER_UNAVAILABLE",
                        "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                        "normalized_mime": None,
                        "retry_used": False,
                        "page_index": 1,
                        "page_count": 1,
                        "bytes_sent": 0,
                        "payload_source": "missing_adapter",
                    }
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code="OCR_PROVIDER_UNAVAILABLE",
                    error_message="missing_adapter",
                    stage="ocr_provider_primary",
                    attempt_number=attempt_number,
                    payload={},
                )
                continue

            plan = _build_provider_runtime_payload_plan(full_provider_name, file_bytes, filename, content_type)
            first_group = (plan.get("groups") or [[]])[0] if isinstance(plan.get("groups"), list) else []
            first_payload = first_group[0] if first_group else {}
            if plan.get("error_code"):
                attempt_number = len(attempts) + 1
                attempts.append(
                    {
                        "stage": "ocr_provider_primary",
                        "provider": full_provider_name,
                        "attempt_number": attempt_number,
                        "status": "guardrail_rejected",
                        "text_len": 0,
                        "error": plan.get("error"),
                        "error_code": plan.get("error_code"),
                        "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                        "normalized_mime": None,
                        "retry_used": False,
                        "page_index": 1,
                        "page_count": 1,
                        "bytes_sent": 0,
                        "payload_source": "plan_error",
                    }
                )
                continue

            try:
                if not await adapter.health_check():
                    unhealthy_attempt_number = len(attempts) + 1
                    unhealthy_payload = dict(first_payload)
                    unhealthy_payload["attempt_number"] = unhealthy_attempt_number
                    attempts.append(
                        _build_provider_attempt_record(
                            stage="ocr_provider_primary",
                            provider_name=full_provider_name,
                            payload=unhealthy_payload,
                            text="",
                            status="unhealthy",
                            error_code="OCR_PROVIDER_UNAVAILABLE",
                            error="provider_unhealthy",
                        )
                    )
                    _record_runtime(
                        provider_name=full_provider_name,
                        error_code="OCR_PROVIDER_UNAVAILABLE",
                        error_message="provider_unhealthy",
                        stage="ocr_provider_primary",
                        attempt_number=unhealthy_attempt_number,
                        payload=unhealthy_payload,
                    )
                    continue

                collected_texts: List[str] = []
                provider_results: List[Any] = []
                selected_payload = first_payload

                for group in plan.get("groups") or []:
                    group_success = False
                    for payload in group:
                        attempt_number = len(attempts) + 1
                        payload = dict(payload)
                        payload["attempt_number"] = attempt_number
                        logger.info(
                            "validate.extraction.provider_input provider=%s attempt=%s original_mime=%s normalized_mime=%s page_count=%s dpi=%s bytes_sent=%s payload_source=%s retry_used=%s",
                            full_provider_name,
                            attempt_number,
                            payload.get("input_mime"),
                            payload.get("normalized_mime"),
                            payload.get("page_count"),
                            payload.get("dpi"),
                            payload.get("bytes_sent"),
                            payload.get("payload_source"),
                            payload.get("retry_used"),
                        )
                        result = await asyncio.wait_for(
                            adapter.process_file_bytes(
                                payload.get("content") or file_bytes,
                                payload.get("filename") or filename,
                                payload.get("normalized_mime") or content_type,
                                uuid4(),
                            ),
                            timeout=settings.OCR_TIMEOUT_SEC,
                        )
                        text = getattr(result, "full_text", "") or ""
                        error_text = getattr(result, "error", None)
                        success = bool((text or "").strip()) and not error_text
                        error_code = None if success else (_map_ocr_provider_error_code(error_text) if error_text else "OCR_EMPTY_RESULT")
                        attempts.append(
                            _build_provider_attempt_record(
                                stage="ocr_provider_primary",
                                provider_name=full_provider_name,
                                payload=payload,
                                text=text,
                                status="success" if success else "empty_output" if not error_text else "error",
                                error_code=error_code,
                                error=error_text,
                            )
                        )
                        logger.info(
                            "validate.extraction.provider_response provider=%s attempt=%s status=%s error_code=%s error=%s text_len=%s retry_used=%s",
                            full_provider_name,
                            attempt_number,
                            attempts[-1]["status"],
                            error_code,
                            error_text,
                            attempts[-1]["text_len"],
                            attempts[-1]["retry_used"],
                        )
                        if success:
                            _record_runtime(
                                provider_name=full_provider_name,
                                error_code=None,
                                error_message=None,
                                stage="ocr_provider_primary",
                                attempt_number=attempt_number,
                                payload=payload,
                                success=True,
                            )
                            selected_payload = payload
                            collected_texts.append(text)
                            provider_results.append(result)
                            group_success = True
                            break
                        logger.warning(
                            "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                            full_provider_name,
                            attempt_number,
                            payload.get("normalized_mime"),
                            payload.get("page_count"),
                            payload.get("bytes_sent"),
                            error_code,
                        )
                        _record_runtime(
                            provider_name=full_provider_name,
                            error_code=error_code,
                            error_message=error_text,
                            stage="ocr_provider_primary",
                            attempt_number=attempt_number,
                            payload=payload,
                        )
                        should_retry_normalized_pdf = (
                            str(payload.get("payload_source") or "") == "runtime_pdf_direct"
                            and str(error_code or "") in {"OCR_UNSUPPORTED_FORMAT", "OCR_EMPTY_RESULT"}
                        )
                        if error_code != "OCR_UNSUPPORTED_FORMAT" and not should_retry_normalized_pdf:
                            break
                    if group_success and not plan.get("aggregate_pages"):
                        break

                if collected_texts:
                    merged_text = _merge_text_sources(*collected_texts)
                    confidence_values = [
                        float(result.overall_confidence)
                        for result in provider_results
                        if isinstance(getattr(result, "overall_confidence", None), (int, float))
                    ]
                    average_confidence = (
                        sum(confidence_values) / len(confidence_values)
                        if confidence_values
                        else None
                    )
                    artifacts = _build_extraction_artifacts_from_ocr(
                        raw_text=merged_text,
                        provider_result=provider_results[0] if provider_results else None,
                        ocr_confidence=average_confidence,
                    )
                    artifacts["provider_attempts"] = attempts
                    artifacts["provider"] = full_provider_name
                    artifacts["normalization"] = {
                        "original_mime": selected_payload.get("input_mime"),
                        "normalized_mime": selected_payload.get("normalized_mime"),
                        "page_count": selected_payload.get("page_count"),
                        "dpi": selected_payload.get("dpi"),
                        "bytes_sent": selected_payload.get("bytes_sent"),
                        "payload_source": selected_payload.get("payload_source"),
                    }
                    return {"text": merged_text, "artifacts": artifacts}
            except asyncio.TimeoutError as exc:
                timeout_attempt_number = len(attempts) + 1
                timeout_payload = dict(first_payload)
                timeout_payload["attempt_number"] = timeout_attempt_number
                attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_provider_primary",
                        provider_name=full_provider_name,
                        payload=timeout_payload,
                        text="",
                        status="timeout",
                        error_code="OCR_TIMEOUT",
                        error="timeout",
                    )
                )
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    full_provider_name,
                    timeout_attempt_number,
                    timeout_payload.get("normalized_mime"),
                    timeout_payload.get("page_count"),
                    timeout_payload.get("bytes_sent"),
                    "OCR_TIMEOUT",
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code="OCR_TIMEOUT",
                    error_message=str(exc),
                    stage="ocr_provider_primary",
                    attempt_number=timeout_attempt_number,
                    payload=timeout_payload,
                )
                continue
            except Exception as exc:
                error_attempt_number = len(attempts) + 1
                error_payload = dict(first_payload)
                error_payload["attempt_number"] = error_attempt_number
                error_code = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
                attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_provider_primary",
                        provider_name=full_provider_name,
                        payload=error_payload,
                        text="",
                        status="error",
                        error_code=error_code,
                        error=str(exc),
                    )
                )
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    full_provider_name,
                    error_attempt_number,
                    error_payload.get("normalized_mime"),
                    error_payload.get("page_count"),
                    error_payload.get("bytes_sent"),
                    error_code,
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code=error_code,
                    error_message=str(exc),
                    stage="ocr_provider_primary",
                    attempt_number=error_attempt_number,
                    payload=error_payload,
                )
                continue

        artifacts = _empty_extraction_artifacts_v1()
        artifacts["provider_attempts"] = attempts
        last_plan = _build_provider_runtime_payload_plan(provider_map.get(provider_order[0], provider_order[0]), file_bytes, filename, content_type)
        last_group = (last_plan.get("groups") or [[]])[0] if isinstance(last_plan.get("groups"), list) else []
        last_input = last_group[0] if last_group else {}
        artifacts["normalization"] = {
            "original_mime": last_input.get("input_mime"),
            "normalized_mime": last_input.get("normalized_mime"),
            "page_count": last_input.get("page_count"),
            "dpi": last_input.get("dpi"),
            "bytes_sent": last_input.get("bytes_sent"),
            "payload_source": last_input.get("payload_source"),
        }
        attempt_error_code = next(
            (attempt.get("error_code") for attempt in attempts if attempt.get("error_code")),
            None,
        )
        artifacts["error_code"] = attempt_error_code or "OCR_EMPTY_RESULT"
        artifacts["error"] = "no_ocr_provider_returned_text"
        return {"text": "", "artifacts": artifacts}
    except Exception as exc:
        artifacts = _empty_extraction_artifacts_v1()
        artifacts["provider_attempts"] = attempts
        fallback_plan = _build_provider_runtime_payload_plan(provider_map.get(provider_order[0], provider_order[0]), file_bytes, filename, content_type)
        fallback_group = (fallback_plan.get("groups") or [[]])[0] if isinstance(fallback_plan.get("groups"), list) else []
        fallback_input = fallback_group[0] if fallback_group else {}
        artifacts["normalization"] = {
            "original_mime": fallback_input.get("input_mime"),
            "normalized_mime": fallback_input.get("normalized_mime"),
            "page_count": fallback_input.get("page_count"),
            "dpi": fallback_input.get("dpi"),
            "bytes_sent": fallback_input.get("bytes_sent"),
            "payload_source": fallback_input.get("payload_source"),
        }
        artifacts["error_code"] = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}
