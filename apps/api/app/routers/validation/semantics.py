from typing import Any, Dict, Optional

EXTRACTION_STATUS = {"success", "partial", "failed"}
COMPLIANCE_STATUS = {"clean", "warning", "reject"}
PIPELINE_VERIFICATION_STATUS = {"VERIFIED", "UNVERIFIED"}


def normalize_extraction_status(value: Optional[str]) -> str:
    token = str(value or "").strip().lower()
    if token in {"success"}:
        return "success"
    if token in {"partial", "warning", "pending", "text_only"}:
        return "partial"
    if token in {"failed", "error", "empty"}:
        return "failed"
    return "partial"


def compliance_status_from_validation(validation_status: Optional[str], critical_count: int = 0, major_count: int = 0) -> str:
    status = str(validation_status or "").strip().lower()
    if status in {"partial", "non_compliant"} or critical_count > 0:
        return "reject"
    if major_count > 0 or status in {"mostly_compliant", "warning"}:
        return "warning"
    return "clean"


def require_failed_reason(extraction_status: str, failed_reason: Optional[str]) -> None:
    if extraction_status == "failed" and not str(failed_reason or "").strip():
        raise ValueError("failed_reason is required when extraction_status=failed")


def assert_no_status_cross_mix(doc: Dict[str, Any]) -> None:
    extraction_status = doc.get("extraction_status")
    compliance_status = doc.get("compliance_status")
    if extraction_status and extraction_status not in EXTRACTION_STATUS:
        raise ValueError(f"Invalid extraction_status: {extraction_status}")
    if compliance_status and compliance_status not in COMPLIANCE_STATUS:
        raise ValueError(f"Invalid compliance_status: {compliance_status}")

    # Prevent compliance tokens inside extraction status by contract
    if extraction_status in COMPLIANCE_STATUS:
        raise ValueError("Cross-mixed status: compliance status token used in extraction_status")


def mark_unverified(payload: Dict[str, Any], reason: str) -> Dict[str, Any]:
    payload["pipeline_verification_status"] = "UNVERIFIED"
    reasons = payload.get("pipeline_verification_fail_reasons") or []
    reasons.append(reason)
    payload["pipeline_verification_fail_reasons"] = reasons
    return payload
