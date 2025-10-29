---
id: story-llm-assist-discrepancy-and-phrasing
status: todo
effort: L
risk: Medium
owners: ["TBD"]
links:
  code: ["glob://apps/api/app/services/llm_service.py", "glob://apps/api/app/services/prompt_manager.py"]
  docs: ["../prd/4-epics-and-milestones.md#epic-3", "../architecture/2-components-and-dataflow.md"]
---

# Story: LLM-Assisted Discrepancy Analysis & Professional Phrasing

## BMAD Framework

### Background
After deterministic rules identify discrepancies in LC documents, users need clear, professional explanations of what's wrong and how to fix it. Current system only provides rule violations without context or guidance.

### Motivation
- **Business Value:** Transform technical rule violations into actionable business guidance
- **User Pain:** SME exporters struggle to understand banking terminology and compliance requirements
- **Competitive Edge:** AI-enhanced explanations differentiate from manual consultant services

### Approach
Integrate LLM (Claude/GPT-4) to analyze deterministic rule results and generate professional, bank-appropriate explanations with suggested remediation steps. Implement safety rails to prevent AI hallucination of non-existent rules.

### Details
Create prompt engineering framework with versioned templates, response validation against rule database, and audit trail for all AI decisions. Support both English and Bangla outputs with banking terminology adaptation.

## User Story

**As an** SME export manager
**I want** AI-powered explanations of compliance issues
**So that** I understand what's wrong and how to fix it in professional banking language

## Acceptance Criteria

### Given-When-Then Scenarios

**AC1: Discrepancy Summarization**
```gherkin
Given deterministic rules have identified 3+ discrepancies in an LC
When the LLM assistant processes the findings
Then a professional summary is generated grouping related issues
And the summary uses appropriate banking terminology
And suggested remediation steps are provided
```

**AC2: Professional Bank Phrasing**
```gherkin
Given rule violations and extracted document data
When the AI generates explanations
Then language is professional and suitable for bank submission
And technical jargon is explained in business terms
And explanations reference specific UCP600 articles
```

**AC3: Safety Rails & Validation**
```gherkin
Given AI-generated compliance explanations
When the system validates the response
Then no hallucinated rules or non-existent articles are mentioned
And all rule references are verified against UCP600 database
And explanations are marked as "AI-assisted" in audit trail
```

**AC4: Multilingual Support**
```gherkin
Given a user's language preference is set to Bangla
When AI explanations are generated
Then responses are provided in appropriate Bangla
And banking terms are culturally adapted
And English technical terms are provided in parentheses
```

## SM Checklist
- [ ] LLM provider integration (Claude/OpenAI) configured
- [ ] Prompt engineering framework implemented
- [ ] Response validation against rule database
- [ ] Safety rails to prevent hallucination
- [ ] Bangla language support and cultural adaptation
- [ ] Audit trail for AI decisions
- [ ] Performance optimization (<5 second responses)
- [ ] Error handling and fallback to deterministic explanations

## Dev Tasks

### Task 1: LLM Integration Foundation
- [ ] LLM provider SDK integration (Anthropic Claude preferred)
- [ ] API key management and rotation
- [ ] Rate limiting and cost controls
- [ ] Async processing for LLM calls

### Task 2: Prompt Engineering Framework
- [ ] Versioned prompt templates system
- [ ] Dynamic prompt generation from rule results
- [ ] Context injection with document metadata
- [ ] A/B testing framework for prompt optimization

### Task 3: Response Validation & Safety
- [ ] Rule reference validation against UCP600 database
- [ ] Hallucination detection and filtering
- [ ] Response quality scoring
- [ ] Fallback to deterministic explanations

### Task 4: Multilingual Implementation
- [ ] Bangla prompt engineering
- [ ] Cultural adaptation for banking terminology
- [ ] Language detection and routing
- [ ] Quality assessment for non-English responses

## QA Test Plan

### Unit Tests
- [ ] Prompt template generation with various rule scenarios
- [ ] Response validation logic with known hallucinations
- [ ] Language routing and cultural adaptation
- [ ] Safety rail triggering with edge cases

### Integration Tests
- [ ] End-to-end LLM processing with real rule results
- [ ] Response time measurement under load
- [ ] Cost monitoring and budget controls
- [ ] Fallback behavior when LLM unavailable

### AI Quality Tests
- [ ] Expert review of 100+ AI-generated explanations
- [ ] Bangla language quality assessment by native speakers
- [ ] Banking terminology appropriateness review
- [ ] Hallucination detection accuracy testing

### Performance Tests
- [ ] Response time under 5 seconds for standard requests
- [ ] Concurrent request handling (50+ simultaneous)
- [ ] Cost per request optimization
- [ ] Error rate monitoring and alerting

## Test Fixtures

### Input: Deterministic Rule Results
```json
{
  "discrepancies": [
    {
      "rule_id": "UCP600_14b",
      "field": "expiry_date",
      "issue": "LC expired before document submission",
      "document_value": "2025-11-30",
      "submission_date": "2025-12-01"
    },
    {
      "rule_id": "UCP600_18c",
      "field": "amount",
      "issue": "Invoice amount exceeds LC amount",
      "lc_amount": "50000.00",
      "invoice_amount": "52000.00"
    }
  ],
  "document_context": {
    "lc_number": "LC2025-001234",
    "beneficiary": "ABC Textiles Ltd"
  }
}
```

### Expected AI Output (English)
```markdown
## Compliance Analysis Summary

Your Letter of Credit submission has **2 critical issues** that require immediate attention:

### 1. Expired Letter of Credit (UCP600 Article 14b)
**Issue:** The LC expired on November 30, 2025, but documents were presented on December 1, 2025.
**Impact:** Banks will reject all documents submitted after the expiry date.
**Recommendation:** Contact your buyer immediately to request an LC amendment extending the expiry date.

### 2. Amount Discrepancy (UCP600 Article 18c)
**Issue:** Your invoice amount ($52,000) exceeds the LC amount ($50,000) by $2,000.
**Impact:** Banks cannot pay more than the LC amount, resulting in automatic rejection.
**Recommendation:** Either reduce the invoice amount to $50,000 or request an LC amendment to increase the amount.

*This analysis was generated with AI assistance and verified against UCP600 compliance rules.*
```

### Pass/Fail Criteria
- **PASS:** >90% expert approval rating for explanation quality
- **PASS:** Zero hallucinated rules in 100 test cases
- **PASS:** Response time consistently under 5 seconds
- **PASS:** Bangla translations rated >85% quality by native speakers
- **FAIL:** Any hallucinated UCP600 articles or non-existent rules

## Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
LLM_PROVIDER=anthropic  # or openai
LLM_MODEL=claude-3-sonnet-20240229
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.3
LLM_TIMEOUT_SECONDS=30
PROMPT_VERSION=v2.1
ENABLE_BANGLA_LLM=true
```

## Code Paths
- **LLM Service:** `apps/api/app/services/llm_service.py`
- **Prompt Manager:** `apps/api/app/services/prompt_manager.py`
- **Validation:** `apps/api/app/services/response_validator.py`
- **Multilingual:** `apps/api/app/utils/i18n_llm.py`
- **Tests:** `apps/api/tests/test_llm_assistance.py`

## Dependencies
- **Prerequisite:** Deterministic rules engine must be completed
- **External:** Anthropic Claude or OpenAI API access
- **Internal:** UCP600 rule database for validation
- **Data:** Bangla language corpus for prompt engineering

## Effort Estimation
- **Prompt Engineering:** 3 days
- **Integration Development:** 4 days
- **Safety & Validation:** 3 days
- **Bangla Language Support:** 4 days
- **Testing & Quality Assurance:** 3 days
- **Total:** 17 days (Large effort due to AI complexity)

## Risk Assessment: Medium
- **AI Quality Risk:** LLM responses may vary in quality and consistency
- **Hallucination Risk:** AI might invent non-existent rules despite safety measures
- **Performance Risk:** LLM API latency could impact user experience
- **Cost Risk:** AI API costs could escalate with high usage
- **Language Risk:** Bangla language AI capabilities may be limited
- **Regulatory Risk:** AI-assisted advice in financial compliance requires careful validation

## Mitigation Strategies
- **Quality Control:** Expert review process for prompt optimization
- **Safety Nets:** Multiple validation layers and fallback to deterministic explanations
- **Performance:** Caching and async processing to minimize latency
- **Cost Management:** Usage monitoring and budget alerts
- **Language Quality:** Native speaker validation and iterative improvement