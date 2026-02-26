"""Utility helpers for verifying third-party JWTs (Supabase/Auth0/etc)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from jose import jwt


logger = logging.getLogger(__name__)

# Cache JWKS responses keyed by URL.  Entries include a TTL so stale keys
# are refreshed automatically.  The cache is invalidated on kid-miss so that
# key rotation is handled without a restart.
JWKS_CACHE: Dict[str, Dict[str, Any]] = {}

# How long (seconds) to cache a JWKS document before re-fetching.
_JWKS_TTL = 3600
# Per-request timeout when fetching JWKS from the identity provider.
_JWKS_TIMEOUT = 10


class ProviderConfig:
    """Configuration describing a remote identity provider."""

    def __init__(
        self,
        name: str,
        issuer: str,
        jwks_url: str,
        audience: Optional[str] = None,
        algorithms: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.issuer = issuer.rstrip("/")
        self.jwks_url = jwks_url
        # None means "do not verify audience" – safe default for Supabase
        # which issues tokens with aud="authenticated" but the value is not
        # always configured on the backend.
        self.audience = audience or None
        # Support both RSA and EC JWTs (Supabase issues ES256)
        self.algorithms = algorithms or ["RS256", "ES256"]


async def _get_jwks(jwks_url: str, *, force_refresh: bool = False) -> Dict[str, Any]:
    """Fetch JWKS (JSON Web Key Set) with a simple TTL cache.

    Args:
        jwks_url: URL of the JWKS endpoint.
        force_refresh: When ``True``, bypass the cache and fetch fresh keys.
            Use this after a kid-miss to handle key rotation.
    """

    now = int(time.time())
    cached = JWKS_CACHE.get(jwks_url)
    if not force_refresh and cached and cached["exp"] > now:
        return cached["data"]

    logger.debug("Fetching JWKS from %s (force_refresh=%s)", jwks_url, force_refresh)
    async with httpx.AsyncClient(timeout=_JWKS_TIMEOUT) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        data = response.json()

    JWKS_CACHE[jwks_url] = {"data": data, "exp": now + _JWKS_TTL}
    return data


def _match_provider(issuer: str, providers: List[ProviderConfig]) -> Optional[ProviderConfig]:
    """Return the provider whose issuer matches ``issuer`` (trailing-slash-safe)."""
    issuer = issuer.rstrip("/")
    for provider in providers:
        if provider.issuer == issuer:
            return provider
    # Loose match: check if issuer starts-with provider issuer (handles sub-paths).
    for provider in providers:
        if issuer.startswith(provider.issuer):
            return provider
    return None


async def verify_jwt(token: str, providers: List[ProviderConfig]) -> Dict[str, Any]:
    """Verify JWT using configured providers.

    Tries each provider in order.  Handles JWKS key rotation by re-fetching
    when a ``kid`` is not found in the cached key set.

    Returns decoded claims on success, raises ``jose.JWTError`` or
    ``ValueError`` on failure.
    """

    unverified_claims = jwt.get_unverified_claims(token)
    issuer = (unverified_claims.get("iss") or "").rstrip("/")
    if not issuer:
        raise ValueError("Missing iss claim in token")

    provider = _match_provider(issuer, providers)
    if not provider:
        raise ValueError(
            f"Unknown token issuer '{issuer}'. "
            f"Configured issuers: {[p.issuer for p in providers]}"
        )

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    # First attempt with cached JWKS.
    jwks = await _get_jwks(provider.jwks_url)
    keys = jwks.get("keys", [])
    key = next((k for k in keys if k.get("kid") == kid), None)

    # Kid not found – rotate: re-fetch JWKS once.
    if key is None:
        logger.info(
            "kid '%s' not in cached JWKS for %s – refreshing key set", kid, provider.jwks_url
        )
        jwks = await _get_jwks(provider.jwks_url, force_refresh=True)
        keys = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), None)

    if key is None:
        raise ValueError(
            f"No matching signing key for kid='{kid}' in JWKS at {provider.jwks_url}"
        )

    # Audience verification: skip when not configured to avoid false rejections.
    # Supabase sets aud="authenticated" by default; callers can still opt-in by
    # setting SUPABASE_AUDIENCE.
    verify_aud = provider.audience is not None
    decode_options: Dict[str, Any] = {
        "verify_aud": verify_aud,
        "verify_exp": True,
    }

    claims = jwt.decode(
        token,
        key,
        algorithms=provider.algorithms,
        audience=provider.audience,
        options=decode_options,
    )

    return {"claims": claims, "provider": provider}


