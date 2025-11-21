"""
Rules Service Interface and DB-backed Adapter

Provides a unified interface for fetching and evaluating rulesets.
Uses the normalized `rules` table (RuleRecord) as the source of truth.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy import and_, desc, nullslast
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.rule_record import RuleRecord
from app.models.ruleset import Ruleset, RulesetStatus

logger = logging.getLogger(__name__)


class RulesService:
    """
    Interface for fetching and evaluating rulesets.
    
    Implementations:
    - DBRulesAdapter: Fetches from Postgres `rules` table (production)
    - RulhubAdapter: Fetches from Rulhub API (future)
    """
    
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns active ruleset with rules array.
        
        Returns:
            {
                "ruleset": {...metadata...},
                "rules": [...array of rule objects...],
                "ruleset_version": "1.0.0",
                "rulebook_version": "UCP600:2007"
            }
            
        Returns None if no active ruleset found for the domain/jurisdiction.
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


class DBRulesAdapter(RulesService):
    """
    DB-backed adapter that fetches rulesets directly from the `rules` table.
    Includes in-memory caching with TTL.
    
    This is the production adapter - rules are stored in Postgres and loaded
    via SQLAlchemy queries, not from JSON files.
    """
    
    def __init__(self, cache_ttl_minutes: int = 10):
        self.cache_ttl_minutes = cache_ttl_minutes
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
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
            cache_key = self._get_cache_key(domain, jurisdiction, document_type)
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            logger.info(f"Cleared cache for {cache_key}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all ruleset cache")
    
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch active ruleset from DB with caching.
        
        Returns None if no active ruleset found (allows validator to skip gracefully).
        """
        cache_key = self._get_cache_key(domain, jurisdiction, document_type)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]
        
        db = SessionLocal()
        try:
            # 1) Find the active ruleset for domain/jurisdiction
            # Order by effective_from (newest first), then created_at (newest first)
            ruleset = (
                db.query(Ruleset)
                .filter(
                    and_(
                        Ruleset.domain == domain,
                        Ruleset.jurisdiction == (jurisdiction or "global"),
                        Ruleset.status == RulesetStatus.ACTIVE.value,
                    )
                )
                .order_by(
                    nullslast(desc(Ruleset.effective_from)),
                    desc(Ruleset.created_at)
                )
                .first()
            )
            
            if not ruleset:
                logger.warning(
                    f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}"
                )
                return None
            
            # 2) Load rules from the `rules` table
            query = (
                db.query(RuleRecord)
                .filter(
                    and_(
                        RuleRecord.ruleset_id == ruleset.id,
                        RuleRecord.is_active.is_(True),
                    )
                )
                .order_by(
                    nullslast(RuleRecord.article.asc()),
                    RuleRecord.rule_id.asc()
                )
            )
            
            if document_type:
                query = query.filter(RuleRecord.document_type == document_type)
            
            rules_rows: List[RuleRecord] = query.all()
            
            # 3) Guardrail: Warn if ruleset has no rules
            if not rules_rows:
                logger.warning(
                    f"Active ruleset {ruleset.id} has 0 rules; check ingestion.",
                    extra={
                        "ruleset_id": str(ruleset.id),
                        "domain": domain,
                        "jurisdiction": jurisdiction,
                    }
                )
            
            # 4) Map DB rows to validator-ready structure
            rules_payload = [self._normalize_rule_record(row) for row in rules_rows]
            
            sample_rule_ids = [rule["rule_id"] for rule in rules_payload[:5]]
            logger.info(
                "DB rules fetch summary",
                extra={
                    "domain": domain,
                    "jurisdiction": jurisdiction,
                    "document_type": document_type or "*",
                    "rule_count": len(rules_payload),
                    "sample_rule_ids": sample_rule_ids,
                    "ruleset_id": str(ruleset.id),
                },
            )
            
            # 5) Build response payload compatible with validator
            result = {
                "ruleset": {
                    "id": str(ruleset.id),
                    "domain": ruleset.domain,
                    "jurisdiction": ruleset.jurisdiction,
                    "ruleset_version": ruleset.ruleset_version,
                    "rulebook_version": ruleset.rulebook_version,
                    "status": ruleset.status,
                    "effective_from": ruleset.effective_from.isoformat() if ruleset.effective_from else None,
                    "effective_to": ruleset.effective_to.isoformat() if ruleset.effective_to else None,
                    "rule_count": ruleset.rule_count,
                    "published_at": ruleset.published_at.isoformat() if ruleset.published_at else None,
                },
                "rules": rules_payload,
                "ruleset_version": ruleset.ruleset_version,
                "rulebook_version": ruleset.rulebook_version,
            }
            
            # Cache the result
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now()
            logger.info(
                "Cached DB ruleset",
                extra={
                    "cache_key": cache_key,
                    "rule_count": len(rules_payload),
                },
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to fetch ruleset from DB",
                exc_info=True,
                extra={
                    "cache_key": cache_key,
                    "domain": domain,
                    "jurisdiction": jurisdiction,
                    "error": str(e),
                }
            )
            raise
        finally:
            db.close()
    
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
        """
        Convert a RuleRecord ORM row into the evaluator-ready payload.
        
        Maps all fields expected by RuleEvaluator and validator.
        """
        # Access metadata via rule_metadata column (mapped to 'metadata' in DB)
        metadata = record.rule_metadata or {}
        
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
            "ruleset_id": str(record.ruleset_id) if record.ruleset_id else None,
            "ruleset_version": record.ruleset_version,
        }

        # Extract common metadata fields to top level for backwards compatibility
        for key in ("documents", "supplements", "notes", "source"):
            value = metadata.get(key)
            if value is not None:
                payload[key] = value

        return payload


class RulesServiceDBAdapter:
    """
    DB-backed adapter for active rules that accepts an existing Session.
    
    Use this when you already have a database session and want to avoid
    creating a new one. Replaces JSON adapter entirely.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_rules(
        self,
        domain: str,
        jurisdiction: str,
        document_type: str = "lc",
    ) -> List[Dict[str, Any]]:
        """
        Returns ONLY active rules from RuleRecord table.
        
        Args:
            domain: Rule domain (e.g., 'icc.ucp600')
            jurisdiction: Jurisdiction (e.g., 'global')
            document_type: Document type (default: 'lc')
            
        Returns:
            List of normalized rule dictionaries
        """
        rules = (
            self.db.query(RuleRecord)
            .filter(
                RuleRecord.domain == domain,
                RuleRecord.jurisdiction == jurisdiction,
                RuleRecord.document_type == document_type,
                RuleRecord.is_active.is_(True),
            )
            .order_by(
                nullslast(RuleRecord.article.asc()),
                RuleRecord.rule_id.asc()
            )
            .all()
        )
        
        # Transform DB objects into normalized rule dicts
        output = []
        for r in rules:
            metadata = r.rule_metadata or {}
            output.append({
                "rule_id": r.rule_id,
                "rule_version": r.rule_version,
                "article": r.article,
                "version": r.version,
                "domain": r.domain,
                "jurisdiction": r.jurisdiction,
                "document_type": r.document_type,
                "rule_type": r.rule_type,
                "title": r.title,
                "reference": r.reference,
                "description": r.description,
                "severity": r.severity,
                "deterministic": r.deterministic,
                "requires_llm": r.requires_llm,
                "conditions": r.conditions or [],
                "expected_outcome": r.expected_outcome or {},
                "tags": r.tags or [],
                "metadata": metadata,
                "checksum": r.checksum,
                "ruleset_id": str(r.ruleset_id) if r.ruleset_id else None,
                "ruleset_version": r.ruleset_version,
            })
            
            # Extract common metadata fields to top level for backwards compatibility
            for key in ("documents", "supplements", "notes", "source"):
                value = metadata.get(key)
                if value is not None:
                    output[-1][key] = value
        
        return output


# Singleton instance
_rules_service: Optional[RulesService] = None


def get_rules_service() -> RulesService:
    """
    Get the configured rules service instance.
    
    Production: Always uses DBRulesAdapter (DB-backed).
    Future: May support RulhubAdapter via feature flag.
    
    Quick verification steps:
    1) SELECT COUNT(*) FROM rules WHERE is_active = true;
       For 'icc.ucp600', expect ~39 rows (or current rule count).
    2) Call RulesService.get_active_ruleset('icc.ucp600', 'global'):
       Should return ruleset metadata + list of rules from DB.
    3) Run a sample LC validation:
       /validate/export should produce issues sourced from DB rules.
    """
    global _rules_service
    
    if _rules_service is None:
        # Check feature flag for Rulhub integration (future)
        use_rulhub = getattr(settings, "USE_RULHUB_API", False)
        
        if use_rulhub:
            # Future: return RulhubAdapter()
            logger.warning("Rulhub integration not yet implemented, falling back to DBRulesAdapter")
        
        # Production: Always use DB-backed adapter
        cache_ttl = getattr(settings, "RULESET_CACHE_TTL_MINUTES", 10)
        _rules_service = DBRulesAdapter(cache_ttl_minutes=cache_ttl)
        logger.info(f"Initialized RulesService (DBRulesAdapter, cache TTL: {cache_ttl}min)")
    
    return _rules_service
