# LCopilot UCP600 & ISBP Compliance Guide

## Overview

LCopilot's Trust Platform now includes comprehensive UCP600 and ISBP compliance validation for all Letter of Credit (LC) processing. This guide explains the compliance features, tier-based access, and how to leverage these capabilities for trade finance operations.

## Compliance Standards Covered

### UCP600 (Uniform Customs and Practice for Documentary Credits)
- **Coverage**: Full ICC Publication 600 compliance validation
- **Rules**: All 39 UCP600 articles with automated checking
- **Focus**: Documentary credit fundamentals, bank obligations, document examination

### ISBP (International Standard Banking Practice)
- **Coverage**: ICC Publication 745 standard banking practices
- **Rules**: Document examination standards and interpretative guidelines
- **Focus**: Practical application of UCP600 in trade finance operations

## Tier-Based Compliance Access

### Free Tier: SME Starter
- **Compliance Checks**: 3 total checks on signup (teaser)
- **Purpose**: Experience how banks evaluate LC compliance
- **Features**:
  - Basic UCP600 rule validation
  - ISBP standard checking
  - Compliance scoring
- **Limitations**:
  - Limited to 3 checks total
  - No audit trail
  - No compliance exports
- **Upgrade Message**: "Try 3 UCP600/ISBP compliance checks — see how banks will view your LC"

### Pro Tier: Active Trader
- **Compliance Checks**: Unlimited
- **Description**: "Full UCP600/ISBP coverage"
- **Features**:
  - Unlimited UCP600/ISBP validation
  - Compliance audit trail
  - SLA compliance reporting
  - Priority compliance support
  - JSON/CSV compliance exports
- **Limitations**:
  - No digital signatures
  - Standard retention (1 year)

### Enterprise Tier: Bank & Corporate
- **Compliance Checks**: Unlimited
- **Description**: "Bank-grade compliance (UCP600/ISBP + signed logs)"
- **Features**:
  - Unlimited compliance validation
  - Digital signature verification
  - Immutable audit trails
  - 7-year compliance retention
  - Bank regulatory reporting
  - PDF compliance exports with digital signatures
  - Dedicated compliance support
- **No Limitations**: Full audit-grade compliance

## Compliance Scoring System

### Scoring Range: 0-100%
- **90-100%**: Excellent compliance (low risk)
- **80-89%**: Good compliance (acceptable risk)
- **70-79%**: Fair compliance (moderate risk)
- **Below 70%**: Poor compliance (high risk)

### Score Calculation
- **UCP600 Score**: Weighted based on rule criticality
- **ISBP Score**: Document examination standards compliance
- **Overall Score**: Combined UCP600 + ISBP weighted average

## Common UCP600/ISBP Violations

Based on platform analysis, the most frequent violations are:

### 1. UCP600-6 (28% frequency)
- **Issue**: Missing or unclear expiry date/place
- **Impact**: Critical - prevents LC usage
- **Resolution**: Ensure clear expiry date and place specifications

### 2. UCP600-20 (22% frequency)
- **Issue**: Commercial invoice discrepancies
- **Impact**: Major - delays payment
- **Resolution**: Verify invoice details match LC requirements exactly

### 3. ISBP-B2 (18% frequency)
- **Issue**: Invoice amount exceeds LC amount
- **Impact**: Critical - automatic dishonor
- **Resolution**: Ensure invoice total does not exceed LC amount

### 4. UCP600-31 (15% frequency)
- **Issue**: Inconsistent or illogical dates
- **Impact**: Major - document conflicts
- **Resolution**: Verify date consistency across all documents

### 5. ISBP-D3 (12% frequency)
- **Issue**: Transport document date issues
- **Impact**: Major - affects goods release
- **Resolution**: Ensure transport documents meet timing requirements

## API Integration

### Compliance Check Endpoint
```bash
POST /api/v1/validate/compliance
```

**Request Body:**
```json
{
  "lc_reference": "LC2024001",
  "documents": [
    {
      "type": "letter_of_credit",
      "content": "...",
      "format": "swift_mt700"
    },
    {
      "type": "commercial_invoice",
      "content": "...",
      "format": "pdf"
    }
  ],
  "check_types": ["ucp600", "isbp"]
}
```

**Response:**
```json
{
  "validation_id": "val_123456789",
  "overall_result": "pass",
  "compliance_score": 92.5,
  "ucp600": {
    "compliant": true,
    "score": 94.2,
    "violations": [],
    "warnings": ["Minor date format inconsistency"]
  },
  "isbp": {
    "compliant": true,
    "score": 90.8,
    "violations": [],
    "discrepancies": []
  },
  "processing_time_ms": 2340,
  "quota_remaining": -1
}
```

### Error Responses

**Quota Exceeded (Free Tier):**
```json
{
  "error": "quota_exceeded",
  "message": "Compliance check quota exceeded for free tier. Upgrade to Pro for unlimited compliance validation.",
  "quota_info": {
    "tier": "free",
    "checks_used": 3,
    "checks_limit": 3
  },
  "upgrade_url": "/upgrade?feature=compliance"
}
```

## Compliance Export Formats

### JSON Export (Pro/Enterprise)
- **Format**: Structured JSON with full compliance details
- **Retention**: Pro (1 year), Enterprise (7 years)
- **Encryption**: KMS encrypted for security

### CSV Export (Pro/Enterprise)
- **Format**: Tabular data for spreadsheet analysis
- **Fields**: All compliance metrics and violation details
- **Use Case**: Compliance reporting and analysis

### PDF Export (Enterprise Only)
- **Format**: Bank-auditable PDF reports
- **Features**: Digital signatures, immutable audit trails
- **Use Case**: Regulatory compliance, bank audits

## Compliance Monitoring

### Status Page Integration
Compliance metrics are displayed on customer status pages:

- **Free Tier**: Compliance teaser with upgrade messaging
- **Pro Tier**: Full UCP600/ISBP coverage status
- **Enterprise Tier**: Bank-grade compliance with violation insights

### SLA Dashboard Integration
Compliance metrics are included in SLA dashboards:

- **Compliance Checks Performed**: Total checks run
- **Compliance Score Average**: Average compliance score
- **Violation Detection Rate**: Percentage of checks with violations
- **UCP600/ISBP Breakdown**: Separate scoring for each standard

## Best Practices for Trade Partners

### For Importers
1. **Pre-validation**: Check LC compliance before accepting terms
2. **Document Preparation**: Ensure all import documents meet ISBP standards
3. **Continuous Monitoring**: Track compliance scores over time

### For Exporters
1. **Document Review**: Validate export documents against UCP600 rules
2. **Risk Assessment**: Use compliance scores for trade partner evaluation
3. **Process Improvement**: Address recurring violations systematically

### For Banks
1. **Audit Trail**: Maintain immutable compliance records
2. **Regulatory Reporting**: Use PDF exports for bank compliance
3. **Risk Management**: Set compliance thresholds for credit decisions

### for Trading Companies
1. **Bulk Validation**: Process multiple LCs efficiently
2. **Compliance Analytics**: Analyze violation patterns across trade lanes
3. **Partner Assessment**: Evaluate trade partner compliance performance

## Integration Examples

### Python SDK Usage
```python
from lcopilot import ComplianceClient

client = ComplianceClient(api_key="your_api_key")

# Run compliance check
result = client.validate_compliance(
    lc_reference="LC2024001",
    documents=[lc_doc, invoice_doc, bl_doc],
    check_types=["ucp600", "isbp"]
)

print(f"Compliance Score: {result.compliance_score}%")
print(f"UCP600 Score: {result.ucp600.score}%")
print(f"ISBP Score: {result.isbp.score}%")

# Export compliance data
export_result = client.export_compliance(
    start_date="2024-01-01",
    end_date="2024-12-31",
    format="csv"
)

print(f"Export URL: {export_result.download_url}")
```

### Node.js Integration
```javascript
const { LCopilotClient } = require('lcopilot-sdk');

const client = new LCopilotClient({
  apiKey: process.env.LCOPILOT_API_KEY
});

async function validateCompliance(lcData) {
  try {
    const result = await client.compliance.validate({
      lcReference: lcData.reference,
      documents: lcData.documents,
      checkTypes: ['ucp600', 'isbp']
    });

    return {
      compliant: result.overallResult === 'pass',
      score: result.complianceScore,
      violations: result.ucp600.violations.concat(result.isbp.violations)
    };
  } catch (error) {
    if (error.code === 'QUOTA_EXCEEDED') {
      throw new Error('Upgrade to Pro tier for unlimited compliance checks');
    }
    throw error;
  }
}
```

## Support and Resources

### Enterprise Support
- **Response Time**: 4 hours
- **Phone Support**: +1-800-LC-PILOT
- **Email**: enterprise-compliance@lcopilot.com
- **Dedicated CSM**: Available for compliance guidance

### Pro Support
- **Response Time**: 24 hours
- **Email**: compliance-support@lcopilot.com
- **Documentation**: Comprehensive compliance guides

### Community Support (Free)
- **Response Time**: 72 hours
- **Email**: community@lcopilot.com
- **Knowledge Base**: Self-service compliance resources

## Compliance Roadmap

### Q1 2025
- [ ] Additional ISBP 745 rules coverage
- [ ] Machine learning compliance scoring improvements
- [ ] Mobile compliance validation app

### Q2 2025
- [ ] UCC 500 legacy support for historical LCs
- [ ] Blockchain compliance verification
- [ ] Multi-language document support

### Q3 2025
- [ ] AI-powered compliance remediation suggestions
- [ ] Real-time compliance monitoring dashboards
- [ ] Integration with major trade finance platforms

---

*This guide is maintained by the LCopilot compliance team. For technical questions or feature requests, contact compliance-support@lcopilot.com*