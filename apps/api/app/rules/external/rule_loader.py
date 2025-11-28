"""
Rule Loader - Load rules from YAML files or database.

Supports:
1. Loading from YAML files in the rules directory
2. Loading from database for dynamic rules
3. Caching for performance
4. Hot-reloading for development
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import yaml

from .rule_schema import Rule, RuleSet, RuleCategory, RuleSeverity, RuleCondition, RuleAction, ConditionOperator


logger = logging.getLogger(__name__)


# Default rules directory
RULES_DIR = Path(__file__).parent / "definitions"


class RuleLoader:
    """
    Loads validation rules from YAML files and/or database.
    
    Usage:
        loader = RuleLoader()
        rules = loader.load_all_rules()
        crossdoc_rules = loader.load_rules_by_category(RuleCategory.CROSSDOC)
    """
    
    def __init__(
        self,
        rules_dir: Optional[Path] = None,
        db_session: Optional[Any] = None,
        cache_enabled: bool = True,
    ):
        self.rules_dir = rules_dir or RULES_DIR
        self.db_session = db_session
        self.cache_enabled = cache_enabled
        
        # Rule cache
        self._rule_cache: Dict[str, Rule] = {}
        self._ruleset_cache: Dict[str, RuleSet] = {}
        self._cache_loaded_at: Optional[datetime] = None
    
    def load_all_rules(self, force_reload: bool = False) -> List[Rule]:
        """
        Load all rules from YAML files and database.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            List of all loaded rules
        """
        if self.cache_enabled and self._rule_cache and not force_reload:
            return list(self._rule_cache.values())
        
        all_rules = []
        
        # Load from YAML files
        yaml_rules = self._load_from_yaml_files()
        all_rules.extend(yaml_rules)
        
        # Load from database (if available)
        if self.db_session:
            db_rules = self._load_from_database()
            all_rules.extend(db_rules)
        
        # Update cache
        self._rule_cache = {r.id: r for r in all_rules}
        self._cache_loaded_at = datetime.utcnow()
        
        logger.info(
            "Loaded %d rules (%d from YAML, %d from DB)",
            len(all_rules),
            len(yaml_rules),
            len(all_rules) - len(yaml_rules),
        )
        
        return all_rules
    
    def load_rule(self, rule_id: str) -> Optional[Rule]:
        """Load a specific rule by ID."""
        if self.cache_enabled and rule_id in self._rule_cache:
            return self._rule_cache[rule_id]
        
        # Try to find in YAML files
        all_rules = self.load_all_rules()
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
    
    def load_ruleset(self, ruleset_id: str) -> Optional[RuleSet]:
        """Load a specific ruleset by ID."""
        if self.cache_enabled and ruleset_id in self._ruleset_cache:
            return self._ruleset_cache[ruleset_id]
        
        # Load all rulesets and cache
        self._load_from_yaml_files()
        return self._ruleset_cache.get(ruleset_id)
    
    def get_all_rulesets(self) -> List[RuleSet]:
        """Get all loaded rulesets."""
        if not self._ruleset_cache:
            self._load_from_yaml_files()
        return list(self._ruleset_cache.values())
    
    def _load_from_yaml_files(self) -> List[Rule]:
        """Load rules from YAML files in the rules directory."""
        all_rules = []
        
        if not self.rules_dir.exists():
            logger.warning("Rules directory does not exist: %s", self.rules_dir)
            # Create with default rules
            self._create_default_rules()
        
        # Find all YAML files
        yaml_files = list(self.rules_dir.glob("*.yaml")) + list(self.rules_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                # Check if it's a ruleset or individual rules
                if "ruleset" in data:
                    ruleset = RuleSet.from_dict({
                        **data.get("ruleset", {}),
                        "rules": data.get("rules", []),
                    })
                    self._ruleset_cache[ruleset.id] = ruleset
                    all_rules.extend(ruleset.rules)
                    logger.debug(
                        "Loaded ruleset '%s' with %d rules from %s",
                        ruleset.id, len(ruleset.rules), yaml_file.name
                    )
                elif "rules" in data:
                    # Just a list of rules
                    rules = [Rule.from_dict(r) for r in data["rules"]]
                    all_rules.extend(rules)
                    logger.debug("Loaded %d rules from %s", len(rules), yaml_file.name)
                
            except Exception as e:
                logger.error("Failed to load rules from %s: %s", yaml_file, e)
        
        return all_rules
    
    def _load_from_database(self) -> List[Rule]:
        """
        Load rules from the database (RuleRecord table).
        
        This loads all active rules that were uploaded via the admin dashboard.
        These rules take precedence over YAML rules with the same ID.
        """
        db_rules = []
        
        if not self.db_session:
            logger.debug("No database session available, skipping database rule loading")
            return db_rules
        
        try:
            from app.models.rule_record import RuleRecord
            
            # Query all active rules from database
            records = (
                self.db_session.query(RuleRecord)
                .filter(RuleRecord.is_active == True)
                .all()
            )
            
            logger.info(f"Found {len(records)} active rules in database")
            
            for record in records:
                try:
                    rule = self._convert_db_record_to_rule(record)
                    if rule:
                        db_rules.append(rule)
                except Exception as e:
                    logger.warning(f"Failed to convert rule {record.rule_id}: {e}")
            
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
                "fail": RuleSeverity.CRITICAL,  # Legacy mapping
                "warn": RuleSeverity.MAJOR,
                "high": RuleSeverity.CRITICAL,
                "medium": RuleSeverity.MAJOR,
                "low": RuleSeverity.MINOR,
            }
            severity = severity_map.get(
                (record.severity or "major").lower(), 
                RuleSeverity.MAJOR
            )
            
            # Map category based on domain or document_type
            category_map = {
                "icc": RuleCategory.UCP600,
                "ucp600": RuleCategory.UCP600,
                "isbp745": RuleCategory.ISBP745,
                "crossdoc": RuleCategory.CROSSDOC,
                "extraction": RuleCategory.EXTRACTION,
                "document": RuleCategory.DOCUMENT,
                "amount": RuleCategory.AMOUNT,
                "party": RuleCategory.PARTY,
                "port": RuleCategory.PORT,
                "goods": RuleCategory.GOODS,
                "timing": RuleCategory.TIMING,
                "guarantee": RuleCategory.CUSTOM,  # URDG
                "lc": RuleCategory.UCP600,
            }
            
            # Determine category from domain or document_type
            domain = (record.domain or "").lower()
            doc_type = (record.document_type or "").lower()
            
            category = RuleCategory.UCP600  # Default
            if domain in category_map:
                category = category_map[domain]
            elif doc_type in category_map:
                category = category_map[doc_type]
            
            # Parse conditions from JSON
            conditions = []
            raw_conditions = record.conditions or []
            for cond_data in raw_conditions:
                if isinstance(cond_data, dict):
                    # Handle different condition formats
                    field = cond_data.get("field") or cond_data.get("path") or ""
                    operator_str = cond_data.get("operator") or cond_data.get("type") or "exists"
                    
                    # Map operator
                    try:
                        operator = ConditionOperator(operator_str)
                    except ValueError:
                        # Handle custom operators from JSON rules
                        operator = ConditionOperator.EXISTS
                    
                    conditions.append(RuleCondition(
                        field=field,
                        operator=operator,
                        value=cond_data.get("value") or cond_data.get("expected_value"),
                        compare_field=cond_data.get("compare_field"),
                        threshold=cond_data.get("threshold"),
                    ))
            
            # Build action from expected_outcome
            expected_outcome = record.expected_outcome or {}
            valid_outcomes = expected_outcome.get("valid", [])
            invalid_outcomes = expected_outcome.get("invalid", [])
            
            action = RuleAction(
                type="issue",
                title=record.title or record.rule_id,
                message=record.description or "",
                suggestion="; ".join(valid_outcomes[:2]) if valid_outcomes else None,
                expected_template=valid_outcomes[0] if valid_outcomes else None,
                actual_template=invalid_outcomes[0] if invalid_outcomes else None,
            )
            
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
                ucp_reference=record.reference,
                isbp_reference=None,
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
    
    def _create_default_rules(self):
        """Create default rule files if they don't exist."""
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        
        # Create extraction rules
        extraction_rules_path = self.rules_dir / "extraction_rules.yaml"
        if not extraction_rules_path.exists():
            self._write_extraction_rules(extraction_rules_path)
        
        # Create crossdoc rules
        crossdoc_rules_path = self.rules_dir / "crossdoc_rules.yaml"
        if not crossdoc_rules_path.exists():
            self._write_crossdoc_rules(crossdoc_rules_path)
    
    def _write_extraction_rules(self, path: Path):
        """Write default extraction rules."""
        rules_yaml = """# LC Extraction Rules
# These rules check that required LC fields were extracted

ruleset:
  id: lc-extraction
  name: LC Extraction Validation
  version: "1.0.0"
  description: Validates that required LC fields were successfully extracted
  category: extraction
  ucp_version: UCP600

rules:
  # Critical fields - block validation if missing
  - id: LC-MISSING-NUMBER
    name: LC Number Required
    category: extraction
    severity: critical
    description: The LC number is required to identify the credit
    ucp_reference: "UCP600 Article 1"
    conditions:
      - field: "lc.number"
        operator: "exists"
    action:
      type: issue
      title: LC Number Missing
      message: The LC reference number could not be extracted from the document.
      suggestion: Ensure the document is a valid Letter of Credit with a visible reference number.
      expected_template: "LC reference number"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.number"]

  - id: LC-MISSING-AMOUNT
    name: LC Amount Required  
    category: extraction
    severity: critical
    description: The LC amount and currency are required for validation
    ucp_reference: "UCP600 Article 18"
    conditions:
      - field: "lc.amount.value"
        operator: "exists"
    action:
      type: issue
      title: LC Amount Missing
      message: The credit amount could not be extracted from the LC.
      suggestion: Verify the LC contains a clearly visible amount field (tag 32B for SWIFT).
      expected_template: "Credit amount with currency"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.amount"]

  - id: LC-MISSING-BENEFICIARY
    name: Beneficiary Required
    category: extraction
    severity: critical
    description: The beneficiary name is required
    ucp_reference: "UCP600 Article 14(k)"
    conditions:
      - field: "lc.beneficiary.name"
        operator: "exists"
    action:
      type: issue
      title: Beneficiary Missing
      message: The beneficiary name could not be extracted from the LC.
      suggestion: Check the LC for tag 59 (beneficiary) or equivalent field.
      expected_template: "Beneficiary name and address"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.beneficiary"]

  - id: LC-MISSING-APPLICANT
    name: Applicant Required
    category: extraction
    severity: critical
    description: The applicant name is required
    ucp_reference: "UCP600 Article 14(k)"
    conditions:
      - field: "lc.applicant.name"
        operator: "exists"
    action:
      type: issue
      title: Applicant Missing
      message: The applicant name could not be extracted from the LC.
      suggestion: Check the LC for tag 50 (applicant) or equivalent field.
      expected_template: "Applicant name and address"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.applicant"]

  # Required fields - major issues if missing
  - id: LC-MISSING-EXPIRY
    name: Expiry Date Required
    category: extraction
    severity: major
    description: The expiry date is required to validate document presentation
    ucp_reference: "UCP600 Article 6(d)"
    conditions:
      - field: "lc.timeline.expiry_date"
        operator: "exists"
    action:
      type: issue
      title: Expiry Date Missing
      message: The LC expiry date could not be extracted.
      suggestion: Check for tag 31D or expiry date field in the LC.
      expected_template: "Expiry date (YYYY-MM-DD)"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.timeline.expiry_date"]

  - id: LC-MISSING-LATEST-SHIPMENT
    name: Latest Shipment Date Required
    category: extraction
    severity: major
    description: The latest shipment date is required for timeline validation
    ucp_reference: "UCP600 Article 6(c)"
    conditions:
      - field: "lc.timeline.latest_shipment"
        operator: "exists"
    action:
      type: issue
      title: Latest Shipment Date Missing
      message: The latest date for shipment could not be extracted.
      suggestion: Check for tag 44C or shipment date field in the LC.
      expected_template: "Latest shipment date"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.timeline.latest_shipment"]

  - id: LC-MISSING-POL
    name: Port of Loading Required
    category: extraction
    severity: major
    description: Port of loading is required for shipment validation
    ucp_reference: "UCP600 Article 20"
    conditions:
      - field: "lc.ports.loading"
        operator: "exists"
    action:
      type: issue
      title: Port of Loading Missing
      message: The port of loading could not be extracted from the LC.
      suggestion: Check for tag 44E or loading port field.
      expected_template: "Port of loading"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.ports.loading"]

  - id: LC-MISSING-POD
    name: Port of Discharge Required
    category: extraction
    severity: major
    description: Port of discharge is required for shipment validation
    ucp_reference: "UCP600 Article 20"
    conditions:
      - field: "lc.ports.discharge"
        operator: "exists"
    action:
      type: issue
      title: Port of Discharge Missing
      message: The port of discharge could not be extracted from the LC.
      suggestion: Check for tag 44F or discharge port field.
      expected_template: "Port of discharge"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.ports.discharge"]

  - id: LC-MISSING-GOODS
    name: Goods Description Required
    category: extraction
    severity: major
    description: Goods description is required for document matching
    ucp_reference: "UCP600 Article 18(c)"
    conditions:
      - field: "lc.goods_description"
        operator: "exists"
    action:
      type: issue
      title: Goods Description Missing
      message: The goods description could not be extracted from the LC.
      suggestion: Check for tag 45A or goods description field.
      expected_template: "Description of goods"
      actual_template: "Not found"
    source_documents: ["letter_of_credit"]
    requires_fields: ["lc.goods_description"]
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(rules_yaml)
        logger.info("Created default extraction rules at %s", path)
    
    def _write_crossdoc_rules(self, path: Path):
        """Write default cross-document rules."""
        rules_yaml = """# Cross-Document Validation Rules
# These rules validate consistency between LC and other documents

ruleset:
  id: crossdoc-validation
  name: Cross-Document Validation
  version: "1.0.0"
  description: Validates consistency between LC and supporting documents
  category: crossdoc
  ucp_version: UCP600

rules:
  - id: CROSSDOC-GOODS-1
    name: Goods Description Match
    category: crossdoc
    severity: major
    description: Invoice goods description must match LC terms
    ucp_reference: "UCP600 Article 18(c)"
    isbp_reference: "ISBP745 C1"
    conditions:
      - field: "lc.goods_description"
        operator: "exists"
      - field: "invoice.goods_description"
        operator: "exists"
      - field: "invoice.goods_description"
        operator: "similar_to"
        compare_field: "lc.goods_description"
        threshold: 0.8
    action:
      type: issue
      title: Product Description Variation
      message: Product description in the commercial invoice differs from LC terms and may trigger a bank discrepancy.
      suggestion: Ensure invoice goods description matches LC exactly or use acceptable variations per ISBP745.
      expected_template: "{lc.goods_description}"
      actual_template: "{invoice.goods_description}"
    source_documents: ["letter_of_credit"]
    target_documents: ["commercial_invoice"]
    requires_fields: ["lc.goods_description", "invoice.goods_description"]

  - id: CROSSDOC-AMOUNT-1
    name: Invoice Amount vs LC
    category: crossdoc
    severity: major
    description: Invoice amount must not exceed LC amount plus tolerance
    ucp_reference: "UCP600 Article 18(b)"
    conditions:
      - field: "lc.amount.value"
        operator: "exists"
      - field: "invoice.amount"
        operator: "exists"
      - field: "invoice.amount"
        operator: "lte"
        compare_field: "invoice_amount_limit"
    action:
      type: issue
      title: Invoice Amount Exceeds LC + Tolerance
      message: The invoiced amount exceeds the LC face value plus allowed tolerance, which may lead to refusal.
      suggestion: Reduce invoice amount to be within LC tolerance limits.
      expected_template: "<= {invoice_amount_limit} (LC + tolerance)"
      actual_template: "{invoice.amount}"
    source_documents: ["letter_of_credit", "commercial_invoice"]
    target_documents: ["commercial_invoice"]
    requires_fields: ["lc.amount.value", "invoice.amount"]

  - id: CROSSDOC-DOC-1
    name: Insurance Certificate Required
    category: crossdoc
    severity: major
    description: Insurance certificate required when LC specifies insurance
    ucp_reference: "UCP600 Article 28"
    conditions:
      - field: "lc_requires_insurance"
        operator: "equals"
        value: true
      - field: "documents_presence.insurance_certificate.present"
        operator: "equals"
        value: true
    action:
      type: issue
      title: Insurance Certificate Missing
      message: The LC references insurance coverage, but no insurance certificate was uploaded.
      suggestion: Upload an insurance certificate that matches LC requirements (minimum CIF + 10%).
      expected_template: "Insurance certificate as per LC requirements"
      actual_template: "Not provided"
    source_documents: ["letter_of_credit"]
    target_documents: ["insurance_certificate"]

  - id: CROSSDOC-BL-1
    name: B/L Shipper vs LC Applicant
    category: crossdoc
    severity: major
    description: B/L shipper should match LC applicant unless otherwise specified
    ucp_reference: "UCP600 Article 20"
    isbp_reference: "ISBP745 E2"
    conditions:
      - field: "lc.applicant.name"
        operator: "exists"
      - field: "bl.shipper"
        operator: "exists"
      - field: "bl.shipper"
        operator: "similar_to"
        compare_field: "lc.applicant.name"
        threshold: 0.85
    action:
      type: issue
      title: B/L Shipper differs from LC Applicant
      message: The shipper on the Bill of Lading does not match the applicant named in the LC.
      suggestion: Verify shipper name matches LC applicant exactly.
      expected_template: "{lc.applicant.name}"
      actual_template: "{bl.shipper}"
    source_documents: ["letter_of_credit", "bill_of_lading"]
    target_documents: ["bill_of_lading"]
    requires_fields: ["lc.applicant.name", "bl.shipper"]

  - id: CROSSDOC-BL-2
    name: B/L Consignee vs LC Beneficiary
    category: crossdoc
    severity: major
    description: B/L consignee should typically be LC beneficiary or to order
    ucp_reference: "UCP600 Article 20"
    conditions:
      - field: "lc.beneficiary.name"
        operator: "exists"
      - field: "bl.consignee"
        operator: "exists"
      - field: "bl.consignee"
        operator: "similar_to"
        compare_field: "lc.beneficiary.name"
        threshold: 0.85
    action:
      type: issue
      title: B/L Consignee differs from LC Beneficiary
      message: The consignee on the Bill of Lading is different from the LC beneficiary.
      suggestion: Verify consignee matches LC requirements (beneficiary or to order of bank).
      expected_template: "{lc.beneficiary.name}"
      actual_template: "{bl.consignee}"
    source_documents: ["letter_of_credit", "bill_of_lading"]
    target_documents: ["bill_of_lading"]
    requires_fields: ["lc.beneficiary.name", "bl.consignee"]

  - id: CROSSDOC-PORT-1
    name: B/L Port of Loading Match
    category: crossdoc
    severity: major
    description: B/L port of loading must match LC specified port
    ucp_reference: "UCP600 Article 20(a)(ii)"
    conditions:
      - field: "lc.ports.loading"
        operator: "exists"
      - field: "bl.port_of_loading"
        operator: "exists"
      - field: "bl.port_of_loading"
        operator: "similar_to"
        compare_field: "lc.ports.loading"
        threshold: 0.9
    action:
      type: issue
      title: B/L Port of Loading Mismatch
      message: The port of loading on B/L does not match the LC specified port.
      suggestion: Ensure B/L shows the exact port of loading as stated in the LC.
      expected_template: "{lc.ports.loading}"
      actual_template: "{bl.port_of_loading}"
    source_documents: ["letter_of_credit", "bill_of_lading"]
    target_documents: ["bill_of_lading"]
    requires_fields: ["lc.ports.loading", "bl.port_of_loading"]

  - id: CROSSDOC-PORT-2
    name: B/L Port of Discharge Match
    category: crossdoc
    severity: major
    description: B/L port of discharge must match LC specified port
    ucp_reference: "UCP600 Article 20(a)(ii)"
    conditions:
      - field: "lc.ports.discharge"
        operator: "exists"
      - field: "bl.port_of_discharge"
        operator: "exists"
      - field: "bl.port_of_discharge"
        operator: "similar_to"
        compare_field: "lc.ports.discharge"
        threshold: 0.9
    action:
      type: issue
      title: B/L Port of Discharge Mismatch
      message: The port of discharge on B/L does not match the LC specified port.
      suggestion: Ensure B/L shows the exact discharge port as stated in the LC.
      expected_template: "{lc.ports.discharge}"
      actual_template: "{bl.port_of_discharge}"
    source_documents: ["letter_of_credit", "bill_of_lading"]
    target_documents: ["bill_of_lading"]
    requires_fields: ["lc.ports.discharge", "bl.port_of_discharge"]
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(rules_yaml)
        logger.info("Created default crossdoc rules at %s", path)
    
    def reload_rules(self):
        """Force reload all rules from source."""
        self._rule_cache.clear()
        self._ruleset_cache.clear()
        self.load_all_rules(force_reload=True)
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        all_rules = self.load_all_rules()
        
        by_category = {}
        by_severity = {}
        
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
        }


# Global rule loader instance
_rule_loader: Optional[RuleLoader] = None


def get_rule_loader(db_session: Optional[Any] = None) -> RuleLoader:
    """
    Get a rule loader instance.
    
    Args:
        db_session: Optional SQLAlchemy session for loading database rules.
                    If provided, returns a fresh loader with DB support.
                    If not provided, returns the cached global loader (YAML only).
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
    access both YAML and database rules.
    """
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        loader = RuleLoader(db_session=db)
        return loader
    except Exception as e:
        logger.warning(f"Could not create DB-backed rule loader: {e}")
        return get_rule_loader()

