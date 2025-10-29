"""
mTLS (Mutual TLS) Authentication for Bank Pilot
Client certificate validation middleware and utilities
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import logging
import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.verification import PolicyBuilder, StoreBuilder

logger = logging.getLogger(__name__)


class ClientCertificate(BaseModel):
    """Client certificate information"""

    common_name: str
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    country: Optional[str] = None
    serial_number: str
    issuer: str
    subject: str
    valid_from: datetime
    valid_to: datetime
    fingerprint: str
    tenant_alias: str

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired"""
        return datetime.utcnow() > self.valid_to

    @property
    def is_valid_period(self) -> bool:
        """Check if certificate is within valid period"""
        now = datetime.utcnow()
        return self.valid_from <= now <= self.valid_to


class MTLSConfig(BaseModel):
    """mTLS configuration for tenant"""

    tenant_alias: str
    enabled: bool = Field(default=False)
    required: bool = Field(default=True)
    ca_certificates: List[str] = Field(default_factory=list)  # Base64 encoded CA certs
    allowed_issuers: List[str] = Field(default_factory=list)
    certificate_validation: str = Field(default="strict", pattern="^(strict|relaxed|disabled)$")
    crl_check: bool = Field(default=True)
    ocsp_check: bool = Field(default=False)
    max_chain_length: int = Field(default=3, ge=1, le=10)

    def add_ca_certificate(self, ca_cert_pem: str) -> bool:
        """Add CA certificate to trusted list"""
        try:
            # Validate certificate format
            cert = x509.load_pem_x509_certificate(ca_cert_pem.encode(), default_backend())
            ca_cert_b64 = base64.b64encode(ca_cert_pem.encode()).decode()

            if ca_cert_b64 not in self.ca_certificates:
                self.ca_certificates.append(ca_cert_b64)
                return True

            return False

        except Exception as e:
            logger.error(f"Invalid CA certificate: {str(e)}")
            return False


class MTLSValidator:
    """mTLS certificate validation"""

    def __init__(self):
        self._tenant_configs: Dict[str, MTLSConfig] = {}
        self._ca_stores: Dict[str, Any] = {}

    async def load_tenant_config(self, tenant_alias: str) -> MTLSConfig:
        """Load mTLS configuration for tenant"""

        if tenant_alias in self._tenant_configs:
            return self._tenant_configs[tenant_alias]

        # Load from storage
        config = await self._load_config_from_storage(tenant_alias)

        if not config:
            # Create default config (disabled)
            config = MTLSConfig(
                tenant_alias=tenant_alias,
                enabled=False
            )

        # Cache config
        self._tenant_configs[tenant_alias] = config

        # Build CA store
        await self._build_ca_store(tenant_alias)

        return config

    async def _load_config_from_storage(self, tenant_alias: str) -> Optional[MTLSConfig]:
        """Load mTLS config from persistent storage"""

        # In production, this would load from database/secrets
        # For now, return None to use defaults
        return None

    async def _build_ca_store(self, tenant_alias: str):
        """Build CA certificate store for validation"""

        config = self._tenant_configs.get(tenant_alias)
        if not config:
            return

        try:
            builder = StoreBuilder()

            # Add CA certificates to store
            for ca_cert_b64 in config.ca_certificates:
                ca_cert_pem = base64.b64decode(ca_cert_b64).decode()
                ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode(), default_backend())
                builder = builder.add_certs([ca_cert])

            # Build store
            store = builder.build()
            self._ca_stores[tenant_alias] = store

        except Exception as e:
            logger.error(f"Failed to build CA store for {tenant_alias}: {str(e)}")

    async def validate_client_certificate(
        self,
        tenant_alias: str,
        cert_pem: str,
        verify_chain: bool = True
    ) -> ClientCertificate:
        """Validate client certificate"""

        config = await self.load_tenant_config(tenant_alias)

        if not config.enabled:
            raise HTTPException(400, "mTLS not enabled for this tenant")

        try:
            # Parse client certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

            # Extract certificate information
            client_cert = self._extract_cert_info(cert, tenant_alias)

            # Validate certificate period
            if client_cert.is_expired:
                raise HTTPException(403, "Client certificate has expired")

            if not client_cert.is_valid_period:
                raise HTTPException(403, "Client certificate not yet valid")

            # Validate certificate chain if required
            if verify_chain and config.certificate_validation == "strict":
                await self._validate_certificate_chain(tenant_alias, cert)

            # Check allowed issuers
            if config.allowed_issuers:
                if client_cert.issuer not in config.allowed_issuers:
                    raise HTTPException(403, f"Certificate issuer not allowed: {client_cert.issuer}")

            # Perform CRL check if enabled
            if config.crl_check:
                await self._check_certificate_revocation(cert)

            # Perform OCSP check if enabled
            if config.ocsp_check:
                await self._check_ocsp_status(cert)

            logger.info(f"Client certificate validated for {tenant_alias}: {client_cert.common_name}")
            return client_cert

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Certificate validation failed for {tenant_alias}: {str(e)}")
            raise HTTPException(403, f"Certificate validation failed: {str(e)}")

    def _extract_cert_info(self, cert: x509.Certificate, tenant_alias: str) -> ClientCertificate:
        """Extract information from X.509 certificate"""

        # Extract subject components
        subject_components = {}
        for attribute in cert.subject:
            subject_components[attribute.oid._name] = attribute.value

        # Extract issuer
        issuer_components = {}
        for attribute in cert.issuer:
            issuer_components[attribute.oid._name] = attribute.value

        # Generate fingerprint
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()

        return ClientCertificate(
            common_name=subject_components.get("commonName", ""),
            organization=subject_components.get("organizationName"),
            organizational_unit=subject_components.get("organizationalUnitName"),
            country=subject_components.get("countryName"),
            serial_number=str(cert.serial_number),
            issuer=issuer_components.get("commonName", ""),
            subject=cert.subject.rfc4514_string(),
            valid_from=cert.not_valid_before,
            valid_to=cert.not_valid_after,
            fingerprint=fingerprint,
            tenant_alias=tenant_alias
        )

    async def _validate_certificate_chain(self, tenant_alias: str, cert: x509.Certificate):
        """Validate certificate chain against CA store"""

        ca_store = self._ca_stores.get(tenant_alias)
        if not ca_store:
            raise ValueError("No CA store configured for tenant")

        try:
            # Build verification policy
            builder = PolicyBuilder().store(ca_store)
            verifier = builder.build()

            # Verify certificate
            # Note: This is simplified - in production you'd validate the full chain
            chain = verifier.build_chain([cert])

            if not chain:
                raise ValueError("Certificate chain validation failed")

        except Exception as e:
            logger.error(f"Certificate chain validation failed: {str(e)}")
            raise

    async def _check_certificate_revocation(self, cert: x509.Certificate):
        """Check certificate revocation status via CRL"""

        # Implementation would fetch and check CRL
        # For now, this is a placeholder
        pass

    async def _check_ocsp_status(self, cert: x509.Certificate):
        """Check certificate status via OCSP"""

        # Implementation would perform OCSP check
        # For now, this is a placeholder
        pass

    async def enable_mtls(
        self,
        tenant_alias: str,
        ca_certificates: List[str],
        allowed_issuers: Optional[List[str]] = None
    ) -> bool:
        """Enable mTLS for tenant"""

        config = await self.load_tenant_config(tenant_alias)
        config.enabled = True
        config.required = True

        # Add CA certificates
        for ca_cert_pem in ca_certificates:
            config.add_ca_certificate(ca_cert_pem)

        if allowed_issuers:
            config.allowed_issuers = allowed_issuers

        # Save configuration
        await self._save_config_to_storage(config)

        # Rebuild CA store
        await self._build_ca_store(tenant_alias)

        logger.info(f"Enabled mTLS for tenant: {tenant_alias}")
        return True

    async def disable_mtls(self, tenant_alias: str) -> bool:
        """Disable mTLS for tenant"""

        config = await self.load_tenant_config(tenant_alias)
        config.enabled = False
        config.required = False

        # Save configuration
        await self._save_config_to_storage(config)

        logger.info(f"Disabled mTLS for tenant: {tenant_alias}")
        return True

    async def _save_config_to_storage(self, config: MTLSConfig):
        """Save mTLS configuration to persistent storage"""

        # In production, this would save to database/secrets
        pass

    def invalidate_cache(self, tenant_alias: str):
        """Invalidate cached configuration"""

        if tenant_alias in self._tenant_configs:
            del self._tenant_configs[tenant_alias]

        if tenant_alias in self._ca_stores:
            del self._ca_stores[tenant_alias]


# Global mTLS validator
_mtls_validator = MTLSValidator()


def extract_client_cert_from_request(request: Request) -> Optional[str]:
    """Extract client certificate from request headers"""

    # Check for certificate in headers (set by load balancer/proxy)
    cert_header = request.headers.get("x-client-cert")
    if cert_header:
        try:
            # Decode URL-encoded certificate
            import urllib.parse
            cert_pem = urllib.parse.unquote(cert_header)
            return cert_pem
        except Exception as e:
            logger.warning(f"Failed to decode client certificate: {str(e)}")

    # Check for certificate in SSL context (direct connection)
    # This would be available in direct HTTPS connections
    if hasattr(request, "scope") and "ssl" in request.scope:
        ssl_info = request.scope["ssl"]
        if "client_cert" in ssl_info:
            return ssl_info["client_cert"]

    return None


async def validate_mtls_for_tenant(tenant_alias: str, cert_pem: str) -> ClientCertificate:
    """Validate mTLS client certificate for tenant"""
    return await _mtls_validator.validate_client_certificate(tenant_alias, cert_pem)


class MTLSMiddleware:
    """FastAPI middleware for mTLS authentication"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation"""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Skip health checks and public endpoints
        path = request.url.path
        if path in ["/health", "/metrics", "/ready", "/docs", "/openapi.json"]:
            await self.app(scope, receive, send)
            return

        # Extract tenant from request
        from app.core.bankpilot.tenant_config import resolve_tenant_from_request
        tenant_config = await resolve_tenant_from_request(request)

        if tenant_config and tenant_config.mtls_enabled:
            # Extract client certificate
            cert_pem = extract_client_cert_from_request(request)

            if not cert_pem:
                if tenant_config.environment == "production":
                    # mTLS required in production
                    logger.warning(f"mTLS required but no client certificate provided for {tenant_config.alias}")

                    response = {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [
                            [b"content-type", b"application/json"],
                            [b"content-length", b"54"],
                        ],
                    }
                    await send(response)

                    response_body = {
                        "type": "http.response.body",
                        "body": b'{"error": "Client certificate required for authentication"}',
                    }
                    await send(response_body)
                    return

            else:
                # Validate client certificate
                try:
                    client_cert = await validate_mtls_for_tenant(tenant_config.alias, cert_pem)

                    # Add certificate info to request scope
                    scope["client_cert"] = client_cert.dict()

                    logger.info(f"mTLS authentication successful for {tenant_config.alias}: {client_cert.common_name}")

                except HTTPException as e:
                    logger.warning(f"mTLS authentication failed for {tenant_config.alias}: {e.detail}")

                    response = {
                        "type": "http.response.start",
                        "status": e.status_code,
                        "headers": [
                            [b"content-type", b"application/json"],
                            [b"content-length", str(len(e.detail) + 12).encode()],
                        ],
                    }
                    await send(response)

                    response_body = {
                        "type": "http.response.body",
                        "body": f'{{"error": "{e.detail}"}}'.encode(),
                    }
                    await send(response_body)
                    return

        # Continue with normal processing
        await self.app(scope, receive, send)


# Missing import fix
from cryptography.hazmat.primitives import hashes