"""
API Tokens Router
CRUD operations for API tokens
"""
from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_tokens_webhooks import APIToken
from app.models import User
from app.schemas.api_tokens_webhooks import (
    APITokenCreate,
    APITokenRead,
    APITokenCreateResponse,
    APITokenUpdate,
    APITokenRevokeRequest,
    APITokenListResponse,
)
from app.services.token_service import TokenService
from app.routers.bank import require_bank_or_admin


router = APIRouter(prefix="/bank/tokens", tags=["bank", "api-tokens"])


@router.post("", response_model=APITokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    token_data: APITokenCreate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new API token"""
    token_service = TokenService(db)
    
    token, full_token = token_service.create_token(
        company_id=current_user.company_id,
        created_by=current_user.id,
        name=token_data.name,
        description=token_data.description,
        scopes=token_data.scopes,
        expires_at=token_data.expires_at,
        rate_limit_per_minute=token_data.rate_limit_per_minute,
        rate_limit_per_hour=token_data.rate_limit_per_hour,
    )
    
    return APITokenCreateResponse(
        token=full_token,
        token_id=token.id,
        token_prefix=token.token_prefix,
        expires_at=token.expires_at,
    )


@router.get("", response_model=APITokenListResponse)
async def list_tokens(
    include_revoked: bool = False,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """List all API tokens for the current company"""
    token_service = TokenService(db)
    tokens = token_service.list_tokens(
        company_id=current_user.company_id,
        include_revoked=include_revoked,
    )
    
    return APITokenListResponse(
        tokens=[APITokenRead.model_validate(t) for t in tokens],
        total=len(tokens),
    )


@router.get("/{token_id}", response_model=APITokenRead)
async def get_token(
    token_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Get a specific API token"""
    token_service = TokenService(db)
    token = token_service.get_token(token_id, current_user.company_id)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )
    
    return APITokenRead.model_validate(token)


@router.put("/{token_id}", response_model=APITokenRead)
async def update_token(
    token_id: UUID,
    token_data: APITokenUpdate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Update an API token"""
    token_service = TokenService(db)
    
    updates = {}
    if token_data.name is not None:
        updates['name'] = token_data.name
    if token_data.description is not None:
        updates['description'] = token_data.description
    if token_data.is_active is not None:
        updates['is_active'] = token_data.is_active
    if token_data.expires_at is not None:
        updates['expires_at'] = token_data.expires_at
    if token_data.scopes is not None:
        updates['scopes'] = token_data.scopes
    
    token = token_service.update_token(token_id, current_user.company_id, updates)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )
    
    return APITokenRead.model_validate(token)


@router.post("/{token_id}/revoke", response_model=APITokenRead)
async def revoke_token(
    token_id: UUID,
    revoke_data: APITokenRevokeRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Revoke an API token"""
    token_service = TokenService(db)
    token = token_service.revoke_token(
        token_id=token_id,
        revoked_by=current_user.id,
        reason=revoke_data.reason,
    )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )
    
    return APITokenRead.model_validate(token)

