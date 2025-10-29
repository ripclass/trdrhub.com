#!/usr/bin/env python3
"""
Bank-Mode Simulator for LCopilot SME Portal
Validates LC documents as if submitted to specific banks with their unique processing styles.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

class BankModeSimulator:
    """
    Simulates how different banks would process and validate LC documents.
    Each bank has unique rules, processing styles, and validation criteria.
    """

    def __init__(self, rules_directory: str = None):
        """Initialize bank simulator with rules directory"""
        if rules_directory is None:
            rules_directory = Path(__file__).parent.parent / "rules" / "banks"

        self.rules_dir = Path(rules_directory)
        self.loaded_banks = {}
        self._load_bank_rules()

    def _load_bank_rules(self):
        """Load all bank rule configurations"""
        if not self.rules_dir.exists():
            print(f"Warning: Bank rules directory not found: {self.rules_dir}")
            return

        for rule_file in self.rules_dir.glob("*.yaml"):
            bank_code = rule_file.stem
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    bank_config = yaml.safe_load(f)
                    self.loaded_banks[bank_code] = bank_config
                    print(f"✅ Loaded rules for {bank_config['bank_info']['name']}")
            except Exception as e:
                print(f"❌ Failed to load {rule_file}: {str(e)}")

    def get_available_banks(self) -> List[Dict[str, str]]:
        """Get list of available banks for simulation"""
        banks = []
        for bank_code, config in self.loaded_banks.items():
            banks.append({
                'code': bank_code,
                'name': config['bank_info']['name'],
                'type': config['bank_info']['type'],
                'style': config['bank_info']['regulatory_style']
            })
        return banks

    def validate_with_bank(self, lc_document: Dict[str, Any], bank_code: str) -> Dict[str, Any]:
        """
        Validate LC document using specific bank's rules and processing style.

        Args:
            lc_document: LC document to validate
            bank_code: Bank identifier (e.g., 'sonali_bank', 'dbbl', 'hsbc_bangladesh')

        Returns:
            Bank-specific validation result with styled messaging
        """
        if bank_code not in self.loaded_banks:
            return self._create_error_response(f"Bank '{bank_code}' not found")

        bank_config = self.loaded_banks[bank_code]

        try:
            # Simulate processing time based on bank efficiency
            processing_time = self._simulate_processing_time(bank_config)

            # Perform bank-specific validation
            validation_result = self._perform_bank_validation(lc_document, bank_config)

            # Apply bank-specific styling and messaging
            styled_result = self._apply_bank_styling(validation_result, bank_config)

            # Add bank-specific metadata
            styled_result.update({
                'bank_info': {
                    'name': bank_config['bank_info']['name'],
                    'code': bank_config['bank_info']['code'],
                    'processing_style': bank_config['bank_info']['regulatory_style']
                },
                'simulation_metadata': {
                    'simulated_processing_time_ms': processing_time,
                    'validation_timestamp': datetime.now().isoformat(),
                    'simulator_version': '2.1.0'
                }
            })

            return styled_result

        except Exception as e:
            return self._create_error_response(f"Validation error: {str(e)}")

    def _simulate_processing_time(self, bank_config: Dict[str, Any]) -> float:
        """Simulate realistic processing time based on bank characteristics"""
        base_time = 2000  # Base 2 seconds

        # Adjust based on bank processing approach
        approach = bank_config['bank_info'].get('processing_approach', 'standard')
        if approach == 'efficient':
            multiplier = 0.7
        elif approach == 'thorough':
            multiplier = 1.5
        elif approach == 'premium':
            multiplier = 0.8
        else:
            multiplier = 1.0

        # Add some realistic variance
        variance = random.uniform(0.8, 1.3)
        return base_time * multiplier * variance

    def _perform_bank_validation(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform validation based on bank-specific rules"""

        validation_results = []
        warnings = []
        bank_specific_notes = []

        # Currency validation
        currency_result = self._validate_currency(lc_document, bank_config)
        validation_results.append(currency_result)

        # Amount validation
        amount_result = self._validate_amount(lc_document, bank_config)
        validation_results.append(amount_result)

        # Date validation
        date_result = self._validate_dates(lc_document, bank_config)
        validation_results.append(date_result)

        # Documentation validation
        doc_result = self._validate_documentation(lc_document, bank_config)
        validation_results.append(doc_result)

        # Insurance validation
        insurance_result = self._validate_insurance(lc_document, bank_config)
        validation_results.append(insurance_result)

        # Beneficiary validation
        beneficiary_result = self._validate_beneficiary(lc_document, bank_config)
        validation_results.append(beneficiary_result)

        # Calculate overall results
        total_checks = len(validation_results)
        passed_checks = sum(1 for result in validation_results if result['status'] == 'pass')
        failed_checks = sum(1 for result in validation_results if result['status'] == 'fail')

        overall_score = passed_checks / total_checks if total_checks > 0 else 0

        # Determine overall status based on bank's risk tolerance
        risk_tolerance = bank_config['validation_profile'].get('risk_tolerance', 'moderate')
        if risk_tolerance == 'low' and failed_checks > 0:
            overall_status = 'rejected'
        elif risk_tolerance == 'moderate' and failed_checks > 2:
            overall_status = 'requires_review'
        elif risk_tolerance == 'conservative' and failed_checks > 1:
            overall_status = 'requires_review'
        else:
            overall_status = 'approved' if failed_checks == 0 else 'conditional_approval'

        return {
            'overall_status': overall_status,
            'compliance_score': round(overall_score, 3),
            'validation_results': validation_results,
            'warnings': warnings,
            'bank_specific_notes': bank_specific_notes,
            'summary': {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'failed_checks': failed_checks,
                'warnings': len(warnings)
            }
        }

    def _validate_currency(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate currency based on bank preferences"""

        amount_info = lc_document.get('amount', {})
        currency = amount_info.get('currency', 'USD') if isinstance(amount_info, dict) else 'USD'
        amount_value = amount_info.get('value', 0) if isinstance(amount_info, dict) else 0

        currency_rules = bank_config.get('specific_rules', {}).get('currency_validation', {})
        preferred_currencies = currency_rules.get('preferred_currencies', ['USD'])
        approval_threshold = currency_rules.get('requires_approval_above', 1000000)

        issues = []

        if currency not in preferred_currencies:
            issues.append(f"Currency {currency} requires special approval")

        if amount_value > approval_threshold:
            issues.append(f"Amount exceeds auto-approval limit")

        return {
            'rule_id': 'CURRENCY_VALIDATION',
            'description': 'Currency and amount validation',
            'status': 'fail' if issues else 'pass',
            'issues': issues,
            'bank_specific': True
        }

    def _validate_amount(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate amount against bank limits"""

        amount_info = lc_document.get('amount', {})
        amount_value = amount_info.get('value', 0) if isinstance(amount_info, dict) else 0

        amount_rules = bank_config.get('specific_rules', {}).get('amount_limits', {})
        single_lc_limit = amount_rules.get('single_lc_limit', 10000000)
        board_approval = amount_rules.get('requires_board_approval', 5000000)

        issues = []
        notes = []

        if amount_value > single_lc_limit:
            issues.append(f"Amount exceeds single LC limit of ${single_lc_limit:,}")
        elif amount_value > board_approval:
            notes.append(f"Amount requires board approval (above ${board_approval:,})")

        return {
            'rule_id': 'AMOUNT_LIMITS',
            'description': 'LC amount limits validation',
            'status': 'fail' if issues else 'pass',
            'issues': issues,
            'notes': notes,
            'bank_specific': True
        }

    def _validate_dates(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate dates based on bank processing requirements"""

        date_rules = bank_config.get('specific_rules', {}).get('date_validation', {})
        min_presentation = date_rules.get('minimum_presentation_period', 21)
        processing_allowance = date_rules.get('processing_time_allowance', 5)

        issues = []
        notes = []

        # Simulate date validation (in real implementation, would parse actual dates)
        if min_presentation > 15:  # Conservative bank
            notes.append(f"Bank requires minimum {min_presentation} days presentation period")

        if processing_allowance > 5:  # Slower processing bank
            notes.append(f"Allow {processing_allowance} additional days for bank processing")

        return {
            'rule_id': 'DATE_VALIDATION',
            'description': 'Date sequence and timing validation',
            'status': 'pass',
            'issues': issues,
            'notes': notes,
            'bank_specific': True
        }

    def _validate_documentation(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate documentation requirements"""

        doc_rules = bank_config.get('specific_rules', {}).get('documentation_requirements', {})
        mandatory_docs = doc_rules.get('mandatory_documents', [])

        required_docs = lc_document.get('required_documents', [])

        missing_docs = []
        for doc in mandatory_docs:
            if not any(doc.lower() in req_doc.lower() for req_doc in required_docs):
                missing_docs.append(doc)

        notes = []
        if doc_rules.get('digital_acceptance'):
            notes.append("Digital documents accepted for faster processing")

        return {
            'rule_id': 'DOCUMENTATION',
            'description': 'Required documents validation',
            'status': 'fail' if missing_docs else 'pass',
            'issues': [f"Missing required document: {doc}" for doc in missing_docs],
            'notes': notes,
            'bank_specific': True
        }

    def _validate_insurance(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate insurance requirements"""

        insurance_rules = bank_config.get('specific_rules', {}).get('insurance_requirements', {})
        min_coverage = insurance_rules.get('minimum_coverage', 110)

        # Check for insurance in document
        insurance_coverage = lc_document.get('insurance_coverage', {})

        issues = []
        notes = []

        if isinstance(insurance_coverage, dict):
            coverage_percent = insurance_coverage.get('percentage', '110%')
            try:
                coverage_value = float(coverage_percent.replace('%', ''))
                if coverage_value < min_coverage:
                    issues.append(f"Insurance coverage {coverage_value}% below required {min_coverage}%")
            except:
                pass

        preferred_insurers = insurance_rules.get('preferred_insurers', [])
        if preferred_insurers:
            notes.append(f"Bank prefers insurers: {', '.join(preferred_insurers[:2])}")

        return {
            'rule_id': 'INSURANCE',
            'description': 'Insurance coverage validation',
            'status': 'fail' if issues else 'pass',
            'issues': issues,
            'notes': notes,
            'bank_specific': True
        }

    def _validate_beneficiary(self, lc_document: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate beneficiary and sanctions screening"""

        beneficiary_rules = bank_config.get('specific_rules', {}).get('beneficiary_validation', {})
        restricted_countries = beneficiary_rules.get('restricted_countries', [])

        beneficiary = lc_document.get('beneficiary', {})
        beneficiary_country = beneficiary.get('country', '') if isinstance(beneficiary, dict) else ''

        issues = []
        notes = []

        if beneficiary_country in restricted_countries:
            issues.append(f"Beneficiary country {beneficiary_country} is restricted")

        screening_level = beneficiary_rules.get('sanctions_screening', 'standard')
        if screening_level == 'enhanced':
            notes.append("Enhanced sanctions screening required")
        elif screening_level == 'automated':
            notes.append("Automated sanctions screening completed")

        return {
            'rule_id': 'BENEFICIARY',
            'description': 'Beneficiary validation and sanctions screening',
            'status': 'fail' if issues else 'pass',
            'issues': issues,
            'notes': notes,
            'bank_specific': True
        }

    def _apply_bank_styling(self, validation_result: Dict[str, Any], bank_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply bank-specific styling and messaging"""

        message_config = bank_config.get('validation_messages', {})
        style = message_config.get('style', 'professional')

        # Add bank-specific messaging style
        validation_result['presentation_style'] = {
            'tone': style,
            'language': message_config.get('language', 'standard'),
            'emphasis': bank_config.get('report_format', {}).get('emphasis', 'compliance')
        }

        # Add bank-specific recommendations
        recommendations = self._generate_bank_recommendations(validation_result, bank_config)
        validation_result['bank_recommendations'] = recommendations

        # Add processing expectations
        processing_profile = bank_config.get('validation_profile', {})
        validation_result['processing_expectations'] = {
            'processing_time': processing_profile.get('processing_time_expectation', 'standard'),
            'documentation_level': processing_profile.get('documentation_requirements', 'standard'),
            'review_strictness': processing_profile.get('strictness_level', 'moderate')
        }

        return validation_result

    def _generate_bank_recommendations(self, validation_result: Dict[str, Any], bank_config: Dict[str, Any]) -> List[str]:
        """Generate bank-specific recommendations"""

        recommendations = []

        # Based on bank type
        bank_type = bank_config['bank_info']['type']

        if bank_type == 'state_owned':
            recommendations.append("Allow extra time for government compliance procedures")
            recommendations.append("Ensure all documentation meets regulatory standards")
        elif bank_type == 'international_commercial':
            recommendations.append("Leverage international banking network for efficiency")
            recommendations.append("Consider premium services for complex transactions")
        elif bank_type == 'private_commercial':
            recommendations.append("Utilize digital banking services for faster processing")
            recommendations.append("Explore automated compliance features")

        # Based on validation results
        if validation_result['overall_status'] in ['rejected', 'requires_review']:
            templates = bank_config.get('validation_messages', {}).get('templates', {})
            for template_key, message in templates.items():
                if any(issue for result in validation_result['validation_results']
                      for issue in result.get('issues', [])):
                    recommendations.append(message)
                    break

        return recommendations

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'error': True,
            'message': error_message,
            'overall_status': 'validation_error',
            'compliance_score': 0.0,
            'validation_results': [],
            'bank_recommendations': ['Please check input and try again'],
            'simulation_metadata': {
                'validation_timestamp': datetime.now().isoformat(),
                'simulator_version': '2.1.0'
            }
        }

def main():
    """Demo the bank simulator"""
    print("🏦 LCopilot Bank-Mode Simulator Demo")
    print("=" * 50)

    # Initialize simulator
    simulator = BankModeSimulator()

    # Show available banks
    available_banks = simulator.get_available_banks()
    print(f"\nAvailable banks for simulation:")
    for bank in available_banks:
        print(f"  • {bank['name']} ({bank['code']}) - {bank['style']} style")

    # Demo LC document
    demo_lc = {
        'lc_number': 'DEMO-LC-001',
        'amount': {'value': 150000, 'currency': 'USD'},
        'beneficiary': {'country': 'India', 'name': 'Demo Exports Ltd'},
        'required_documents': [
            'Commercial Invoice',
            'Bill of Lading',
            'Insurance Policy'
        ],
        'insurance_coverage': {'percentage': '110%'}
    }

    print(f"\n📄 Demo LC: {demo_lc['lc_number']} - ${demo_lc['amount']['value']:,} USD")

    # Test with each bank
    for bank in available_banks[:3]:  # Test first 3 banks
        print(f"\n--- {bank['name']} Simulation ---")
        result = simulator.validate_with_bank(demo_lc, bank['code'])

        print(f"Overall Status: {result['overall_status']}")
        print(f"Compliance Score: {result['compliance_score']:.1%}")
        print(f"Processing Style: {result.get('presentation_style', {}).get('tone', 'N/A')}")

        if result.get('bank_recommendations'):
            print("Bank Recommendations:")
            for rec in result['bank_recommendations'][:2]:
                print(f"  • {rec}")

if __name__ == "__main__":
    main()