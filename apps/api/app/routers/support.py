"""
API endpoint for support ticket creation with context pre-filling.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.security import get_current_user
from ..models import User
from pydantic import BaseModel, Field, EmailStr

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["support"])


class EnvironmentInfo(BaseModel):
    """Environment information for frontend display."""
    environment: str  # development, staging, production
    is_production: bool
    is_staging: bool
    is_development: bool
    use_stubs: bool
    sample_data_mode: bool  # Alias for use_stubs


@router.get("/environment", response_model=EnvironmentInfo)
async def get_environment_info():
    """Get environment information for displaying environment banner."""
    return EnvironmentInfo(
        environment=settings.ENVIRONMENT,
        is_production=settings.is_production(),
        is_staging=settings.ENVIRONMENT == "staging",
        is_development=settings.is_development(),
        use_stubs=settings.USE_STUBS,
        sample_data_mode=settings.USE_STUBS
    )


class SupportTicketCreate(BaseModel):
    """Schema for creating a support ticket."""
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = Field(..., description="bug, feature_request, question, billing, technical")
    priority: str = Field("normal", description="low, normal, high, urgent")
    
    # Context information (pre-filled by frontend)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context: page, user_agent, error_message, etc.")
    
    # Optional contact override (defaults to current user)
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None


class SupportTicketResponse(BaseModel):
    """Response schema for support ticket creation."""
    ticket_id: str
    status: str
    message: str
    created_at: datetime


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a support ticket with pre-filled context.
    
    Context can include:
    - current_page: URL or page identifier
    - user_agent: Browser user agent
    - error_message: Any error message encountered
    - screenshots: Base64 encoded screenshots (if provided)
    - browser_info: Browser version, OS, etc.
    - account_info: User role, company, plan type
    """
    # Use current user info if available, otherwise use provided contact info
    contact_email = ticket_data.contact_email or (current_user.email if current_user else None)
    contact_name = ticket_data.contact_name or (current_user.full_name or current_user.username if current_user else "Guest")
    
    if not contact_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact email is required"
        )
    
    # Enrich context with request information
    enriched_context = {
        **(ticket_data.context or {}),
        "user_id": str(current_user.id) if current_user else None,
        "user_role": current_user.role if current_user else None,
        "company_id": str(current_user.company_id) if current_user and current_user.company_id else None,
        "request_path": str(request.url.path),
        "request_method": request.method,
        "timestamp": datetime.utcnow().isoformat(),
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
    }
    
    # Generate ticket ID (in production, this would be created in a ticketing system)
    ticket_id = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{UUID().hex[:8].upper()}"
    
    # TODO: In production, integrate with actual ticketing system (Zendesk, Freshdesk, etc.)
    # For now, log the ticket and return success
    logger.info(
        "Support ticket created",
        extra={
            "ticket_id": ticket_id,
            "subject": ticket_data.subject,
            "category": ticket_data.category,
            "priority": ticket_data.priority,
            "contact_email": contact_email,
            "context": enriched_context
        }
    )
    
    # In production, you would:
    # 1. Create ticket in ticketing system
    # 2. Send confirmation email to user
    # 3. Notify support team
    # 4. Store ticket reference in database
    
    return SupportTicketResponse(
        ticket_id=ticket_id,
        status="created",
        message="Support ticket created successfully. Our team will respond within 24 hours.",
        created_at=datetime.utcnow()
    )


@router.get("/context")
async def get_support_context(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get pre-filled context for support ticket form.
    This endpoint provides context information that can be used to pre-fill the support form.
    """
    context = {
        "user_id": str(current_user.id) if current_user else None,
        "user_email": current_user.email if current_user else None,
        "user_name": current_user.full_name or current_user.username if current_user else None,
        "user_role": current_user.role if current_user else None,
        "company_id": str(current_user.company_id) if current_user and current_user.company_id else None,
        "current_page": str(request.url.path),
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    return context

