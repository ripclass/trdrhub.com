#!/usr/bin/env python3
"""
Bank Profile Engine for LCopilot Trust Platform
Integrates bank enforcement profiles with the validation pipeline.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

@dataclass
class BankProfile:
    """Represents a bank enforcement profile"""
    bank_code: str
    name: str
    swift_code: str
    category: str
    enforcement_level: str
    patterns: List[str]
    market_share: str
    description: str

@dataclass
class EnforcementPattern:
    """Represents an enforcement pattern with rule overrides"""
    name: str
    description: str
    rule_overrides: Dict[str, Any]

@dataclass
class EnforcementLevel:
    """Represents enforcement level configuration"""
    name: str
    description: str
    base_compliance_threshold: float
    discrepancy_multiplier: float
    rejection_rate_typical: str

class BankProfileEngine:
    """
    Engine for loading and applying bank enforcement profiles to validation results.
    Integrates with the existing compliance validation pipeline.
    """

    def __init__(self, profiles_path: str = None):
        """Initialize the bank profile engine"""
        if profiles_path is None:
            profiles_path = Path(__file__).parent.parent / "profiles" / "bank_profiles.yaml"

        self.profiles_path = Path(profiles_path)
        self.profiles = {}
        self.patterns = {}
        self.enforcement_levels = {}
        self.category_characteristics = {}
        self.metadata = {}

        self.logger = logging.getLogger(__name__)
        self._load_profiles()

    def _load_profiles(self):
        """Load bank profiles from YAML file"""
        try:
            if not self.profiles_path.exists():
                self.logger.warning(f"Bank profiles file not found: {self.profiles_path}")
                return

            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Load metadata
            self.metadata = data.get('metadata', {})

            # Load enforcement patterns
            raw_patterns = data.get('enforcement_patterns', {})
            for pattern_name, pattern_data in raw_patterns.items():
                self.patterns[pattern_name] = EnforcementPattern(
                    name=pattern_name,
                    description=pattern_data.get('description', ''),
                    rule_overrides=pattern_data.get('rule_overrides', {})
                )

            # Load enforcement levels
            raw_levels = data.get('enforcement_levels', {})
            for level_name, level_data in raw_levels.items():
                self.enforcement_levels[level_name] = EnforcementLevel(
                    name=level_name,
                    description=level_data.get('description', ''),
                    base_compliance_threshold=level_data.get('base_compliance_threshold', 0.75),
                    discrepancy_multiplier=level_data.get('discrepancy_multiplier', 1.0),
                    rejection_rate_typical=level_data.get('rejection_rate_typical', 'Unknown')
                )

            # Load category characteristics
            self.category_characteristics = data.get('category_characteristics', {})

            # Load bank profiles
            raw_banks = data.get('banks', {})
            for bank_code, bank_data in raw_banks.items():
                self.profiles[bank_code] = BankProfile(
                    bank_code=bank_code,
                    name=bank_data.get('name', ''),
                    swift_code=bank_data.get('swift_code', ''),
                    category=bank_data.get('category', ''),
                    enforcement_level=bank_data.get('enforcement_level', ''),
                    patterns=bank_data.get('patterns', []),
                    market_share=bank_data.get('market_share', ''),
                    description=bank_data.get('description', '')
                )

            self.logger.info(f"Loaded {len(self.profiles)} bank profiles, {len(self.patterns)} patterns, {len(self.enforcement_levels)} enforcement levels")

        except Exception as e:
            self.logger.error(f"Failed to load bank profiles: {str(e)}")
            self.profiles = {}

    def get_bank_profile(self, bank_code: str) -> Optional[BankProfile]:
        """Get bank profile by bank code"""
        return self.profiles.get(bank_code.upper())

    def get_banks_by_category(self, category: str) -> List[BankProfile]:
        """Get all banks in a specific category"""
        return [profile for profile in self.profiles.values() if profile.category == category]

    def get_all_categories(self) -> List[str]:
        """Get all available bank categories"""
        return list(set(profile.category for profile in self.profiles.values()))

    def get_banks_for_dropdown(self) -> Dict[str, List[Dict[str, str]]]:
        """Get banks organized by category for UI dropdown"""
        categories = {
            'state_owned': {'label': 'State-Owned Banks', 'banks': []},
            'private': {'label': 'Private Commercial Banks', 'banks': []},
            'islamic': {'label': 'Islamic Shariah Banks', 'banks': []},
            'foreign': {'label': 'Foreign Banks', 'banks': []}
        }

        for profile in self.profiles.values():
            if profile.category in categories:
                categories[profile.category]['banks'].append({
                    'code': profile.bank_code,
                    'name': profile.name,
                    'enforcement_level': profile.enforcement_level.replace('_', ' ').title(),
                    'description': profile.description
                })

        # Sort banks within each category by name
        for category in categories.values():
            category['banks'].sort(key=lambda x: x['name'])

        return categories

    def apply_bank_profile(self, validation_result: Dict[str, Any], bank_code: str) -> Dict[str, Any]:
        """
        Apply bank-specific enforcement profile to validation results.
        Modifies compliance scores and rule interpretations based on bank profile.
        """
        profile = self.get_bank_profile(bank_code)
        if not profile:
            self.logger.warning(f"Bank profile not found for {bank_code}")
            return validation_result

        # Get enforcement level configuration
        enforcement_config = self.enforcement_levels.get(profile.enforcement_level)
        if not enforcement_config:
            self.logger.warning(f"Enforcement level not found: {profile.enforcement_level}")
            return validation_result

        # Create enhanced result with bank profile data
        enhanced_result = validation_result.copy()

        # Add bank profile information
        enhanced_result['bank_profile'] = {
            'bank_code': profile.bank_code,
            'bank_name': profile.name,
            'swift_code': profile.swift_code,
            'category': profile.category,
            'enforcement_level': profile.enforcement_level,
            'market_share': profile.market_share,
            'description': profile.description,
            'enforcement_config': {
                'description': enforcement_config.description,
                'base_compliance_threshold': enforcement_config.base_compliance_threshold,
                'discrepancy_multiplier': enforcement_config.discrepancy_multiplier,
                'rejection_rate_typical': enforcement_config.rejection_rate_typical
            }
        }

        # Apply enforcement level adjustments
        original_score = enhanced_result.get('compliance_score', 0.0)

        # Adjust compliance score based on enforcement level
        if enforcement_config.discrepancy_multiplier != 1.0:
            # More strict enforcement reduces effective compliance
            adjusted_score = self._apply_enforcement_adjustment(
                original_score,
                enforcement_config.discrepancy_multiplier,
                enforcement_config.base_compliance_threshold
            )
            enhanced_result['compliance_score'] = adjusted_score
            enhanced_result['original_compliance_score'] = original_score

        # Apply pattern-specific rule overrides
        enhanced_result = self._apply_pattern_overrides(enhanced_result, profile.patterns)

        # Update overall status based on adjusted score and thresholds
        enhanced_result['overall_status'] = self._determine_bank_specific_status(
            enhanced_result.get('compliance_score', 0.0),
            enforcement_config,
            enhanced_result.get('validated_rules', [])
        )

        # Add bank-specific recommendations
        enhanced_result['bank_recommendations'] = self._generate_bank_recommendations(
            profile,
            enforcement_config,
            enhanced_result
        )

        # Add processing expectations
        category_info = self.category_characteristics.get(profile.category, {})
        enhanced_result['processing_expectations'] = {
            'typical_processing_time': category_info.get('typical_processing_time', 'Unknown'),
            'documentation_requirements': category_info.get('documentation_requirements', 'Standard'),
            'flexibility_level': category_info.get('flexibility_level', 'Moderate'),
            'government_oversight': category_info.get('government_oversight', 'Standard')
        }

        return enhanced_result

    def _apply_enforcement_adjustment(self, original_score: float, multiplier: float, threshold: float) -> float:
        """Apply enforcement level adjustment to compliance score"""
        if multiplier == 1.0:
            return original_score

        # Higher multiplier means stricter enforcement (lower effective compliance)
        if multiplier > 1.0:
            # Calculate penalty based on how far below perfect compliance
            penalty = (1.0 - original_score) * (multiplier - 1.0)
            adjusted_score = max(0.0, original_score - penalty)
        else:
            # More lenient enforcement (higher effective compliance)
            bonus = (1.0 - original_score) * (1.0 - multiplier)
            adjusted_score = min(1.0, original_score + bonus)

        return round(adjusted_score, 3)

    def _apply_pattern_overrides(self, result: Dict[str, Any], pattern_names: List[str]) -> Dict[str, Any]:
        """Apply pattern-specific rule overrides to validation result"""

        # Collect all rule overrides from patterns
        all_overrides = {}
        for pattern_name in pattern_names:
            pattern = self.patterns.get(pattern_name)
            if pattern:
                all_overrides.update(pattern.rule_overrides)

        # Apply overrides to validated rules
        validated_rules = result.get('validated_rules', [])
        for rule in validated_rules:
            rule_id = rule.get('id', '').lower()

            # Check for specific overrides
            for override_key, override_value in all_overrides.items():
                if override_key.lower() in rule_id or any(keyword in rule_id for keyword in override_key.split('_')):
                    # Apply override based on value type
                    if override_value == "fail_on_minor_differences" and rule.get('status') == 'pass':
                        # Stricter enforcement - convert warnings to fails
                        if 'minor' in rule.get('details', '').lower() or 'variation' in rule.get('details', '').lower():
                            rule['status'] = 'fail'
                            rule['bank_override'] = f"Failed due to {override_key} enforcement"

                    elif override_value == "zero_tolerance" and rule.get('status') != 'fail':
                        # Zero tolerance - any issue becomes a failure
                        if rule.get('details') and len(rule.get('issues', [])) > 0:
                            rule['status'] = 'fail'
                            rule['bank_override'] = f"Failed due to zero tolerance policy"

                    elif override_value == "exact_match_required":
                        # Exact match required
                        if 'approximate' in rule.get('details', '').lower() or 'similar' in rule.get('details', '').lower():
                            rule['status'] = 'fail'
                            rule['bank_override'] = f"Exact match required by bank policy"

        return result

    def _determine_bank_specific_status(self, compliance_score: float, enforcement_config: EnforcementLevel, rules: List[Dict[str, Any]]) -> str:
        """Determine overall validation status based on bank-specific thresholds"""

        failed_rules = [rule for rule in rules if rule.get('status') == 'fail']
        failed_count = len(failed_rules)

        # Apply bank-specific thresholds
        if compliance_score < enforcement_config.base_compliance_threshold:
            return 'non_compliant'
        elif failed_count > 0:
            # Different tolerance levels based on enforcement
            if enforcement_config.name in ['hyper_conservative', 'very_strict']:
                return 'non_compliant' if failed_count > 0 else 'compliant'
            elif enforcement_config.name == 'conservative':
                return 'non_compliant' if failed_count > 1 else 'compliant'
            else:
                return 'issues_found' if failed_count > 2 else 'compliant'
        else:
            return 'compliant'

    def _generate_bank_recommendations(self, profile: BankProfile, enforcement_config: EnforcementLevel, result: Dict[str, Any]) -> List[str]:
        """Generate bank-specific recommendations"""
        recommendations = []

        # Category-specific recommendations
        if profile.category == 'state_owned':
            recommendations.extend([
                "Allow additional processing time for government compliance procedures",
                "Ensure all documentation is perfectly formatted with no variations",
                "Consider government import permits may be required"
            ])
        elif profile.category == 'private':
            recommendations.extend([
                "Leverage digital banking services for faster processing",
                "Consider relationship manager consultation for complex cases"
            ])
        elif profile.category == 'islamic':
            recommendations.extend([
                "Ensure all financial instruments comply with Shariah principles",
                "Verify insurance providers are Takaful-compliant where possible",
                "Review commodity descriptions for Shariah compatibility"
            ])
        elif profile.category == 'foreign':
            recommendations.extend([
                "Follow strict international documentation standards",
                "Ensure compliance with both local and home country regulations",
                "Consider premium services for complex international transactions"
            ])

        # Enforcement level specific recommendations
        if enforcement_config.name in ['hyper_conservative', 'very_strict']:
            recommendations.append("Triple-check all documentation for exact accuracy")
            recommendations.append("Consider legal review for high-value transactions")
        elif enforcement_config.name == 'conservative':
            recommendations.append("Review all documentation carefully before submission")
        elif enforcement_config.name == 'moderate':
            recommendations.append("Standard documentation review should be sufficient")

        # Bank-specific recommendations based on patterns
        for pattern_name in profile.patterns:
            pattern = self.patterns.get(pattern_name)
            if pattern:
                if 'currency' in pattern.name.lower():
                    recommendations.append(f"Pay special attention to currency consistency - {profile.name} strictly enforces this")
                elif 'address' in pattern.name.lower():
                    recommendations.append(f"Ensure exact beneficiary address matching - {profile.name} requires precision")
                elif 'insurance' in pattern.name.lower():
                    recommendations.append(f"Verify insurance coverage meets {profile.name}'s minimum requirements")

        # Compliance score based recommendations
        compliance_score = result.get('compliance_score', 0.0)
        if compliance_score < enforcement_config.base_compliance_threshold:
            recommendations.insert(0, f"⚠️ Below {profile.name}'s acceptance threshold - significant issues require resolution")

        return recommendations[:6]  # Limit to top 6 recommendations

    def get_profile_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded profiles"""
        if not self.profiles:
            return {"error": "No profiles loaded"}

        stats = {
            "total_banks": len(self.profiles),
            "by_category": {},
            "by_enforcement_level": {},
            "metadata": self.metadata
        }

        for profile in self.profiles.values():
            # Category stats
            if profile.category not in stats["by_category"]:
                stats["by_category"][profile.category] = 0
            stats["by_category"][profile.category] += 1

            # Enforcement level stats
            if profile.enforcement_level not in stats["by_enforcement_level"]:
                stats["by_enforcement_level"][profile.enforcement_level] = 0
            stats["by_enforcement_level"][profile.enforcement_level] += 1

        return stats

def main():
    """Demo the bank profile engine"""
    print("🏦 LCopilot Bank Profile Engine Demo")
    print("=" * 50)

    engine = BankProfileEngine()

    # Show statistics
    stats = engine.get_profile_statistics()
    print(f"\n📊 Loaded {stats['total_banks']} banks:")
    for category, count in stats['by_category'].items():
        print(f"  • {category.replace('_', ' ').title()}: {count} banks")

    print(f"\n📈 Enforcement Levels:")
    for level, count in stats['by_enforcement_level'].items():
        print(f"  • {level.replace('_', ' ').title()}: {count} banks")

    # Show sample profiles
    print(f"\n🏛️ Sample State Bank - SONALI:")
    sonali = engine.get_bank_profile('SONALI')
    if sonali:
        print(f"  • Name: {sonali.name}")
        print(f"  • Enforcement: {sonali.enforcement_level}")
        print(f"  • Market Share: {sonali.market_share}")

    print(f"\n🏢 Sample Private Bank - BRAC_BANK:")
    brac = engine.get_bank_profile('BRAC_BANK')
    if brac:
        print(f"  • Name: {brac.name}")
        print(f"  • Enforcement: {brac.enforcement_level}")
        print(f"  • Market Share: {brac.market_share}")

    # Show dropdown data
    dropdown_data = engine.get_banks_for_dropdown()
    print(f"\n📋 Dropdown Categories:")
    for category, data in dropdown_data.items():
        print(f"  • {data['label']}: {len(data['banks'])} banks")

if __name__ == "__main__":
    main()