"""Customer-facing Proofline trade-case endpoints."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import (
    CompanyMember,
    Document,
    MemberRole,
    MemberStatus,
    RemediationAction,
    TradeCaseDocument,
    TradeCaseStatus,
    User,
)
from app.repositories.proofline import ProoflineRepository
from app.schemas.proofline import (
    TradeCaseCreate,
    TradeCaseDetailResponse,
    TradeCaseDocumentAssociate,
    TradeCaseDocumentResponse,
    TradeCaseListResponse,
    TradeCasePartyCreate,
    TradeCasePartyResponse,
    TradeCaseSummaryResponse,
    TradeCaseUpdate,
    RemediationResponseRequest,
)
from app.services.audit_service import AuditService
from app.services.proofline.documents import (
    DuplicateCaseDocument,
    ProoflineDocumentAccessError,
    associate_document,
    list_case_documents,
)
from app.services.proofline.uploads import ProoflineUploadError, ingest_case_document
from app.services.proofline.processing import (
    SubmissionValidationError,
    load_case_context,
    process_trade_case_by_id,
    validate_submission_context,
)
from app.services.proofline.state import InvalidTradeCaseTransition, transition_case
from app.services.proofline.remediation import (
    RemediationWorkflowError,
    respond_to_action,
    submit_corrections,
)
from app.services.proofline.billing import (
    ProoflineCheckoutError,
    is_checkout_enabled as is_proofline_checkout_enabled,
    quote_for_case,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proofline/cases", tags=["proofline"])


def _company_id(current_user: User) -> UUID:
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A company workspace is required to use Proofline",
        )
    return company_id


def ensure_case_write_access(db: Session, current_user: User) -> None:
    """Enforce current CompanyMember write semantics, with legacy-user continuity."""
    company_id = _company_id(current_user)
    member = (
        db.query(CompanyMember)
        .filter(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == current_user.id,
            CompanyMember.status == MemberStatus.ACTIVE.value,
        )
        .first()
    )
    if member is not None and member.role == MemberRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only Proofline access",
        )
    if member is None and str(getattr(current_user, "role", "")).lower() == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only Proofline access",
        )


def _audit_action(
    *, db: Session, current_user: User, action: str, trade_case_id: UUID, values: dict
) -> None:
    """Call the existing audit hook without including trade-document content."""
    try:
        AuditService(db).log_action(
            action=action,
            user=current_user,
            resource_type="proofline_trade_case",
            resource_id=str(trade_case_id),
            request_data=values,
        )
    except Exception:
        logger.exception(
            "Proofline audit hook failed",
            extra={"trade_case_id": str(trade_case_id), "action": action},
        )


def _case_response(
    repository: ProoflineRepository, trade_case, *, detail: bool
) -> TradeCaseSummaryResponse | TradeCaseDetailResponse:
    document_count, finding_counts = repository.summary_counts(
        company_id=trade_case.company_id, case_id=trade_case.id
    )
    values = {
        "id": trade_case.id,
        "case_reference": trade_case.case_reference,
        "company_id": trade_case.company_id,
        "title": trade_case.title,
        "status": trade_case.status,
        "payment_arrangement": trade_case.payment_arrangement,
        "service_package_id": trade_case.service_package_id,
        "payment_status": getattr(trade_case, "payment_status", None),
        "amount_paid_cents": getattr(trade_case, "amount_paid_cents", None),
        "credit_amount_cents": getattr(trade_case, "credit_amount_cents", 0) or 0,
        "payment_currency": getattr(trade_case, "payment_currency", None),
        "recommended_decision": trade_case.recommended_decision,
        "final_decision": trade_case.final_decision,
        "currency": trade_case.currency,
        "amount": trade_case.amount,
        "origin_country": trade_case.origin_country,
        "destination_country": trade_case.destination_country,
        "document_count": document_count,
        "finding_counts": finding_counts,
        "created_at": trade_case.created_at,
        "updated_at": trade_case.updated_at,
    }
    if detail:
        snapshot = repository.customer_snapshot(
            company_id=trade_case.company_id, case_id=trade_case.id
        )
        parties = [
            {
                "id": party.id,
                "role": party.role,
                "name": party.name,
                "country_code": party.country_code,
                "identifiers": party.identifiers or {},
            }
            for party in snapshot["parties"]
        ]
        documents = []
        for association, document in snapshot.get("documents", []):
            extracted = getattr(document, "extracted_fields", None) or {}
            documents.append(
                {
                    "id": association.id,
                    "document_id": association.document_id,
                    "logical_key": association.logical_key,
                    "document_type": association.document_type,
                    "filename": document.original_filename,
                    "version": association.version_number,
                    "supersedes_id": association.supersedes_id,
                    "correction_round": association.correction_round,
                    "is_current": association.is_current,
                    "extraction_status": extracted.get("extraction_status")
                    if isinstance(extracted, dict)
                    else None,
                    "created_at": association.created_at,
                }
            )
        checks = []
        for check in snapshot["checks"]:
            result_summary = check.result_summary or {}
            checks.append(
                {
                    "id": check.id,
                    "module": check.module,
                    "state": check.state,
                    "applicable": check.applicable,
                    "applicability_reason": check.applicability_reason,
                    "source_record_type": check.source_record_type,
                    "source_record_id": check.source_record_id,
                    "summary": result_summary.get("summary")
                    if isinstance(result_summary, dict)
                    else None,
                    "completed_at": check.completed_at,
                }
            )
        findings = [
            {
                "id": finding.id,
                "source_module": finding.source_module,
                "source_finding_id": finding.source_finding_id,
                "category": finding.category,
                "severity": finding.severity,
                "title": finding.title,
                "explanation": finding.explanation,
                "affected_entity": finding.affected_entity,
                "affected_document_id": finding.affected_document_id,
                "affected_field": finding.affected_field,
                "expected": finding.expected,
                "observed": finding.observed,
                "suggested_correction": finding.suggested_correction,
                "automated": finding.is_automated,
                "visibility": finding.visibility,
                "status": finding.status,
                "reviewer_decision": finding.reviewer_decision,
                "rule_reference": finding.rule_reference,
                "evidence_references": finding.evidence_references or [],
                "created_at": finding.created_at,
                "updated_at": finding.updated_at,
            }
            for finding in snapshot["findings"]
        ]
        actions = [
            {
                "id": action.id,
                "finding_id": action.finding_id,
                "requested_action": action.requested_action,
                "responsible_party": action.responsible_party,
                "requested_document_type": action.requested_document_type,
                "due_at": action.due_at,
                "customer_response": action.customer_response,
                "correction_document_id": action.correction_document_id,
                "status": action.status,
                "correction_round": action.correction_round,
            }
            for action in snapshot["actions"]
        ]
        decisions = [
            {
                "id": decision.id,
                "version": decision.version_number,
                "decision": decision.decision,
                "decision_type": decision.decision_type,
                "summary": decision.summary,
                "reason": decision.reason,
                "reviewer_id": decision.reviewer_user_id,
                "decided_at": decision.decided_at,
                "report_version": decision.report_version,
            }
            for decision in snapshot["decisions"]
        ]
        values.update(
            {
                "customer_user_id": trade_case.customer_user_id,
                "owner_user_id": trade_case.owner_user_id,
                "payment_terms": trade_case.payment_terms,
                "shipment_date": trade_case.shipment_date,
                "expected_payment_date": trade_case.expected_payment_date,
                "transaction_details": trade_case.transaction_details or {},
                "source_lcopilot_session_id": trade_case.source_lcopilot_session_id,
                "final_report_id": trade_case.final_report_id,
                "parties": parties,
                "documents": documents,
                "checks": checks,
                "findings": findings,
                "actions": actions,
                "decision_history": decisions,
            }
        )
        return TradeCaseDetailResponse.model_validate(values)
    return TradeCaseSummaryResponse.model_validate(values)


@router.post("", response_model=TradeCaseDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_trade_case(
    payload: TradeCaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    values = payload.model_dump(exclude_none=True)
    if "payment_arrangement" in values:
        values["payment_arrangement"] = values["payment_arrangement"].value
    try:
        trade_case = repository.create_case(
            company_id=company_id,
            customer_user_id=current_user.id,
            owner_user_id=current_user.id,
            values=values,
        )
        db.commit()
        db.refresh(trade_case)
    except Exception:
        db.rollback()
        logger.exception("Failed to create Proofline case")
        raise HTTPException(status_code=500, detail="Failed to create trade case")

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_case_created",
        trade_case_id=trade_case.id,
        values={
            "payment_arrangement": trade_case.payment_arrangement,
            "service_package_id": trade_case.service_package_id,
        },
    )
    return _case_response(repository, trade_case, detail=True)


@router.get("", response_model=TradeCaseListResponse)
async def list_trade_cases(
    status_filter: Optional[TradeCaseStatus] = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseListResponse:
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    rows, total = repository.list_cases(
        company_id=company_id,
        status=status_filter.value if status_filter else None,
        offset=offset,
        limit=limit,
    )
    return TradeCaseListResponse(
        items=[_case_response(repository, row, detail=False) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{case_id}", response_model=TradeCaseDetailResponse)
async def get_trade_case(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=_company_id(current_user), case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    return _case_response(repository, trade_case, detail=True)


@router.patch("/{case_id}", response_model=TradeCaseDetailResponse)
async def update_trade_case(
    case_id: UUID,
    payload: TradeCaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=_company_id(current_user), case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    if trade_case.status != TradeCaseStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only draft trade cases can be edited")

    values = payload.model_dump(exclude_unset=True)
    if "payment_arrangement" in values and values["payment_arrangement"] is not None:
        values["payment_arrangement"] = values["payment_arrangement"].value
    try:
        repository.update_case(trade_case, values=values)
        db.commit()
        db.refresh(trade_case)
    except Exception:
        db.rollback()
        logger.exception("Failed to update Proofline case", extra={"trade_case_id": str(case_id)})
        raise HTTPException(status_code=500, detail="Failed to update trade case")

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_case_updated",
        trade_case_id=trade_case.id,
        values={"updated_fields": sorted(values)},
    )
    return _case_response(repository, trade_case, detail=True)


@router.post("/{case_id}/submit", response_model=TradeCaseDetailResponse)
async def submit_trade_case(
    case_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    """Validate and submit a draft, then process it outside the request session."""
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    if trade_case.status != TradeCaseStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only a draft trade case can be submitted")
    try:
        validate_submission_context(load_case_context(db, trade_case))
        if is_proofline_checkout_enabled():
            quote_for_case(db, trade_case)
            transition_case(
                db,
                trade_case,
                TradeCaseStatus.AWAITING_PAYMENT,
                actor_type="customer",
                actor_user_id=current_user.id,
                reason="Case scope confirmed; payment is required before review starts",
                idempotency_key=f"customer-awaiting-payment:{trade_case.id}:0",
            )
            trade_case.payment_status = "pending"
        else:
            transition_case(
                db,
                trade_case,
                TradeCaseStatus.SUBMITTED,
                actor_type="customer",
                actor_user_id=current_user.id,
                reason="Customer submitted the trade case for verified review",
                idempotency_key=f"customer-submit:{trade_case.id}:0",
            )
        db.commit()
        db.refresh(trade_case)
    except SubmissionValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except ProoflineCheckoutError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidTradeCaseTransition as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to submit Proofline case", extra={"trade_case_id": str(case_id)}
        )
        raise HTTPException(status_code=500, detail="Failed to submit trade case")

    if trade_case.status == TradeCaseStatus.SUBMITTED.value:
        background_tasks.add_task(
            process_trade_case_by_id,
            case_id=trade_case.id,
            company_id=company_id,
        )
    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_case_submitted",
        trade_case_id=trade_case.id,
        values={"payment_arrangement": trade_case.payment_arrangement},
    )
    return _case_response(repository, trade_case, detail=True)


@router.post("/{case_id}/actions/{action_id}/respond", response_model=TradeCaseDetailResponse)
async def respond_to_remediation_action(
    case_id: UUID,
    action_id: UUID,
    payload: RemediationResponseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    action = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.id == action_id,
            RemediationAction.company_id == company_id,
            RemediationAction.trade_case_id == case_id,
        )
        .first()
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Correction request not found")
    correction_document = None
    if payload.correction_document_id:
        correction_document = (
            db.query(TradeCaseDocument)
            .filter(
                TradeCaseDocument.id == payload.correction_document_id,
                TradeCaseDocument.company_id == company_id,
                TradeCaseDocument.trade_case_id == case_id,
                TradeCaseDocument.is_current.is_(True),
            )
            .first()
        )
        if correction_document is None:
            raise HTTPException(status_code=404, detail="Corrected document not found")
    try:
        respond_to_action(
            db,
            trade_case,
            action,
            customer_user_id=current_user.id,
            response=payload.response,
            correction_document=correction_document,
        )
        db.commit()
        db.refresh(trade_case)
    except RemediationWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_correction_response",
        trade_case_id=case_id,
        values={"action_id": str(action_id), "has_corrected_document": correction_document is not None},
    )
    return _case_response(repository, trade_case, detail=True)


@router.post("/{case_id}/resubmit", response_model=TradeCaseDetailResponse)
async def resubmit_trade_case(
    case_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    actions = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.company_id == company_id,
            RemediationAction.trade_case_id == case_id,
            RemediationAction.status.in_(("requested", "customer_responded", "resolved")),
        )
        .all()
    )
    try:
        submit_corrections(
            db,
            trade_case,
            customer_user_id=current_user.id,
            actions=actions,
        )
        db.commit()
        db.refresh(trade_case)
    except RemediationWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    background_tasks.add_task(
        process_trade_case_by_id,
        case_id=trade_case.id,
        company_id=company_id,
    )
    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_customer_resubmitted",
        trade_case_id=case_id,
        values={"correction_round": trade_case.correction_rounds_used},
    )
    return _case_response(repository, trade_case, detail=True)


def _ensure_case_intake_mutable(trade_case) -> None:
    if trade_case.status not in {
        TradeCaseStatus.DRAFT.value,
        TradeCaseStatus.ACTION_REQUIRED.value,
    }:
        raise HTTPException(status_code=409, detail="Case intake cannot be changed in this state")


def _party_response(party) -> TradeCasePartyResponse:
    return TradeCasePartyResponse(
        id=party.id,
        role=party.role,
        name=party.name,
        country_code=party.country_code,
        identifiers=party.identifiers or {},
    )


@router.post(
    "/{case_id}/parties",
    response_model=TradeCasePartyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trade_case_party(
    case_id: UUID,
    payload: TradeCasePartyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCasePartyResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    _ensure_case_intake_mutable(trade_case)
    party = repository.create_party(
        company_id=company_id,
        case_id=case_id,
        values=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(party)
    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_party_created",
        trade_case_id=case_id,
        values={"party_id": str(party.id), "role": party.role},
    )
    return _party_response(party)


@router.delete("/{case_id}/parties/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade_case_party(
    case_id: UUID,
    party_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    _ensure_case_intake_mutable(trade_case)
    if not repository.delete_party(
        company_id=company_id, case_id=case_id, party_id=party_id
    ):
        raise HTTPException(status_code=404, detail="Trade-case party not found")
    db.commit()
    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_party_deleted",
        trade_case_id=case_id,
        values={"party_id": str(party_id)},
    )


def _document_response(db: Session, association) -> TradeCaseDocumentResponse:
    document = db.query(Document).filter(Document.id == association.document_id).first()
    if document is None:
        raise HTTPException(status_code=409, detail="Source document record is unavailable")
    extracted = getattr(document, "extracted_fields", None) or {}
    extraction_status = extracted.get("extraction_status") if isinstance(extracted, dict) else None
    return TradeCaseDocumentResponse(
        id=association.id,
        document_id=association.document_id,
        logical_key=association.logical_key,
        document_type=association.document_type,
        filename=document.original_filename,
        version=association.version_number,
        supersedes_id=association.supersedes_id,
        correction_round=association.correction_round,
        is_current=association.is_current,
        extraction_status=extraction_status,
        created_at=association.created_at,
    )


@router.get("/{case_id}/documents", response_model=list[TradeCaseDocumentResponse])
async def get_trade_case_documents(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TradeCaseDocumentResponse]:
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    if repository.get_case(company_id=company_id, case_id=case_id) is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    return [
        _document_response(db, association)
        for association in list_case_documents(
            db, company_id=company_id, trade_case_id=case_id
        )
    ]


@router.post(
    "/{case_id}/documents",
    response_model=TradeCaseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_trade_case_document(
    case_id: UUID,
    payload: TradeCaseDocumentAssociate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDocumentResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    if trade_case.status not in {
        TradeCaseStatus.DRAFT.value,
        TradeCaseStatus.ACTION_REQUIRED.value,
        TradeCaseStatus.CUSTOMER_RESUBMITTED.value,
    }:
        raise HTTPException(status_code=409, detail="Documents cannot be changed in this case state")

    try:
        association = associate_document(
            db,
            trade_case=trade_case,
            company_id=company_id,
            actor_user_id=current_user.id,
            document_id=payload.document_id,
            logical_key=payload.logical_key,
            document_type=payload.document_type,
            content_hash=payload.content_hash,
            supersedes_id=payload.supersedes_id,
            correction_round=payload.correction_round,
        )
        db.commit()
        db.refresh(association)
    except ProoflineDocumentAccessError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Document is not available")
    except DuplicateCaseDocument as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_document_attached",
        trade_case_id=trade_case.id,
        values={
            "document_id": str(association.document_id),
            "logical_key": association.logical_key,
            "version": association.version_number,
            "correction_round": association.correction_round,
        },
    )
    return _document_response(db, association)


@router.post(
    "/{case_id}/documents/upload",
    response_model=TradeCaseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_trade_case_document(
    case_id: UUID,
    file: UploadFile = File(...),
    logical_key: str = Form(..., min_length=1, max_length=128),
    document_type: Optional[str] = Form(default=None, max_length=64),
    supersedes_id: Optional[UUID] = Form(default=None),
    correction_round: int = Form(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDocumentResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=company_id, case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    if trade_case.status not in {
        TradeCaseStatus.DRAFT.value,
        TradeCaseStatus.ACTION_REQUIRED.value,
        TradeCaseStatus.CUSTOMER_RESUBMITTED.value,
    }:
        raise HTTPException(status_code=409, detail="Documents cannot be changed in this case state")
    try:
        association = await ingest_case_document(
            db,
            trade_case=trade_case,
            user=current_user,
            file=file,
            logical_key=logical_key,
            declared_document_type=document_type,
            supersedes_id=supersedes_id,
            correction_round=correction_round,
        )
        db.commit()
        db.refresh(association)
    except (ProoflineUploadError, DuplicateCaseDocument, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except ProoflineDocumentAccessError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Document version is not available")
    except Exception:
        db.rollback()
        logger.exception(
            "Proofline document upload failed", extra={"trade_case_id": str(case_id)}
        )
        raise HTTPException(status_code=502, detail="Document processing is temporarily unavailable")

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_document_uploaded",
        trade_case_id=case_id,
        values={
            "document_id": str(association.document_id),
            "logical_key": association.logical_key,
            "document_type": association.document_type,
            "version": association.version_number,
            "correction_round": association.correction_round,
        },
    )
    return _document_response(db, association)


__all__ = ["router"]
