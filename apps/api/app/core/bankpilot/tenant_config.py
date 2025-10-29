"""
Bank Pilot Tenant Configuration Management
Handles subdomain/instance config resolution and tenant-scoped settings
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging
import os
import json

logger = logging.getLogger(__name__)


class SLATier(str, Enum):
    DEMO = "demo"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class Environment(str, Enum):
    SANDBOX = "sandbox"
    UAT = "uat"
    PRODUCTION = "production"


class TenantConfig(BaseModel):
    """Bank pilot tenant configuration"""

    alias: str = Field(..., pattern=r"^[a-z0-9-]+$", max_length=32)
    name: str = Field(..., max_length=128)
    domain: str
    environment: Environment
    sla_tier: SLATier

    # Security settings
    mtls_enabled: bool = Field(default=False)
    ip_whitelist: List[str] = Field(default_factory=list)
    mfa_required: bool = Field(default=True)
    session_ttl_hours: int = Field(default=8, ge=1, le=24)

    # Feature flags
    features: List[str] = Field(default_factory=list)

    # Billing configuration
    billing_enabled: bool = Field(default=False)
    billing_model: str = Field(default="demo")
    rate_limit_per_hour: int = Field(default=1000)

    # Data residency
    data_region: str = Field(default="us-east-1")
    backup_regions: List[str] = Field(default_factory=list)
    encryption_enabled: bool = Field(default=True)

    # Observability
    metrics_enabled: bool = Field(default=True)
    logging_level: str = Field(default="INFO")
    tracing_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)

    # Metadata
    contact_email: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Labels for K8s and monitoring
    labels: Dict[str, str] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TenantResolver:
    """Resolves tenant configuration from request context"""

    def __init__(self):
        self._tenant_cache: Dict[str, TenantConfig] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_update: Dict[str, datetime] = {}

    async def resolve_from_request(self, request) -> Optional[TenantConfig]:
        """Resolve tenant config from incoming request"""

        # Check for subdomain-based tenant resolution
        host = request.headers.get("host", "")
        if host:
            tenant_alias = await self._extract_tenant_from_host(host)
            if tenant_alias:
                return await self.get_tenant_config(tenant_alias)

        # Check for header-based tenant resolution
        tenant_header = request.headers.get("x-tenant-id")
        if tenant_header:
            return await self.get_tenant_config(tenant_header)

        # Check for path-based tenant resolution
        path = request.url.path
        if path.startswith("/api/v1/tenant/"):
            path_segments = path.split("/")
            if len(path_segments) >= 5:
                tenant_alias = path_segments[4]
                return await self.get_tenant_config(tenant_alias)

        return None

    async def _extract_tenant_from_host(self, host: str) -> Optional[str]:
        """Extract tenant alias from hostname"""

        # Remove port if present
        host = host.split(":")[0]

        # Handle enterprise subdomain pattern: {tenant}.enterprise.trdrhub.com
        if ".enterprise.trdrhub.com" in host:
            tenant_alias = host.split(".")[0]
            return tenant_alias if tenant_alias != "enterprise" else None

        # Handle dedicated instance pattern: {tenant}-trdrhub.com
        if host.endswith("-trdrhub.com"):
            tenant_alias = host.replace("-trdrhub.com", "")
            return tenant_alias

        return None

    async def get_tenant_config(self, alias: str) -> Optional[TenantConfig]:
        """Get tenant configuration by alias"""

        # Check cache first
        if alias in self._tenant_cache:
            last_update = self._last_cache_update.get(alias)
            if last_update and (datetime.utcnow() - last_update).seconds < self._cache_ttl:
                return self._tenant_cache[alias]

        # Load from persistent storage
        config = await self._load_tenant_config(alias)

        if config:
            # Update cache
            self._tenant_cache[alias] = config
            self._last_cache_update[alias] = datetime.utcnow()

        return config

    async def _load_tenant_config(self, alias: str) -> Optional[TenantConfig]:
        """Load tenant configuration from storage"""

        try:
            # In production, this would load from database
            # For now, load from config files
            config_path = f"/etc/trdrhub/tenants/{alias}.json"

            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                return TenantConfig(**config_data)

            # Fallback to environment-based config
            return await self._load_from_environment(alias)

        except Exception as e:
            logger.error(f"Failed to load tenant config for {alias}: {str(e)}")
            return None

    async def _load_from_environment(self, alias: str) -> Optional[TenantConfig]:
        """Load tenant config from environment variables"""

        env_prefix = f"TENANT_{alias.upper().replace('-', '_')}_"

        # Check if this tenant is configured via environment
        if not os.getenv(f"{env_prefix}NAME"):
            return None

        try:
            config_data = {
                "alias": alias,
                "name": os.getenv(f"{env_prefix}NAME"),
                "domain": os.getenv(f"{env_prefix}DOMAIN", f"{alias}.enterprise.trdrhub.com"),
                "environment": os.getenv(f"{env_prefix}ENVIRONMENT", "sandbox"),
                "sla_tier": os.getenv(f"{env_prefix}SLA_TIER", "demo"),
                "mtls_enabled": os.getenv(f"{env_prefix}MTLS_ENABLED", "false").lower() == "true",
                "ip_whitelist": os.getenv(f"{env_prefix}IP_WHITELIST", "").split(",") if os.getenv(f"{env_prefix}IP_WHITELIST") else [],
                "billing_enabled": os.getenv(f"{env_prefix}BILLING_ENABLED", "false").lower() == "true",
                "data_region": os.getenv(f"{env_prefix}DATA_REGION", "us-east-1"),
                "contact_email": os.getenv(f"{env_prefix}CONTACT_EMAIL"),
                "created_by": os.getenv(f"{env_prefix}CREATED_BY", "system"),
                "created_at": datetime.utcnow().isoformat()
            }

            return TenantConfig(**config_data)

        except Exception as e:
            logger.error(f"Failed to load tenant config from environment for {alias}: {str(e)}")
            return None

    def invalidate_cache(self, alias: str):
        """Invalidate cached tenant config"""
        if alias in self._tenant_cache:
            del self._tenant_cache[alias]
        if alias in self._last_cache_update:
            del self._last_cache_update[alias]


# Global tenant resolver instance
_tenant_resolver = TenantResolver()


async def get_tenant_config(alias: str) -> Optional[TenantConfig]:
    """Get tenant configuration by alias"""
    return await _tenant_resolver.get_tenant_config(alias)


async def resolve_tenant_from_request(request) -> Optional[TenantConfig]:
    """Resolve tenant from request context"""
    return await _tenant_resolver.resolve_from_request(request)


def get_sla_labels(tenant_config: TenantConfig) -> Dict[str, str]:
    """Get SLA tier labels for metrics and monitoring"""

    return {
        "tenant": tenant_config.alias,
        "sla_tier": tenant_config.sla_tier,
        "environment": tenant_config.environment,
        "billing_enabled": str(tenant_config.billing_enabled).lower(),
        "data_region": tenant_config.data_region
    }


def get_tenant_resource_limits(sla_tier: SLATier) -> Dict[str, Any]:
    """Get resource limits based on SLA tier"""

    limits = {
        SLATier.DEMO: {
            "cpu_request": "250m",
            "cpu_limit": "500m",
            "memory_request": "256Mi",
            "memory_limit": "512Mi",
            "storage": "1Gi",
            "concurrent_requests": 10,
            "rate_limit_per_hour": 1000
        },
        SLATier.BRONZE: {
            "cpu_request": "500m",
            "cpu_limit": "1000m",
            "memory_request": "512Mi",
            "memory_limit": "1Gi",
            "storage": "10Gi",
            "concurrent_requests": 50,
            "rate_limit_per_hour": 5000
        },
        SLATier.SILVER: {
            "cpu_request": "1000m",
            "cpu_limit": "2000m",
            "memory_request": "1Gi",
            "memory_limit": "2Gi",
            "storage": "50Gi",
            "concurrent_requests": 100,
            "rate_limit_per_hour": 10000
        },
        SLATier.GOLD: {
            "cpu_request": "2000m",
            "cpu_limit": "4000m",
            "memory_request": "2Gi",
            "memory_limit": "4Gi",
            "storage": "100Gi",
            "concurrent_requests": 250,
            "rate_limit_per_hour": 25000
        },
        SLATier.PLATINUM: {
            "cpu_request": "4000m",
            "cpu_limit": "8000m",
            "memory_request": "4Gi",
            "memory_limit": "8Gi",
            "storage": "500Gi",
            "concurrent_requests": 500,
            "rate_limit_per_hour": 100000
        }
    }

    return limits.get(sla_tier, limits[SLATier.DEMO])


def get_sla_targets(sla_tier: SLATier) -> Dict[str, Any]:
    """Get SLA targets based on tier"""

    targets = {
        SLATier.DEMO: {
            "uptime_percentage": 99.0,
            "response_time_p95_ms": 1000,
            "response_time_p99_ms": 2000,
            "error_rate_threshold": 5.0,
            "support_hours": "business",
            "maintenance_window": "weekends"
        },
        SLATier.BRONZE: {
            "uptime_percentage": 99.5,
            "response_time_p95_ms": 800,
            "response_time_p99_ms": 1500,
            "error_rate_threshold": 3.0,
            "support_hours": "extended",
            "maintenance_window": "planned"
        },
        SLATier.SILVER: {
            "uptime_percentage": 99.8,
            "response_time_p95_ms": 500,
            "response_time_p99_ms": 1000,
            "error_rate_threshold": 2.0,
            "support_hours": "24x5",
            "maintenance_window": "planned"
        },
        SLATier.GOLD: {
            "uptime_percentage": 99.9,
            "response_time_p95_ms": 300,
            "response_time_p99_ms": 500,
            "error_rate_threshold": 1.0,
            "support_hours": "24x7",
            "maintenance_window": "emergency-only"
        },
        SLATier.PLATINUM: {
            "uptime_percentage": 99.95,
            "response_time_p95_ms": 200,
            "response_time_p99_ms": 300,
            "error_rate_threshold": 0.5,
            "support_hours": "24x7",
            "maintenance_window": "emergency-only"
        }
    }

    return targets.get(sla_tier, targets[SLATier.DEMO])