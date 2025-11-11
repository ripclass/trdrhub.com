"""
Token Service for API Token Management
Handles token generation, validation, masking, and lifecycle management
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.api_tokens_webhooks import APIToken
from app.models import User, Company


class TokenService:
    """Service for managing API tokens"""
    
    TOKEN_PREFIX = "bk_live_"  # Bank live token prefix
    TOKEN_LENGTH = 32  # Random part length (after prefix)
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_token(self) -> Tuple[str, str]:
        """
        Generate a new API token.
        Returns: (full_token, token_hash)
        """
        # Generate random token part
        random_part = secrets.token_urlsafe(self.TOKEN_LENGTH)
        full_token = f"{self.TOKEN_PREFIX}{random_part}"
        
        # Hash the token for storage
        token_hash = hashlib.sha256(full_token.encode()).hexdigest()
        
        return full_token, token_hash
    
    def create_token(
        self,
        company_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        scopes: Optional[list] = None,
        expires_at: Optional[datetime] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
    ) -> Tuple[APIToken, str]:
        """
        Create a new API token.
        Returns: (token_model, full_token_string)
        """
        full_token, token_hash = self.generate_token()
        
        token = APIToken(
            company_id=company_id,
            created_by=created_by,
            name=name,
            description=description,
            token_hash=token_hash,
            token_prefix=self.TOKEN_PREFIX,
            scopes=scopes or [],
            expires_at=expires_at,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            is_active=True,
        )
        
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        
        return token, full_token
    
    def validate_token(self, token: str) -> Optional[APIToken]:
        """
        Validate an API token and return the token model if valid.
        Returns None if token is invalid, expired, or revoked.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find token by hash
        db_token = self.db.query(APIToken).filter(
            APIToken.token_hash == token_hash
        ).first()
        
        if not db_token:
            return None
        
        # Check if active
        if not db_token.is_active:
            return None
        
        # Check if revoked
        if db_token.revoked_at:
            return None
        
        # Check if expired
        if db_token.expires_at and db_token.expires_at < datetime.utcnow():
            return None
        
        return db_token
    
    def record_token_usage(self, token: APIToken, ip_address: Optional[str] = None) -> None:
        """Record token usage (update last_used_at and usage_count)"""
        token.last_used_at = datetime.utcnow()
        token.last_used_ip = ip_address
        token.usage_count += 1
        self.db.commit()
    
    def revoke_token(
        self,
        token_id: uuid.UUID,
        revoked_by: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[APIToken]:
        """Revoke an API token"""
        token = self.db.query(APIToken).filter(APIToken.id == token_id).first()
        
        if not token:
            return None
        
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        token.revoked_by = revoked_by
        token.revoke_reason = reason
        
        self.db.commit()
        self.db.refresh(token)
        
        return token
    
    def mask_token(self, token: APIToken) -> str:
        """
        Return a masked version of the token for display.
        Format: bk_live_****...**** (shows prefix + last 4 chars)
        """
        # Token prefix is already stored, so we can show it
        # For the random part, we show last 4 characters
        # Since we don't store the full token, we can't show the actual last 4
        # So we'll just show the prefix + masked part
        return f"{token.token_prefix}****...****"
    
    def list_tokens(
        self,
        company_id: uuid.UUID,
        include_revoked: bool = False
    ) -> list[APIToken]:
        """List all tokens for a company"""
        query = self.db.query(APIToken).filter(
            APIToken.company_id == company_id
        )
        
        if not include_revoked:
            query = query.filter(
                and_(
                    APIToken.is_active == True,
                    or_(
                        APIToken.expires_at.is_(None),
                        APIToken.expires_at > datetime.utcnow()
                    )
                )
            )
        
        return query.order_by(APIToken.created_at.desc()).all()
    
    def get_token(self, token_id: uuid.UUID, company_id: uuid.UUID) -> Optional[APIToken]:
        """Get a specific token by ID"""
        return self.db.query(APIToken).filter(
            and_(
                APIToken.id == token_id,
                APIToken.company_id == company_id
            )
        ).first()
    
    def update_token(
        self,
        token_id: uuid.UUID,
        company_id: uuid.UUID,
        updates: dict
    ) -> Optional[APIToken]:
        """Update token properties"""
        token = self.get_token(token_id, company_id)
        
        if not token:
            return None
        
        # Update allowed fields
        if 'name' in updates:
            token.name = updates['name']
        if 'description' in updates:
            token.description = updates['description']
        if 'is_active' in updates:
            token.is_active = updates['is_active']
        if 'expires_at' in updates:
            token.expires_at = updates['expires_at']
        if 'scopes' in updates:
            token.scopes = updates['scopes']
        
        self.db.commit()
        self.db.refresh(token)
        
        return token

