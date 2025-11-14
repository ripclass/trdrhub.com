"""Supabase-friendly onboarding API."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Company, User
from ..schemas.onboarding import (
    CompanyPayload,
    OnboardingProgressPayload,
    OnboardingRequirements,
    OnboardingStatus,
)
from ..core.security import get_current_user, require_admin, infer_effective_role


router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _sanitize_role(role: str) -> str:
    role_normalized = role.lower()
    allowed = {
        "exporter",
        "importer",
        "tenant_admin",
        "bank_officer",
        "bank_admin",
        "system_admin",
        "bank",
    }
    if role_normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role selection")
    if role_normalized == "bank":
        return "bank_officer"
    return role_normalized


def _requirements_for_user(user: User) -> OnboardingRequirements:
    req = OnboardingRequirements()
    if not user.company_id:
        req.basic.extend(["company_name", "company_type"])
    data = user.onboarding_data or {}
    company_data = data.get("company", {})
    if user.role in {"bank_officer", "bank_admin"}:
        req.legal.extend(["legal_name", "registration_number", "regulator_id", "country"])
        req.docs.append("kyc_package")
        user.kyc_required = True
        user.status = user.status or "pending"
        if user.kyc_status is None:
            user.kyc_status = "pending"
    if not data.get("business_types"):
        req.basic.append("business_types")
    if user.role == "tenant_admin" and not company_data.get("size"):
        req.basic.append("company_size")
    return req


def _ensure_company(db: Session, user: User, payload: CompanyPayload) -> Company:
    company: Company
    if user.company_id:
        company = db.query(Company).get(user.company_id)
        if not company:
            company = Company(name=payload.name, contact_email=user.email)
            db.add(company)
            db.flush()
            user.company_id = company.id
    else:
        company = Company(name=payload.name, contact_email=user.email)
        db.add(company)
        db.flush()
        user.company_id = company.id

    company.name = payload.name
    event_meta = company.event_metadata or {}
    if payload.type:
        event_meta["business_type"] = payload.type
    if payload.size:
        event_meta["company_size"] = payload.size
    if event_meta:
        company.event_metadata = event_meta
    if payload.legal_name:
        company.legal_name = payload.legal_name
    if payload.registration_number:
        company.registration_number = payload.registration_number
    if payload.regulator_id:
        company.regulator_id = payload.regulator_id
    if payload.country:
        company.country = payload.country

    company.contact_email = user.email

    return company


def _persist_onboarding_data(user: User, data: Dict[str, Any]) -> None:
    payload = user.onboarding_data or {}
    payload.update(data)
    user.onboarding_data = payload


@router.get("/status", response_model=OnboardingStatus)
async def get_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnboardingStatus:
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 GET /onboarding/status called for user {current_user.id} ({current_user.email})")
    logger.info(f"📊 Current user state: company_id={current_user.company_id}, onboarding_data={current_user.onboarding_data}, onboarding_completed={current_user.onboarding_completed}")
    
    # Fast path: If user already has onboarding_data, skip restoration
    needs_restoration = not current_user.onboarding_data or current_user.onboarding_data == {}
    
    if needs_restoration:
        company = None
        needs_commit = False
        try:
            # Try to get company - first by ID, then by email
            if current_user.company_id:
                company = db.query(Company).filter(Company.id == current_user.company_id).first()
                if company:
                    logger.info(f"📋 Found company {company.id} for user {current_user.id} by company_id")
                else:
                    logger.warning(f"⚠️ User {current_user.id} has company_id {current_user.company_id} but company not found")
            
            if not company and current_user.email:
                # Only query by email if no company_id (to avoid unnecessary queries)
                company = db.query(Company).filter(Company.contact_email == current_user.email).first()
                if company:
                    # Link company to user
                    current_user.company_id = company.id
                    needs_commit = True
                    logger.info(f"🔗 Found and linking company {company.id} to user {current_user.id} by email {current_user.email}")
                else:
                    logger.warning(f"⚠️ No company found for user {current_user.id} with email {current_user.email}")
                    # Auto-create a company for users who don't have one
                    # This fixes users registered before company creation was fully implemented
                    try:
                        # Extract company name from email domain or use user's name
                        email_domain = current_user.email.split('@')[1] if '@' in current_user.email else 'company'
                        company_name = current_user.full_name.split()[0] + " Company" if current_user.full_name else f"Company for {email_domain}"
                        
                        # Create company with default "both" type for users who might be combined
                        # (We'll let them update it during onboarding if needed)
                        company = Company(
                            name=company_name,
                            contact_email=current_user.email,
                            event_metadata={
                                "business_type": "both",  # Default to "both" for flexibility
                                "company_size": "sme",  # Default to SME
                                "auto_created": True  # Flag to indicate this was auto-created
                            }
                        )
                        db.add(company)
                        db.flush()
                        current_user.company_id = company.id
                        needs_commit = True
                        logger.info(f"🏗️ Auto-created company {company.id} for user {current_user.id} ({current_user.email})")
                    except Exception as create_error:
                        logger.error(f"❌ Failed to auto-create company: {str(create_error)}")
                        logger.error(traceback.format_exc())
                        # Continue without company - user can complete onboarding to create one
            
            if company:
                # Build restored data
                event_metadata = company.event_metadata or {}
                company_type = event_metadata.get('company_type') or event_metadata.get('business_type')
                company_size = event_metadata.get('company_size')
                
                restored_data = {}
                if company.name:
                    restored_data['company'] = {
                        'name': company.name,
                        'type': company_type,
                        'size': company_size,
                        'legal_name': company.legal_name,
                        'registration_number': company.registration_number,
                        'regulator_id': company.regulator_id,
                        'country': company.country,
                    }
                
                # Restore business_types
                if company_type == 'both':
                    restored_data['business_types'] = ['exporter', 'importer']
                elif company_type:
                    restored_data['business_types'] = [company_type]
                
                # Set restored data
                if restored_data:
                    current_user.onboarding_data = restored_data
                    needs_commit = True
                    logger.info(f"📦 Restored onboarding data for user {current_user.id}: {restored_data}")
                
                # Auto-complete if we have company info and user is not a bank
                if company.name and company_type and current_user.role not in {'bank_officer', 'bank_admin'}:
                    if not current_user.onboarding_completed:
                        current_user.onboarding_completed = True
                        current_user.status = 'active'
                        needs_commit = True
                        logger.info(f"✅ Auto-completed onboarding for user {current_user.id}")
                
                # Commit all changes at once
                if needs_commit:
                    db.commit()
                    db.refresh(current_user)  # Refresh to get updated data
                    logger.info(f"✅ Successfully restored and linked company for user {current_user.id}")
        except Exception as restore_error:
            logger.error(f"❌ Error restoring onboarding data for user {current_user.id}: {str(restore_error)}")
            logger.error(traceback.format_exc())
            db.rollback()
            # Continue - return status with whatever data we have
    
    # Build and return status (no additional commits needed)
    try:
        requirements = _requirements_for_user(current_user)
        computed_role = infer_effective_role(current_user)
        
        logger.info(f"📊 Role computation: user.role={current_user.role}, computed_role={computed_role}, company_type={onboarding_data.get('company', {}).get('type')}, business_types={onboarding_data.get('business_types')}")
        
        return OnboardingStatus(
            user_id=str(current_user.id),
            role=computed_role,  # Use computed role instead of raw user.role
            company_id=str(current_user.company_id) if current_user.company_id else None,
            completed=current_user.onboarding_completed,
            step=current_user.onboarding_step,
            status=current_user.status,
            kyc_status=current_user.kyc_status,
            required=requirements,
            details=current_user.onboarding_data or {},
        )
    except Exception as final_error:
        logger.error(f"Error building OnboardingStatus: {str(final_error)}")
        logger.error(traceback.format_exc())
        # Return basic status on error - still try to compute role from onboarding_data
        error_onboarding_data = current_user.onboarding_data or {}
        error_computed_role = infer_effective_role(current_user)
        
        return OnboardingStatus(
            user_id=str(current_user.id),
            role=error_computed_role,
            company_id=str(current_user.company_id) if current_user.company_id else None,
            completed=current_user.onboarding_completed or False,
            step=current_user.onboarding_step,
            status=current_user.status or "active",
            kyc_status=current_user.kyc_status,
            required=OnboardingRequirements(),
            details=error_onboarding_data,
        )


@router.put("/progress", response_model=OnboardingStatus)
async def update_progress(
    payload: OnboardingProgressPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OnboardingStatus:
    if payload.role:
        role = _sanitize_role(payload.role)
        current_user.role = role
        if role.startswith("bank"):
            current_user.kyc_required = True
            current_user.status = current_user.status or "pending"

    if payload.onboarding_step:
        current_user.onboarding_step = payload.onboarding_step

    if payload.company:
        company = _ensure_company(db, current_user, payload.company)
        _persist_onboarding_data(
            current_user,
            {
                "company": {
                    "name": company.name,
                    "type": payload.company.type,
                    "size": payload.company.size,
                    "legal_name": company.legal_name,
                    "registration_number": company.registration_number,
                    "regulator_id": company.regulator_id,
                    "country": company.country,
                }
            },
        )

    if payload.business_types is not None:
        _persist_onboarding_data(current_user, {"business_types": payload.business_types})

    if payload.submit_for_review and current_user.role in {"bank_officer", "bank_admin"}:
        current_user.status = "under_review"
        current_user.kyc_status = "submitted"
        current_user.kyc_required = True

    if payload.complete and current_user.role not in {"bank_officer", "bank_admin"}:
        current_user.onboarding_completed = True
        current_user.status = "approved"

    if payload.approved and current_user.role in {"bank_officer", "bank_admin"}:
        current_user.status = "approved"
        current_user.onboarding_completed = True
        current_user.kyc_status = "approved"

    db.commit()
    db.refresh(current_user)

    requirements = _requirements_for_user(current_user)
    db.commit()

    return OnboardingStatus(
        user_id=str(current_user.id),
        role=current_user.role,
        company_id=str(current_user.company_id) if current_user.company_id else None,
        completed=current_user.onboarding_completed,
        step=current_user.onboarding_step,
        status=current_user.status,
        kyc_status=current_user.kyc_status,
        required=requirements,
        details=current_user.onboarding_data or {},
    )


@router.post("/approve/{user_id}", response_model=OnboardingStatus)
async def approve_user(
    user_id: UUID,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> OnboardingStatus:
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target.status = "approved"
    target.onboarding_completed = True
    target.kyc_status = "approved"
    target.approved_at = datetime.utcnow()
    db.commit()
    requirements = _requirements_for_user(target)
    db.commit()

    return OnboardingStatus(
        user_id=str(target.id),
        role=target.role,
        company_id=str(target.company_id) if target.company_id else None,
        completed=target.onboarding_completed,
        step=target.onboarding_step,
        status=target.status,
        kyc_status=target.kyc_status,
        required=requirements,
        details=target.onboarding_data or {},
    )
    progress.last_accessed = datetime.now(timezone.utc)
    # Serialize datetime to ISO string
    progress_dict = progress.model_dump(mode='json')
    if progress_dict.get('last_accessed'):
        progress_dict['last_accessed'] = progress_dict['last_accessed'].isoformat() if hasattr(progress_dict['last_accessed'], 'isoformat') else progress_dict['last_accessed']
    current_user.onboarding_data = progress_dict
    
    db.commit()
    db.refresh(current_user)
    
    return OnboardingStatus(
        needs_onboarding=not current_user.onboarding_completed,
        onboarding_completed=current_user.onboarding_completed,
        current_progress=progress,
        role=current_user.role
    )


@router.post("/reset")
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset onboarding status (allow re-access)."""
    current_user.onboarding_completed = False
    current_user.onboarding_data = _get_default_progress()
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Onboarding reset successfully",
        "onboarding_completed": False
    }

