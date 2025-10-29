#!/usr/bin/env python3
"""
Compliance Integration Adapter
Bridges the old compliance engine with the new rule-based engine
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import asdict

from .rule_engine import RuleEngine, ValidationResult, RuleResult
from .compliance_engine import (
    UCP600ISBPComplianceEngine,
    ComplianceResult,
    ComplianceStatus as OldComplianceStatus
)
from ..tiers.tier_manager import TierManager

logger = logging.getLogger(__name__)


class ComplianceIntegration:
    """Integration layer between old and new compliance engines"""

    def __init__(self, environment: str = "production"):
        self.environment = environment

        # Initialize both engines
        self.new_engine = RuleEngine()
        self.old_engine = UCP600ISBPComplianceEngine(environment)

        # Initialize tier manager
        self.tier_manager = TierManager()

        # Preference: use new engine by default
        self.use_new_engine = True

        logger.info(f"Compliance integration initialized - using {'new' if self.use_new_engine else 'old'} engine")

    def validate_lc_compliance(self,
                              lc_document: Dict[str, Any],
                              customer_id: str,
                              tier: Optional[str] = None,
                              remaining_free_checks: Optional[int] = None) -> Dict[str, Any]:
        """
        Unified compliance validation with tier gating

        Returns standardized compliance result
        """

        if tier is None:
            tier = self.old_engine.get_customer_tier(customer_id)

        # Check tier allowance before processing
        lc_size_mb = len(str(lc_document).encode('utf-8')) / (1024 * 1024)  # Rough size estimate
        usage_result = self.tier_manager.check_usage_allowance(customer_id, tier, lc_size_mb)

        if not usage_result.allowed:
            # Return tier-gated response
            return {
                "compliance_score": 0.0,
                "overall_status": "blocked",
                "tier_used": tier,
                "validated_rules": [],
                "execution_time_ms": 0,
                "upsell_triggered": True,
                "upsell_message": usage_result.upsell_message,
                "checks_remaining": usage_result.checks_remaining_month,
                "tier_limits": {
                    "daily": usage_result.tier_limits.max_checks_per_day,
                    "monthly": usage_result.tier_limits.max_checks_per_month,
                    "max_file_size_mb": usage_result.tier_limits.max_lc_size_mb
                },
                "error": "Usage limit exceeded"
            }

        try:
            if self.use_new_engine:
                # Use new rule-based engine
                result = self.new_engine.validate(lc_document, tier, remaining_free_checks)
                standard_result = self._convert_new_result_to_standard(result, customer_id)
            else:
                # Use old compliance engine
                result = self.old_engine.validate_against_compliance_rules(lc_document, customer_id)
                standard_result = self._convert_old_result_to_standard(result)

            # Record successful usage
            self.tier_manager.record_usage(customer_id, tier, success=True)

            # Add upsell information if triggered
            if usage_result.upsell_triggered:
                standard_result["upsell_triggered"] = True
                standard_result["upsell_message"] = usage_result.upsell_message
                standard_result["checks_remaining"] = usage_result.checks_remaining_month

            return standard_result

        except Exception as e:
            logger.error(f"Compliance validation failed: {str(e)}")

            # Fallback to the other engine
            try:
                if self.use_new_engine:
                    logger.info("Falling back to old engine")
                    result = self.old_engine.validate_against_compliance_rules(lc_document, customer_id)
                    standard_result = self._convert_old_result_to_standard(result)
                else:
                    logger.info("Falling back to new engine")
                    result = self.new_engine.validate(lc_document, tier, remaining_free_checks)
                    standard_result = self._convert_new_result_to_standard(result, customer_id)

                # Record successful usage even for fallback
                self.tier_manager.record_usage(customer_id, tier, success=True)

                return standard_result

            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                return self._create_error_result(str(e), customer_id, tier)

    def _convert_new_result_to_standard(self, result: ValidationResult, customer_id: str) -> Dict[str, Any]:
        """Convert new engine result to standardized format"""

        # Map status values
        status_map = {
            "pass": "PASS",
            "fail": "FAIL",
            "warning": "WARNING",
            "error": "ERROR"
        }

        # Convert rule results to violations format
        violations = []
        for rule_result in result.results:
            violations.append({
                "rule_id": rule_result.id,
                "rule_number": rule_result.id,
                "status": status_map.get(rule_result.status.value, "ERROR"),
                "severity": self._map_severity_from_score(rule_result.score),
                "title": f"Rule {rule_result.id}",
                "details": rule_result.details,
                "field_location": getattr(rule_result, 'field_location', None),
                "suggested_fix": getattr(rule_result, 'suggested_fix', None),
                "trade_impact": None,
                "bank_impact": None
            })

        # Calculate metrics
        passed_rules = len([v for v in violations if v["status"] == "PASS"])
        failed_rules = len([v for v in violations if v["status"] == "FAIL"])
        warning_rules = len([v for v in violations if v["status"] == "WARNING"])

        # Determine overall status
        if failed_rules > 0:
            overall_status = "FAIL"
        elif warning_rules > 0:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"

        return {
            "document_id": f"doc_{int(result.timestamp.timestamp())}",
            "customer_id": customer_id,
            "lc_reference": "LC-NEW-ENGINE",
            "validation_timestamp": result.timestamp,

            # Overall results
            "source": result.source,
            "compliance_score": result.score,
            "overall_status": overall_status,

            # Detailed results
            "validated_rules": violations,
            "total_rules_checked": len(violations),
            "rules_passed": passed_rules,
            "rules_failed": failed_rules,
            "rules_warnings": warning_rules,

            # Performance metrics
            "validation_time_ms": 0,  # New engine doesn't track this yet

            # Audit information
            "engine_version": "2.0.0-advanced",
            "rules_version": ",".join([f"{k}:{v}" for k, v in result.rule_versions.items()]),
            "tier_used": result.tier_used,

            # New engine specific
            "upsell_triggered": result.upsell_triggered,
            "checks_remaining": result.checks_remaining,
            "rule_versions": result.rule_versions
        }

    def _convert_old_result_to_standard(self, result: ComplianceResult) -> Dict[str, Any]:
        """Convert old engine result to standardized format"""

        # Convert to dict and add new engine fields
        result_dict = asdict(result)

        # Map old status enum to string
        result_dict["overall_status"] = result.overall_status.value.upper()

        # Convert violations
        violations = []
        for violation in result.validated_rules:
            violations.append({
                "rule_id": violation.rule_id,
                "rule_number": violation.rule_number,
                "status": violation.status.value.upper(),
                "severity": violation.severity,
                "title": violation.title,
                "details": violation.details,
                "field_location": violation.field_location,
                "suggested_fix": violation.suggested_fix,
                "trade_impact": violation.trade_impact,
                "bank_impact": violation.bank_impact
            })

        result_dict["validated_rules"] = violations
        result_dict["validation_timestamp"] = result.validation_timestamp

        # Add new engine compatibility fields
        result_dict.update({
            "upsell_triggered": False,  # Old engine doesn't have this
            "checks_remaining": -1 if result.tier_used != 'free' else 0,
            "rule_versions": {}
        })

        return result_dict

    def _map_severity_from_score(self, score: float) -> str:
        """Map score to severity level"""
        if score >= 3.0:
            return "critical"
        elif score >= 2.0:
            return "major"
        elif score >= 1.0:
            return "minor"
        else:
            return "advisory"

    def _create_error_result(self, error_message: str, customer_id: str, tier: str) -> Dict[str, Any]:
        """Create error result when validation fails"""
        from datetime import datetime, timezone

        return {
            "document_id": f"error_{int(datetime.now().timestamp())}",
            "customer_id": customer_id,
            "lc_reference": "ERROR",
            "validation_timestamp": datetime.now(timezone.utc),

            "source": "compliance_integration_error",
            "compliance_score": 0.0,
            "overall_status": "ERROR",

            "validated_rules": [{
                "rule_id": "system_error",
                "rule_number": "SYS-ERROR",
                "status": "ERROR",
                "severity": "critical",
                "title": "Compliance Validation Error",
                "details": error_message,
                "field_location": "system",
                "suggested_fix": "Contact technical support",
                "trade_impact": "Unable to validate compliance",
                "bank_impact": "System unavailable for compliance checking"
            }],

            "total_rules_checked": 0,
            "rules_passed": 0,
            "rules_failed": 1,
            "rules_warnings": 0,

            "validation_time_ms": 0,

            "engine_version": "error",
            "rules_version": "error",
            "tier_used": tier,

            "upsell_triggered": False,
            "checks_remaining": 0,
            "rule_versions": {}
        }

    def get_engine_status(self) -> Dict[str, Any]:
        """Get status of both engines"""
        try:
            new_engine_status = "healthy"
            new_engine_rules = len(self.new_engine.ucp600_rules) + len(self.new_engine.isbp_rules) + len(self.new_engine.local_bd_rules)
        except Exception as e:
            new_engine_status = f"error: {str(e)}"
            new_engine_rules = 0

        try:
            old_engine_status = "healthy"
            old_engine_rules = len(self.old_engine.rules)
        except Exception as e:
            old_engine_status = f"error: {str(e)}"
            old_engine_rules = 0

        return {
            "integration_version": "1.0.0",
            "active_engine": "new" if self.use_new_engine else "old",
            "engines": {
                "new_rule_engine": {
                    "status": new_engine_status,
                    "total_rules": new_engine_rules,
                    "dsl_functions": len(getattr(self.new_engine, 'dsl_functions', [])),
                    "supports_tiers": True,
                    "supports_versioning": True
                },
                "old_compliance_engine": {
                    "status": old_engine_status,
                    "total_rules": old_engine_rules,
                    "version": getattr(self.old_engine, 'engine_version', 'unknown'),
                    "supports_tiers": True,
                    "supports_versioning": False
                }
            }
        }

    def switch_engine(self, use_new_engine: bool = True):
        """Switch between engines"""
        self.use_new_engine = use_new_engine
        logger.info(f"Switched to {'new' if use_new_engine else 'old'} engine")

    def get_compliance_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get compliance summary (delegates to appropriate engine)"""
        if self.use_new_engine:
            # New engine doesn't have this method yet, create basic summary
            tier = self.old_engine.get_customer_tier(customer_id)  # Still use old for customer data

            return {
                "customer_id": customer_id,
                "tier": tier,
                "compliance_engine": {
                    "type": "advanced_rule_engine",
                    "version": "2.0.0",
                    "dsl_enabled": True,
                    "total_rules": len(self.new_engine.ucp600_rules) + len(self.new_engine.isbp_rules) + len(self.new_engine.local_bd_rules)
                },
                "tier_features": {
                    "free": "Trial - 3 advanced compliance checks with DSL evaluation",
                    "pro": "Unlimited advanced compliance with full DSL rule engine",
                    "enterprise": "Bank-grade advanced compliance with audit logging and custom rules"
                }[tier]
            }
        else:
            return self.old_engine.get_compliance_summary(customer_id)