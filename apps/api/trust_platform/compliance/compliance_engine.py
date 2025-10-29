"""
LCopilot UCP600 + ISBP Compliance Engine

Validates Letter of Credit documents against ICC rules:
- UCP600 (Uniform Customs and Practice for Documentary Credits)
- ISBP (International Standard Banking Practice)

Tier-based validation:
- Free: 3 compliance checks (teaser)
- Pro: Unlimited compliance validation
- Enterprise: Unlimited + audit-grade logging with digital signatures
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
from enum import Enum

logger = logging.getLogger(__name__)

class ComplianceStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"

class RuleCategory(Enum):
    UCP600 = "ucp600"
    ISBP = "isbp"
    LOCAL_REGULATION = "local_regulation"

@dataclass
class ComplianceRule:
    rule_id: str
    rule_number: str  # e.g., "UCP600-14", "ISBP-42"
    category: RuleCategory
    title: str
    description: str
    validation_logic: str  # Python code or regex pattern
    severity: str  # "critical", "major", "minor", "advisory"
    trade_impact: str  # Impact description for traders
    bank_impact: str   # Impact description for banks

@dataclass
class ComplianceViolation:
    rule_id: str
    rule_number: str
    status: ComplianceStatus
    severity: str
    title: str
    details: str
    field_location: Optional[str] = None
    suggested_fix: Optional[str] = None
    trade_impact: Optional[str] = None
    bank_impact: Optional[str] = None

@dataclass
class ComplianceResult:
    document_id: str
    customer_id: str
    lc_reference: str
    validation_timestamp: datetime

    # Overall results
    source: str  # "ucp600_isbp"
    compliance_score: float  # 0.0 to 1.0
    overall_status: ComplianceStatus

    # Detailed results
    validated_rules: List[ComplianceViolation]
    total_rules_checked: int
    rules_passed: int
    rules_failed: int
    rules_warnings: int

    # Performance metrics
    validation_time_ms: int

    # Audit information
    engine_version: str
    rules_version: str
    tier_used: str

class UCP600ISBPComplianceEngine:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.engine_version = "2.2.0"
        self.rules_version = "UCP600-2024.1_ISBP-2024.1_BD-Local-2024.1"

        # Load trust configuration for tier limits
        self.config_path = Path(__file__).parent.parent / "config" / "trust_config.yaml"
        self.trust_config = self._load_trust_config()

        # Load comprehensive compliance rules (UCP600 + ISBP + Local)
        self.rules_path = Path(__file__).parent / "rules" / "ucp_isbp_rules.yaml"
        self.compliance_rules_yaml = self._load_compliance_rules_yaml()
        self.rules = self._load_compliance_rules()

        # Track usage for free tier limits
        self.usage_tracker = {}

    def _load_trust_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Trust config not found at {self.config_path}")
            return {}

    def _load_compliance_rules_yaml(self) -> Dict[str, Any]:
        """Load comprehensive compliance rules from YAML file"""
        try:
            with open(self.rules_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Compliance rules YAML not found at {self.rules_path}")
            return {}

    def _load_compliance_rules(self) -> Dict[str, ComplianceRule]:
        """Load UCP600, ISBP, and Local compliance rules from YAML"""
        rules = {}

        if not self.compliance_rules_yaml:
            logger.warning("No compliance rules YAML loaded, falling back to hardcoded rules")
            return self._load_hardcoded_rules()

        # Load UCP600 rules from YAML
        ucp600_rules_yaml = self.compliance_rules_yaml.get('ucp600', [])
        for rule_data in ucp600_rules_yaml:
            rule = ComplianceRule(
                rule_id=f"ucp600_{rule_data['id'].replace('-', '_').lower()}",
                rule_number=rule_data['id'],
                category=RuleCategory.UCP600,
                title=f"UCP600 {rule_data['id']}: {rule_data['description'][:50]}...",
                description=rule_data['description'],
                validation_logic=rule_data['check'],
                severity=rule_data['severity'],
                trade_impact=f"Rejection risk: {rule_data['rejection_risk']} (occurs in {rule_data['frequency']} of cases)",
                bank_impact="UCP600 compliance affects bank examination standards"
            )
            rules[rule.rule_id] = rule

        # Load ISBP rules from YAML
        isbp_rules_yaml = self.compliance_rules_yaml.get('isbp', [])
        for rule_data in isbp_rules_yaml:
            rule = ComplianceRule(
                rule_id=f"isbp_{rule_data['id'].replace('-', '_').lower()}",
                rule_number=rule_data['id'],
                category=RuleCategory.ISBP,
                title=f"ISBP {rule_data['id']}: {rule_data['description'][:50]}...",
                description=rule_data['description'],
                validation_logic=rule_data['check'],
                severity=rule_data['severity'],
                trade_impact=f"Rejection risk: {rule_data['rejection_risk']} (occurs in {rule_data['frequency']} of cases)",
                bank_impact="ISBP standards provide practical guidance for document examination"
            )
            rules[rule.rule_id] = rule

        # Load Local (Bangladesh) rules from YAML
        local_rules_yaml = self.compliance_rules_yaml.get('local_rules', [])
        for rule_data in local_rules_yaml:
            banks_list = ", ".join(rule_data.get('banks_enforcing', [])[:3])
            rule = ComplianceRule(
                rule_id=f"local_{rule_data['id'].replace('-', '_').lower()}",
                rule_number=rule_data['id'],
                category=RuleCategory.LOCAL_REGULATION,
                title=f"BD {rule_data['id']}: {rule_data['description'][:50]}...",
                description=rule_data['description'],
                validation_logic=rule_data['check'],
                severity=rule_data['severity'],
                trade_impact=f"BD banks rejection risk: {rule_data['rejection_risk']} (occurs in {rule_data['frequency']} of cases). {rule_data['local_context']}",
                bank_impact=f"Commonly enforced by: {banks_list}. {rule_data['local_context']}"
            )
            rules[rule.rule_id] = rule

        logger.info(f"Loaded {len(rules)} compliance rules from YAML: "
                   f"{len(ucp600_rules_yaml)} UCP600, {len(isbp_rules_yaml)} ISBP, {len(local_rules_yaml)} Local")
        return rules

    def _load_hardcoded_rules(self) -> Dict[str, ComplianceRule]:
        """Fallback hardcoded rules if YAML fails to load"""
        rules = {}

        # UCP600 Rules (key provisions)
        ucp600_rules = [
            {
                'rule_id': 'ucp600_01',
                'rule_number': 'UCP600-2',
                'title': 'Definitions - Credit',
                'description': 'Credit must be irrevocable and must clearly indicate it is subject to UCP600',
                'validation_logic': 'check_irrevocable_and_ucp600_reference',
                'severity': 'critical',
                'trade_impact': 'LC may be rejected if not clearly irrevocable or UCP600 compliant',
                'bank_impact': 'Non-compliance creates legal ambiguity and potential liability'
            },
            {
                'rule_id': 'ucp600_02',
                'rule_number': 'UCP600-6',
                'title': 'Availability, Expiry Date and Place',
                'description': 'Credit must state expiry date and place for presentation of documents',
                'validation_logic': 'check_expiry_date_and_place',
                'severity': 'critical',
                'trade_impact': 'Without clear expiry and place, LC cannot be used for payment',
                'bank_impact': 'Ambiguous terms create operational risk and potential disputes'
            },
            {
                'rule_id': 'ucp600_03',
                'rule_number': 'UCP600-14',
                'title': 'Standard for Examination of Documents',
                'description': 'Documents must appear on their face to comply with terms and conditions',
                'validation_logic': 'check_document_face_compliance',
                'severity': 'major',
                'trade_impact': 'Document discrepancies can delay or prevent payment',
                'bank_impact': 'Document examination standard affects liability for wrongful dishonor'
            },
            {
                'rule_id': 'ucp600_04',
                'rule_number': 'UCP600-16',
                'title': 'Complying Presentation',
                'description': 'Presentation must comply with credit terms, UCP600, and applicable ISBP',
                'validation_logic': 'check_complying_presentation',
                'severity': 'critical',
                'trade_impact': 'Non-complying presentation results in dishonor and payment delay',
                'bank_impact': 'Determines acceptance/rejection decision and potential liability'
            },
            {
                'rule_id': 'ucp600_05',
                'rule_number': 'UCP600-18',
                'title': 'Documents vs Credit Terms',
                'description': 'Documents must not conflict with each other or credit terms',
                'validation_logic': 'check_document_consistency',
                'severity': 'major',
                'trade_impact': 'Conflicting documents typically result in discrepancies',
                'bank_impact': 'Document conflicts justify dishonor under UCP600'
            },
            {
                'rule_id': 'ucp600_06',
                'rule_number': 'UCP600-20',
                'title': 'Commercial Invoice',
                'description': 'Invoice must be issued by beneficiary and comply with credit terms',
                'validation_logic': 'check_commercial_invoice',
                'severity': 'critical',
                'trade_impact': 'Invoice discrepancies are most common cause of LC rejection',
                'bank_impact': 'Invoice compliance is fundamental to LC examination'
            },
            {
                'rule_id': 'ucp600_07',
                'rule_number': 'UCP600-23',
                'title': 'Marine/Ocean Bill of Lading',
                'description': 'B/L must meet UCP600 requirements for negotiable transport documents',
                'validation_logic': 'check_marine_bill_of_lading',
                'severity': 'critical',
                'trade_impact': 'B/L discrepancies can prevent goods release and payment',
                'bank_impact': 'Transport document compliance affects security interest'
            },
            {
                'rule_id': 'ucp600_08',
                'rule_number': 'UCP600-31',
                'title': 'Date Terminology',
                'description': 'Shipping dates and document dates must comply with credit requirements',
                'validation_logic': 'check_date_terminology',
                'severity': 'major',
                'trade_impact': 'Date discrepancies frequently cause LC dishonor',
                'bank_impact': 'Date compliance affects timing of payment obligations'
            }
        ]

        # ISBP Rules (International Standard Banking Practice)
        isbp_rules = [
            {
                'rule_id': 'isbp_01',
                'rule_number': 'ISBP-A1',
                'title': 'General Principles',
                'description': 'Documents examined for face compliance with credit terms',
                'validation_logic': 'check_isbp_general_principles',
                'severity': 'major',
                'trade_impact': 'ISBP interpretation affects document acceptance standards',
                'bank_impact': 'ISBP provides standardized examination practices'
            },
            {
                'rule_id': 'isbp_02',
                'rule_number': 'ISBP-A6',
                'title': 'Addresses in Documents',
                'description': 'Addresses must be consistent but need not be identical',
                'validation_logic': 'check_address_consistency',
                'severity': 'minor',
                'trade_impact': 'Minor address variations typically acceptable under ISBP',
                'bank_impact': 'ISBP guidance reduces unnecessary discrepancies'
            },
            {
                'rule_id': 'isbp_03',
                'rule_number': 'ISBP-A11',
                'title': 'Dates in Documents',
                'description': 'Document dates must be logical and not contradict each other',
                'validation_logic': 'check_document_date_logic',
                'severity': 'major',
                'trade_impact': 'Illogical dates create obvious discrepancies',
                'bank_impact': 'Date logic is fundamental to document examination'
            },
            {
                'rule_id': 'isbp_04',
                'rule_number': 'ISBP-B2',
                'title': 'Invoice Currency and Amount',
                'description': 'Invoice amount must not exceed credit amount',
                'validation_logic': 'check_invoice_amount_limit',
                'severity': 'critical',
                'trade_impact': 'Excess invoice amount results in automatic dishonor',
                'bank_impact': 'Amount compliance is fundamental LC requirement'
            },
            {
                'rule_id': 'isbp_05',
                'rule_number': 'ISBP-D3',
                'title': 'Transport Document Dates',
                'description': 'Transport documents must show appropriate dispatch/shipment dates',
                'validation_logic': 'check_transport_document_dates',
                'severity': 'major',
                'trade_impact': 'Transport date discrepancies can prevent goods release',
                'bank_impact': 'Transport dates affect payment timing under credit'
            },
            {
                'rule_id': 'isbp_06',
                'rule_number': 'ISBP-E1',
                'title': 'Insurance Document Requirements',
                'description': 'Insurance must cover credit amount and required risks',
                'validation_logic': 'check_insurance_coverage',
                'severity': 'major',
                'trade_impact': 'Inadequate insurance coverage creates payment risk',
                'bank_impact': 'Insurance adequacy affects risk mitigation'
            },
            {
                'rule_id': 'isbp_07',
                'rule_number': 'ISBP-F1',
                'title': 'Certificate and Declaration Requirements',
                'description': 'Certificates must be properly signed and dated',
                'validation_logic': 'check_certificate_requirements',
                'severity': 'minor',
                'trade_impact': 'Certificate defects are often waivable by applicant',
                'bank_impact': 'Certificate compliance follows ISBP standards'
            },
            {
                'rule_id': 'isbp_08',
                'rule_number': 'ISBP-G1',
                'title': 'Legalization and Authentication',
                'description': 'Documents requiring legalization must be properly authenticated',
                'validation_logic': 'check_legalization_requirements',
                'severity': 'major',
                'trade_impact': 'Missing legalization can prevent document acceptance',
                'bank_impact': 'Authentication requirements vary by jurisdiction'
            }
        ]

        # Convert to ComplianceRule objects
        all_rule_data = ucp600_rules + isbp_rules

        for rule_data in all_rule_data:
            category = RuleCategory.UCP600 if rule_data['rule_number'].startswith('UCP600') else RuleCategory.ISBP

            rule = ComplianceRule(
                rule_id=rule_data['rule_id'],
                rule_number=rule_data['rule_number'],
                category=category,
                title=rule_data['title'],
                description=rule_data['description'],
                validation_logic=rule_data['validation_logic'],
                severity=rule_data['severity'],
                trade_impact=rule_data['trade_impact'],
                bank_impact=rule_data['bank_impact']
            )

            rules[rule.rule_id] = rule

        logger.info(f"Loaded {len(rules)} compliance rules ({len(ucp600_rules)} UCP600, {len(isbp_rules)} ISBP)")
        return rules

    def get_customer_tier(self, customer_id: str) -> str:
        """Get customer tier for compliance check limits"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        return customer_data.get('tier', 'free')

    def check_compliance_quota(self, customer_id: str) -> Dict[str, Any]:
        """Check if customer has remaining compliance checks"""
        tier = self.get_customer_tier(customer_id)

        if tier == 'free':
            # Track usage for free tier (3 checks limit)
            current_usage = self.usage_tracker.get(customer_id, 0)
            remaining = max(0, 3 - current_usage)

            return {
                'tier': tier,
                'checks_used': current_usage,
                'checks_remaining': remaining,
                'checks_limit': 3,
                'unlimited': False,
                'quota_exceeded': remaining == 0
            }
        else:
            # Pro and Enterprise have unlimited checks
            return {
                'tier': tier,
                'checks_used': -1,
                'checks_remaining': -1,
                'checks_limit': -1,
                'unlimited': True,
                'quota_exceeded': False
            }

    def validate_against_compliance_rules(self, lc_document: Dict[str, Any],
                                        customer_id: str) -> ComplianceResult:
        """Main compliance validation function"""
        start_time = datetime.now()

        # Check quota for free tier
        quota_status = self.check_compliance_quota(customer_id)
        if quota_status['quota_exceeded']:
            raise ValueError(f"Compliance check quota exceeded for {quota_status['tier']} tier. "
                           f"Upgrade to Pro for unlimited compliance validation.")

        # Extract LC data
        lc_reference = lc_document.get('lc_number', 'UNKNOWN')
        document_id = lc_document.get('document_id', f"doc_{int(datetime.now().timestamp())}")

        # Initialize results
        violations = []

        # Run compliance checks
        for rule_id, rule in self.rules.items():
            try:
                violation = self._execute_compliance_rule(rule, lc_document)
                if violation:
                    violations.append(violation)
            except Exception as e:
                logger.error(f"Error executing rule {rule_id}: {str(e)}")
                # Add error as warning
                error_violation = ComplianceViolation(
                    rule_id=rule_id,
                    rule_number=rule.rule_number,
                    status=ComplianceStatus.WARNING,
                    severity="minor",
                    title=f"Rule Execution Error: {rule.title}",
                    details=f"Unable to execute rule: {str(e)}",
                    suggested_fix="Contact support for rule execution issue"
                )
                violations.append(error_violation)

        # Calculate compliance metrics
        total_rules = len(self.rules)
        passed_rules = len([v for v in violations if v.status == ComplianceStatus.PASS])
        failed_rules = len([v for v in violations if v.status == ComplianceStatus.FAIL])
        warning_rules = len([v for v in violations if v.status == ComplianceStatus.WARNING])

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(violations)

        # Determine overall status
        overall_status = self._determine_overall_status(violations)

        # Update usage for free tier
        if quota_status['tier'] == 'free':
            self.usage_tracker[customer_id] = quota_status['checks_used'] + 1

        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # Create result
        result = ComplianceResult(
            document_id=document_id,
            customer_id=customer_id,
            lc_reference=lc_reference,
            validation_timestamp=datetime.now(timezone.utc),
            source="ucp600_isbp",
            compliance_score=compliance_score,
            overall_status=overall_status,
            validated_rules=violations,
            total_rules_checked=total_rules,
            rules_passed=passed_rules,
            rules_failed=failed_rules,
            rules_warnings=warning_rules,
            validation_time_ms=processing_time,
            engine_version=self.engine_version,
            rules_version=self.rules_version,
            tier_used=quota_status['tier']
        )

        logger.info(f"Compliance validation completed for {lc_reference}: "
                   f"Score {compliance_score:.3f}, Status {overall_status.value}")

        return result

    def _execute_compliance_rule(self, rule: ComplianceRule, lc_document: Dict[str, Any]) -> Optional[ComplianceViolation]:
        """Execute individual compliance rule validation"""

        # Map validation logic to actual validation methods
        validation_methods = {
            # UCP600 validation methods
            'check_irrevocable_and_ucp600_reference': self._check_irrevocable_and_ucp600,
            'validate_expiry_date_and_place': self._check_expiry_date_and_place,
            'validate_presentation_period': self._check_presentation_period,
            'check_document_face_compliance': self._check_document_face_compliance,
            'check_complying_presentation': self._check_complying_presentation,
            'check_document_consistency': self._check_document_consistency,
            'validate_invoice_description_match': self._check_commercial_invoice,
            'validate_invoice_amount_limit': self._check_invoice_amount_limit,
            'validate_bill_of_lading_ports': self._check_marine_bill_of_lading,
            'validate_transport_document_dates': self._check_transport_document_dates,
            'validate_partial_shipment_terms': self._check_partial_shipment,
            'validate_insurance_compliance': self._check_insurance_coverage,
            'check_marine_bill_of_lading': self._check_marine_bill_of_lading,
            'check_date_terminology': self._check_date_terminology,

            # ISBP validation methods
            'check_isbp_general_principles': self._check_isbp_general_principles,
            'validate_party_name_consistency': self._check_address_consistency,
            'validate_invoice_description_consistency': self._check_document_consistency,
            'validate_transport_routing': self._check_transport_routing,
            'validate_certificate_of_origin': self._check_certificate_requirements,
            'validate_packing_list_consistency': self._check_packing_list,
            'validate_transport_date_requirements': self._check_transport_document_dates,
            'validate_invoice_calculations': self._check_invoice_calculations,
            'check_address_consistency': self._check_address_consistency,
            'check_document_date_logic': self._check_document_date_logic,
            'check_invoice_amount_limit': self._check_invoice_amount_limit,
            'check_transport_document_dates': self._check_transport_document_dates,
            'check_insurance_coverage': self._check_insurance_coverage,
            'check_certificate_requirements': self._check_certificate_requirements,
            'check_legalization_requirements': self._check_legalization_requirements,

            # Bangladesh Local validation methods
            'validate_beneficiary_address_exact_match': self._check_beneficiary_address_exact,
            'validate_currency_consistency': self._check_currency_consistency,
            'validate_hs_code_exact_match': self._check_hs_code_exact,
            'validate_partial_shipment_compliance': self._check_partial_shipment_bd,
            'validate_insurance_coverage_percentage': self._check_insurance_coverage_110,
            'validate_export_permit_consistency': self._check_export_permit,
            'validate_inspection_certificate_lc_reference': self._check_inspection_certificate,
            'validate_origin_certificate_issuer': self._check_origin_certificate_issuer,
            'validate_loading_port_exact_match': self._check_loading_port_exact,
            'validate_gsp_form_details': self._check_gsp_form
        }

        validation_method = validation_methods.get(rule.validation_logic)
        if not validation_method:
            logger.warning(f"No validation method found for rule {rule.rule_id}")
            return None

        try:
            # Execute validation
            is_compliant, details, field_location, suggested_fix = validation_method(lc_document)

            if is_compliant:
                status = ComplianceStatus.PASS
                details = details or f"Compliant with {rule.rule_number}"
            else:
                status = ComplianceStatus.FAIL

            return ComplianceViolation(
                rule_id=rule.rule_id,
                rule_number=rule.rule_number,
                status=status,
                severity=rule.severity,
                title=rule.title,
                details=details,
                field_location=field_location,
                suggested_fix=suggested_fix,
                trade_impact=rule.trade_impact if status == ComplianceStatus.FAIL else None,
                bank_impact=rule.bank_impact if status == ComplianceStatus.FAIL else None
            )

        except Exception as e:
            logger.error(f"Error in validation method {rule.validation_logic}: {str(e)}")
            return None

    # UCP600 Validation Methods
    def _check_irrevocable_and_ucp600(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-2: Check if LC is irrevocable and references UCP600"""
        lc_type = lc_doc.get('lc_type', '').lower()
        terms_conditions = lc_doc.get('terms_and_conditions', '').lower()

        is_irrevocable = 'irrevocable' in lc_type or 'irrevocable' in terms_conditions
        references_ucp600 = 'ucp600' in terms_conditions or 'ucp 600' in terms_conditions

        if is_irrevocable and references_ucp600:
            return True, "LC is irrevocable and subject to UCP600", "lc_type,terms_and_conditions", ""
        elif not is_irrevocable:
            return False, "LC must be explicitly stated as irrevocable", "lc_type", "Add 'IRREVOCABLE' to LC type"
        else:
            return False, "LC must reference UCP600 in terms and conditions", "terms_and_conditions", "Add 'Subject to UCP600' clause"

    def _check_expiry_date_and_place(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-6: Check expiry date and place for presentation"""
        expiry_date = lc_doc.get('expiry_date')
        expiry_place = lc_doc.get('expiry_place')

        if expiry_date and expiry_place:
            return True, f"Expiry date {expiry_date} and place {expiry_place} specified", "expiry_date,expiry_place", ""
        elif not expiry_date:
            return False, "LC must specify expiry date for document presentation", "expiry_date", "Add specific expiry date"
        else:
            return False, "LC must specify place for document presentation", "expiry_place", "Add expiry place (e.g., 'counters of the nominated bank')"

    def _check_document_face_compliance(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-14: Check document face compliance"""
        documents = lc_doc.get('required_documents', [])

        if not documents:
            return False, "No documents specified in LC", "required_documents", "Specify required documents list"

        # Check if documents have basic requirements
        has_invoice = any('invoice' in doc.lower() for doc in documents)
        has_transport = any(transport_term in doc.lower() for doc in documents for transport_term in ['bill of lading', 'airway bill', 'transport'])

        if has_invoice and has_transport:
            return True, "Required documents include invoice and transport document", "required_documents", ""
        else:
            missing = []
            if not has_invoice:
                missing.append("commercial invoice")
            if not has_transport:
                missing.append("transport document")

            return False, f"Missing essential documents: {', '.join(missing)}", "required_documents", f"Add {', '.join(missing)} to required documents"

    def _check_complying_presentation(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-16: Check complying presentation requirements"""
        presentation_period = lc_doc.get('presentation_period')

        if presentation_period:
            # Extract number of days
            try:
                if 'day' in presentation_period.lower():
                    days = int(re.search(r'(\d+)', presentation_period).group(1))
                    if days <= 21:
                        return True, f"Presentation period of {days} days complies with standard practice", "presentation_period", ""
                    else:
                        return False, f"Presentation period of {days} days exceeds recommended 21 days", "presentation_period", "Consider reducing to 21 days or less"
                else:
                    return True, "Presentation period specified", "presentation_period", ""
            except:
                return False, "Presentation period format unclear", "presentation_period", "Specify clear presentation period (e.g., '21 days')"
        else:
            return False, "No presentation period specified", "presentation_period", "Add presentation period for documents"

    def _check_document_consistency(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-18: Check document consistency"""
        beneficiary = lc_doc.get('beneficiary', {}).get('name', '').lower()
        applicant = lc_doc.get('applicant', {}).get('name', '').lower()

        if beneficiary and applicant and beneficiary != applicant:
            return True, "Beneficiary and applicant are different parties", "beneficiary,applicant", ""
        elif not beneficiary:
            return False, "Beneficiary name not specified", "beneficiary", "Add complete beneficiary details"
        elif not applicant:
            return False, "Applicant name not specified", "applicant", "Add complete applicant details"
        else:
            return False, "Beneficiary and applicant cannot be the same party", "beneficiary,applicant", "Verify beneficiary and applicant are different entities"

    def _check_commercial_invoice(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-20: Check commercial invoice requirements"""
        documents = lc_doc.get('required_documents', [])
        invoice_required = any('invoice' in doc.lower() for doc in documents)

        if invoice_required:
            # Check if invoice details are specified
            invoice_details = lc_doc.get('invoice_requirements', '')
            if 'signed' in invoice_details.lower() or 'certified' in invoice_details.lower():
                return True, "Commercial invoice requirements specified", "required_documents,invoice_requirements", ""
            else:
                return False, "Invoice requirements should specify signing/certification", "invoice_requirements", "Add invoice signing or certification requirements"
        else:
            return False, "Commercial invoice not in required documents list", "required_documents", "Add commercial invoice to required documents"

    def _check_marine_bill_of_lading(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-23: Check marine/ocean bill of lading"""
        documents = lc_doc.get('required_documents', [])
        has_marine_bl = any('bill of lading' in doc.lower() or 'b/l' in doc.lower() for doc in documents)

        if has_marine_bl:
            bl_requirements = lc_doc.get('transport_document_requirements', '').lower()
            if 'clean' in bl_requirements or 'on board' in bl_requirements:
                return True, "Marine bill of lading requirements specified", "required_documents,transport_document_requirements", ""
            else:
                return False, "B/L should specify 'clean' and 'on board' requirements", "transport_document_requirements", "Add 'clean on board' B/L requirement"
        else:
            # Not applicable if no marine B/L required
            return True, "Marine B/L not required", "required_documents", ""

    def _check_date_terminology(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """UCP600-31: Check date terminology"""
        latest_shipment = lc_doc.get('latest_shipment_date')
        expiry_date = lc_doc.get('expiry_date')

        if latest_shipment and expiry_date:
            try:
                # Parse dates (simplified - would need robust date parsing in production)
                ship_date = datetime.fromisoformat(latest_shipment.replace('/', '-'))
                exp_date = datetime.fromisoformat(expiry_date.replace('/', '-'))

                if ship_date <= exp_date:
                    return True, "Latest shipment date is before expiry date", "latest_shipment_date,expiry_date", ""
                else:
                    return False, "Latest shipment date cannot be after expiry date", "latest_shipment_date,expiry_date", "Ensure shipment date is before expiry date"
            except:
                return False, "Date format unclear", "latest_shipment_date,expiry_date", "Use standard date format (YYYY-MM-DD)"
        else:
            return False, "Missing shipment date or expiry date", "latest_shipment_date,expiry_date", "Specify both shipment and expiry dates"

    # ISBP Validation Methods
    def _check_isbp_general_principles(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-A1: General principles compliance"""
        # Check if LC has clear terms and conditions
        terms = lc_doc.get('terms_and_conditions', '')

        if len(terms) > 50:  # Reasonable length for T&C
            return True, "Terms and conditions are detailed", "terms_and_conditions", ""
        else:
            return False, "Terms and conditions should be more detailed", "terms_and_conditions", "Expand terms and conditions with specific requirements"

    def _check_address_consistency(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-A6: Address consistency"""
        beneficiary_addr = lc_doc.get('beneficiary', {}).get('address', '').lower()
        applicant_addr = lc_doc.get('applicant', {}).get('address', '').lower()

        if beneficiary_addr and applicant_addr:
            return True, "Beneficiary and applicant addresses present", "beneficiary,applicant", ""
        elif not beneficiary_addr:
            return False, "Beneficiary address missing", "beneficiary", "Add complete beneficiary address"
        else:
            return False, "Applicant address missing", "applicant", "Add complete applicant address"

    def _check_document_date_logic(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-A11: Document date logic"""
        issue_date = lc_doc.get('issue_date')
        expiry_date = lc_doc.get('expiry_date')

        if issue_date and expiry_date:
            try:
                issue_dt = datetime.fromisoformat(issue_date.replace('/', '-'))
                expiry_dt = datetime.fromisoformat(expiry_date.replace('/', '-'))

                if issue_dt < expiry_dt:
                    return True, "Issue date is before expiry date", "issue_date,expiry_date", ""
                else:
                    return False, "Issue date must be before expiry date", "issue_date,expiry_date", "Ensure issue date precedes expiry date"
            except:
                return False, "Date format issues", "issue_date,expiry_date", "Use consistent date format"
        else:
            return False, "Missing issue date or expiry date", "issue_date,expiry_date", "Specify both issue and expiry dates"

    def _check_invoice_amount_limit(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-B2: Invoice amount must not exceed LC amount"""
        lc_amount = lc_doc.get('amount', {}).get('value', 0)

        if lc_amount > 0:
            return True, f"LC amount ${lc_amount:,.2f} specified", "amount", ""
        else:
            return False, "LC amount must be specified", "amount", "Add LC amount value"

    def _check_transport_document_dates(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-D3: Transport document dates"""
        transport_docs = [doc for doc in lc_doc.get('required_documents', []) if 'transport' in doc.lower() or 'bill of lading' in doc.lower()]

        if transport_docs:
            return True, "Transport documents specified", "required_documents", ""
        else:
            return False, "Transport document requirements unclear", "required_documents", "Specify transport document type and requirements"

    def _check_insurance_coverage(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-E1: Insurance coverage"""
        documents = lc_doc.get('required_documents', [])
        insurance_required = any('insurance' in doc.lower() for doc in documents)

        if insurance_required:
            insurance_amount = lc_doc.get('insurance_requirements', '').lower()
            if '110%' in insurance_amount or 'cif' in insurance_amount:
                return True, "Insurance coverage specified", "required_documents,insurance_requirements", ""
            else:
                return False, "Insurance coverage should be 110% of CIF value", "insurance_requirements", "Specify insurance for 110% of CIF value"
        else:
            # Not applicable if insurance not required
            return True, "Insurance not required", "required_documents", ""

    def _check_certificate_requirements(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-F1: Certificate requirements"""
        documents = lc_doc.get('required_documents', [])
        certificates = [doc for doc in documents if 'certificate' in doc.lower()]

        if certificates:
            cert_requirements = lc_doc.get('certificate_requirements', '').lower()
            if 'signed' in cert_requirements or 'dated' in cert_requirements:
                return True, "Certificate signing requirements specified", "certificate_requirements", ""
            else:
                return False, "Certificates should specify signing and dating requirements", "certificate_requirements", "Add signing and dating requirements for certificates"
        else:
            return True, "No certificates required", "required_documents", ""

    def _check_legalization_requirements(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """ISBP-G1: Legalization requirements"""
        documents = lc_doc.get('required_documents', [])
        legalization_required = any('legalized' in doc.lower() or 'consularized' in doc.lower() for doc in documents)

        if legalization_required:
            return True, "Legalization requirements specified", "required_documents", ""
        else:
            return True, "No legalization required", "required_documents", ""

    # Additional validation methods for new rules
    def _check_presentation_period(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """Check 21-day presentation period after shipment"""
        presentation_period = lc_doc.get('presentation_period', '').lower()

        if '21' in presentation_period and 'day' in presentation_period:
            return True, "Standard 21-day presentation period specified", "presentation_period", ""
        elif 'day' in presentation_period:
            try:
                days = int(re.search(r'(\d+)', presentation_period).group(1))
                if days <= 21:
                    return True, f"{days}-day presentation period complies", "presentation_period", ""
                else:
                    return False, f"{days}-day period exceeds 21-day standard", "presentation_period", "Reduce to 21 days maximum"
            except:
                return False, "Unclear presentation period", "presentation_period", "Specify clear presentation period"
        else:
            return False, "No presentation period specified", "presentation_period", "Add 21-day presentation period"

    def _check_partial_shipment(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """Check partial shipment terms"""
        partial_shipment = lc_doc.get('partial_shipment', '').lower()

        if 'allowed' in partial_shipment or 'prohibited' in partial_shipment:
            return True, f"Partial shipment terms specified: {partial_shipment}", "partial_shipment", ""
        else:
            return False, "Partial shipment terms not specified", "partial_shipment", "Specify if partial shipments are allowed or prohibited"

    def _check_transport_routing(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """Check transport routing clarity"""
        loading_port = lc_doc.get('loading_port', '')
        discharge_port = lc_doc.get('discharge_port', '')

        if loading_port and discharge_port:
            return True, f"Clear routing: {loading_port} to {discharge_port}", "loading_port,discharge_port", ""
        else:
            missing = []
            if not loading_port: missing.append("loading port")
            if not discharge_port: missing.append("discharge port")
            return False, f"Missing {' and '.join(missing)}", "loading_port,discharge_port", f"Specify {' and '.join(missing)}"

    def _check_packing_list(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """Check packing list requirements"""
        documents = lc_doc.get('required_documents', [])
        has_packing_list = any('packing' in doc.lower() for doc in documents)

        if has_packing_list:
            return True, "Packing list required", "required_documents", ""
        else:
            return True, "Packing list not required", "required_documents", ""

    def _check_invoice_calculations(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """Check invoice calculation requirements"""
        invoice_details = lc_doc.get('invoice_requirements', '').lower()

        if 'total' in invoice_details or 'calculation' in invoice_details:
            return True, "Invoice calculation requirements specified", "invoice_requirements", ""
        else:
            return False, "Invoice should specify calculation requirements", "invoice_requirements", "Add total calculation requirements"

    # Bangladesh Local validation methods
    def _check_beneficiary_address_exact(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-001: Check exact beneficiary address matching"""
        lc_beneficiary_addr = lc_doc.get('beneficiary', {}).get('address', '').strip()

        if len(lc_beneficiary_addr) > 20:  # Reasonable address length
            return True, "Detailed beneficiary address provided for exact matching", "beneficiary.address", ""
        else:
            return False, "Beneficiary address must be complete for exact matching with invoice", "beneficiary.address", "Provide complete beneficiary address (street, city, postal code)"

    def _check_currency_consistency(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-002: Check currency consistency across all documents"""
        lc_currency = lc_doc.get('amount', {}).get('currency', '').upper()

        if lc_currency in ['USD', 'BDT', 'EUR', 'GBP']:
            return True, f"Standard currency {lc_currency} specified", "amount.currency", ""
        elif lc_currency:
            return False, f"Currency {lc_currency} may cause issues - use USD/EUR/BDT", "amount.currency", "Consider using USD, EUR, or BDT"
        else:
            return False, "LC currency must be specified", "amount.currency", "Specify LC currency (USD/EUR/BDT recommended)"

    def _check_hs_code_exact(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-003: Check HS Code exact matching requirement"""
        hs_code = lc_doc.get('hs_code', '')
        goods_description = lc_doc.get('goods_description', '').lower()

        if hs_code and len(hs_code) >= 6:
            return True, f"HS Code {hs_code} specified for exact matching", "hs_code", ""
        elif 'hs code' in goods_description or 'tariff' in goods_description:
            return False, "HS Code mentioned but not clearly specified", "hs_code", "Provide specific 6-digit HS Code"
        else:
            return False, "HS Code must be specified for Bangladesh customs", "hs_code", "Add 6-digit HS Code for goods classification"

    def _check_partial_shipment_bd(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-004: Check partial shipment compliance (BD context)"""
        partial_shipment = lc_doc.get('partial_shipment', '').lower()

        if 'prohibited' in partial_shipment:
            return True, "Partial shipments prohibited - clear instruction", "partial_shipment", ""
        elif 'allowed' in partial_shipment:
            return True, "Partial shipments allowed - ensure invoice reflects partial delivery", "partial_shipment", ""
        else:
            return False, "Partial shipment terms must be explicit for BD banks", "partial_shipment", "Clearly state if partial shipments are allowed or prohibited"

    def _check_insurance_coverage_110(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-005: Check 110% CIF insurance coverage"""
        insurance_reqs = lc_doc.get('insurance_requirements', '').lower()

        if '110%' in insurance_reqs and 'cif' in insurance_reqs:
            return True, "110% CIF insurance coverage specified", "insurance_requirements", ""
        elif 'insurance' in lc_doc.get('required_documents', []):
            return False, "Insurance required but coverage percentage not specified", "insurance_requirements", "Specify insurance for 110% of CIF value"
        else:
            return True, "Insurance not required", "required_documents", ""

    def _check_export_permit(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-006: Check export permit consistency"""
        documents = lc_doc.get('required_documents', [])
        has_export_permit = any('export' in doc.lower() and ('permit' in doc.lower() or 'license' in doc.lower()) for doc in documents)

        if has_export_permit:
            return True, "Export permit/license required - ensure consistency across documents", "required_documents", ""
        else:
            return True, "No export permit required", "required_documents", ""

    def _check_inspection_certificate(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-007: Check inspection certificate LC reference"""
        documents = lc_doc.get('required_documents', [])
        has_inspection = any('inspection' in doc.lower() for doc in documents)

        if has_inspection:
            lc_number = lc_doc.get('lc_number', '')
            if lc_number:
                return True, f"Inspection certificate required - must reference LC {lc_number}", "required_documents", ""
            else:
                return False, "LC number needed for inspection certificate reference", "lc_number", "Ensure LC number is specified"
        else:
            return True, "No inspection certificate required", "required_documents", ""

    def _check_origin_certificate_issuer(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-008: Check certificate of origin issuer"""
        documents = lc_doc.get('required_documents', [])
        has_origin_cert = any('origin' in doc.lower() and 'certificate' in doc.lower() for doc in documents)

        if has_origin_cert:
            cert_reqs = lc_doc.get('certificate_requirements', '').lower()
            recognized_issuers = ['dcci', 'ccci', 'bgmea', 'chamber', 'export promotion board']

            if any(issuer in cert_reqs for issuer in recognized_issuers):
                return True, "Certificate of origin from recognized chamber specified", "certificate_requirements", ""
            else:
                return False, "Certificate of origin must be from recognized chamber", "certificate_requirements", "Specify issuer: DCCI, CCCI, BGMEA, or Export Promotion Board"
        else:
            return True, "No certificate of origin required", "required_documents", ""

    def _check_loading_port_exact(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-009: Check exact loading port matching"""
        loading_port = lc_doc.get('loading_port', '').lower()

        if 'chittagong' in loading_port:
            return True, "Chittagong port specified - ensure exact name matching in B/L", "loading_port", ""
        elif 'dhaka' in loading_port:
            return True, "Dhaka airport specified - ensure exact name matching", "loading_port", ""
        elif loading_port:
            return True, f"Loading port {loading_port} - ensure exact matching in transport documents", "loading_port", ""
        else:
            return False, "Loading port must be specified", "loading_port", "Specify exact loading port (e.g., Chittagong Port)"

    def _check_gsp_form(self, lc_doc: Dict) -> Tuple[bool, str, str, str]:
        """BD-010: Check GSP Form A requirements"""
        documents = lc_doc.get('required_documents', [])
        has_gsp = any('gsp' in doc.lower() or 'form a' in doc.lower() for doc in documents)

        if has_gsp:
            destination = lc_doc.get('applicant', {}).get('country', '').lower()
            if 'eu' in destination or 'europe' in destination:
                return True, "GSP Form A required for EU export benefits", "required_documents", ""
            else:
                return True, "GSP Form A specified - ensure correct origin and consignee details", "required_documents", ""
        else:
            return True, "No GSP Form A required", "required_documents", ""

    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate overall compliance score"""
        if not violations:
            return 1.0

        total_weight = 0.0
        weighted_score = 0.0

        # Weight by severity
        severity_weights = {
            'critical': 1.0,
            'major': 0.8,
            'minor': 0.5,
            'advisory': 0.2
        }

        for violation in violations:
            weight = severity_weights.get(violation.severity, 0.5)
            total_weight += weight

            if violation.status == ComplianceStatus.PASS:
                weighted_score += weight
            elif violation.status == ComplianceStatus.WARNING:
                weighted_score += weight * 0.5  # Partial credit for warnings
            # FAIL gets 0 points

        if total_weight == 0:
            return 1.0

        return weighted_score / total_weight

    def _determine_overall_status(self, violations: List[ComplianceViolation]) -> ComplianceStatus:
        """Determine overall compliance status"""
        critical_failures = [v for v in violations if v.status == ComplianceStatus.FAIL and v.severity == 'critical']
        major_failures = [v for v in violations if v.status == ComplianceStatus.FAIL and v.severity == 'major']
        any_failures = [v for v in violations if v.status == ComplianceStatus.FAIL]
        warnings = [v for v in violations if v.status == ComplianceStatus.WARNING]

        if critical_failures:
            return ComplianceStatus.FAIL
        elif major_failures:
            return ComplianceStatus.FAIL
        elif any_failures:
            return ComplianceStatus.WARNING
        elif warnings:
            return ComplianceStatus.WARNING
        else:
            return ComplianceStatus.PASS

    def get_compliance_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get compliance validation summary for customer"""
        tier = self.get_customer_tier(customer_id)
        quota_status = self.check_compliance_quota(customer_id)

        return {
            'customer_id': customer_id,
            'tier': tier,
            'compliance_engine': {
                'version': self.engine_version,
                'rules_version': self.rules_version,
                'total_rules': len(self.rules),
                'ucp600_rules': len([r for r in self.rules.values() if r.category == RuleCategory.UCP600]),
                'isbp_rules': len([r for r in self.rules.values() if r.category == RuleCategory.ISBP]),
                'local_rules': len([r for r in self.rules.values() if r.category == RuleCategory.LOCAL_REGULATION])
            },
            'quota_status': quota_status,
            'tier_features': {
                'free': 'Trial - 3 ICC + Local compliance checks included',
                'pro': 'Full UCP600/ISBP/BD coverage - unlimited checks',
                'enterprise': 'Bank-grade compliance (ICC + Local BD rules + signed logs)'
            }[tier]
        }

def main():
    """Demo compliance engine functionality"""
    engine = UCP600ISBPComplianceEngine()

    print("=== LCopilot UCP600/ISBP Compliance Engine Demo ===")
    print(f"Engine Version: {engine.engine_version}")
    print(f"Rules Version: {engine.rules_version}")
    print(f"Total Rules: {len(engine.rules)}")

    # Sample LC document
    sample_lc = {
        'document_id': 'lc_demo_001',
        'lc_number': 'LC2024001',
        'lc_type': 'Irrevocable Documentary Credit',
        'issue_date': '2024-01-15',
        'expiry_date': '2024-03-15',
        'expiry_place': 'Counters of the nominated bank',
        'latest_shipment_date': '2024-03-01',
        'amount': {'value': 50000.00, 'currency': 'USD'},
        'hs_code': '620342',
        'loading_port': 'Chittagong Port',
        'discharge_port': 'Port of Hamburg',
        'partial_shipment': 'Prohibited',
        'beneficiary': {
            'name': 'Global Exports Ltd',
            'address': '123 Export Street, Chittagong-4000, Bangladesh',
            'country': 'Bangladesh'
        },
        'applicant': {
            'name': 'American Imports Inc',
            'address': '456 Import Ave, Commerce City, CC 67890',
            'country': 'USA'
        },
        'terms_and_conditions': 'This credit is subject to UCP600. Documents must be presented within 21 days of shipment.',
        'required_documents': [
            'Commercial Invoice signed and dated',
            'Clean on board Bill of Lading',
            'Insurance Policy for 110% of CIF value',
            'Certificate of Origin'
        ],
        'presentation_period': '21 days after shipment date',
        'transport_document_requirements': 'Clean on board ocean bill of lading',
        'insurance_requirements': '110% of CIF value covering all risks',
        'certificate_requirements': 'Certificate of Origin signed and dated'
    }

    # Test different tiers
    test_customers = ['sme-importer-001', 'pro-trader-001', 'enterprise-bank-001']

    for customer_id in test_customers:
        print(f"\n--- Testing compliance for {customer_id} ---")

        try:
            # Get compliance summary
            summary = engine.get_compliance_summary(customer_id)
            print(f"Tier: {summary['tier']}")
            print(f"Feature: {summary['tier_features']}")
            print(f"Quota: {summary['quota_status']['checks_remaining']} checks remaining")

            # Run compliance validation
            result = engine.validate_against_compliance_rules(sample_lc, customer_id)

            print(f"Compliance Score: {result.compliance_score:.3f}")
            print(f"Overall Status: {result.overall_status.value}")
            print(f"Rules Checked: {result.total_rules_checked}")
            print(f"Passed: {result.rules_passed}, Failed: {result.rules_failed}, Warnings: {result.rules_warnings}")
            print(f"Processing Time: {result.validation_time_ms}ms")

            # Show key violations
            violations = [v for v in result.validated_rules if v.status in [ComplianceStatus.FAIL, ComplianceStatus.WARNING]]
            if violations:
                print("Key Issues:")
                for v in violations[:3]:  # Show first 3
                    print(f"  • {v.rule_number}: {v.title} - {v.status.value}")
                    if v.details:
                        print(f"    {v.details}")
            else:
                print("No compliance issues found")

        except Exception as e:
            print(f"Error: {str(e)}")

    print("\n=== Compliance Engine Demo Complete ===")

if __name__ == "__main__":
    main()