"""
RulHub API Client — TRDR Hub's interface to the RulHub compliance engine.

Hard rules:
1. All calls are server-side only. Never expose the API key to the browser.
2. Never duplicate rule logic in TRDR Hub — RulHub is the authority.
3. Cache reference data (schemas, country data) 24h. Never cache validation/screening.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Reference data cache: key -> (data, expiry_ts)
_REF_CACHE: Dict[str, tuple] = {}
_REF_CACHE_TTL = 86400  # 24 hours


def _cache_get(key: str) -> Optional[Any]:
    entry = _REF_CACHE.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _cache_set(key: str, data: Any) -> None:
    _REF_CACHE[key] = (data, time.time() + _REF_CACHE_TTL)


class RulHubAPIError(Exception):
    """Raised when RulHub returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"RulHub API {status_code}: {detail}")


class RulHubRateLimited(RulHubAPIError):
    """429 — caller should show upgrade prompt."""
    pass


class RulHubClient:
    """
    Async HTTP client for the RulHub compliance API.

    Usage:
        client = RulHubClient()
        result = await client.validate_document(fields, "commercial_invoice", "ae")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.RULHUB_API_URL or "https://api.rulhub.com").rstrip("/")
        self.api_key = api_key or settings.RULHUB_API_KEY or ""
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        try:
            resp = await client.request(method, path, json=json, params=params)
        except httpx.TimeoutException:
            logger.error("RulHub request timed out: %s %s", method, path)
            raise RulHubAPIError(504, f"Timeout calling {path}")
        except httpx.ConnectError as exc:
            logger.error("RulHub connection failed: %s", exc)
            raise RulHubAPIError(503, "RulHub unreachable")

        if resp.status_code == 429:
            raise RulHubRateLimited(429, "Rate limited — upgrade plan")
        if resp.status_code == 401:
            raise RulHubAPIError(401, "Invalid API key")
        if resp.status_code == 422:
            detail = resp.text[:500]
            raise RulHubAPIError(422, f"Bad request: {detail}")
        if resp.status_code >= 500:
            raise RulHubAPIError(resp.status_code, "RulHub server error")
        if resp.status_code >= 400:
            raise RulHubAPIError(resp.status_code, resp.text[:500])

        return resp.json()

    # -------------------------------------------------------------------------
    # Validation endpoints (NEVER cache)
    # -------------------------------------------------------------------------

    async def validate_document(
        self,
        document_fields: Dict[str, Any],
        document_type: str,
        jurisdiction: str = "global",
        rules: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /v1/validate — single-document validation.

        Returns:
            {
                "data": {
                    "discrepancies": [
                        {"rule_id", "severity", "finding", "expected", ...}
                    ],
                    "rules_evaluated": N,
                    ...
                }
            }
        """
        payload: Dict[str, Any] = {
            "document": document_fields,
            "document_type": document_type,
            "jurisdiction": jurisdiction,
        }
        if rules:
            payload["rules"] = rules
        result = await self._request("POST", "/v1/validate", json=payload)
        return result.get("data", result)

    async def validate_document_set(
        self,
        documents: List[Dict[str, Any]],
        jurisdiction: str = "global",
    ) -> Dict[str, Any]:
        """
        POST /v1/validate/set — multi-document cross-validation.

        Each document in the list should have:
            {"document_type": "...", "fields": {...}}

        Returns:
            {
                "data": {
                    "discrepancies": [...],
                    "cross_doc_issues": [...],
                    ...
                }
            }
        """
        payload = {
            "documents": documents,
            "jurisdiction": jurisdiction,
        }
        result = await self._request("POST", "/v1/validate/set", json=payload)
        return result.get("data", result)

    # -------------------------------------------------------------------------
    # Screening endpoints (NEVER cache)
    # -------------------------------------------------------------------------

    async def screen_sanctions(self, parties: List[Dict[str, str]]) -> Dict[str, Any]:
        """POST /v1/screen/sanctions — OFAC/EU/UN/UK screening."""
        result = await self._request("POST", "/v1/screen/sanctions", json={"parties": parties})
        return result.get("data", result)

    async def screen_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/screen/entity — UBO/PEP/shell company."""
        result = await self._request("POST", "/v1/screen/entity", json=entity)
        return result.get("data", result)

    async def screen_tbml(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/screen/tbml — trade-based money laundering red flags."""
        result = await self._request("POST", "/v1/screen/tbml", json=transaction)
        return result.get("data", result)

    async def screen_route(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/screen/route — route + vessel risk."""
        result = await self._request("POST", "/v1/screen/route", json=route)
        return result.get("data", result)

    # -------------------------------------------------------------------------
    # Rules search (NEVER cache — results depend on query)
    # -------------------------------------------------------------------------

    async def search_rules(self, query: str, **kwargs) -> Dict[str, Any]:
        """POST /v1/rules/search — keyword search across 6,000 rules."""
        payload = {"query": query, **kwargs}
        result = await self._request("POST", "/v1/rules/search", json=payload)
        return result.get("data", result)

    # -------------------------------------------------------------------------
    # Reference data (cached 24h)
    # -------------------------------------------------------------------------

    async def get_schemas(self) -> Dict[str, Any]:
        """GET /v1/data/schemas — document field schemas."""
        cached = _cache_get("schemas")
        if cached is not None:
            return cached
        result = await self._request("GET", "/v1/data/schemas")
        data = result.get("data", result)
        _cache_set("schemas", data)
        return data

    async def get_country_requirements(self) -> Dict[str, Any]:
        """GET /v1/data/country-requirements — 58 countries."""
        cached = _cache_get("country_requirements")
        if cached is not None:
            return cached
        result = await self._request("GET", "/v1/data/country-requirements")
        data = result.get("data", result)
        _cache_set("country_requirements", data)
        return data


# ---------------------------------------------------------------------------
# RulHub adapter that implements the RulesService interface
# ---------------------------------------------------------------------------

def _flatten_for_rulhub(raw: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    """Flatten the massive db_rule_payload into RulHub's expected shape.

    RulHub expects: {"beneficiary_name": "...", "amount": 150000, ...}
    We receive: {"lc": {nested...}, "extracted_context": {nested...}, ...}
    """
    flat: Dict[str, Any] = {}

    # Extract LC fields from the "lc" or "credit" sub-dict
    lc = raw.get("lc") or raw.get("credit") or {}
    if isinstance(lc, dict):
        for key in (
            "lc_number", "number", "amount", "currency", "expiry_date",
            "issue_date", "latest_shipment_date", "goods_description",
            "port_of_loading", "port_of_discharge", "partial_shipments",
            "transshipment", "incoterm", "payment_terms",
            "documents_required", "additional_conditions",
            "available_with", "available_by",
        ):
            val = lc.get(key)
            if val is not None and val != "" and val != []:
                # Unwrap dict-shaped amounts/parties to scalar
                if isinstance(val, dict) and "value" in val:
                    flat[key] = val["value"]
                elif isinstance(val, dict) and "name" in val:
                    flat[key] = val["name"]
                else:
                    flat[key] = val

        # Parties — flatten from dict to name string
        for party_key in ("applicant", "beneficiary", "issuing_bank", "advising_bank"):
            party = lc.get(party_key)
            if isinstance(party, dict):
                flat[f"{party_key}_name"] = party.get("name", "")
                flat[f"{party_key}_address"] = party.get("address", "")
            elif isinstance(party, str) and party:
                flat[f"{party_key}_name"] = party

    # Extract per-doc-type fields from payload keys
    for dtype in ("invoice", "bill_of_lading", "insurance", "certificate_of_origin", "packing_list"):
        doc_data = raw.get(dtype)
        if isinstance(doc_data, dict):
            for k, v in doc_data.items():
                if k.startswith("_"):
                    continue
                if v is None or v == "" or v == []:
                    continue
                flat[f"{dtype}_{k}"] = v

    # Top-level scalars that the caller already extracted.
    # NEVER include "jurisdiction", "domain", "version", "metadata",
    # or "taxonomy" here — rulhub's validate_v1 helper auto-promotes
    # those keys from the document body to hard SQL filters
    # (Rule.domain == X, Rule.version == X, etc., exact equality).
    # trdrhub's internal "domain" is "icc.ucp600" but the seeded rules
    # use "icc_core" — sending ours strips all matches to zero.
    # Jurisdiction is already passed as a top-level HTTP payload field.
    for key in ("lc_number", "amount", "currency", "expiry_date"):
        val = raw.get(key)
        if val is not None and val != "" and key not in flat:
            flat[key] = val

    return flat


class RulHubRulesAdapter:
    """
    RulesService-compatible adapter backed by the RulHub API.

    Drop-in replacement for DBRulesAdapter in get_rules_service().
    Delegates rule evaluation to RulHub — no local rule logic.
    """

    def __init__(self, client: Optional[RulHubClient] = None):
        self.client = client or RulHubClient()

    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch schemas from RulHub as the 'ruleset' equivalent."""
        try:
            schemas = await self.client.get_schemas()
            return {
                "ruleset": {
                    "id": "rulhub",
                    "domain": domain,
                    "jurisdiction": jurisdiction,
                    "ruleset_version": "api",
                    "rulebook_version": "UCP600:2007",
                    "status": "active",
                    "source": "rulhub_api",
                },
                "rules": [],  # rules are evaluated server-side by RulHub
                "ruleset_version": "api",
                "rulebook_version": "UCP600:2007",
                "schemas": schemas,
            }
        except RulHubAPIError as exc:
            logger.warning("RulHub get_active_ruleset failed: %s", exc)
            return None

    async def evaluate_rules(
        self, rules: List[Dict], input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delegate rule evaluation to RulHub POST /v1/validate.

        Maps the input_context to the RulHub API shape and returns
        discrepancies in the IssueEngine-compatible format.
        """
        doc_type = input_context.get("document_type", "lc")
        jurisdiction = input_context.get("jurisdiction", "global")
        rules_family = input_context.get("rules")
        raw_fields = input_context.get("fields", input_context)

        # Flatten the massive db_rule_payload into the clean shape
        # RulHub expects: {field: scalar_value, ...}
        flat = _flatten_for_rulhub(raw_fields, doc_type)

        try:
            result = await self.client.validate_document(
                flat, doc_type, jurisdiction, rules=rules_family,
            )
            discrepancies = result.get("discrepancies", [])

            # Map RulHub discrepancies to our internal finding shape
            findings = []
            for d in discrepancies:
                findings.append({
                    "rule_id": d.get("rule_id", ""),
                    "severity": d.get("severity", "major"),
                    "title": d.get("finding", d.get("title", "")),
                    "expected": d.get("expected", ""),
                    "found": d.get("found", d.get("actual", "")),
                    "description": d.get("explanation", d.get("description", "")),
                    "suggested_fix": d.get("suggested_fix", ""),
                    "ucp_reference": d.get("rule", d.get("ucp_reference", "")),
                    "source_layer": "rulhub_deterministic",
                    "document_type": doc_type,
                })

            return {
                "outcomes": findings,
                "violations": [f for f in findings if f["severity"] in ("critical", "major")],
                "ruleset_version": "rulhub_api",
                "rules_evaluated": result.get("rules_evaluated", len(findings)),
            }
        except RulHubRateLimited:
            logger.warning("RulHub rate limited during evaluate_rules")
            raise  # Let caller fall back to DB rules
        except RulHubAPIError as exc:
            logger.error("RulHub evaluate_rules failed: %s", exc)
            raise  # Let caller fall back to DB rules + Opus veto

    async def validate_document_set(
        self,
        documents: List[Dict[str, Any]],
        jurisdiction: str = "global",
    ) -> Dict[str, Any]:
        """
        Cross-document validation via POST /v1/validate/set.

        This is the new capability — RulHub does cross-doc matching
        (amount consistency, party names, dates, ports, goods).
        """
        try:
            return await self.client.validate_document_set(documents, jurisdiction)
        except RulHubAPIError as exc:
            logger.error("RulHub validate_document_set failed: %s", exc)
            return {"discrepancies": [], "cross_doc_issues": [], "_error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_client: Optional[RulHubClient] = None


def get_rulhub_client() -> RulHubClient:
    """Get or create the singleton RulHub client."""
    global _client
    if _client is None:
        _client = RulHubClient()
    return _client
