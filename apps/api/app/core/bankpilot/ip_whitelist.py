"""
IP Whitelist Management for Bank Pilot
CIDR-based allow/deny management with tenant scoping
"""

from typing import List, Optional, Set, Dict, Any
from ipaddress import IPv4Network, IPv6Network, AddressValueError, ip_address
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Request
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IPWhitelistRule(BaseModel):
    """IP whitelist rule definition"""

    cidr: str = Field(..., description="CIDR notation (e.g., 192.168.1.0/24)")
    description: str = Field(..., max_length=256)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    tenant_alias: str

    @validator("cidr")
    def validate_cidr(cls, v):
        """Validate CIDR notation"""
        try:
            # Try IPv4 first
            IPv4Network(v, strict=False)
            return v
        except AddressValueError:
            try:
                # Try IPv6
                IPv6Network(v, strict=False)
                return v
            except AddressValueError:
                raise ValueError(f"Invalid CIDR notation: {v}")

    class Config:
        use_enum_values = True


class IPWhitelistConfig(BaseModel):
    """Tenant IP whitelist configuration"""

    tenant_alias: str
    enabled: bool = Field(default=True)
    default_action: str = Field(default="deny", pattern="^(allow|deny)$")
    rules: List[IPWhitelistRule] = Field(default_factory=list)
    bypass_internal: bool = Field(default=True)
    log_blocked_requests: bool = Field(default=True)
    rate_limit_blocked: bool = Field(default=True)

    def add_rule(self, cidr: str, description: str, created_by: str) -> IPWhitelistRule:
        """Add new whitelist rule"""
        rule = IPWhitelistRule(
            cidr=cidr,
            description=description,
            created_by=created_by,
            tenant_alias=self.tenant_alias
        )
        self.rules.append(rule)
        return rule

    def remove_rule(self, cidr: str) -> bool:
        """Remove whitelist rule by CIDR"""
        original_count = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.cidr != cidr]
        return len(self.rules) < original_count

    def get_active_cidrs(self) -> List[str]:
        """Get list of active CIDR blocks"""
        return [rule.cidr for rule in self.rules if rule.enabled]


class IPWhitelistManager:
    """Manages IP whitelist rules and validation"""

    def __init__(self):
        self._tenant_configs: Dict[str, IPWhitelistConfig] = {}
        self._compiled_networks: Dict[str, List[Any]] = {}

    async def load_tenant_config(self, tenant_alias: str) -> IPWhitelistConfig:
        """Load IP whitelist configuration for tenant"""

        if tenant_alias in self._tenant_configs:
            return self._tenant_configs[tenant_alias]

        # Load from storage (database/config files)
        config = await self._load_config_from_storage(tenant_alias)

        if not config:
            # Create default config
            config = IPWhitelistConfig(
                tenant_alias=tenant_alias,
                enabled=False,  # Disabled by default
                default_action="deny"
            )

        # Cache config
        self._tenant_configs[tenant_alias] = config

        # Compile networks for performance
        await self._compile_networks(tenant_alias)

        return config

    async def _load_config_from_storage(self, tenant_alias: str) -> Optional[IPWhitelistConfig]:
        """Load configuration from persistent storage"""

        # In production, this would load from database
        # For now, return None to use defaults
        return None

    async def _compile_networks(self, tenant_alias: str):
        """Pre-compile IP networks for fast lookup"""

        config = self._tenant_configs.get(tenant_alias)
        if not config:
            return

        networks = []
        for rule in config.rules:
            if rule.enabled:
                try:
                    # Try IPv4 first
                    network = IPv4Network(rule.cidr, strict=False)
                    networks.append(network)
                except AddressValueError:
                    try:
                        # Try IPv6
                        network = IPv6Network(rule.cidr, strict=False)
                        networks.append(network)
                    except AddressValueError:
                        logger.warning(f"Invalid CIDR in rule: {rule.cidr}")

        self._compiled_networks[tenant_alias] = networks

    async def validate_ip(self, tenant_alias: str, client_ip: str) -> bool:
        """Validate if client IP is allowed"""

        config = await self.load_tenant_config(tenant_alias)

        # If IP whitelisting is disabled, allow all
        if not config.enabled:
            return True

        # Check for internal/private IPs if bypass is enabled
        if config.bypass_internal and self._is_internal_ip(client_ip):
            return True

        # Parse client IP
        try:
            client_addr = ip_address(client_ip)
        except AddressValueError:
            logger.warning(f"Invalid client IP address: {client_ip}")
            return False

        # Check against compiled networks
        networks = self._compiled_networks.get(tenant_alias, [])

        for network in networks:
            if client_addr in network:
                return True

        # Default action
        return config.default_action == "allow"

    def _is_internal_ip(self, ip_str: str) -> bool:
        """Check if IP is internal/private"""

        try:
            addr = ip_address(ip_str)

            # Check for private IPv4 ranges
            private_v4_networks = [
                IPv4Network("10.0.0.0/8"),
                IPv4Network("172.16.0.0/12"),
                IPv4Network("192.168.0.0/16"),
                IPv4Network("127.0.0.0/8"),  # Loopback
            ]

            if addr.version == 4:
                for network in private_v4_networks:
                    if addr in network:
                        return True

            # Check for private IPv6 ranges
            if addr.version == 6:
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    return True

            return False

        except AddressValueError:
            return False

    async def add_whitelist_rule(
        self,
        tenant_alias: str,
        cidr: str,
        description: str,
        created_by: str
    ) -> IPWhitelistRule:
        """Add new whitelist rule"""

        config = await self.load_tenant_config(tenant_alias)
        rule = config.add_rule(cidr, description, created_by)

        # Save to storage
        await self._save_config_to_storage(config)

        # Recompile networks
        await self._compile_networks(tenant_alias)

        logger.info(f"Added IP whitelist rule for {tenant_alias}: {cidr}")
        return rule

    async def remove_whitelist_rule(self, tenant_alias: str, cidr: str) -> bool:
        """Remove whitelist rule"""

        config = await self.load_tenant_config(tenant_alias)
        removed = config.remove_rule(cidr)

        if removed:
            # Save to storage
            await self._save_config_to_storage(config)

            # Recompile networks
            await self._compile_networks(tenant_alias)

            logger.info(f"Removed IP whitelist rule for {tenant_alias}: {cidr}")

        return removed

    async def enable_whitelist(self, tenant_alias: str) -> bool:
        """Enable IP whitelisting for tenant"""

        config = await self.load_tenant_config(tenant_alias)
        config.enabled = True

        # Save to storage
        await self._save_config_to_storage(config)

        logger.info(f"Enabled IP whitelisting for {tenant_alias}")
        return True

    async def disable_whitelist(self, tenant_alias: str) -> bool:
        """Disable IP whitelisting for tenant"""

        config = await self.load_tenant_config(tenant_alias)
        config.enabled = False

        # Save to storage
        await self._save_config_to_storage(config)

        logger.info(f"Disabled IP whitelisting for {tenant_alias}")
        return True

    async def _save_config_to_storage(self, config: IPWhitelistConfig):
        """Save configuration to persistent storage"""

        # In production, this would save to database
        pass

    def invalidate_cache(self, tenant_alias: str):
        """Invalidate cached configuration"""

        if tenant_alias in self._tenant_configs:
            del self._tenant_configs[tenant_alias]

        if tenant_alias in self._compiled_networks:
            del self._compiled_networks[tenant_alias]


# Global IP whitelist manager
_ip_whitelist_manager = IPWhitelistManager()


async def validate_client_ip(tenant_alias: str, client_ip: str) -> bool:
    """Validate if client IP is whitelisted for tenant"""
    return await _ip_whitelist_manager.validate_ip(tenant_alias, client_ip)


async def add_ip_whitelist_rule(
    tenant_alias: str,
    cidr: str,
    description: str,
    created_by: str
) -> IPWhitelistRule:
    """Add IP whitelist rule for tenant"""
    return await _ip_whitelist_manager.add_whitelist_rule(
        tenant_alias, cidr, description, created_by
    )


async def remove_ip_whitelist_rule(tenant_alias: str, cidr: str) -> bool:
    """Remove IP whitelist rule for tenant"""
    return await _ip_whitelist_manager.remove_whitelist_rule(tenant_alias, cidr)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers"""

    # Check for forwarded headers (proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection
    client_host = request.client.host if request.client else "unknown"
    return client_host


class IPWhitelistMiddleware:
    """FastAPI middleware for IP whitelisting"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation"""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Skip health checks and internal endpoints
        path = request.url.path
        if path in ["/health", "/metrics", "/ready"]:
            await self.app(scope, receive, send)
            return

        # Extract tenant from request
        from app.core.bankpilot.tenant_config import resolve_tenant_from_request
        tenant_config = await resolve_tenant_from_request(request)

        if tenant_config:
            # Get client IP
            client_ip = get_client_ip(request)

            # Validate IP whitelist
            is_allowed = await validate_client_ip(tenant_config.alias, client_ip)

            if not is_allowed:
                # Log blocked request
                logger.warning(
                    f"IP blocked for tenant {tenant_config.alias}: "
                    f"client_ip={client_ip}, path={path}"
                )

                # Return 403 Forbidden
                response = {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"content-length", b"46"],
                    ],
                }
                await send(response)

                response_body = {
                    "type": "http.response.body",
                    "body": b'{"error": "Access denied - IP not whitelisted"}',
                }
                await send(response_body)
                return

        # Continue with normal processing
        await self.app(scope, receive, send)