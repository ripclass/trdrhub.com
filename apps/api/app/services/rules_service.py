"""
Rules Service Interface and Local Adapter

Provides a unified interface for fetching and evaluating rulesets.
Supports caching and future Rulhub integration.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class RulesService:
    """
    Interface for fetching and evaluating rulesets.
    
    Implementations:
    - LocalAdapter: Fetches from Supabase via API
    - RulhubAdapter: Fetches from Rulhub API (future)
    """
    
    async def get_active_ruleset(
        self, domain: str, jurisdiction: str = "global"
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
    
    def _get_cache_key(self, domain: str, jurisdiction: str) -> str:
        """Generate cache key for domain/jurisdiction combination."""
        return f"{domain}:{jurisdiction}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        age = datetime.now() - timestamp
        return age < timedelta(minutes=self.cache_ttl_minutes)
    
    def _clear_cache_entry(self, domain: str, jurisdiction: str):
        """Clear a specific cache entry."""
        cache_key = self._get_cache_key(domain, jurisdiction)
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
        logger.info(f"Cleared cache for {cache_key}")
    
    def clear_cache(self, domain: Optional[str] = None, jurisdiction: Optional[str] = None):
        """
        Clear cache entries.
        
        If domain/jurisdiction provided, clears only that entry.
        Otherwise clears all cache.
        """
        if domain and jurisdiction:
            self._clear_cache_entry(domain, jurisdiction)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all ruleset cache")
    
    async def get_active_ruleset(
        self, domain: str, jurisdiction: str = "global"
    ) -> Dict[str, Any]:
        """
        Fetch active ruleset from API with caching.
        
        Cache key: {domain}:{jurisdiction}
        Cache TTL: configurable (default 10 minutes)
        """
        cache_key = self._get_cache_key(domain, jurisdiction)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]
        
        # Fetch from API
        try:
            # Use internal DB access instead of HTTP for better performance
            # This avoids HTTP overhead when running in the same process
            from app.database import SessionLocal
            from app.models.ruleset import Ruleset, RulesetStatus
            from sqlalchemy import and_
            from app.services.rules_storage import RulesStorageService
            
            db = SessionLocal()
            try:
                ruleset = db.query(Ruleset).filter(
                    and_(
                        Ruleset.domain == domain,
                        Ruleset.jurisdiction == jurisdiction,
                        Ruleset.status == RulesetStatus.ACTIVE.value
                    )
                ).first()
                
                if not ruleset:
                    raise ValueError(f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}")
                
                # Fetch content from storage (synchronous call)
                storage_service = RulesStorageService()
                file_data = storage_service.get_ruleset_file(ruleset.file_path)
                rules_content = file_data.get("content", [])
                
                ruleset_metadata = {
                    "id": str(ruleset.id),
                    "domain": ruleset.domain,
                    "jurisdiction": ruleset.jurisdiction,
                    "ruleset_version": ruleset.ruleset_version,
                    "rulebook_version": ruleset.rulebook_version,
                    "file_path": ruleset.file_path,
                    "status": ruleset.status,
                    "rule_count": ruleset.rule_count,
                    "published_at": ruleset.published_at.isoformat() if ruleset.published_at else None,
                }
            finally:
                db.close()
            
            result = {
                "ruleset": ruleset_metadata,
                "rules": rules_content if isinstance(rules_content, list) else [],
                "ruleset_version": ruleset_metadata.get("ruleset_version", "unknown"),
                "rulebook_version": ruleset_metadata.get("rulebook_version", "unknown"),
            }
            
            # Update cache
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(f"Cached ruleset {cache_key} (rules: {len(result['rules'])})")
            
            return result
            
        except ValueError as e:
            # Re-raise ValueError (no active ruleset found)
            raise
        except Exception as e:
            logger.error(f"Failed to fetch ruleset {cache_key}: {e}")
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

