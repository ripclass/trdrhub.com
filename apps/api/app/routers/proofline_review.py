"""Internal analyst workspace for Proofline trade cases."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.security import require_sysadmin
from app.database import get_db
from app.models import (
    Company,
    BuyerRequirement,
    Document,
    ProoflineFinding,
    RemediationAction,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseDecision,
    TradeCaseDocument,
    TradeCaseEvent,
    TradeCaseOutcome,
    TradeCaseParty,
    TradeCaseStatus,
    User,
)
from app.schemas.proofline_review import (
    AnalystClaimRequest,
    AnalystCorrectionRequest,
    AnalystDecisionRequest,
    AnalystFindingCreate,
    AnalystFindingUpdate,
    AnalystNoteRequest,
    BuyerRequirementActivationRequest,
    BuyerRequirementCreate,
    BuyerRequirementResponse,
)
from app.services.audit_service import AuditService
from app.services.proofline.review import (
    REVIEW_QUEUE_STATUSES,
    ReviewWorkflowError,
    add_internal_note,
    approve_final_decision,
    claim_case,
    request_correction,
)
from app.services.proofline.reports import ProoflineReportError, generate_proofline_report
from app.services.proofline.feature_flags import require_proofline_enabled
from app.services.proofline.analytics import build_operational_metrics
from app.services.proofline.notifications import notify_customer


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/admin/proofline",
    tags=["Proofline Analyst Queue"],
    dependencies=[Depends(require_proofline_enabled), Depends(require_sysadmin)],
)


def _case_or_404(db: Session, case_id: UUID) -> TradeCase:
    trade_case = (
        db.query(TradeCase)
        .filter(TradeCase.id == case_id, TradeCase.deleted_at.is_(None))
        .first()
    )
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    return trade_case


def _finding_or_404(db: Session, case_id: UUID, finding_id: UUID) -> ProoflineFinding:
    finding = (
        db.query(ProoflineFinding)
        .filter(
            ProoflineFinding.id == finding_id,
            ProoflineFinding.trade_case_id == case_id,
        )
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


def _audit(db: Session, admin: User, action: str, case_id: UUID, values: dict) -> None:
    try:
        AuditService(db).log_action(
            action=action,
            user=admin,
            resource_type="proofline_trade_case",
            resource_id=str(case_id),
            request_data=values,
        )
    except Exception:
        logger.exception("Proofline analyst audit hook failed", extra={"trade_case_id": str(case_id)})


def _audit_requirement(
    db: Session, admin: User, action: str, requirement_id: UUID, values: dict
) -> None:
    try:
        AuditService(db).log_action(
            action=action,
            user=admin,
            resource_type="proofline_buyer_requirement",
            resource_id=str(requirement_id),
            request_data=values,
        )
    except Exception:
        logger.exception(
            "Proofline buyer requirement audit hook failed",
            extra={"buyer_requirement_id": str(requirement_id)},
        )


def _download_url(document: Document) -> Optional[str]:
    try:
        from app.utils.s3_client import get_s3_client

        return get_s3_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": os.getenv("S3_BUCKET_NAME", "lcopilot-documents"),
                "Key": document.s3_key,
            },
            ExpiresIn=3600,
        )
    except Exception:
        return None


@router.get("")
def list_proofline_queue(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer: Optional[str] = None,
    service_package: Optional[str] = None,
    reviewer: Optional[UUID] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    query = (
        db.query(TradeCase, Company, User)
        .join(Company, Company.id == TradeCase.company_id)
        .outerjoin(User, User.id == TradeCase.customer_user_id)
        .filter(TradeCase.deleted_at.is_(None))
    )
    query = query.filter(
        TradeCase.status == status_filter
        if status_filter
        else TradeCase.status.in_(REVIEW_QUEUE_STATUSES)
    )
    if customer:
        token = f"%{customer.strip()}%"
        query = query.filter((Company.name.ilike(token)) | (User.email.ilike(token)))
    if service_package:
        query = query.filter(TradeCase.service_package_id == service_package)
    if reviewer:
        query = query.filter(TradeCase.reviewer_user_id == reviewer)
    rows = query.order_by(TradeCase.updated_at.asc()).limit(limit).all()
    items = []
    for trade_case, company, customer_user in rows:
        finding_count = (
            db.query(ProoflineFinding)
            .filter(
                ProoflineFinding.trade_case_id == trade_case.id,
                ProoflineFinding.status.in_(("open", "customer_action_required", "unable_to_resolve")),
            )
            .count()
        )
        items.append({
            "id": str(trade_case.id),
            "case_reference": trade_case.case_reference,
            "title": trade_case.title,
            "status": trade_case.status,
            "payment_arrangement": trade_case.payment_arrangement,
            "service_package_id": trade_case.service_package_id,
            "recommended_decision": trade_case.recommended_decision,
            "reviewer_user_id": str(trade_case.reviewer_user_id) if trade_case.reviewer_user_id else None,
            "customer_name": company.name,
            "customer_email": customer_user.email if customer_user else company.contact_email,
            "finding_count": finding_count,
            "submitted_at": trade_case.submitted_at.isoformat() if trade_case.submitted_at else None,
            "updated_at": trade_case.updated_at.isoformat() if trade_case.updated_at else None,
        })
    return {"count": len(items), "items": items}


@router.get("/metrics")
def get_proofline_operational_metrics(
    days: int = Query(default=30, ge=1, le=365),
    company_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    """Return case-level operational metrics without document contents."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    case_query = db.query(TradeCase).filter(
        TradeCase.deleted_at.is_(None),
        TradeCase.created_at >= since,
    )
    if company_id is not None:
        case_query = case_query.filter(TradeCase.company_id == company_id)
    cases = case_query.all()
    case_ids = [item.id for item in cases]
    findings = []
    outcomes = []
    if case_ids:
        findings = (
            db.query(ProoflineFinding)
            .filter(ProoflineFinding.trade_case_id.in_(case_ids))
            .all()
        )
        outcomes = (
            db.query(TradeCaseOutcome)
            .filter(TradeCaseOutcome.trade_case_id.in_(case_ids))
            .all()
        )
    return build_operational_metrics(
        cases=cases,
        findings=findings,
        outcomes=outcomes,
        period_days=days,
    )


@router.get("/buyer-requirements", response_model=list[BuyerRequirementResponse])
def list_buyer_requirements(
    company_id: UUID,
    buyer_reference: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
) -> list[BuyerRequirementResponse]:
    query = db.query(BuyerRequirement).filter(BuyerRequirement.company_id == company_id)
    if buyer_reference:
        query = query.filter(BuyerRequirement.buyer_reference == buyer_reference.strip())
    if not include_inactive:
        query = query.filter(BuyerRequirement.is_active.is_(True))
    rows = query.order_by(
        BuyerRequirement.buyer_reference.asc(),
        BuyerRequirement.title.asc(),
        BuyerRequirement.version.desc(),
    ).all()
    return [BuyerRequirementResponse.model_validate(item) for item in rows]


@router.post(
    "/buyer-requirements",
    response_model=BuyerRequirementResponse,
    status_code=201,
)
def create_buyer_requirement(
    payload: BuyerRequirementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
) -> BuyerRequirementResponse:
    if db.query(Company.id).filter(Company.id == payload.company_id).first() is None:
        raise HTTPException(status_code=404, detail="Company workspace not found")
    values = payload.model_dump()
    values["buyer_reference"] = values["buyer_reference"].strip()
    requirement = BuyerRequirement(
        id=uuid.uuid4(),
        created_by_user_id=admin.id,
        **values,
    )
    db.add(requirement)
    try:
        db.commit()
        db.refresh(requirement)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This buyer requirement version already exists",
        )
    _audit_requirement(
        db,
        admin,
        "proofline_buyer_requirement_created",
        requirement.id,
        {
            "company_id": str(requirement.company_id),
            "buyer_reference": requirement.buyer_reference,
            "version": requirement.version,
        },
    )
    return BuyerRequirementResponse.model_validate(requirement)


@router.patch(
    "/buyer-requirements/{requirement_id}/activation",
    response_model=BuyerRequirementResponse,
)
def set_buyer_requirement_activation(
    requirement_id: UUID,
    payload: BuyerRequirementActivationRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
) -> BuyerRequirementResponse:
    requirement = (
        db.query(BuyerRequirement)
        .filter(BuyerRequirement.id == requirement_id)
        .first()
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Buyer requirement not found")
    requirement.is_active = payload.is_active
    requirement.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(requirement)
    _audit_requirement(
        db,
        admin,
        "proofline_buyer_requirement_activation_changed",
        requirement.id,
        {"is_active": requirement.is_active, "version": requirement.version},
    )
    return BuyerRequirementResponse.model_validate(requirement)


@router.get("/{case_id}")
def get_proofline_review_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    parties = db.query(TradeCaseParty).filter(TradeCaseParty.trade_case_id == case_id).all()
    documents = (
        db.query(TradeCaseDocument, Document)
        .join(Document, Document.id == TradeCaseDocument.document_id)
        .filter(TradeCaseDocument.trade_case_id == case_id)
        .order_by(TradeCaseDocument.logical_key, TradeCaseDocument.version_number.desc())
        .all()
    )
    checks = db.query(TradeCaseCheckRun).filter(TradeCaseCheckRun.trade_case_id == case_id).all()
    findings = db.query(ProoflineFinding).filter(ProoflineFinding.trade_case_id == case_id).all()
    actions = db.query(RemediationAction).filter(RemediationAction.trade_case_id == case_id).all()
    decisions = (
        db.query(TradeCaseDecision)
        .filter(TradeCaseDecision.trade_case_id == case_id)
        .order_by(TradeCaseDecision.version_number.desc())
        .all()
    )
    events = (
        db.query(TradeCaseEvent)
        .filter(TradeCaseEvent.trade_case_id == case_id)
        .order_by(TradeCaseEvent.occurred_at.desc())
        .limit(200)
        .all()
    )
    return {
        "case": {
            "id": str(trade_case.id),
            "case_reference": trade_case.case_reference,
            "title": trade_case.title,
            "status": trade_case.status,
            "payment_arrangement": trade_case.payment_arrangement,
            "service_package_id": trade_case.service_package_id,
            "recommended_decision": trade_case.recommended_decision,
            "final_decision": trade_case.final_decision,
            "reviewer_user_id": str(trade_case.reviewer_user_id) if trade_case.reviewer_user_id else None,
            "origin_country": trade_case.origin_country,
            "destination_country": trade_case.destination_country,
            "currency": trade_case.currency,
            "amount": str(trade_case.amount) if trade_case.amount is not None else None,
            "payment_terms": trade_case.payment_terms,
            "transaction_details": trade_case.transaction_details or {},
            "correction_rounds_used": trade_case.correction_rounds_used,
        },
        "parties": [{
            "id": str(item.id), "role": item.role, "name": item.name,
            "country_code": item.country_code, "identifiers": item.identifiers or {},
        } for item in parties],
        "documents": [{
            "id": str(association.id),
            "document_id": str(document.id),
            "logical_key": association.logical_key,
            "document_type": association.document_type,
            "filename": document.original_filename,
            "version": association.version_number,
            "correction_round": association.correction_round,
            "is_current": association.is_current,
            "ocr_confidence": document.ocr_confidence,
            "extracted_fields": document.extracted_fields or {},
            "download_url": _download_url(document),
        } for association, document in documents],
        "checks": [{
            "id": str(item.id), "module": item.module, "state": item.state,
            "applicable": item.applicable, "required": item.required,
            "summary": (item.result_summary or {}).get("summary"),
            "safe_error_message": item.safe_error_message,
        } for item in checks],
        "findings": [{
            "id": str(item.id), "source_module": item.source_module,
            "category": item.category, "severity": item.severity, "title": item.title,
            "explanation": item.explanation, "expected": item.expected,
            "observed": item.observed, "suggested_correction": item.suggested_correction,
            "visibility": item.visibility, "status": item.status,
            "reviewer_decision": item.reviewer_decision,
            "rule_reference": item.rule_reference,
            "evidence_references": item.evidence_references or [],
        } for item in findings],
        "actions": [{
            "id": str(item.id), "finding_id": str(item.finding_id),
            "requested_action": item.requested_action, "responsible_party": item.responsible_party,
            "requested_document_type": item.requested_document_type, "status": item.status,
            "correction_round": item.correction_round, "customer_response": item.customer_response,
            "resolution_notes": item.resolution_notes,
        } for item in actions],
        "decisions": [{
            "id": str(item.id), "version": item.version_number, "decision_type": item.decision_type,
            "decision": item.decision, "summary": item.summary, "reason": item.reason,
            "override_reason": item.override_reason,
            "reviewer_user_id": str(item.reviewer_user_id) if item.reviewer_user_id else None,
            "decided_at": item.decided_at.isoformat() if item.decided_at else None,
        } for item in decisions],
        "timeline": [{
            "id": str(item.id), "event_type": item.event_type, "from_status": item.from_status,
            "to_status": item.to_status, "actor_type": item.actor_type, "reason": item.reason,
            "details": item.details or {}, "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None,
        } for item in events],
    }


@router.post("/{case_id}/claim")
def claim_proofline_case(
    case_id: UUID,
    payload: AnalystClaimRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    try:
        claim_case(db, trade_case, reviewer_user_id=admin.id, force=payload.force)
        db.commit()
    except ReviewWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit(db, admin, "proofline_case_claimed", case_id, {"force": payload.force})
    return {"reviewer_user_id": str(trade_case.reviewer_user_id)}


@router.post("/{case_id}/notes")
def create_proofline_internal_note(
    case_id: UUID,
    payload: AnalystNoteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    try:
        event = add_internal_note(db, trade_case, reviewer_user_id=admin.id, note=payload.note)
        db.commit()
    except ReviewWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit(db, admin, "proofline_internal_note_added", case_id, {"event_id": str(event.id)})
    return {"id": str(event.id)}


@router.patch("/{case_id}/findings/{finding_id}")
def update_proofline_finding(
    case_id: UUID,
    finding_id: UUID,
    payload: AnalystFindingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    finding = _finding_or_404(db, case_id, finding_id)
    try:
        from app.services.proofline.review import ensure_reviewable_status
        ensure_reviewable_status(trade_case.status)
        values = payload.model_dump(exclude_unset=True)
        if "status" in values and values["status"] is not None:
            values["status"] = values["status"].value
        for field, value in values.items():
            setattr(finding, field, value)
        finding.reviewed_by_user_id = admin.id
        finding.updated_at = datetime.now(timezone.utc)
        db.commit()
    except ReviewWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit(db, admin, "proofline_finding_reviewed", case_id, {"finding_id": str(finding_id), "fields": sorted(values)})
    return {"id": str(finding.id), "status": finding.status, "visibility": finding.visibility}


@router.post("/{case_id}/findings")
def add_proofline_finding(
    case_id: UUID,
    payload: AnalystFindingCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    from app.services.proofline.review import ensure_reviewable_status
    try:
        ensure_reviewable_status(trade_case.status)
    except ReviewWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    finding = ProoflineFinding(
        id=uuid.uuid4(), company_id=trade_case.company_id, trade_case_id=case_id,
        source_module="human_reviewer", source_finding_id=f"HUMAN-{uuid.uuid4()}",
        source_detail_reference={"reviewer_user_id": str(admin.id)},
        is_automated=False, status="open", created_by_user_id=admin.id,
        reviewed_by_user_id=admin.id, evidence_references=[], rule_reference=None,
        **payload.model_dump(),
    )
    db.add(finding)
    db.commit()
    _audit(db, admin, "proofline_finding_added", case_id, {"finding_id": str(finding.id)})
    return {"id": str(finding.id)}


@router.post("/{case_id}/corrections")
def request_proofline_correction(
    case_id: UUID,
    payload: AnalystCorrectionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    try:
        finding = _finding_or_404(db, case_id, UUID(payload.finding_id))
        action = request_correction(
            db, trade_case, finding, reviewer_user_id=admin.id,
            requested_action=payload.requested_action,
            responsible_party=payload.responsible_party,
            requested_document_type=payload.requested_document_type,
            due_at=payload.due_at,
        )
        db.commit()
    except (ReviewWorkflowError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit(db, admin, "proofline_correction_requested", case_id, {"action_id": str(action.id), "finding_id": payload.finding_id})
    notify_customer(db, trade_case, event="action_required")
    return {"id": str(action.id), "status": action.status, "correction_round": action.correction_round}


@router.post("/{case_id}/decisions")
def decide_proofline_case(
    case_id: UUID,
    payload: AnalystDecisionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    trade_case = _case_or_404(db, case_id)
    report = None
    try:
        decision = approve_final_decision(
            db, trade_case, reviewer_user_id=admin.id,
            decision=payload.decision, summary=payload.summary, reason=payload.reason,
            override_reason=payload.override_reason, idempotency_key=payload.idempotency_key,
        )
        if trade_case.status in {
            TradeCaseStatus.CLEARED.value,
            TradeCaseStatus.CONDITIONALLY_CLEARED.value,
            TradeCaseStatus.BLOCKED.value,
        }:
            report = generate_proofline_report(
                db,
                trade_case=trade_case,
                decision=decision,
                reviewer=admin,
            )
        db.commit()
    except ProoflineReportError as exc:
        db.rollback()
        logger.exception(
            "Proofline final report generation failed",
            extra={"trade_case_id": str(case_id)},
        )
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit(db, admin, "proofline_final_decision_approved", case_id, {
        "decision": decision.decision,
        "version": decision.version_number,
        "report_id": str(report.id) if report else None,
        "report_version": report.report_version if report else None,
    })
    if report is not None:
        notify_customer(db, trade_case, event="final_report_ready")
    return {
        "id": str(decision.id),
        "decision": decision.decision,
        "version": decision.version_number,
        "status": trade_case.status,
        "report_id": str(report.id) if report else None,
        "report_version": report.report_version if report else None,
    }


__all__ = ["router"]
