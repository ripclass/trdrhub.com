from __future__ import annotations

from datetime import datetime
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def get_active_overlay(bank_id: str, db_session) -> Optional[Dict[str, Any]]:
    """Load active bank policy overlay (best-effort)."""
    try:
        from app.models.bank_policy import BankPolicyOverlay

        bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
        overlay = db_session.query(BankPolicyOverlay).filter(
            BankPolicyOverlay.bank_id == bank_uuid,
            BankPolicyOverlay.active == True,
        ).first()

        if not overlay:
            return None
        return {
            "id": str(overlay.id),
            "version": overlay.version,
            "config": overlay.config,
        }
    except Exception as e:
        logger.warning(f"Failed to load policy overlay for bank {bank_id}: {e}")
        return None


def get_active_exceptions(bank_id: str, db_session) -> List[Dict[str, Any]]:
    """Load active bank policy exceptions (best-effort)."""
    try:
        from app.models.bank_policy import BankPolicyException

        bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
        exceptions = db_session.query(BankPolicyException).filter(
            BankPolicyException.bank_id == bank_uuid
        ).filter(
            (BankPolicyException.expires_at.is_(None))
            | (BankPolicyException.expires_at > datetime.utcnow())
        ).all()

        return [
            {
                "id": str(e.id),
                "rule_code": e.rule_code,
                "scope": e.scope,
                "effect": e.effect,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            }
            for e in exceptions
        ]
    except Exception as e:
        logger.warning(f"Failed to load policy exceptions for bank {bank_id}: {e}")
        return []


def apply_policy_overlay(
    validation_results: List[Dict[str, Any]],
    overlay: Optional[Dict[str, Any]],
    document_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply overlay severity adjustments without changing result schema."""
    if not overlay or not overlay.get("config"):
        return validation_results

    config = overlay["config"]
    stricter_checks = config.get("stricter_checks", {})
    thresholds = config.get("thresholds", {})

    max_date_slippage = stricter_checks.get("max_date_slippage_days")
    if max_date_slippage is not None:
        for result in validation_results:
            if "date" in result.get("rule", "").lower() or "date" in result.get("title", "").lower():
                pass

    severity_override = thresholds.get("discrepancy_severity_override")
    if severity_override:
        for result in validation_results:
            if not result.get("passed", False):
                result["severity"] = severity_override
                result["policy_override"] = True

    return validation_results


def apply_policy_exceptions(
    validation_results: List[Dict[str, Any]],
    exceptions: List[Dict[str, Any]],
    document_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply matching policy exceptions to failed rules only."""
    if not exceptions:
        return validation_results

    for result in validation_results:
        if result.get("passed", False):
            continue

        rule_code = result.get("rule", "")
        for exception in exceptions:
            if exception["rule_code"] != rule_code:
                continue

            scope = exception.get("scope", {})
            matches_scope = True
            if scope.get("client"):
                doc_client = document_data.get("client_name") or document_data.get("client")
                if doc_client != scope["client"]:
                    matches_scope = False
            if scope.get("branch") and matches_scope:
                if document_data.get("branch") != scope["branch"]:
                    matches_scope = False
            if scope.get("product") and matches_scope:
                if document_data.get("product") != scope["product"]:
                    matches_scope = False
            if not matches_scope:
                continue

            effect = exception.get("effect", "waive")
            if effect == "waive":
                result["passed"] = True
                result["waived"] = True
                result["waived_reason"] = f"Policy exception: {exception.get('reason', 'N/A')}"
                result["severity"] = "info"
            elif effect == "downgrade":
                current_severity = result.get("severity", "critical")
                if current_severity == "critical":
                    result["severity"] = "major"
                elif current_severity == "major":
                    result["severity"] = "minor"
                result["exception_applied"] = True
            elif effect == "override":
                result["passed"] = True
                result["overridden"] = True
                result["override_reason"] = f"Policy exception: {exception.get('reason', 'N/A')}"

            result["exception_id"] = exception.get("id")
            break

    return validation_results


def _build_policy_metrics(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    discrepancies = [r for r in validation_results if not r.get("passed", False)]
    severity = {}
    for result in discrepancies:
        level = result.get("severity", "unknown")
        severity[level] = severity.get(level, 0) + 1
    return {
        "discrepancies": len(discrepancies),
        "severity": severity,
    }


def _collect_exception_applications(validation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    applications = []
    for result in validation_results:
        if not (result.get("exception_id") or result.get("waived") or result.get("overridden") or result.get("exception_applied")):
            continue

        effect = None
        if result.get("waived"):
            effect = "waive"
        elif result.get("overridden"):
            effect = "override"
        elif result.get("exception_applied"):
            effect = "downgrade"

        exception_id = result.get("exception_id")
        rule_code = result.get("rule", "")
        if exception_id and rule_code:
            applications.append({
                "exception_id": exception_id,
                "rule_code": rule_code,
                "effect": effect,
            })
    return applications


def _write_policy_application_events(
    *,
    db_session,
    bank_id: str,
    validation_session_id: Optional[str],
    user_id: Optional[str],
    overlay: Optional[Dict[str, Any]],
    exception_applications: List[Dict[str, Any]],
    metrics_before: Dict[str, Any],
    metrics_after: Dict[str, Any],
    result_summary: Dict[str, Any],
    document_type: Optional[str],
    processing_time_ms: int,
) -> None:
    if not validation_session_id or not user_id:
        return

    application_type = "both" if overlay and exception_applications else ("overlay" if overlay else ("exception" if exception_applications else "none"))
    if application_type == "none":
        return

    from app.models.bank_policy import BankPolicyApplicationEvent

    bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
    session_uuid = UUID(validation_session_id) if isinstance(validation_session_id, str) else validation_session_id
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

    before_severity = metrics_before["severity"]
    after_severity = metrics_after["severity"]
    severity_changes = {}
    for severity in set(before_severity) | set(after_severity):
        delta = after_severity.get(severity, 0) - before_severity.get(severity, 0)
        if delta:
            severity_changes[severity] = delta

    overlay_id = overlay.get("id") if overlay else None
    overlay_version = overlay.get("version") if overlay else None

    if overlay:
        overlay_uuid = UUID(overlay_id) if isinstance(overlay_id, str) else overlay_id
        db_session.add(BankPolicyApplicationEvent(
            validation_session_id=session_uuid,
            bank_id=bank_uuid,
            user_id=user_uuid,
            overlay_id=overlay_uuid,
            overlay_version=overlay_version,
            application_type="overlay" if not exception_applications else "both",
            discrepancies_before=metrics_before["discrepancies"],
            discrepancies_after=metrics_after["discrepancies"],
            severity_changes=severity_changes,
            result_summary=result_summary,
            document_type=document_type,
            processing_time_ms=processing_time_ms,
        ))

    for exc_app in exception_applications:
        exception_uuid = UUID(exc_app["exception_id"]) if isinstance(exc_app["exception_id"], str) else exc_app["exception_id"]
        db_session.add(BankPolicyApplicationEvent(
            validation_session_id=session_uuid,
            bank_id=bank_uuid,
            user_id=user_uuid,
            overlay_id=UUID(overlay_id) if overlay_id and isinstance(overlay_id, str) else overlay_id,
            overlay_version=overlay_version,
            exception_id=exception_uuid,
            application_type="exception" if not overlay else "both",
            rule_code=exc_app["rule_code"],
            exception_effect=exc_app["effect"],
            discrepancies_before=metrics_before["discrepancies"],
            discrepancies_after=metrics_after["discrepancies"],
            severity_changes=severity_changes,
            result_summary=result_summary,
            document_type=document_type,
            processing_time_ms=processing_time_ms,
        ))

    db_session.commit()


async def apply_bank_policy(
    validation_results: List[Dict[str, Any]],
    bank_id: str,
    document_data: Dict[str, Any],
    db_session,
    validation_session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply bank policy and write audit events as best-effort side effects."""
    if not bank_id:
        return validation_results

    try:
        start_time = time.time()
        metrics_before = _build_policy_metrics(validation_results)

        overlay = get_active_overlay(bank_id, db_session)
        if overlay:
            validation_results = apply_policy_overlay(validation_results, overlay, document_data)

        exceptions = get_active_exceptions(bank_id, db_session)
        if exceptions:
            validation_results = apply_policy_exceptions(validation_results, exceptions, document_data)

        exception_applications = _collect_exception_applications(validation_results)
        metrics_after = _build_policy_metrics(validation_results)

        rules_affected: List[str] = []
        severity_upgrades = 0
        severity_downgrades = 0
        waived_rules = 0
        overridden_rules = 0
        for result in validation_results:
            if result.get("waived"):
                waived_rules += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("overridden"):
                overridden_rules += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("exception_applied"):
                severity_downgrades += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("policy_override"):
                severity_upgrades += 1
                rules_affected.append(result.get("rule", ""))

        result_summary = {
            "rules_affected": list(set(rules_affected)),
            "severity_upgrades": severity_upgrades,
            "severity_downgrades": severity_downgrades,
            "waived_rules": waived_rules,
            "overridden_rules": overridden_rules,
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        try:
            _write_policy_application_events(
                db_session=db_session,
                bank_id=bank_id,
                validation_session_id=validation_session_id,
                user_id=user_id,
                overlay=overlay,
                exception_applications=exception_applications,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                result_summary=result_summary,
                document_type=document_data.get("document_type"),
                processing_time_ms=processing_time_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to log policy application event: {e}", exc_info=True)
            db_session.rollback()

        return validation_results
    except Exception as e:
        logger.error(f"Failed to apply bank policy: {e}", exc_info=True)
        return validation_results
