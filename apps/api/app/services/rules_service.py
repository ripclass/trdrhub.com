"""
Rules Service Interface and Local Adapter

Provides a unified interface for fetching and evaluating rulesets.
Supports caching and future Rulhub integration.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy import and_

from app.config import settings
from app.database import SessionLocal
from app.models.rule_record import RuleRecord
from app.models.ruleset import Ruleset, RulesetStatus

logger = logging.getLogger(__name__)


class RulesService:
    """
    Interface for fetching and evaluating rulesets.
    
    Implementations:
    - LocalAdapter: Fetches from Supabase via API
    - RulhubAdapter: Fetches from Rulhub API (future)
    """
    
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns active ruleset with rules array.
        
        Returns:
            {
                "ruleset": {...metadata...},
                "rules": [...array of rule objects...],
                "ruleset_version": "1.0.0",
                "rulebook_version": "UCP600:2007"
            }
        """
        raise NotImplementedError
    
    async def evaluate_rules(
        self, rules: List[Dict], input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates rules against document context.
        
        Returns:
            {
                "outcomes": [...],
                "violations": [...],
                "ruleset_version": "...",
                "rules_evaluated": N
            }
        """
        raise NotImplementedError


class LocalAdapter(RulesService):
    """
    Local adapter that fetches rulesets from Supabase via API.
    Includes in-memory caching with TTL.
    """
    
    def __init__(self, cache_ttl_minutes: int = 10):
        self.cache_ttl_minutes = cache_ttl_minutes
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._api_base_url = settings.API_BASE_URL or "http://localhost:8000"
    
    def _get_cache_key(self, domain: str, jurisdiction: str, document_type: Optional[str]) -> str:
        """Generate cache key for domain/jurisdiction/document_type combination."""
        doc_key = document_type or "*"
        return f"{domain}:{jurisdiction}:{doc_key}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        age = datetime.now() - timestamp
        return age < timedelta(minutes=self.cache_ttl_minutes)
    
    def _clear_cache_entry(self, domain: str, jurisdiction: str, document_type: Optional[str]):
        """Clear a specific cache entry."""
        cache_key = self._get_cache_key(domain, jurisdiction, document_type)
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
        logger.info(f"Cleared cache for {cache_key}")
    
    def clear_cache(
        self,
        domain: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        document_type: Optional[str] = None,
    ):
        """
        Clear cache entries.
        
        If domain/jurisdiction provided, clears only that entry.
        Otherwise clears all cache.
        """
        if domain and jurisdiction:
            self._clear_cache_entry(domain, jurisdiction, document_type)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all ruleset cache")
    
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch active ruleset from API with caching.
        
        Cache key: {domain}:{jurisdiction}
        Cache TTL: configurable (default 10 minutes)
        """
        cache_key = self._get_cache_key(domain, jurisdiction, document_type)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]
        
        try:
            db = SessionLocal()
            try:
                ruleset = (
                    db.query(Ruleset)
                    .filter(
                        and_(
                            Ruleset.domain == domain,
                            Ruleset.jurisdiction == jurisdiction,
                            Ruleset.status == RulesetStatus.ACTIVE.value,
                        )
                    )
                    .first()
                )

                if not ruleset:
                    logger.error("No active ruleset found", extra={"domain": domain, "jurisdiction": jurisdiction})
                    raise ValueError(f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}")

                query = (
                    db.query(RuleRecord)
                    .filter(
                        RuleRecord.ruleset_id == ruleset.id,
                        RuleRecord.domain == domain,
                        RuleRecord.is_active.is_(True),
                    )
                )
                if document_type:
                    query = query.filter(RuleRecord.document_type == document_type)

                records: List[RuleRecord] = query.all()

                normalized_rules = [self._normalize_rule_record(record) for record in records]
                sample_rule_ids = [rule["rule_id"] for rule in normalized_rules[:5]]
                logger.info(
                    "DB rules fetch summary",
                    extra={
                        "domain": domain,
                        "jurisdiction": jurisdiction,
                        "document_type": document_type or "*",
                        "rule_count": len(normalized_rules),
                        "sample_rule_ids": sample_rule_ids,
                    },
                )

                ruleset_metadata = {
                    "id": str(ruleset.id),
                    "domain": ruleset.domain,
                    "jurisdiction": ruleset.jurisdiction,
                    "ruleset_version": ruleset.ruleset_version,
                    "rulebook_version": ruleset.rulebook_version,
                    "status": ruleset.status,
                    "rule_count": len(normalized_rules),
                    "published_at": ruleset.published_at.isoformat() if ruleset.published_at else None,
                }
            finally:
                db.close()

            result = {
                "ruleset": ruleset_metadata,
                "rules": normalized_rules,
                "ruleset_version": ruleset_metadata.get("ruleset_version", "unknown"),
                "rulebook_version": ruleset_metadata.get("rulebook_version", "unknown"),
            }

            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(
                "Cached DB ruleset",
                extra={
                    "cache_key": cache_key,
                    "rule_count": len(normalized_rules),
                },
            )

            return result

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to fetch ruleset from DB", exc_info=True, extra={"cache_key": cache_key})
            raise
    
    async def evaluate_rules(
        self, rules: List[Dict], input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate rules against input context.
        
        This is a placeholder - actual evaluation is done by RuleEvaluator.
        This method exists for interface compatibility.
        """
        # Import here to avoid circular dependency
        from app.services.rule_evaluator import RuleEvaluator
        
        evaluator = RuleEvaluator()
        return await evaluator.evaluate_rules(rules, input_context)

    def _normalize_rule_record(self, record: RuleRecord) -> Dict[str, Any]:
        """Convert a RuleRecord ORM row into the evaluator-ready payload."""
        metadata = record.metadata or {}
        payload: Dict[str, Any] = {
            "rule_id": record.rule_id,
            "rule_version": record.rule_version,
            "article": record.article,
            "version": record.version,
            "domain": record.domain,
            "jurisdiction": record.jurisdiction,
            "document_type": record.document_type,
            "rule_type": record.rule_type,
            "severity": record.severity,
            "deterministic": record.deterministic,
            "requires_llm": record.requires_llm,
            "title": record.title,
            "reference": record.reference,
            "description": record.description,
            "conditions": record.conditions or [],
            "expected_outcome": record.expected_outcome or {},
            "tags": record.tags or [],
            "metadata": metadata,
            "checksum": record.checksum,
        }

        for key in ("documents", "supplements", "notes", "source"):
            value = metadata.get(key)
            if value is not None:
                payload[key] = value

        return payload


# Singleton instance
_rules_service: Optional[RulesService] = None


def get_rules_service() -> RulesService:
    """Get the configured rules service instance."""
    global _rules_service
    
    if _rules_service is None:
        # Check feature flag for Rulhub integration
        use_rulhub = getattr(settings, "USE_RULHUB_API", False)
        
        if use_rulhub:
            # Future: return RulhubAdapter()
            logger.warning("Rulhub integration not yet implemented, falling back to LocalAdapter")
        
        cache_ttl = getattr(settings, "RULESET_CACHE_TTL_MINUTES", 10)
        _rules_service = LocalAdapter(cache_ttl_minutes=cache_ttl)
        logger.info(f"Initialized RulesService (LocalAdapter, cache TTL: {cache_ttl}min)")
    
    return _rules_service

