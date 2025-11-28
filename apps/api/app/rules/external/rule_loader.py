"""
Rule Loader - Database-First Rule Loading with Future Rulhub API Support.

Architecture:
============
CURRENT: Database (admin dashboard) → Validation Engine
FUTURE:  Rulhub API → Local Cache → Validation Engine

Key Principles:
- Database is the single source of truth
- YAML files are deprecated (bootstrap only, to be removed)
- Ready for Rulhub API integration when available
- Caching with TTL for performance
"""

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .rule_schema import Rule, RuleSet, RuleCategory, RuleSeverity, RuleCondition, RuleAction, ConditionOperator


logger = logging.getLogger(__name__)


# Cache configuration
CACHE_TTL_MINUTES = 15  # Re-fetch rules every 15 minutes
RULHUB_API_ENABLED = False  # Set to True when Rulhub API is ready


class RuleLoader:
    """
    Database-first rule loader with future Rulhub API support.
    
    Usage:
        loader = RuleLoader(db_session=db)
        rules = loader.load_all_rules()
        
    Future (when Rulhub API ready):
        loader = RuleLoader(rulhub_api_key="xxx")
        rules = loader.load_all_rules()  # Will fetch from Rulhub API
    """
    
    def __init__(
        self,
        db_session: Optional[Any] = None,
        rulhub_api_key: Optional[str] = None,
        rulhub_api_url: Optional[str] = None,
        cache_enabled: bool = True,
    ):
        self.db_session = db_session
        self.rulhub_api_key = rulhub_api_key
        self.rulhub_api_url = rulhub_api_url or "https://api.rulhub.com/v1"
        self.cache_enabled = cache_enabled
        
        # Rule cache
        self._rule_cache: Dict[str, Rule] = {}
        self._ruleset_cache: Dict[str, RuleSet] = {}
        self._cache_loaded_at: Optional[datetime] = None
        self._cache_hash: Optional[str] = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL."""
        if not self._cache_loaded_at:
            return False
        
        cache_age = datetime.utcnow() - self._cache_loaded_at
        return cache_age < timedelta(minutes=CACHE_TTL_MINUTES)
    
    def load_all_rules(self, force_reload: bool = False) -> List[Rule]:
        """
        Load all rules from database (or future Rulhub API).
        
        Priority:
        1. If Rulhub API enabled and key provided → fetch from Rulhub
        2. Otherwise → fetch from local database
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            List of all loaded rules
        """
        # Check cache first
        if self.cache_enabled and self._rule_cache and self._is_cache_valid() and not force_reload:
            logger.debug("Returning %d cached rules", len(self._rule_cache))
            return list(self._rule_cache.values())
        
        all_rules = []
        source = "unknown"
        
        # Priority 1: Rulhub API (future)
        if RULHUB_API_ENABLED and self.rulhub_api_key:
            try:
                rulhub_rules = self._load_from_rulhub_api()
                if rulhub_rules:
                    all_rules = rulhub_rules
                    source = "rulhub_api"
            except Exception as e:
                logger.error(f"Rulhub API failed, falling back to database: {e}")
        
        # Priority 2: Database (current implementation)
        if not all_rules and self.db_session:
            db_rules = self._load_from_database()
            if db_rules:
                all_rules = db_rules
                source = "database"
        
        # Log result
        if all_rules:
            logger.info(
                "Loaded %d rules from %s (categories: %s)",
                len(all_rules),
                source,
                self._summarize_categories(all_rules),
            )
        else:
            logger.warning("No rules loaded! Check database connection or Rulhub API.")
        
        # Update cache
        self._rule_cache = {r.id: r for r in all_rules}
        self._cache_loaded_at = datetime.utcnow()
        self._cache_hash = self._compute_cache_hash(all_rules)
        
        return all_rules
    
    def _summarize_categories(self, rules: List[Rule]) -> str:
        """Summarize rule categories for logging."""
        by_category: Dict[str, int] = {}
        for r in rules:
            cat = r.category.value if isinstance(r.category, RuleCategory) else str(r.category)
            by_category[cat] = by_category.get(cat, 0) + 1
        return ", ".join(f"{k}:{v}" for k, v in sorted(by_category.items()))
    
    def _compute_cache_hash(self, rules: List[Rule]) -> str:
        """Compute hash of rules for change detection."""
        rule_ids = sorted([r.id for r in rules])
        return hashlib.md5("|".join(rule_ids).encode()).hexdigest()[:8]
    
    def load_rule(self, rule_id: str) -> Optional[Rule]:
        """Load a specific rule by ID."""
        if self.cache_enabled and rule_id in self._rule_cache:
            return self._rule_cache[rule_id]
        
        # Reload all rules and try again
        self.load_all_rules()
        return self._rule_cache.get(rule_id)
    
    def load_rules_by_category(self, category: RuleCategory) -> List[Rule]:
        """Load rules filtered by category."""
        all_rules = self.load_all_rules()
        return [r for r in all_rules if r.category == category]
    
    def load_rules_by_severity(self, severity: RuleSeverity) -> List[Rule]:
        """Load rules filtered by severity."""
        all_rules = self.load_all_rules()
        return [r for r in all_rules if r.severity == severity]
    
    def load_enabled_rules(self) -> List[Rule]:
        """Load only enabled rules."""
        all_rules = self.load_all_rules()
        return [r for r in all_rules if r.enabled]
    
    def load_rules_by_domain(self, domain: str) -> List[Rule]:
        """
        Load rules by their domain (e.g., 'ucp600', 'urdg758', 'eucp').
        This is useful for filtering rules by ruleset.
        """
        all_rules = self.load_all_rules()
        domain_lower = domain.lower()
        return [r for r in all_rules if domain_lower in r.id.lower()]
    
    def get_all_rulesets(self) -> List[RuleSet]:
        """Get all loaded rulesets."""
        return list(self._ruleset_cache.values())
    
    # =========================================================================
    # DATABASE LOADING (Current Implementation)
    # =========================================================================
    
    def _load_from_database(self) -> List[Rule]:
        """
        Load rules from the database (RuleRecord table).
        
        This loads all active rules that were uploaded via the admin dashboard.
        """
        db_rules = []
        
        if not self.db_session:
            logger.debug("No database session available")
            return db_rules
        
        try:
            from app.models.rule_record import RuleRecord
            
            # Query all active rules from database
            records = (
                self.db_session.query(RuleRecord)
                .filter(RuleRecord.is_active == True)
                .order_by(RuleRecord.ruleset_id, RuleRecord.rule_id)
                .all()
            )
            
            logger.info(f"Found {len(records)} active rules in database")
            
            # Group by ruleset for logging
            by_ruleset: Dict[str, int] = {}
            
            for record in records:
                try:
                    rule = self._convert_db_record_to_rule(record)
                    if rule:
                        db_rules.append(rule)
                        ruleset = record.ruleset_id or "unknown"
                        by_ruleset[ruleset] = by_ruleset.get(ruleset, 0) + 1
                except Exception as e:
                    logger.warning(f"Failed to convert rule {record.rule_id}: {e}")
            
            # Log breakdown by ruleset
            for ruleset, count in sorted(by_ruleset.items()):
                logger.info(f"  {ruleset}: {count} rules")
            
            logger.info(f"Successfully loaded {len(db_rules)} rules from database")
            
        except Exception as e:
            logger.error(f"Failed to load rules from database: {e}", exc_info=True)
        
        return db_rules
    
    def _convert_db_record_to_rule(self, record) -> Optional[Rule]:
        """
        Convert a RuleRecord (database model) to a Rule (execution model).
        """
        try:
            # Map severity
            severity_map = {
                "critical": RuleSeverity.CRITICAL,
                "major": RuleSeverity.MAJOR,
                "minor": RuleSeverity.MINOR,
                "info": RuleSeverity.INFO,
                "fail": RuleSeverity.CRITICAL,
                "warn": RuleSeverity.MAJOR,
                "high": RuleSeverity.CRITICAL,
                "medium": RuleSeverity.MAJOR,
                "low": RuleSeverity.MINOR,
            }
            severity = severity_map.get(
                (record.severity or "major").lower(), 
                RuleSeverity.MAJOR
            )
            
            # Map category based on domain, ruleset, or document_type
            category = self._determine_category(record)
            
            # Parse conditions from JSON
            conditions = self._parse_conditions(record.conditions or [])
            
            # Build action from expected_outcome
            action = self._build_action(record)
            
            # Extract references
            reference = record.reference or ""
            ucp_ref = reference if "UCP600" in reference or "Article" in reference else None
            isbp_ref = reference if "ISBP" in reference else None
            urdg_ref = reference if "URDG" in reference else None
            eucp_ref = reference if "eUCP" in reference else None
            
            # Create Rule object
            rule = Rule(
                id=record.rule_id,
                name=record.title or record.rule_id,
                category=category,
                severity=severity,
                description=record.description or "",
                conditions=conditions,
                action=action,
                enabled=record.is_active,
                version=record.version or "1.0.0",
                ucp_reference=ucp_ref or urdg_ref or eucp_ref,  # Use whatever reference is available
                isbp_reference=isbp_ref,
                source_documents=[],
                target_documents=[],
                requires_fields=[],
                optional_fields=[],
                can_override=True,
            )
            
            return rule
            
        except Exception as e:
            logger.error(f"Error converting rule {record.rule_id}: {e}", exc_info=True)
            return None
    
    def _determine_category(self, record) -> RuleCategory:
        """Determine rule category from database record."""
        # First check ruleset_id
        ruleset = (record.ruleset_id or "").lower()
        if "ucp600" in ruleset or "ucp-600" in ruleset:
            return RuleCategory.UCP600
        if "urdg" in ruleset:
            return RuleCategory.CUSTOM  # URDG rules
        if "eucp" in ruleset or "e-ucp" in ruleset:
            return RuleCategory.CUSTOM  # eUCP rules
        if "isbp" in ruleset:
            return RuleCategory.ISBP745
        if "crossdoc" in ruleset:
            return RuleCategory.CROSSDOC
        
        # Check domain
        domain = (record.domain or "").lower()
        domain_map = {
            "icc": RuleCategory.UCP600,
            "ucp600": RuleCategory.UCP600,
            "ucp": RuleCategory.UCP600,
            "isbp745": RuleCategory.ISBP745,
            "isbp": RuleCategory.ISBP745,
            "crossdoc": RuleCategory.CROSSDOC,
            "extraction": RuleCategory.EXTRACTION,
            "document": RuleCategory.DOCUMENT,
            "amount": RuleCategory.AMOUNT,
            "party": RuleCategory.PARTY,
            "port": RuleCategory.PORT,
            "goods": RuleCategory.GOODS,
            "timing": RuleCategory.TIMING,
            "guarantee": RuleCategory.CUSTOM,
            "lc": RuleCategory.UCP600,
        }
        
        for key, cat in domain_map.items():
            if key in domain:
                return cat
        
        # Check document_type as fallback
        doc_type = (record.document_type or "").lower()
        for key, cat in domain_map.items():
            if key in doc_type:
                return cat
        
        return RuleCategory.UCP600  # Default
    
    def _parse_conditions(self, raw_conditions: List[Any]) -> List[RuleCondition]:
        """Parse conditions from JSON format."""
        conditions = []
        
        for cond_data in raw_conditions:
            if not isinstance(cond_data, dict):
                continue
            
            # Handle different condition formats
            field = cond_data.get("field") or cond_data.get("path") or ""
            operator_str = cond_data.get("operator") or cond_data.get("type") or "exists"
            
            # Map operator
            try:
                operator = ConditionOperator(operator_str)
            except ValueError:
                # Handle custom operators from JSON rules
                operator_mapping = {
                    "required": ConditionOperator.EXISTS,
                    "match": ConditionOperator.EQUALS,
                    "contains": ConditionOperator.CONTAINS,
                    "compare": ConditionOperator.EQUALS,
                    "range": ConditionOperator.BETWEEN,
                    "pattern": ConditionOperator.MATCHES,
                }
                operator = operator_mapping.get(operator_str, ConditionOperator.EXISTS)
            
            conditions.append(RuleCondition(
                field=field,
                operator=operator,
                value=cond_data.get("value") or cond_data.get("expected_value"),
                compare_field=cond_data.get("compare_field"),
                threshold=cond_data.get("threshold"),
            ))
        
        return conditions
    
    def _build_action(self, record) -> RuleAction:
        """Build action from expected_outcome."""
        expected_outcome = record.expected_outcome or {}
        valid_outcomes = expected_outcome.get("valid", [])
        invalid_outcomes = expected_outcome.get("invalid", [])
        
        return RuleAction(
            type="issue",
            title=record.title or record.rule_id,
            message=record.description or "",
            suggestion="; ".join(valid_outcomes[:2]) if valid_outcomes else None,
            expected_template=valid_outcomes[0] if valid_outcomes else None,
            actual_template=invalid_outcomes[0] if invalid_outcomes else None,
        )
    
    # =========================================================================
    # RULHUB API (Future Implementation)
    # =========================================================================
    
    def _load_from_rulhub_api(self) -> List[Rule]:
        """
        Load rules from Rulhub API.
        
        FUTURE: This will be the primary source when Rulhub API is ready.
        
        API Contract (planned):
            GET /v1/rulesets/{domain}
            Headers: Authorization: Bearer {api_key}
            Response: { rules: [...], version: "1.0.0", hash: "abc123" }
        """
        if not RULHUB_API_ENABLED:
            return []
        
        if not self.rulhub_api_key:
            logger.warning("Rulhub API enabled but no API key provided")
            return []
        
        try:
            import httpx
            
            # Fetch rulesets from Rulhub API
            headers = {
                "Authorization": f"Bearer {self.rulhub_api_key}",
                "Accept": "application/json",
            }
            
            # Get available rulesets
            response = httpx.get(
                f"{self.rulhub_api_url}/rulesets",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            
            rulesets_data = response.json()
            all_rules = []
            
            # Fetch each ruleset's rules
            for ruleset in rulesets_data.get("rulesets", []):
                ruleset_id = ruleset.get("id")
                rules_response = httpx.get(
                    f"{self.rulhub_api_url}/rulesets/{ruleset_id}/rules",
                    headers=headers,
                    timeout=30.0,
                )
                rules_response.raise_for_status()
                
                rules_data = rules_response.json()
                for rule_data in rules_data.get("rules", []):
                    rule = self._convert_rulhub_rule(rule_data)
                    if rule:
                        all_rules.append(rule)
            
            logger.info(f"Loaded {len(all_rules)} rules from Rulhub API")
            return all_rules
            
        except Exception as e:
            logger.error(f"Failed to load from Rulhub API: {e}")
            return []
    
    def _convert_rulhub_rule(self, rule_data: Dict[str, Any]) -> Optional[Rule]:
        """
        Convert Rulhub API response to Rule object.
        
        FUTURE: Implement when Rulhub API schema is finalized.
        """
        # Placeholder - implement when Rulhub API is ready
        return None
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def reload_rules(self):
        """Force reload all rules from source."""
        self._rule_cache.clear()
        self._ruleset_cache.clear()
        self._cache_loaded_at = None
        self.load_all_rules(force_reload=True)
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        all_rules = self.load_all_rules()
        
        by_category: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        
        for rule in all_rules:
            cat = rule.category.value if isinstance(rule.category, RuleCategory) else str(rule.category)
            by_category[cat] = by_category.get(cat, 0) + 1
            
            sev = rule.severity.value if isinstance(rule.severity, RuleSeverity) else str(rule.severity)
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return {
            "total_rules": len(all_rules),
            "enabled_rules": len([r for r in all_rules if r.enabled]),
            "rulesets": len(self._ruleset_cache),
            "by_category": by_category,
            "by_severity": by_severity,
            "cache_loaded_at": self._cache_loaded_at.isoformat() if self._cache_loaded_at else None,
            "cache_hash": self._cache_hash,
            "source": "rulhub_api" if (RULHUB_API_ENABLED and self.rulhub_api_key) else "database",
        }


# Global rule loader instance
_rule_loader: Optional[RuleLoader] = None


def get_rule_loader(db_session: Optional[Any] = None) -> RuleLoader:
    """
    Get a rule loader instance.
    
    Args:
        db_session: SQLAlchemy session for loading database rules.
                    REQUIRED for rules to load.
    """
    global _rule_loader
    
    # If db_session provided, create a fresh loader with DB support
    if db_session is not None:
        return RuleLoader(db_session=db_session)
    
    # Otherwise return/create the global cached loader
    if _rule_loader is None:
        _rule_loader = RuleLoader()
    return _rule_loader


def get_rule_loader_with_db() -> RuleLoader:
    """
    Get a rule loader with database session from the app context.
    
    This creates a new database session and returns a loader that can
    access database rules.
    """
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        loader = RuleLoader(db_session=db)
        return loader
    except Exception as e:
        logger.warning(f"Could not create DB-backed rule loader: {e}")
        return RuleLoader()


def get_rule_loader_with_rulhub(api_key: str, api_url: Optional[str] = None) -> RuleLoader:
    """
    Get a rule loader configured for Rulhub API (future).
    
    Args:
        api_key: Rulhub API key
        api_url: Optional custom API URL (default: https://api.rulhub.com/v1)
    """
    return RuleLoader(
        rulhub_api_key=api_key,
        rulhub_api_url=api_url,
    )
