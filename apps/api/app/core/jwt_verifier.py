"""Utility helpers for verifying third-party JWTs (Supabase/Auth0/etc)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
from jose import jwt


JWKS_CACHE: Dict[str, Dict[str, Any]] = {}


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
        self.audience = audience
        # Support both RSA and EC JWTs (Supabase may issue ES256)
        self.algorithms = algorithms or ["RS256", "ES256"]


async def _get_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch JWKS (JSON Web Key Set) with a simple TTL cache."""

    now = int(time.time())
    cached = JWKS_CACHE.get(jwks_url)
    if cached and cached["exp"] > now:
        return cached["data"]

    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        data = response.json()

    JWKS_CACHE[jwks_url] = {"data": data, "exp": now + 3600}
    return data


def _match_provider(issuer: str, providers: List[ProviderConfig]) -> Optional[ProviderConfig]:
    issuer = issuer.rstrip("/")
    for provider in providers:
        if provider.issuer == issuer:
            return provider
    return None


async def verify_jwt(token: str, providers: List[ProviderConfig]) -> Dict[str, Any]:
    """Verify JWT using configured providers.

    Returns decoded claims on success, raises jose.JWTError on failure.
    """

    unverified_claims = jwt.get_unverified_claims(token)
    issuer = unverified_claims.get("iss")
    if not issuer:
        raise ValueError("Missing iss claim")

    provider = _match_provider(issuer, providers)
    if not provider:
        raise ValueError("Unknown token issuer")

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = await _get_jwks(provider.jwks_url)
    keys = jwks.get("keys", [])
    key = next((k for k in keys if k.get("kid") == kid), None)
    if not key:
        raise ValueError("No matching signing key")

    claims = jwt.decode(
        token,
        key,
        algorithms=provider.algorithms,
        audience=provider.audience,
        options={"verify_aud": provider.audience is not None, "verify_exp": True},
    )

    return {"claims": claims, "provider": provider}


