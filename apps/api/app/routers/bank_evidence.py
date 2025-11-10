"""
Bank Evidence Packs API endpoints.

Generate comprehensive evidence packs (PDF/ZIP) with validation findings, documents, and audit trails.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel
import logging

from ..database import get_db
from app.models import User, ValidationSession
from app.models.company import Company
from app.models import BankTenant
from ..core.security import get_current_user, require_bank_or_admin

router = APIRouter(prefix="/bank/evidence-packs", tags=["bank-evidence"])
logger = logging.getLogger(__name__)


class ValidationSessionRead(BaseModel):
    id: str
    lc_number: str
    client_name: str
    status: str
    completed_at: str
    discrepancy_count: int
    document_count: int
    compliance_score: float
    
    class Config:
        from_attributes = True


class GeneratePackRequest(BaseModel):
    session_ids: List[str]
    format: str  # "pdf" or "zip"
    include_documents: bool = True
    include_findings: bool = True
    include_audit_trail: bool = True


class GeneratePackResponse(BaseModel):
    pack_id: str
    download_url: str
    format: str
    size_bytes: int
    expires_at: str


@router.get("/sessions", response_model=List[ValidationSessionRead])
async def list_validation_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status: completed, failed, processing"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    List validation sessions for evidence pack generation.
    
    Returns completed validation sessions scoped to the bank's clients.
    """
    bank_company_id = current_user.company_id
    
    # Build query - get validation sessions from bank's tenant companies
    # Join through BankTenant to find all companies managed by this bank
    query = db.query(ValidationSession).join(
        Company, ValidationSession.company_id == Company.id
    ).join(
        BankTenant, Company.id == BankTenant.tenant_id
    ).filter(
        BankTenant.bank_id == bank_company_id  # Sessions from bank's tenant companies
    )
    
    # Filter by status
    if status:
        query = query.filter(ValidationSession.status == status)
    else:
        # Default to completed sessions
        query = query.filter(ValidationSession.status == "completed")
    
    # Order by processing_completed_at descending
    query = query.order_by(desc(ValidationSession.processing_completed_at))
    
    # Paginate
    sessions = query.offset(offset).limit(limit).all()
    
    # Convert to response format
    result = []
    for session in sessions:
        # Get client name
        client_name = "Unknown"
        if session.company_id:
            company = db.query(Company).filter(Company.id == session.company_id).first()
            if company:
                client_name = company.name
        
        # Get discrepancy count (from validation results)
        discrepancy_count = 0
        if hasattr(session, 'discrepancy_count'):
            discrepancy_count = session.discrepancy_count
        else:
            # Count from discrepancies table if available
            from app.models.discrepancy import Discrepancy
            discrepancy_count = db.query(Discrepancy).filter(
                Discrepancy.validation_session_id == session.id
            ).count()
        
        # Get document count
        document_count = 0
        if hasattr(session, 'document_count'):
            document_count = session.document_count
        else:
            # Count from documents table if available
            from app.models.document import Document
            document_count = db.query(Document).filter(
                Document.validation_session_id == session.id
            ).count()
        
        # Get LC number from extracted_data or lc_version
        lc_number = "Unknown"
        if session.extracted_data and isinstance(session.extracted_data, dict):
            lc_number = session.extracted_data.get('lc_number') or session.extracted_data.get('lcNumber') or "Unknown"
        elif session.lc_version:
            lc_number = session.lc_version.lc_number or "Unknown"
        
        # Get compliance score from validation_results
        compliance_score = 0.0
        if session.validation_results and isinstance(session.validation_results, dict):
            compliance_score = session.validation_results.get('compliance_score') or session.validation_results.get('complianceScore') or 0.0
        
        result.append(ValidationSessionRead(
            id=str(session.id),
            lc_number=lc_number,
            client_name=client_name,
            status=session.status or "unknown",
            completed_at=session.processing_completed_at.isoformat() if session.processing_completed_at else datetime.utcnow().isoformat(),
            discrepancy_count=discrepancy_count,
            document_count=document_count,
            compliance_score=compliance_score
        ))
    
    return result


@router.post("/generate", response_model=GeneratePackResponse)
async def generate_evidence_pack(
    request: GeneratePackRequest = Body(...),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Generate evidence pack (PDF or ZIP) for selected validation sessions.
    
    Includes:
    - Validation findings and discrepancies
    - Original documents
    - Audit trail and timestamps
    - Compliance scores
    """
    bank_company_id = current_user.company_id
    
    # Validate session IDs belong to bank's clients
    sessions = []
    for session_id_str in request.session_ids:
        try:
            session_id = UUID(session_id_str)
            session = db.query(ValidationSession).join(
                Company, ValidationSession.company_id == Company.id
            ).join(
                BankTenant, Company.id == BankTenant.tenant_id
            ).filter(
                and_(
                    ValidationSession.id == session_id,
                    BankTenant.bank_id == bank_company_id
                )
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Validation session {session_id_str} not found or access denied"
                )
            
            sessions.append(session)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid session ID: {session_id_str}"
            )
    
    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid sessions provided"
        )
    
    # TODO: Implement actual PDF/ZIP generation
    # This would involve:
    # 1. Collecting all documents for the sessions
    # 2. Collecting all discrepancies/findings
    # 3. Collecting audit trail entries
    # 4. Generating PDF report or ZIP archive
    # 5. Uploading to storage (S3/Supabase Storage)
    # 6. Returning download URL
    
    # Placeholder response
    pack_id = f"pack-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    download_url = f"/api/bank/evidence-packs/download/{pack_id}"
    expires_at = (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat()
    
    logger.info(f"Evidence pack generation requested: {len(sessions)} sessions, format={request.format}")
    
    return GeneratePackResponse(
        pack_id=pack_id,
        download_url=download_url,
        format=request.format,
        size_bytes=0,  # TODO: Calculate actual size
        expires_at=expires_at
    )


@router.get("/download/{pack_id}")
async def download_evidence_pack(
    pack_id: str,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Download generated evidence pack.
    
    TODO: Implement actual file download
    """
    # Placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Evidence pack download not yet implemented"
    )

