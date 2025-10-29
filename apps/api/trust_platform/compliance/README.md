# LCopilot Advanced Rule-Based Compliance Engine

A sophisticated compliance validation system for Letters of Credit, featuring DSL-based rule evaluation, IP-safe authoring practices, and comprehensive tier-based access control.

## 🚀 Overview

The Advanced Rule-Based Compliance Engine validates LC documents against:
- **UCP600** (Uniform Customs and Practice for Documentary Credits)
- **ISBP** (International Standard Banking Practice)
- **Local Banking Regulations** (Bangladesh focus)

### Key Features

- **DSL-Based Evaluation**: Express complex compliance rules using Domain Specific Language
- **IP-Safe Authoring**: Paraphrase and reference ICC standards without direct quotation
- **Version Control**: Semantic versioning for rules with changelog tracking
- **Tier-Based Access**: Free (3 checks), Pro (unlimited), Enterprise (audit-grade)
- **Handler Dispatch**: Python handlers for complex validation logic
- **Comprehensive Testing**: Full test fixtures and CI/CD integration

## 📁 Architecture

```
trust_platform/compliance/
├── rule_engine.py           # Core DSL evaluation engine
├── compliance_integration.py # Legacy engine integration
├── rule_linter.py           # IP-safe rule validation
├── rule_author_cli.py       # Rule authoring tools
├── rules/                   # YAML rule definitions
│   ├── ucp600.yaml         # UCP600 compliance rules
│   ├── isbp.yaml           # ISBP document standards
│   └── local_bd.yaml       # Bangladesh local rules
├── handlers/                # Python validation handlers
│   ├── date_logic.py       # Date relationship validation
│   ├── presentation_period.py # UCP600-14 handler
│   └── origin_certificate.py # BD certificate validation
├── fixtures/                # Test data
├── tests/                   # Unit tests
└── README.md               # This documentation
```

## 🔧 Quick Start

### 1. Basic Usage

```python
from trust_platform.compliance.rule_engine import RuleEngine

# Initialize engine
engine = RuleEngine()

# Validate LC document
lc_document = {
    "lc_number": "LC2024001",
    "expiry_date": "2024-03-15",
    "expiry_place": "Dhaka, Bangladesh",
    "amount": {"value": 50000.00, "currency": "USD"},
    # ... more fields
}

# Run validation
result = engine.validate(lc_document, tier="pro")

print(f"Compliance Score: {result.score}")
print(f"Violations: {len([r for r in result.results if r.status.value == 'fail'])}")
```

### 2. CLI Usage

```bash
# Create new rule
python rule_author_cli.py rules:new --id UCP600-XX

# Lint rules for IP safety
python rule_author_cli.py rules:lint

# Test specific rule
python rule_author_cli.py rules:test --id UCP600-14

# List all rules
python rule_author_cli.py rules:list
```

## 📝 DSL Functions Reference

The Domain Specific Language supports these validation functions:

### Field Validation
- `exists(field_path)` - Check if field exists
- `not_empty(field_path)` - Check if field has value
- `length(field_path, min, max)` - Validate string length

### Text Matching
- `equals(field_path, "value")` - Exact match
- `equalsIgnoreCase(field_path, "value")` - Case-insensitive match
- `contains(field_path, "substring")` - Contains text
- `containsIgnoreCase(field_path, "substring")` - Case-insensitive contains
- `matches(field_path, "regex")` - Regex pattern match

### Numeric Operations
- `greaterThan(field_path, number)` - Numeric comparison
- `lessThan(field_path, number)` - Numeric comparison
- `amountGreaterThan(amount_field, number)` - Amount comparison
- `amountLessThan(amount_field, number)` - Amount comparison

### Date Operations
- `dateWithinDays(date_field, days)` - Date within range
- `dateAfter(date_field, "YYYY-MM-DD")` - After specific date
- `dateBefore(date_field, "YYYY-MM-DD")` - Before specific date

### Complex Logic
- `check_handler(handler_name)` - Call Python handler function

## 📋 Rule Definition Format

Rules are defined in YAML with this structure:

```yaml
metadata:
  standard: "UCP600"
  version: "2024.1"
  description: "UCP600 compliance rules"
  last_updated: "2024-12-20"

rules:
  - id: "UCP600-6"
    title: "Expiry Date and Place Requirement"
    reference: "UCP600 Art. 6"
    severity: "high"
    applies_to: ["credit"]
    preconditions:
      - field_exists: expiry_date
    dsl: "exists(expiry_place) && not_empty(expiry_place)"
    examples:
      pass: ["fixtures/ucp600_compliant_credit.json"]
      fail: ["fixtures/missing_expiry_place.json"]
    version: "1.0.0"
```

## 🎯 Tier-Based Access Control

### Free Tier (SME Starter)
- 3 compliance checks total
- Basic UCP600/ISBP validation
- Upsell prompt after quota exhaustion
- No audit trail

### Pro Tier (Active Trader)
- Unlimited compliance checks
- Full UCP600/ISBP/BD coverage
- Compliance reporting
- 1-year audit retention

### Enterprise Tier (Bank & Corporate)
- Unlimited compliance checks
- Bank-grade audit logging
- 7-year retention
- Digital signatures
- Custom rule support

## 🔍 Handler Development

For complex validation logic, create Python handlers:

```python
# handlers/my_rule.py
from typing import Dict, Any

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Custom validation logic

    Returns:
        Dictionary with status, details, field_location, suggested_fix
    """
    try:
        # Your validation logic here
        if validation_passes:
            return {
                "status": "pass",
                "details": "Validation successful",
                "field_location": "field_name"
            }
        else:
            return {
                "status": "fail",
                "details": "Validation failed because...",
                "field_location": "field_name",
                "suggested_fix": "Fix by doing..."
            }
    except Exception as e:
        return {
            "status": "error",
            "details": f"Error: {str(e)}",
            "field_location": "unknown"
        }
```

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Test Specific Fixtures
```bash
# Test UCP600 compliance
python -c "
from rule_engine import RuleEngine
import json

engine = RuleEngine()
with open('fixtures/ucp600_compliant_credit.json') as f:
    lc = json.load(f)

result = engine.validate(lc, 'pro')
print(f'Score: {result.score}, Violations: {len([r for r in result.results if r.status.value == \"fail\"])}')
"
```

### Available Test Fixtures
- `ucp600_compliant_credit.json` - Fully compliant LC
- `date_logic_violations.json` - Date sequence issues
- `bangladesh_compliance_pass.json` - BD local rule compliance
- `bangladesh_compliance_fail.json` - Multiple BD violations
- `isbp_document_issues.json` - Document examination failures
- `free_tier_test.json` - Free tier quota testing
- `comprehensive_test_suite.json` - Full feature testing

## 🚨 IP-Safe Authoring Guidelines

To avoid ICC copyright infringement:

### ✅ Allowed Practices
- Reference article numbers (e.g., "UCP600 Art. 14")
- Paraphrase requirements in your own words
- Use functional descriptions
- Create original validation logic

### ❌ Forbidden Practices
- Direct quotation of ICC text
- Copy-paste from UCP600/ISBP publications
- Long verbatim excerpts
- Reproducing ICC examples

### Example Transformations

**Bad (Direct Quote):**
```yaml
title: "Documents must appear on their face to comply with the terms and conditions of the credit"
```

**Good (Paraphrased):**
```yaml
title: "Document Face Compliance Check"
description: "Validates that presented documents meet LC requirements on face value examination"
```

## 🔄 Migration from Legacy Engine

The system includes backward compatibility:

```python
from trust_platform.compliance.compliance_integration import ComplianceIntegration

# Initialize with both engines
integration = ComplianceIntegration()

# Validate using new engine (default)
result = integration.validate_lc_compliance(lc_document, customer_id)

# Switch to legacy engine if needed
integration.switch_engine(use_new_engine=False)
result = integration.validate_lc_compliance(lc_document, customer_id)
```

## 📊 Performance & Monitoring

### Metrics Tracked
- Validation time per document
- Rule execution success rates
- Tier usage statistics
- Handler performance
- Cache hit rates

### Logging
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('compliance')

# Logs include:
# - Rule execution results
# - Handler dispatch events
# - Tier quota tracking
# - Performance metrics
```

## 🔧 Configuration

### Trust Platform Integration

The engine integrates with the existing trust configuration in `trust_platform/config/trust_config.yaml`:

```yaml
compliance:
  ucp600: true
  isbp: true
  tiers:
    free:
      enabled: true
      checks_included: 3
    pro:
      enabled: true
      checks_included: unlimited
    enterprise:
      enabled: true
      audit_logging: true
      retention_years: 7
```

## 🚀 Deployment

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Lint rules
python rule_author_cli.py rules:lint
```

### Production
- Enable audit logging for Enterprise tier
- Configure retention policies
- Set up monitoring dashboards
- Implement backup procedures

## 📈 Roadmap

### Phase 2 Features
- [ ] SWIFT MT700 compliance rules
- [ ] Standby LC (ISP98) support
- [ ] Machine learning rule suggestions
- [ ] Real-time collaboration tools
- [ ] Visual rule builder interface

### Integration Targets
- [ ] Core banking systems (Temenos, Flexcube)
- [ ] Trade finance platforms (Finastra, Kyriba)
- [ ] Document management systems
- [ ] Blockchain trade platforms

## 📞 Support

### Rule Development Support
- **Documentation**: See individual rule YAML files
- **CLI Help**: `python rule_author_cli.py --help`
- **Handler Examples**: Check `handlers/` directory

### Technical Support
- **Logs**: Check application logs for debugging
- **Test Data**: Use fixtures for consistent testing
- **Performance**: Monitor validation times and optimize DSL expressions

## 🏗️ Contributing

### Adding New Rules

1. **Research**: Ensure IP-safe paraphrasing
2. **Create**: Use CLI `rules:new --id RULE-ID`
3. **Implement**: Write DSL or handler logic
4. **Test**: Create pass/fail fixtures
5. **Lint**: Run `rules:lint` for validation
6. **Document**: Update rule reference docs

### Handler Development

1. **Template**: Use existing handlers as templates
2. **Validate**: Return proper status dictionary
3. **Test**: Create comprehensive test cases
4. **Document**: Add docstrings and examples
5. **Register**: Update handler dispatch mapping

---

**Built for LCopilot Trust Platform** | **Version 2.0.0** | **Last Updated: 2024-12-20**