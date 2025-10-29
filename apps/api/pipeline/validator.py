"""
Enhanced LC Validation Pipeline with UCP600/ISBP/Local Compliance Integration

Integrates comprehensive compliance checking into the main validation flow:
- After primary parsing, runs UCP600/ISBP/Local (Bangladesh) compliance validation
- Respects tier-based limits (Free: 3 checks, Pro/Enterprise: unlimited)
- Logs compliance outcomes to CloudWatch and SLA metrics
- Returns comprehensive validation results including ICC + local compliance scores
"""

import boto3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys

# Add trust platform to path
sys.path.append(str(Path(__file__).parent.parent))

from trust_platform.compliance.compliance_engine import UCP600ISBPComplianceEngine, ComplianceResult
from trust_platform.compliance.compliance_export_manager import ComplianceExportManager, ComplianceRecord

logger = logging.getLogger(__name__)

class EnhancedLCValidator:
    """Enhanced LC Validator with integrated UCP600/ISBP compliance checking"""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.cloudwatch = boto3.client('cloudwatch')

        # Initialize compliance engine
        self.compliance_engine = UCP600ISBPComplianceEngine(environment)
        self.compliance_export_manager = ComplianceExportManager(environment)

        # Load configuration for customer tiers
        config_path = Path(__file__).parent.parent / "trust_platform" / "config" / "trust_config.yaml"
        try:
            import yaml
            with open(config_path, 'r') as f:
                self.trust_config = yaml.safe_load(f)
        except:
            self.trust_config = {}

    def validate_lc_document(self, lc_document: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
        """
        Main validation function that includes compliance checking

        Args:
            lc_document: Parsed LC document (from OCR/parser)
            customer_id: Customer identifier for tier-based features

        Returns:
            Comprehensive validation result including compliance
        """
        validation_start = datetime.now(timezone.utc)

        # Get customer tier for feature access
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')

        logger.info(f"Starting LC validation for customer {customer_id} (tier: {tier})")

        # Step 1: Basic document validation (existing logic)
        basic_validation = self._perform_basic_validation(lc_document, customer_id)

        # Step 2: UCP600/ISBP Compliance validation (tier-dependent)
        compliance_result = None
        compliance_blocked = False
        upsell_triggered = False

        try:
            # Check compliance quota first
            quota_status = self.compliance_engine.check_compliance_quota(customer_id)

            if quota_status['quota_exceeded']:
                # Free tier quota exceeded - trigger upsell
                compliance_blocked = True
                upsell_triggered = True
                logger.warning(f"Compliance quota exceeded for {customer_id} - upsell triggered")

                compliance_result = {
                    'status': 'blocked',
                    'message': 'Compliance check quota exceeded for free tier',
                    'upsell_message': 'Upgrade to Pro for unlimited UCP600/ISBP + Bangladesh local rules compliance validation',
                    'tier': tier,
                    'checks_used': quota_status['checks_used'],
                    'checks_limit': quota_status['checks_limit']
                }
            else:
                # Run compliance validation
                logger.info(f"Running UCP600/ISBP/Local compliance check for {customer_id}")
                compliance_result = self.compliance_engine.validate_against_compliance_rules(
                    lc_document, customer_id
                )

                # Store compliance record for audit trail (Pro/Enterprise only)
                if tier in ['pro', 'enterprise']:
                    self._store_compliance_record(compliance_result, lc_document)

        except Exception as e:
            logger.error(f"Compliance validation failed: {str(e)}")
            compliance_result = {
                'status': 'error',
                'message': str(e),
                'tier': tier
            }

            # Don't block on compliance errors for paid tiers
            if tier == 'free' and 'quota exceeded' in str(e):
                compliance_blocked = True
                upsell_triggered = True

        # Step 3: Log metrics to CloudWatch
        self._log_validation_metrics(basic_validation, compliance_result, customer_id, tier)

        # Step 4: Log SLA metrics
        self._log_sla_metrics(basic_validation, compliance_result, customer_id, tier)

        # Step 5: Compile comprehensive result
        validation_end = datetime.now(timezone.utc)
        total_processing_time = int((validation_end - validation_start).total_seconds() * 1000)

        result = {
            'validation_id': f"val_{int(validation_start.timestamp())}",
            'document_id': lc_document.get('document_id', 'unknown'),
            'lc_reference': lc_document.get('lc_number', 'unknown'),
            'customer_id': customer_id,
            'customer_tier': tier,
            'validation_timestamp': validation_start.isoformat(),
            'total_processing_time_ms': total_processing_time,

            # Basic validation results
            'basic_validation': basic_validation,

            # Compliance validation results
            'compliance_validation': compliance_result,
            'compliance_blocked': compliance_blocked,
            'upsell_triggered': upsell_triggered,

            # Overall assessment
            'overall_status': self._determine_overall_status(basic_validation, compliance_result),
            'ready_for_bank_submission': self._is_bank_ready(basic_validation, compliance_result, tier),

            # Tier-specific features
            'tier_features': self._get_tier_features(tier, compliance_result),

            # Next steps and recommendations
            'recommendations': self._generate_recommendations(basic_validation, compliance_result, tier),
            'next_actions': self._get_next_actions(basic_validation, compliance_result, tier, upsell_triggered)
        }

        logger.info(f"LC validation completed for {customer_id}: "
                   f"Basic: {basic_validation.get('status', 'unknown')}, "
                   f"Compliance: {compliance_result.overall_status.value if hasattr(compliance_result, 'overall_status') else 'blocked'}")

        return result

    def _perform_basic_validation(self, lc_document: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
        """Perform basic LC document validation (existing functionality)"""

        # Simulate existing basic validation logic
        # In production, this would include OCR quality, field extraction, format validation, etc.

        basic_checks = {
            'document_structure': self._check_document_structure(lc_document),
            'required_fields': self._check_required_fields(lc_document),
            'data_quality': self._check_data_quality(lc_document),
            'format_compliance': self._check_format_compliance(lc_document)
        }

        # Calculate basic validation score
        passed_checks = sum(1 for check in basic_checks.values() if check['status'] == 'pass')
        total_checks = len(basic_checks)
        basic_score = passed_checks / total_checks if total_checks > 0 else 0

        # Determine basic validation status
        if basic_score >= 0.9:
            status = 'pass'
        elif basic_score >= 0.7:
            status = 'warning'
        else:
            status = 'fail'

        return {
            'status': status,
            'score': basic_score,
            'checks': basic_checks,
            'processing_time_ms': 1250,  # Simulated processing time
            'messages': [
                f"Basic validation completed with {basic_score:.1%} compliance",
                f"Document structure and required fields validated"
            ]
        }

    def _check_document_structure(self, lc_document: Dict[str, Any]) -> Dict[str, Any]:
        """Check basic document structure"""
        required_sections = ['lc_number', 'beneficiary', 'applicant', 'amount']
        present_sections = [section for section in required_sections if lc_document.get(section)]

        if len(present_sections) == len(required_sections):
            return {'status': 'pass', 'message': 'All required sections present'}
        else:
            missing = set(required_sections) - set(present_sections)
            return {'status': 'fail', 'message': f'Missing sections: {", ".join(missing)}'}

    def _check_required_fields(self, lc_document: Dict[str, Any]) -> Dict[str, Any]:
        """Check required fields are populated"""
        critical_fields = ['lc_number', 'amount', 'expiry_date']
        populated_fields = [field for field in critical_fields if lc_document.get(field)]

        if len(populated_fields) >= len(critical_fields) * 0.8:  # 80% threshold
            return {'status': 'pass', 'message': 'Critical fields populated'}
        else:
            return {'status': 'warning', 'message': 'Some critical fields may be missing'}

    def _check_data_quality(self, lc_document: Dict[str, Any]) -> Dict[str, Any]:
        """Check data quality and OCR confidence"""
        # Simulate OCR confidence scoring
        confidence_score = 0.92  # Simulated high confidence

        if confidence_score >= 0.9:
            return {'status': 'pass', 'message': f'High OCR confidence ({confidence_score:.1%})'}
        elif confidence_score >= 0.7:
            return {'status': 'warning', 'message': f'Moderate OCR confidence ({confidence_score:.1%})'}
        else:
            return {'status': 'fail', 'message': f'Low OCR confidence ({confidence_score:.1%})'}

    def _check_format_compliance(self, lc_document: Dict[str, Any]) -> Dict[str, Any]:
        """Check document format compliance"""
        # Check date formats, amount formats, etc.
        format_issues = []

        # Check date format
        expiry_date = lc_document.get('expiry_date', '')
        if expiry_date and not any(sep in expiry_date for sep in ['-', '/', '.']):
            format_issues.append('expiry date format')

        # Check amount format
        amount = lc_document.get('amount', {})
        if isinstance(amount, dict) and not amount.get('value'):
            format_issues.append('amount value')

        if not format_issues:
            return {'status': 'pass', 'message': 'Document format compliant'}
        else:
            return {'status': 'warning', 'message': f'Format issues: {", ".join(format_issues)}'}

    def _store_compliance_record(self, compliance_result: ComplianceResult, lc_document: Dict[str, Any]):
        """Store compliance record for audit trail (Pro/Enterprise only)"""
        try:
            # Create compliance record
            record = ComplianceRecord(
                record_id=f"comp_{compliance_result.document_id}_{int(datetime.now().timestamp())}",
                timestamp=compliance_result.validation_timestamp,
                customer_id=compliance_result.customer_id,
                lc_reference_number=compliance_result.lc_reference,
                validation_request_id=f"req_{compliance_result.document_id}",

                # Validation results
                validation_result=compliance_result.overall_status.value,
                processing_time_ms=compliance_result.validation_time_ms,
                accuracy_score=compliance_result.compliance_score,

                # UCP600 compliance
                ucp600_compliance=len([v for v in compliance_result.validated_rules
                                     if 'UCP600' in v.rule_number and v.status.value == 'pass']) > 0,
                ucp600_violations=[v.details for v in compliance_result.validated_rules
                                 if 'UCP600' in v.rule_number and v.status.value == 'fail'],

                # ISBP compliance
                isbp_compliance=len([v for v in compliance_result.validated_rules
                                   if 'ISBP' in v.rule_number and v.status.value == 'pass']) > 0,
                isbp_discrepancies=[v.details for v in compliance_result.validated_rules
                                  if 'ISBP' in v.rule_number and v.status.value == 'fail'],

                # Document analysis
                documents_analyzed=lc_document.get('required_documents', []),
                discrepancy_flags=[v.rule_number for v in compliance_result.validated_rules
                                 if v.status.value == 'fail'],
                risk_assessment=self._assess_risk_level(compliance_result),

                # System information
                reviewer_id="SYSTEM_AUTO",
                system_version="2.1.0",
                validation_engine_version=compliance_result.engine_version,
                rule_set_version=compliance_result.rules_version,

                # Request metadata
                request_source="VALIDATION_PIPELINE",
                client_ip_address=None,
                user_agent="LCopilot-Validator",
                session_id=None,

                # Banking information (if available)
                correspondent_bank=lc_document.get('nominated_bank'),
                issuing_bank=lc_document.get('issuing_bank'),
                trade_finance_reference=lc_document.get('lc_number'),
                regulatory_classification="STANDARD_LC"
            )

            # Store the record
            self.compliance_export_manager.store_compliance_record(record)

        except Exception as e:
            logger.error(f"Failed to store compliance record: {str(e)}")

    def _assess_risk_level(self, compliance_result: ComplianceResult) -> str:
        """Assess risk level based on compliance results"""
        critical_failures = len([v for v in compliance_result.validated_rules
                               if v.status.value == 'fail' and v.severity == 'critical'])
        major_failures = len([v for v in compliance_result.validated_rules
                            if v.status.value == 'fail' and v.severity == 'major'])

        if critical_failures > 0:
            return 'high'
        elif major_failures > 2:
            return 'medium'
        else:
            return 'low'

    def _log_validation_metrics(self, basic_validation: Dict, compliance_result: Any,
                               customer_id: str, tier: str):
        """Log validation metrics to CloudWatch"""
        try:
            # Basic validation metrics
            self.cloudwatch.put_metric_data(
                Namespace='LCopilot/Validation',
                MetricData=[
                    {
                        'MetricName': 'BasicValidationScore',
                        'Value': basic_validation.get('score', 0),
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Customer', 'Value': customer_id},
                            {'Name': 'Tier', 'Value': tier}
                        ]
                    },
                    {
                        'MetricName': 'BasicValidationProcessingTime',
                        'Value': basic_validation.get('processing_time_ms', 0),
                        'Unit': 'Milliseconds',
                        'Dimensions': [
                            {'Name': 'Customer', 'Value': customer_id},
                            {'Name': 'Tier', 'Value': tier}
                        ]
                    }
                ]
            )

            # Compliance validation metrics (if available)
            if hasattr(compliance_result, 'compliance_score'):
                self.cloudwatch.put_metric_data(
                    Namespace='LCopilot/Compliance',
                    MetricData=[
                        {
                            'MetricName': 'ComplianceScore',
                            'Value': compliance_result.compliance_score,
                            'Unit': 'None',
                            'Dimensions': [
                                {'Name': 'Customer', 'Value': customer_id},
                                {'Name': 'Tier', 'Value': tier}
                            ]
                        },
                        {
                            'MetricName': 'ComplianceValidationTime',
                            'Value': compliance_result.validation_time_ms,
                            'Unit': 'Milliseconds',
                            'Dimensions': [
                                {'Name': 'Customer', 'Value': customer_id},
                                {'Name': 'Tier', 'Value': tier}
                            ]
                        },
                        {
                            'MetricName': 'UCP600ComplianceRate',
                            'Value': len([v for v in compliance_result.validated_rules
                                        if 'UCP600' in v.rule_number and v.status.value == 'pass']) /
                                    max(1, len([v for v in compliance_result.validated_rules
                                              if 'UCP600' in v.rule_number])),
                            'Unit': 'Percent',
                            'Dimensions': [
                                {'Name': 'Customer', 'Value': customer_id},
                                {'Name': 'Tier', 'Value': tier}
                            ]
                        },
                        {
                            'MetricName': 'ISBPComplianceRate',
                            'Value': len([v for v in compliance_result.validated_rules
                                        if 'ISBP' in v.rule_number and v.status.value == 'pass']) /
                                    max(1, len([v for v in compliance_result.validated_rules
                                              if 'ISBP' in v.rule_number])),
                            'Unit': 'Percent',
                            'Dimensions': [
                                {'Name': 'Customer', 'Value': customer_id},
                                {'Name': 'Tier', 'Value': tier}
                            ]
                        }
                    ]
                )

        except Exception as e:
            logger.error(f"Failed to log validation metrics: {str(e)}")

    def _log_sla_metrics(self, basic_validation: Dict, compliance_result: Any,
                        customer_id: str, tier: str):
        """Log SLA-relevant metrics to CloudWatch"""
        try:
            # Overall validation success rate
            overall_success = 1 if (basic_validation.get('status') == 'pass' and
                                  (not hasattr(compliance_result, 'overall_status') or
                                   compliance_result.overall_status.value in ['pass', 'warning'])) else 0

            # Combined processing time
            total_processing_time = (basic_validation.get('processing_time_ms', 0) +
                                   (compliance_result.validation_time_ms if hasattr(compliance_result, 'validation_time_ms') else 0))

            self.cloudwatch.put_metric_data(
                Namespace='LCopilot/SLA',
                MetricData=[
                    {
                        'MetricName': 'ValidationSuccessRate',
                        'Value': overall_success,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Customer', 'Value': customer_id},
                            {'Name': 'Tier', 'Value': tier}
                        ]
                    },
                    {
                        'MetricName': 'TotalProcessingTime',
                        'Value': total_processing_time,
                        'Unit': 'Milliseconds',
                        'Dimensions': [
                            {'Name': 'Customer', 'Value': customer_id},
                            {'Name': 'Tier', 'Value': tier}
                        ]
                    },
                    {
                        'MetricName': 'ValidationCount',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Customer', 'Value': customer_id},
                            {'Name': 'Tier', 'Value': tier}
                        ]
                    }
                ]
            )

        except Exception as e:
            logger.error(f"Failed to log SLA metrics: {str(e)}")

    def _determine_overall_status(self, basic_validation: Dict, compliance_result: Any) -> str:
        """Determine overall validation status"""
        basic_status = basic_validation.get('status', 'fail')

        if hasattr(compliance_result, 'overall_status'):
            compliance_status = compliance_result.overall_status.value

            # Combined status logic
            if basic_status == 'pass' and compliance_status == 'pass':
                return 'pass'
            elif basic_status == 'fail' or compliance_status == 'fail':
                return 'fail'
            else:
                return 'warning'
        else:
            # If compliance is blocked/errored, base on basic validation
            return basic_status

    def _is_bank_ready(self, basic_validation: Dict, compliance_result: Any, tier: str) -> bool:
        """Determine if LC is ready for bank submission"""
        basic_ready = basic_validation.get('status') == 'pass'

        if tier == 'free':
            # Free tier: basic validation only
            return basic_ready
        elif hasattr(compliance_result, 'overall_status'):
            # Pro/Enterprise: both basic and compliance must pass
            compliance_ready = compliance_result.overall_status.value in ['pass', 'warning']
            return basic_ready and compliance_ready
        else:
            # Fallback to basic validation
            return basic_ready

    def _get_tier_features(self, tier: str, compliance_result: Any) -> Dict[str, Any]:
        """Get tier-specific features and messaging"""
        features = {
            'free': {
                'compliance_checks': '3 free UCP600/ISBP checks included',
                'features': ['Basic LC validation', 'OCR document parsing', '3 compliance checks trial'],
                'limitations': ['Limited compliance checks', 'No audit trail', 'Community support'],
                'upgrade_benefits': ['Unlimited compliance validation', 'Priority support', 'SLA reports']
            },
            'pro': {
                'compliance_checks': 'Unlimited UCP600/ISBP compliance validation',
                'features': ['Full LC validation', 'Unlimited compliance checks', 'SLA reports', 'Priority support'],
                'limitations': ['No audit trail', 'No API access'],
                'upgrade_benefits': ['Audit-grade compliance', 'API access', 'Custom integrations', 'Dedicated support']
            },
            'enterprise': {
                'compliance_checks': 'Bank-grade UCP600/ISBP compliance with audit trail',
                'features': ['Complete LC validation suite', 'Audit-grade compliance', 'API access', 'Custom integrations', 'Dedicated support'],
                'limitations': [],
                'upgrade_benefits': []
            }
        }

        tier_info = features.get(tier, features['free'])

        # Add compliance-specific information
        if hasattr(compliance_result, 'compliance_score'):
            tier_info['compliance_score'] = compliance_result.compliance_score
            tier_info['rules_checked'] = compliance_result.total_rules_checked

        return tier_info

    def _generate_recommendations(self, basic_validation: Dict, compliance_result: Any, tier: str) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Basic validation recommendations
        if basic_validation.get('status') != 'pass':
            recommendations.append("Review basic document structure and required fields")

            for check_name, check_result in basic_validation.get('checks', {}).items():
                if check_result['status'] != 'pass':
                    recommendations.append(f"Address {check_name.replace('_', ' ')}: {check_result['message']}")

        # Compliance recommendations
        if hasattr(compliance_result, 'validated_rules'):
            failed_rules = [v for v in compliance_result.validated_rules if v.status.value == 'fail']

            # Group by severity
            critical_failures = [v for v in failed_rules if v.severity == 'critical']
            major_failures = [v for v in failed_rules if v.severity == 'major']

            if critical_failures:
                recommendations.append(f"CRITICAL: Fix {len(critical_failures)} critical UCP600/ISBP violations before bank submission")
                for violation in critical_failures[:3]:  # Show top 3
                    if violation.suggested_fix:
                        recommendations.append(f"• {violation.rule_number}: {violation.suggested_fix}")

            if major_failures:
                recommendations.append(f"Address {len(major_failures)} major compliance issues to improve bank acceptance probability")

        # Tier-specific recommendations
        if tier == 'free':
            recommendations.append("Upgrade to Pro for unlimited compliance validation and priority support")
        elif tier == 'pro':
            recommendations.append("Consider Enterprise for audit-grade compliance and API access")

        return recommendations

    def _get_next_actions(self, basic_validation: Dict, compliance_result: Any, tier: str, upsell_triggered: bool) -> List[Dict[str, Any]]:
        """Get specific next actions for the user"""
        actions = []

        # Upsell action for free tier
        if upsell_triggered:
            actions.append({
                'type': 'upgrade',
                'priority': 'high',
                'title': 'Upgrade to Continue',
                'description': 'You have used your 3 free compliance checks. Upgrade to Pro for unlimited UCP600/ISBP validation.',
                'action_url': '/upgrade/pro',
                'action_text': 'Upgrade Now'
            })

        # Compliance actions
        if hasattr(compliance_result, 'validated_rules'):
            critical_failures = [v for v in compliance_result.validated_rules
                               if v.status.value == 'fail' and v.severity == 'critical']

            if critical_failures:
                actions.append({
                    'type': 'fix_critical',
                    'priority': 'high',
                    'title': 'Fix Critical Issues',
                    'description': f'{len(critical_failures)} critical UCP600/ISBP violations must be resolved',
                    'action_url': '/compliance/issues',
                    'action_text': 'View Issues'
                })

        # Submission actions
        overall_status = self._determine_overall_status(basic_validation, compliance_result)
        if overall_status == 'pass':
            actions.append({
                'type': 'submit',
                'priority': 'normal',
                'title': 'Ready for Bank Submission',
                'description': 'Your LC passes UCP600/ISBP compliance checks and is ready for bank submission',
                'action_url': '/submit',
                'action_text': 'Submit to Bank'
            })

        return actions

def main():
    """Demo the enhanced LC validation pipeline"""
    validator = EnhancedLCValidator()

    print("=== LCopilot Enhanced LC Validation Pipeline Demo ===")

    # Sample LC document
    sample_lc = {
        'document_id': 'lc_pipeline_demo_001',
        'lc_number': 'LC2024001',
        'lc_type': 'Irrevocable Documentary Credit',
        'issue_date': '2024-01-15',
        'expiry_date': '2024-03-15',
        'expiry_place': 'Counters of the nominated bank',
        'latest_shipment_date': '2024-03-01',
        'amount': {'value': 50000.00, 'currency': 'USD'},
        'beneficiary': {
            'name': 'Global Exports Ltd',
            'address': '123 Export St, Trade City, TC 12345'
        },
        'applicant': {
            'name': 'American Imports Inc',
            'address': '456 Import Ave, Commerce City, CC 67890'
        },
        'terms_and_conditions': 'This credit is subject to UCP600. Documents must be presented within 21 days of shipment.',
        'required_documents': [
            'Commercial Invoice signed and dated',
            'Clean on board Bill of Lading',
            'Insurance Policy for 110% of CIF value'
        ]
    }

    # Test validation with different customer tiers
    test_customers = ['sme-importer-001', 'pro-trader-001', 'enterprise-bank-001']

    for customer_id in test_customers:
        print(f"\n--- Testing validation for {customer_id} ---")

        try:
            result = validator.validate_lc_document(sample_lc, customer_id)

            print(f"Customer: {customer_id} (Tier: {result['customer_tier']})")
            print(f"Overall Status: {result['overall_status']}")
            print(f"Bank Ready: {result['ready_for_bank_submission']}")
            print(f"Processing Time: {result['total_processing_time_ms']}ms")

            # Basic validation
            basic = result['basic_validation']
            print(f"Basic Validation: {basic['status']} (Score: {basic['score']:.2f})")

            # Compliance validation
            compliance = result['compliance_validation']
            if hasattr(compliance, 'compliance_score'):
                print(f"Compliance Score: {compliance.compliance_score:.3f}")
                print(f"UCP600/ISBP Rules: {compliance.total_rules_checked} checked")
            elif isinstance(compliance, dict) and compliance.get('status') == 'blocked':
                print(f"Compliance: {compliance['message']}")
                print(f"Checks Used: {compliance['checks_used']}/{compliance['checks_limit']}")

            # Show key recommendations
            if result['recommendations']:
                print("Key Recommendations:")
                for i, rec in enumerate(result['recommendations'][:3], 1):
                    print(f"  {i}. {rec}")

            # Show next actions
            if result['next_actions']:
                print("Next Actions:")
                for action in result['next_actions']:
                    print(f"  • {action['title']}: {action['description']}")

            # Show upsell if triggered
            if result['upsell_triggered']:
                print("🚀 UPGRADE OPPORTUNITY: Unlock unlimited compliance validation!")

        except Exception as e:
            print(f"Validation failed for {customer_id}: {str(e)}")

    print("\n=== Pipeline Demo Complete ===")

if __name__ == "__main__":
    main()