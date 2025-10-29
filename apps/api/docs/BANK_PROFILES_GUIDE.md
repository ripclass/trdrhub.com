# LCopilot Bank Enforcement Profiles Guide

Complete documentation for using bank-specific enforcement profiles to validate Letter of Credit compliance with realistic banking standards.

## Overview

LCopilot Trust Platform includes comprehensive enforcement profiles for all 41+ active trade finance banks in Bangladesh. Each profile reflects the bank's real-world validation style, enforcement strictness, and processing approach.

### Why Bank Profiles Matter

Different banks enforce LC compliance rules differently based on their:
- **Ownership Structure**: State-owned vs Private vs Foreign
- **Risk Appetite**: Conservative vs Moderate vs Strict
- **Processing Style**: Manual vs Digital vs Premium
- **Regulatory Environment**: Local vs International standards

## Bank Categories & Enforcement Levels

### 🏛️ State-Owned Banks (4 banks)
**Enforcement Level**: Hyper-Conservative

These government-owned banks apply the strictest interpretation of compliance rules due to regulatory oversight and risk-averse culture.

| Bank | Code | Market Share | Characteristics |
|------|------|--------------|----------------|
| Sonali Bank Limited | `SONALI` | 14.2% | Largest state bank, extremely conservative |
| Janata Bank Limited | `JANATA` | 8.1% | Second largest, equally conservative |
| Agrani Bank Limited | `AGRANI` | 6.8% | Rigid documentation requirements |
| Rupali Bank Limited | `RUPALI` | 4.2% | Exact documentation compliance emphasis |

**Typical Features**:
- Zero tolerance for discrepancies
- Extended processing times (7-14 days)
- Government approval required for large amounts
- Exact address and currency matching
- Conservative insurance requirements (110%+ mandatory)

### 🏢 Private Commercial Banks (21 banks)
**Enforcement Level**: Moderate

Business-friendly banks that balance compliance requirements with commercial pragmatism.

| Bank | Code | Market Share | Notable Features |
|------|------|--------------|------------------|
| BRAC Bank Limited | `BRAC_BANK` | 4.8% | SME-friendly, pragmatic partial shipments |
| Dutch-Bangla Bank Limited | `DUTCH_BANGLA` | 5.2% | Tech-forward, efficient processing |
| Eastern Bank Limited | `EASTERN_BANK` | 3.1% | Standard validation practices |
| Prime Bank Limited | `PRIME_BANK` | 3.7% | Insurance compliance emphasis |
| AB Bank, Bank Asia, City Bank, Dhaka Bank, IFIC Bank, Jamuna Bank, Mercantile Bank, Mutual Trust, National Bank, NCC Bank, One Bank, Pubali Bank, Southeast Bank, Standard Bank, Trust Bank, UCB, Uttara Bank | Various | 1.4%-2.9% each | Standard moderate enforcement |

**Typical Features**:
- Balanced rule enforcement
- Digital processing capabilities
- Business-friendly policies
- Reasonable compliance thresholds
- Standard processing times (3-7 days)

### 🕌 Islamic Shariah Banks (7 banks)
**Enforcement Level**: Conservative

Banks following Islamic banking principles with additional Shariah compliance requirements.

| Bank | Code | Market Share | Specialization |
|------|------|--------------|----------------|
| Islami Bank Bangladesh Limited | `ISLAMI_BANK_BD` | 8.7% | Largest Islamic bank, comprehensive Shariah compliance |
| Shahjalal Islami Bank Limited | `SHAHJALAL_ISLAMI` | 2.4% | Conservative validation approach |
| Social Islami Bank Limited | `SOCIAL_ISLAMI` | 1.8% | Exact documentation emphasis |
| First Security Islami Bank Limited | `FSIBL` | 1.6% | Strict date compliance |
| Al-Arafah Islami Bank Limited | `AL_ARAFH_ISLAMI` | 1.9% | Currency and insurance rules |
| Union Bank Limited | `UNION_BANK` | 1.3% | Currency compliance focus |
| Global Islami Bank Limited | `GLOBAL_ISLAMI` | 1.1% | Conservative approach |

**Typical Features**:
- Shariah-compliant documentation required
- Takaful insurance preferences
- Conservative interpretation of rules
- Enhanced documentation scrutiny
- Processing time: 5-10 days

### 🌍 Foreign Banks (9 banks)
**Enforcement Level**: Very Strict

International banks applying comprehensive global standards and multi-jurisdictional compliance.

| Bank | Code | Market Share | Home Country | Standards |
|------|------|--------------|--------------|-----------|
| Standard Chartered Bank | `STANDARD_CHARTERED` | 3.2% | UK | Comprehensive UCP600 + ISBP |
| HSBC Bangladesh | `HSBC` | 2.8% | UK | International premium standards |
| Citibank N.A. | `CITI` | 1.4% | USA | Strict date compliance focus |
| State Bank of India | `SBI` | 0.9% | India | Full UCP600 enforcement |
| Commercial Bank of Ceylon | `COM_BANK_CEYLON` | 0.8% | Sri Lanka | Currency enforcement |
| Habib Bank Limited | `HABIB_BANK` | 0.7% | Pakistan | Date compliance emphasis |
| Bank Alfalah Limited | `BANK_ALFALAH` | 0.6% | Pakistan | Enhanced local requirements |
| National Bank of Pakistan | `NBP` | 0.5% | Pakistan | Insurance requirements focus |
| Woori Bank | `WOORI` | 0.3% | South Korea | UCP600 + ISBP comprehensive |

**Typical Features**:
- Full UCP600 and ISBP compliance
- Multi-jurisdictional regulatory requirements
- Premium service standards
- International documentation standards
- Fast processing (2-5 days) but very strict

## How to Use Bank Profiles

### For SMEs

#### 1. **Accessing Bank Mode Validation**

Visit the LCopilot SME Portal at `/validate` and:

1. Select your pricing tier (Free/Professional/Enterprise)
2. Choose a bank from the **"Bank Enforcement Validation"** dropdown
3. Upload your LC document or paste JSON
4. Click **"Validate LC Compliance"**

#### 2. **Understanding Results**

Each bank-specific validation provides:

- **Bank Information**: Name, category, enforcement level, market share
- **Adjusted Compliance Score**: Modified based on bank's strictness
- **Bank-Specific Recommendations**: Tailored advice for that bank
- **Processing Expectations**: Typical timeframes and requirements
- **Enforcement Profile**: Description of bank's validation approach

#### 3. **Choosing the Right Bank**

**For Conservative Approach**: Choose state-owned banks (Sonali, Janata) if you want to ensure maximum compliance that will pass anywhere.

**For Business Efficiency**: Choose private banks (BRAC, DBBL, Eastern) for balanced compliance with reasonable processing times.

**For Shariah Compliance**: Choose Islamic banks (Islami Bank BD, Shahjalal) for Shariah-compliant transactions.

**For International Standards**: Choose foreign banks (HSBC, Standard Chartered) for complex international transactions.

### For Banks

#### 1. **Requesting Profile Updates**

Banks can request updates to their enforcement profiles by:

1. **Email**: Contact support@lcopilot.com with:
   - Bank name and SWIFT code
   - Specific changes requested
   - Supporting documentation
   - Contact information for verification

2. **Documentation Required**:
   - Official bank letterhead request
   - Details of current enforcement policies
   - Examples of specific rule interpretations
   - Processing time expectations

3. **Update Process**:
   - Review by LCopilot compliance team
   - Bank verification and confirmation
   - Testing with bank representatives
   - Deployment to production systems
   - Notification to enterprise customers

#### 2. **Profile Customization Options**

Banks can customize:

- **Enforcement Strictness**: Adjust discrepancy tolerance levels
- **Processing Expectations**: Update typical processing timeframes
- **Documentation Requirements**: Specify mandatory documents
- **Currency Preferences**: Set preferred currency lists
- **Insurance Requirements**: Define minimum coverage levels
- **Recommendation Messages**: Customize bank-specific advice

## Technical Implementation

### API Integration

#### Basic Usage

```bash
curl -X POST https://api.lcopilot.com/validate \
  -H "Content-Type: application/json" \
  -d '{
    "lc_document": { ... },
    "bank_mode": "BRAC_BANK",
    "tier": "pro"
  }'
```

#### Response Format

```json
{
  "compliance_score": 0.87,
  "overall_status": "compliant",
  "bank_profile": {
    "bank_name": "BRAC Bank Limited",
    "bank_code": "BRAC_BANK",
    "enforcement_level": "moderate",
    "category": "private",
    "market_share": "4.8%",
    "description": "Major private bank known for SME-friendly approach"
  },
  "bank_recommendations": [
    "Leverage digital banking services for faster processing",
    "Consider relationship manager consultation for complex cases"
  ],
  "processing_expectations": {
    "typical_processing_time": "3-7 days",
    "documentation_requirements": "Standard",
    "flexibility_level": "Moderate"
  },
  "validated_rules": [ ... ]
}
```

### Web Portal Integration

The SME Portal automatically loads bank profiles at `/validate`:

```html
<select name="bank_mode" id="bank_mode">
  <option value="">Standard Validation</option>
  <optgroup label="State-Owned Banks">
    <option value="SONALI">Sonali Bank (Hyper Conservative)</option>
    <option value="JANATA">Janata Bank (Hyper Conservative)</option>
    ...
  </optgroup>
  <optgroup label="Private Commercial Banks">
    <option value="BRAC_BANK">BRAC Bank (Moderate)</option>
    <option value="DUTCH_BANGLA">Dutch-Bangla Bank (Moderate)</option>
    ...
  </optgroup>
  ...
</select>
```

## Enforcement Patterns

### Pattern Definitions

Each bank profile uses specific enforcement patterns:

#### `exact_beneficiary_address`
- Requires exact match of beneficiary address
- No variations or abbreviations accepted
- Used by: State-owned banks

#### `strict_currency_consistency`
- Enforces exact currency consistency across documents
- Zero tolerance for currency mismatches
- Used by: State-owned and Islamic banks

#### `balanced_rule_enforcement`
- Standard balanced approach to validation
- Reasonable tolerance for minor variations
- Used by: Private commercial banks

#### `full_ucp600` & `full_isbp`
- Comprehensive international standards compliance
- Detailed document examination requirements
- Used by: Foreign banks

#### `shariah_documents_required`
- Additional Shariah compliance validation
- Takaful insurance requirements
- Used by: Islamic banks

### Customizing Patterns

Banks can request custom patterns by:

1. Defining specific rule interpretations
2. Providing examples of acceptable variations
3. Specifying rejection criteria
4. Documenting processing procedures

## Testing & Validation

### Test Fixtures Available

LCopilot provides test fixtures for each bank category:

- **`sonali_fail.json`**: Document that fails hyper-conservative validation
- **`brac_pass.json`**: Document that passes moderate validation
- **`islami_conservative.json`**: Document tested with Shariah compliance
- **`hsbc_strict.json`**: Document tested with international standards

### Running Tests

```bash
# Run comprehensive bank profile tests
cd /path/to/lcopilot-api
python3 tests/test_bank_profiles.py

# Test specific bank validation
python3 -c "
from trust_platform.compliance.bank_profile_engine import BankProfileEngine
engine = BankProfileEngine()
print(engine.get_profile_statistics())
"
```

## Frequently Asked Questions

### For SMEs

**Q: Which bank should I test with for maximum compliance assurance?**
A: Test with state-owned banks (Sonali, Janata) first. If your LC passes their hyper-conservative validation, it will likely pass at any bank.

**Q: Why do I get different compliance scores for the same LC?**
A: Different banks have different enforcement levels. A score of 85% with HSBC (very strict) might be 92% with BRAC Bank (moderate) for the same document.

**Q: Can I test with multiple banks at once?**
A: Currently, select one bank per validation. We recommend testing with your target bank first, then with a conservative bank for assurance.

### For Banks

**Q: How accurate are the enforcement profiles?**
A: Profiles are based on publicly available information and industry knowledge. Banks can request updates to ensure accuracy.

**Q: How often are profiles updated?**
A: Profiles are reviewed quarterly and updated as needed based on bank feedback and regulatory changes.

**Q: Can we get a private/custom profile?**
A: Yes, enterprise banks can request custom profiles with specific enforcement parameters and private validation logic.

## Compliance & Legal Notes

### IP-Safe Implementation

All bank profiles are developed using LCopilot's IP-safe authoring process:

- Based on publicly available regulatory information
- Independent interpretation of banking standards
- No proprietary bank procedures incorporated
- Original language and terminology used
- Regular legal review and compliance audits

### Data Sources

Profiles are derived from:
- Bangladesh Bank public circulars
- Published banking regulations
- Industry analysis and reports
- Public bank documentation
- Regulatory authority guidelines

### Disclaimers

- Profiles reflect general enforcement tendencies, not guarantees
- Actual bank decisions may vary based on specific circumstances
- LCopilot validation is advisory, not legally binding
- Banks may change policies without notice
- Final validation authority rests with the issuing bank

---

## Support & Updates

### Getting Help

- **Documentation**: docs.lcopilot.com/bank-profiles
- **Support Email**: support@lcopilot.com
- **Enterprise Support**: enterprise@lcopilot.com
- **Bank Relations**: banks@lcopilot.com

### Profile Updates

**Version**: 1.0.0
**Last Updated**: January 2024
**Next Review**: April 2024
**Total Banks**: 41 active profiles

### Change Log

- **v1.0.0** (Jan 2024): Initial release with 41 Bangladesh banks
- **Upcoming**: Monthly updates based on bank feedback
- **Planned**: Regional expansion to other South Asian markets

---

*This guide covers the comprehensive bank enforcement profile system. For technical implementation details, see the API documentation. For bank-specific inquiries, contact our bank relations team.*