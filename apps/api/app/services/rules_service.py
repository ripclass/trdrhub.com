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

    # =========================================================================
    # RULE DESCRIPTION LOOKUP (DB + AI Fallback)
    # =========================================================================
    
    # In-memory cache for rule descriptions (article -> description)
    _description_cache: Dict[str, Optional[str]] = {}
    
    async def get_rule_description(
        self,
        article: str,
        domain: str = "icc.ucp600",
        use_ai_fallback: bool = True,
    ) -> Optional[str]:
        """
        Get human-readable description for a rule article.
        
        Lookup priority:
        1. In-memory cache
        2. Rules database (admin-uploaded rulesets)
        3. AI-generated fallback (if enabled)
        
        Args:
            article: Article reference, e.g., "14", "14(a)", "A14"
            domain: Rule domain, e.g., "icc.ucp600" or "icc.isbp745"
            use_ai_fallback: Whether to use AI to generate description if not in DB
            
        Returns:
            Description string or None if not found
        """
        # Normalize article reference
        article_clean = self._normalize_article_reference(article)
        cache_key = f"{domain}:{article_clean}"
        
        # 1. Check cache
        if cache_key in self._description_cache:
            return self._description_cache[cache_key]
        
        # 2. Query database
        description = self._lookup_description_from_db(article_clean, domain)
        if description:
            self._description_cache[cache_key] = description
            return description
        
        # 3. AI fallback
        if use_ai_fallback:
            description = await self._generate_description_with_ai(article_clean, domain)
            if description:
                self._description_cache[cache_key] = description
                return description
        
        # Not found anywhere
        self._description_cache[cache_key] = None
        return None
    
    def _normalize_article_reference(self, article: str) -> str:
        """Normalize article reference for lookup."""
        import re
        if not article:
            return ""
        
        # Remove common prefixes
        # "UCP600 Article 14(a)" -> "14(a)"
        # "ISBP745 A14" -> "A14"
        # "Article 14" -> "14"
        cleaned = article.strip()
        cleaned = re.sub(r"^(?:UCP600\s*)?(?:Article\s*)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:ISBP745\s*)?(?:¶)?", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def _lookup_description_from_db(self, article: str, domain: str) -> Optional[str]:
        """Query rules database for description."""
        db = SessionLocal()
        try:
            # Try exact match on article field
            record = db.query(RuleRecord).filter(
                RuleRecord.article == article,
                RuleRecord.domain == domain,
                RuleRecord.is_active == True,
            ).first()
            
            if record and record.description:
                logger.debug(f"Found rule description in DB: {domain}/{article}")
                return record.description
            
            # Try matching by rule_id pattern (e.g., "UCP600-14" or "ISBP745-A14")
            if domain == "icc.ucp600":
                rule_id_pattern = f"UCP600-{article}%"
            elif domain == "icc.isbp745":
                rule_id_pattern = f"ISBP745-{article}%"
            else:
                rule_id_pattern = f"{article}%"
            
            record = db.query(RuleRecord).filter(
                RuleRecord.rule_id.ilike(rule_id_pattern),
                RuleRecord.domain == domain,
                RuleRecord.is_active == True,
            ).first()
            
            if record and record.description:
                logger.debug(f"Found rule description by rule_id pattern: {domain}/{article}")
                return record.description
            
            # Also try title as fallback (many rules have descriptive titles)
            if record and record.title:
                return record.title
            
            return None
        except Exception as e:
            logger.warning(f"Error looking up rule description: {e}")
            return None
        finally:
            db.close()
    
    async def _generate_description_with_ai(self, article: str, domain: str) -> Optional[str]:
        """Generate rule description using AI as fallback."""
        try:
            from app.services.llm_provider import LLMProviderFactory
            
            # Determine rulebook name
            if domain == "icc.ucp600":
                rulebook = "UCP600 (Uniform Customs and Practice for Documentary Credits)"
                article_ref = f"Article {article}"
            elif domain == "icc.isbp745":
                rulebook = "ISBP745 (International Standard Banking Practice)"
                article_ref = f"Paragraph {article}"
            else:
                rulebook = domain
                article_ref = article
            
            prompt = f"""Provide a brief, one-sentence description of {article_ref} from {rulebook}.
            
The description should be suitable for a tooltip explaining what this rule requires.
Respond with ONLY the description text, no additional formatting or explanation.

Example format: "Banks must examine documents within 5 banking days following presentation."
"""
            
            system_prompt = "You are an expert in international trade finance and documentary credits. Provide accurate, concise rule descriptions."
            
            output, _, _, provider = await LLMProviderFactory.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=100,
                temperature=0.1,
                model_override="gpt-4o-mini",  # Use cheap model for simple lookups
            )
            
            if output:
                description = output.strip().strip('"').strip("'")
                logger.info(f"Generated AI description for {domain}/{article} via {provider}")
                return description
            
            return None
        except Exception as e:
            logger.warning(f"AI fallback failed for rule description: {e}")
            return None


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


# =============================================================================
# CONVENIENCE FUNCTIONS FOR RULE DESCRIPTION LOOKUP
# =============================================================================

async def get_ucp_description(article: str, use_ai_fallback: bool = True) -> Optional[str]:
    """
    Get description for a UCP600 article.
    
    Args:
        article: Article reference, e.g., "14", "14(a)", "UCP600 Article 14"
        use_ai_fallback: Whether to use AI if not in database
        
    Returns:
        Description string or None
    """
    service = get_rules_service()
    if isinstance(service, DBRulesAdapter):
        return await service.get_rule_description(article, "icc.ucp600", use_ai_fallback)
    return None


async def get_isbp_description(article: str, use_ai_fallback: bool = True) -> Optional[str]:
    """
    Get description for an ISBP745 paragraph.
    
    Args:
        article: Paragraph reference, e.g., "A14", "ISBP745 A14"
        use_ai_fallback: Whether to use AI if not in database
        
    Returns:
        Description string or None
    """
    service = get_rules_service()
    if isinstance(service, DBRulesAdapter):
        return await service.get_rule_description(article, "icc.isbp745", use_ai_fallback)
    return None


def get_ucp_description_sync(article: str, use_ai_fallback: bool = False) -> Optional[str]:
    """
    Synchronous version of get_ucp_description.
    
    Note: AI fallback disabled by default in sync version to avoid blocking.
    For AI fallback, use the async version.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't run async in running loop - use DB-only lookup
            service = get_rules_service()
            if isinstance(service, DBRulesAdapter):
                return service._lookup_description_from_db(
                    service._normalize_article_reference(article),
                    "icc.ucp600"
                )
            return None
        return loop.run_until_complete(get_ucp_description(article, use_ai_fallback))
    except RuntimeError:
        # No event loop - create one
        return asyncio.run(get_ucp_description(article, use_ai_fallback))


def get_isbp_description_sync(article: str, use_ai_fallback: bool = False) -> Optional[str]:
    """
    Synchronous version of get_isbp_description.
    
    Note: AI fallback disabled by default in sync version to avoid blocking.
    For AI fallback, use the async version.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't run async in running loop - use DB-only lookup
            service = get_rules_service()
            if isinstance(service, DBRulesAdapter):
                return service._lookup_description_from_db(
                    service._normalize_article_reference(article),
                    "icc.isbp745"
                )
            return None
        return loop.run_until_complete(get_isbp_description(article, use_ai_fallback))
    except RuntimeError:
        # No event loop - create one
        return asyncio.run(get_isbp_description(article, use_ai_fallback))
