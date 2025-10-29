"""
Authentication utilities for partner integrations.
Supports OAuth2, API Keys, and mTLS.
"""

import jwt
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from cryptography.fernet import Fernet
import httpx
import ssl
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.integrations import CompanyIntegration
from ..config import settings


class IntegrationAuthManager:
    """Manages authentication for partner integrations."""

    def __init__(self):
        self.encryption_key = settings.ENCRYPTION_KEY.encode() if hasattr(settings, 'ENCRYPTION_KEY') else Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

    def encrypt_credential(self, credential: str) -> str:
        """Encrypt sensitive credentials for database storage."""
        if not credential:
            return ""
        return self.cipher.encrypt(credential.encode()).decode()

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt credentials for API calls."""
        if not encrypted_credential:
            return ""
        try:
            return self.cipher.decrypt(encrypted_credential.encode()).decode()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt credentials"
            )

    async def get_api_key_headers(self, company_integration: CompanyIntegration) -> Dict[str, str]:
        """Generate headers for API key authentication."""
        api_key = self.decrypt_credential(company_integration.api_key)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key not configured for integration"
            )

        return {
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    async def get_oauth2_headers(self, company_integration: CompanyIntegration) -> Dict[str, str]:
        """Generate headers for OAuth2 authentication."""
        # Check if token is expired
        if company_integration.is_oauth_expired:
            await self.refresh_oauth_token(company_integration)

        access_token = self.decrypt_credential(company_integration.oauth_token)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth token not available for integration"
            )

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def refresh_oauth_token(self, company_integration: CompanyIntegration) -> None:
        """Refresh OAuth2 token using refresh token."""
        refresh_token = self.decrypt_credential(company_integration.oauth_refresh_token)
        client_id = company_integration.client_id
        client_secret = self.decrypt_credential(company_integration.client_secret)

        if not all([refresh_token, client_id, client_secret]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth credentials incomplete"
            )

        # Get token endpoint from integration config
        token_url = company_integration.integration.custom_config.get('token_url')
        if not token_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token URL not configured for integration"
            )

        # Prepare refresh request
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    timeout=30.0
                )
                response.raise_for_status()
                token_data = response.json()

                # Update stored tokens
                company_integration.oauth_token = self.encrypt_credential(token_data['access_token'])
                if 'refresh_token' in token_data:
                    company_integration.oauth_refresh_token = self.encrypt_credential(token_data['refresh_token'])

                # Calculate expiry
                expires_in = token_data.get('expires_in', 3600)
                company_integration.oauth_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 5 min buffer

            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to refresh OAuth token: {str(e)}"
                )

    def create_mtls_context(self, company_integration: CompanyIntegration) -> ssl.SSLContext:
        """Create SSL context for mTLS authentication."""
        if not company_integration.integration.requires_mtls:
            return None

        custom_config = company_integration.custom_config or {}
        cert_path = custom_config.get('client_cert_path')
        key_path = custom_config.get('client_key_path')
        ca_path = custom_config.get('ca_cert_path')

        if not cert_path or not key_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="mTLS certificates not configured"
            )

        context = ssl.create_default_context()
        context.load_cert_chain(cert_path, key_path)

        if ca_path:
            context.load_verify_locations(ca_path)

        return context

    def generate_idempotency_key(self, session_id: str, integration_id: str) -> str:
        """Generate idempotency key for API calls."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{session_id}:{integration_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature for security."""
        if not secret:
            return True  # Skip verification if no secret configured

        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Support different signature formats
        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)

    def generate_jwt_token(self, payload: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
        """Generate JWT token for API authentication."""
        payload.update({
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'iss': 'lcopilot'
        })

        return jwt.encode(payload, secret, algorithm='HS256')

    def verify_jwt_token(self, token: str, secret: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


class RateLimiter:
    """Rate limiting for partner API calls."""

    def __init__(self):
        self.request_counts: Dict[str, Dict[str, int]] = {}

    def is_allowed(self, integration_id: str, company_id: str, limit: int) -> Tuple[bool, int]:
        """Check if request is within rate limit."""
        key = f"{integration_id}:{company_id}"
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)
        minute_key = current_minute.isoformat()

        if key not in self.request_counts:
            self.request_counts[key] = {}

        # Clean old entries (keep only current and previous minute)
        for mk in list(self.request_counts[key].keys()):
            if mk < (current_minute - timedelta(minutes=1)).isoformat():
                del self.request_counts[key][mk]

        current_count = self.request_counts[key].get(minute_key, 0)

        if current_count >= limit:
            return False, limit - current_count

        # Increment counter
        self.request_counts[key][minute_key] = current_count + 1
        return True, limit - current_count - 1

    def get_reset_time(self) -> datetime:
        """Get when rate limit resets."""
        return datetime.utcnow().replace(second=0, microsecond=0) + timedelta(minutes=1)


class APIKeyGenerator:
    """Generate secure API keys for partners."""

    @staticmethod
    def generate_api_key(prefix: str = "lcp") -> str:
        """Generate a secure API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"

    @staticmethod
    def generate_webhook_secret() -> str:
        """Generate webhook signing secret."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()


# Global instances
auth_manager = IntegrationAuthManager()
rate_limiter = RateLimiter()
api_key_generator = APIKeyGenerator()