"""
Bank-Specific Rules Layer

Different banks have different interpretations of UCP600/ISBP745.
This module provides bank-specific profiles that adjust validation strictness.

Supported Banks:
- ICBC (Industrial and Commercial Bank of China) - Strict
- HSBC - Standard with some leniency
- Standard Chartered - Moderate
- Citi - Standard
- Deutsche Bank - Strict on dates
- Default - Lenient (UCP600 minimum)

Usage:
    profile = get_bank_profile("ICBC")
    if profile.strict_port_spelling:
        # Use exact port matching
    else:
        # Use UN/LOCODE canonical matching
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum


class BankStrictness(str, Enum):
    """Bank strictness levels."""
    LENIENT = "lenient"      # Accept most variations
    STANDARD = "standard"    # UCP600/ISBP745 standard interpretation
    STRICT = "strict"        # Strict interpretation, minimal tolerance


@dataclass
class PortMatchingRules:
    """Rules for port name matching."""
    strict_spelling: bool = False           # Require exact spelling
    accept_unlisted_ports: bool = True      # Accept ports not in UN/LOCODE
    require_country: bool = False           # Require country name with port
    accept_city_only: bool = True           # Accept "NEW YORK" without "PORT OF"


@dataclass
class DateHandlingRules:
    """Rules for date validation."""
    strict_format: bool = False             # Require specific date format
    accepted_formats: List[str] = field(default_factory=lambda: [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y%m%d"
    ])
    allow_partial_dates: bool = True        # Accept "SEPTEMBER 2026" as any day
    earliest_backdating_days: int = 3       # Allow documents dated up to N days before


@dataclass
class AmountRules:
    """Rules for amount validation."""
    default_tolerance_pct: float = 5.0      # Default if not specified in LC
    apply_tolerance_to_increase: bool = True  # Apply tolerance to amount increases
    apply_tolerance_to_decrease: bool = True  # Apply tolerance to amount decreases
    strict_currency_matching: bool = True    # Require exact currency code


@dataclass  
class DocumentRules:
    """Rules for document validation."""
    accept_combined_documents: bool = True   # Accept invoice + packing list combined
    accept_copies_as_originals: bool = False # Accept copies marked as originals
    strict_signature_requirement: bool = False  # Require handwritten signatures
    accept_digital_signatures: bool = True   # Accept digital/electronic signatures
    strict_issuer_matching: bool = False     # Require exact issuer name match


@dataclass
class PartyNameRules:
    """Rules for party name matching."""
    strict_matching: bool = False           # Require exact name match
    accept_abbreviations: bool = True       # Accept "Ltd" = "Limited"
    accept_ampersand_variation: bool = True # Accept "&" = "and"
    minimum_similarity: float = 0.7         # Minimum fuzzy match score


@dataclass
class BankProfile:
    """Complete bank validation profile."""
    bank_code: str
    bank_name: str
    strictness: BankStrictness
    
    # Component rules
    port_rules: PortMatchingRules = field(default_factory=PortMatchingRules)
    date_rules: DateHandlingRules = field(default_factory=DateHandlingRules)
    amount_rules: AmountRules = field(default_factory=AmountRules)
    document_rules: DocumentRules = field(default_factory=DocumentRules)
    party_rules: PartyNameRules = field(default_factory=PartyNameRules)
    
    # Bank-specific quirks
    special_requirements: List[str] = field(default_factory=list)
    blocked_conditions: List[str] = field(default_factory=list)  # Auto-reject conditions
    
    # Metadata
    country: str = ""
    region: str = ""  # APAC, EMEA, Americas
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_code": self.bank_code,
            "bank_name": self.bank_name,
            "strictness": self.strictness.value,
            "port_rules": {
                "strict_spelling": self.port_rules.strict_spelling,
                "accept_unlisted_ports": self.port_rules.accept_unlisted_ports,
            },
            "date_rules": {
                "strict_format": self.date_rules.strict_format,
                "allow_partial_dates": self.date_rules.allow_partial_dates,
            },
            "amount_rules": {
                "default_tolerance_pct": self.amount_rules.default_tolerance_pct,
            },
            "party_rules": {
                "strict_matching": self.party_rules.strict_matching,
                "minimum_similarity": self.party_rules.minimum_similarity,
            },
            "special_requirements": self.special_requirements,
        }


# =============================================================================
# PREDEFINED BANK PROFILES
# =============================================================================

# Default lenient profile
DEFAULT_PROFILE = BankProfile(
    bank_code="DEFAULT",
    bank_name="Default (UCP600 Standard)",
    strictness=BankStrictness.LENIENT,
    port_rules=PortMatchingRules(
        strict_spelling=False,
        accept_unlisted_ports=True,
    ),
    date_rules=DateHandlingRules(
        strict_format=False,
        allow_partial_dates=True,
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,
        minimum_similarity=0.7,
    ),
)

# ICBC - Known for strictness
ICBC_PROFILE = BankProfile(
    bank_code="ICBC",
    bank_name="Industrial and Commercial Bank of China",
    strictness=BankStrictness.STRICT,
    port_rules=PortMatchingRules(
        strict_spelling=False,  # Uses UN/LOCODE canonicalization
        accept_unlisted_ports=False,
        require_country=True,
    ),
    date_rules=DateHandlingRules(
        strict_format=True,
        accepted_formats=["%Y%m%d", "%Y-%m-%d"],  # SWIFT format preferred
        allow_partial_dates=False,
        earliest_backdating_days=0,  # No backdating
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
        apply_tolerance_to_increase=True,
        apply_tolerance_to_decrease=True,
        strict_currency_matching=True,
    ),
    document_rules=DocumentRules(
        accept_combined_documents=False,
        accept_copies_as_originals=False,
        strict_signature_requirement=True,
        accept_digital_signatures=True,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,  # Still allows normalized matching
        accept_abbreviations=True,
        minimum_similarity=0.85,  # Higher threshold
    ),
    special_requirements=[
        "Chinese language translation may be required",
        "Dual dating on B/L not accepted",
    ],
    country="China",
    region="APAC",
)

# HSBC - Generally reasonable
HSBC_PROFILE = BankProfile(
    bank_code="HSBC",
    bank_name="HSBC Holdings",
    strictness=BankStrictness.STANDARD,
    port_rules=PortMatchingRules(
        strict_spelling=False,
        accept_unlisted_ports=True,
    ),
    date_rules=DateHandlingRules(
        strict_format=False,
        allow_partial_dates=True,
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,
        minimum_similarity=0.75,
    ),
    special_requirements=[
        "Electronic B/L via Bolero accepted",
    ],
    country="UK",
    region="EMEA",
)

# Standard Chartered - Moderate
STANDARD_CHARTERED_PROFILE = BankProfile(
    bank_code="SCB",
    bank_name="Standard Chartered Bank",
    strictness=BankStrictness.STANDARD,
    port_rules=PortMatchingRules(
        strict_spelling=False,
        accept_unlisted_ports=True,
    ),
    date_rules=DateHandlingRules(
        strict_format=False,
        allow_partial_dates=True,
        earliest_backdating_days=2,
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,
        minimum_similarity=0.7,
    ),
    country="UK",
    region="APAC",
)

# Citi - Standard
CITI_PROFILE = BankProfile(
    bank_code="CITI",
    bank_name="Citibank",
    strictness=BankStrictness.STANDARD,
    port_rules=PortMatchingRules(
        strict_spelling=False,
        accept_unlisted_ports=True,
    ),
    date_rules=DateHandlingRules(
        strict_format=False,
        allow_partial_dates=True,
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,
        minimum_similarity=0.7,
    ),
    country="USA",
    region="Americas",
)

# Deutsche Bank - Strict on dates and formatting
DEUTSCHE_BANK_PROFILE = BankProfile(
    bank_code="DB",
    bank_name="Deutsche Bank",
    strictness=BankStrictness.STRICT,
    port_rules=PortMatchingRules(
        strict_spelling=False,
        accept_unlisted_ports=False,
    ),
    date_rules=DateHandlingRules(
        strict_format=True,
        accepted_formats=["%Y-%m-%d", "%d.%m.%Y"],  # German format also accepted
        allow_partial_dates=False,
    ),
    amount_rules=AmountRules(
        default_tolerance_pct=5.0,
        strict_currency_matching=True,
    ),
    party_rules=PartyNameRules(
        strict_matching=False,
        minimum_similarity=0.8,
    ),
    country="Germany",
    region="EMEA",
)

# Bank profiles registry
BANK_PROFILES: Dict[str, BankProfile] = {
    "DEFAULT": DEFAULT_PROFILE,
    "ICBC": ICBC_PROFILE,
    "ICBCUS": ICBC_PROFILE,  # ICBC US branch
    "ICBCCN": ICBC_PROFILE,  # ICBC China
    "HSBC": HSBC_PROFILE,
    "HSBCHK": HSBC_PROFILE,  # HSBC Hong Kong
    "SCB": STANDARD_CHARTERED_PROFILE,
    "SCBL": STANDARD_CHARTERED_PROFILE,
    "CITI": CITI_PROFILE,
    "CITIBANK": CITI_PROFILE,
    "DB": DEUTSCHE_BANK_PROFILE,
    "DEUTSCHE": DEUTSCHE_BANK_PROFILE,
}


def get_bank_profile(bank_code: Optional[str] = None) -> BankProfile:
    """
    Get bank profile by code.
    
    Args:
        bank_code: Bank identifier (e.g., "ICBC", "HSBC")
        
    Returns:
        BankProfile for the bank, or DEFAULT if not found
    """
    if not bank_code:
        return DEFAULT_PROFILE
    
    # Normalize code
    code_upper = bank_code.upper().strip()
    
    # Direct match
    if code_upper in BANK_PROFILES:
        return BANK_PROFILES[code_upper]
    
    # Partial match (e.g., "ICBCUS33XXX" matches "ICBC")
    for profile_code, profile in BANK_PROFILES.items():
        if profile_code in code_upper or code_upper.startswith(profile_code):
            return profile
    
    # SWIFT BIC lookup (first 4 chars)
    bic_prefix = code_upper[:4] if len(code_upper) >= 4 else code_upper
    for profile_code, profile in BANK_PROFILES.items():
        if profile_code.startswith(bic_prefix):
            return profile
    
    return DEFAULT_PROFILE


def detect_bank_from_lc(lc_data: Dict[str, Any]) -> BankProfile:
    """
    Detect bank profile from LC data.
    
    Looks for bank identifiers in:
    - issuing_bank field
    - advising_bank field
    - SWIFT codes in LC text
    """
    # Try issuing bank first
    issuing_bank = lc_data.get("issuing_bank", "")
    if issuing_bank:
        profile = get_bank_profile(issuing_bank)
        if profile.bank_code != "DEFAULT":
            return profile
    
    # Try advising bank
    advising_bank = lc_data.get("advising_bank", "")
    if advising_bank:
        profile = get_bank_profile(advising_bank)
        if profile.bank_code != "DEFAULT":
            return profile
    
    # Look for SWIFT codes in raw text
    raw_text = lc_data.get("raw_text", "")
    for bank_code in BANK_PROFILES.keys():
        if bank_code in raw_text.upper():
            return BANK_PROFILES[bank_code]
    
    return DEFAULT_PROFILE


def apply_bank_strictness(
    base_threshold: float,
    profile: BankProfile,
    check_type: str,
) -> float:
    """
    Adjust threshold based on bank strictness.
    
    Args:
        base_threshold: Base threshold value (0-1)
        profile: Bank profile
        check_type: Type of check ("amount", "party", "port", "date")
        
    Returns:
        Adjusted threshold
    """
    multipliers = {
        BankStrictness.LENIENT: 0.9,    # Lower thresholds (more permissive)
        BankStrictness.STANDARD: 1.0,   # No change
        BankStrictness.STRICT: 1.15,    # Higher thresholds (more strict)
    }
    
    multiplier = multipliers.get(profile.strictness, 1.0)
    
    # Apply check-type specific adjustments
    if check_type == "party":
        return min(1.0, profile.party_rules.minimum_similarity)
    elif check_type == "amount":
        # For amounts, return tolerance percentage (inverted logic)
        return profile.amount_rules.default_tolerance_pct
    
    return min(1.0, base_threshold * multiplier)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BankProfile",
    "BankStrictness",
    "PortMatchingRules",
    "DateHandlingRules",
    "AmountRules",
    "DocumentRules",
    "PartyNameRules",
    "get_bank_profile",
    "detect_bank_from_lc",
    "apply_bank_strictness",
    "BANK_PROFILES",
    "DEFAULT_PROFILE",
]

