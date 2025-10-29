# LCopilot LLM Assist Layer Documentation

## Overview

The LLM Assist Layer provides AI-powered assistance for trade finance operations, offering discrepancy analysis, amendment drafting, and intelligent chat support while maintaining strict compliance guardrails and audit trails.

## Architecture

### Core Components

1. **LLM Service Layer** (`app/services/llm_assist.py`)
   - AI-powered discrepancy analysis
   - Bank-style document drafting
   - Amendment generation
   - Interactive chat assistance

2. **API Endpoints** (`app/routes/ai.py`)
   - RESTful endpoints for AI services
   - Access control and rate limiting
   - Comprehensive error handling

3. **Frontend Components** (`components/ai/`)
   - AI Summary Panel
   - Interactive Chat Widget
   - Amendment Flow Interface

4. **Database Models**
   - AI audit event tracking
   - Confidence scoring history
   - Fallback mechanism logging

## Features

### 1. AI Discrepancy Summary

**Endpoint:** `POST /api/ai/discrepancies`

Analyzes trade finance discrepancies using advanced language models with fallback to rule-based systems.

**Features:**
- Multi-modal analysis (text + document images)
- Confidence scoring (0.0 - 1.0)
- Automatic fallback when confidence < 0.6
- Multilingual support (English/Bangla)
- Comprehensive audit logging

**Request Format:**
```json
{
  "lc_id": "LC001",
  "discrepancies": [
    {
      "discrepancy_id": "DISC001",
      "field_name": "shipment_date",
      "expected_value": "2024-01-15",
      "actual_value": "2024-01-20",
      "severity": "medium"
    }
  ],
  "language": "en",
  "include_recommendations": true,
  "analysis_depth": "detailed"
}
```

**Response Format:**
```json
{
  "content": "Analysis of 3 discrepancies found...",
  "confidence_score": 0.85,
  "model_used": "gpt-4",
  "fallback_used": false,
  "language": "en",
  "audit_event_id": "audit_12345"
}
```

### 2. Bank Draft Generation

**Endpoint:** `POST /api/ai/bank-draft`

Generates professional bank-style discrepancy notifications in SWIFT MT799 format.

**Access Control:**
- Bank users: Full access
- SME users: Limited access (basic templates only)
- Regulatory users: Read-only access

**Features:**
- Professional banking language
- Regulatory compliance formatting
- Multi-currency support
- UCP 600 compliance

**Request Format:**
```json
{
  "lc_id": "LC001",
  "discrepancies": [...],
  "recipient_bank": "CITIUS33",
  "notification_type": "discrepancy_advice",
  "language": "en",
  "include_legal_disclaimer": true
}
```

### 3. Amendment Draft Generation

**Endpoint:** `POST /api/ai/amendment-draft`

Generates suggested amendment language for trade finance documents.

**Features:**
- Context-aware amendment suggestions
- UCP 600 compliance checking
- Risk assessment integration
- Version control for amendments
- SWIFT MT707 format support

**Amendment Types:**
- `full`: Complete amendment (MT707)
- `partial`: Partial amendment
- `cancellation`: Cancellation request
- `correction`: Error correction

**Request Format:**
```json
{
  "lc_id": "LC001",
  "discrepancies": [...],
  "amendment_type": "full",
  "custom_instructions": "Include regulatory compliance notes",
  "language": "en",
  "include_rationale": true,
  "format": "swift_mt707"
}
```

### 4. AI Chat Assistant

**Endpoint:** `POST /api/ai/chat`

Interactive AI chat for trade finance assistance with domain-specific knowledge.

**Features:**
- Context-aware responses
- Session-based conversation memory
- Trade finance domain expertise
- Guardrails against non-trade finance queries

**Usage Limits:**
- SME users: 100 messages/month
- Bank users: Unlimited
- Rate limiting: 10 requests/minute

**Request Format:**
```json
{
  "message": "Explain UCP 600 Article 14",
  "session_id": "session_12345",
  "lc_id": "LC001",
  "language": "en",
  "context": {
    "conversation_history": [...]
  }
}
```

## Frontend Components

### AISummaryPanel

Location: `components/ai/AISummaryPanel.tsx`

React component for displaying AI-powered discrepancy analysis.

**Props:**
- `lcId`: Letter of Credit ID
- `discrepancies`: Array of discrepancy objects
- `onRefresh`: Callback for refresh action
- `className`: CSS classes

**Features:**
- One-click summary generation
- Confidence score visualization
- Fallback indicator
- Model information display

### AIChatWidget

Location: `components/ai/AIChatWidget.tsx`

Interactive chat widget for AI assistance.

**Props:**
- `lcId`: Letter of Credit ID (optional)
- `minimized`: Minimize state
- `onToggleMinimize`: Toggle handler
- `onClose`: Close handler

**Features:**
- Real-time messaging
- Message history
- Confidence scoring per message
- Minimize/maximize functionality

### AIAmendmentFlow

Location: `components/ai/AIAmendmentFlow.tsx`

Complete amendment generation workflow.

**Props:**
- `lcId`: Letter of Credit ID
- `currentDiscrepancies`: Current discrepancy list
- `onAmendmentGenerated`: Success callback

**Features:**
- Amendment type selection
- Custom instructions input
- Generated amendment preview
- Copy/download functionality
- Field change suggestions

## Business Model Protection

### Dual Billing Enforcement

The LLM Assist Layer enforces the dual billing model through:

1. **Access Control**
   - SME users: Basic AI features
   - Bank users: Advanced AI capabilities
   - Different pricing tiers

2. **Usage Tracking**
   - All AI requests logged with billing events
   - Token usage monitoring
   - Rate limiting by user type

3. **Feature Restrictions**
   - Bank draft generation restricted to bank users
   - Advanced analysis features for premium tiers
   - API key management per organization

### Billing Events

All AI operations generate immutable billing events:

```python
billing_event = BillingEvent(
    user_id=user.id,
    organization_id=user.organization_id,
    event_type="ai_discrepancy_analysis",
    resource_id=lc_id,
    tokens_used=response_tokens,
    cost_usd=calculated_cost,
    metadata={
        "model_used": model_name,
        "confidence_score": confidence,
        "fallback_used": fallback_flag
    }
)
```

## Compliance & Audit

### Audit Logging

All AI interactions are comprehensively logged:

```python
class AIAuditEvent(Base):
    __tablename__ = "ai_audit_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    lc_id = Column(String, nullable=True)
    request_type = Column(Enum(AIRequestType), nullable=False)
    model_used = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=True)
    fallback_used = Column(Boolean, default=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Compliance Features

1. **Data Privacy**
   - No sensitive data stored in AI model context
   - Automatic data anonymization
   - GDPR compliance for EU users

2. **Regulatory Compliance**
   - UCP 600 compliance checking
   - SWIFT message format validation
   - Regulatory approval workflows

3. **Audit Trail**
   - Complete request/response logging
   - User action tracking
   - Immutable audit records

## Security

### Authentication & Authorization

```python
@router.post("/api/ai/discrepancies")
async def generate_discrepancy_summary(
    request: DiscrepancySummaryRequest,
    current_user: User = Depends(get_current_user)
):
    # Access control enforced at endpoint level
    # Additional checks within service layer
```

### Rate Limiting

- 10 requests/minute per user
- 100 requests/hour for SME users
- Unlimited for bank users
- Automatic throttling during high load

### Data Protection

- Input sanitization
- Output filtering
- PII detection and redaction
- Secure model communication

## Configuration

### Environment Variables

```bash
# AI Service Configuration
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
AI_MODEL_PRIMARY=gpt-4
AI_MODEL_FALLBACK=gpt-3.5-turbo
AI_CONFIDENCE_THRESHOLD=0.6

# Rate Limiting
AI_RATE_LIMIT_PER_MINUTE=10
AI_RATE_LIMIT_PER_HOUR=100

# Monitoring
AI_METRICS_ENABLED=true
AI_AUDIT_RETENTION_DAYS=365
```

### Model Configuration

```python
class AIConfig:
    PRIMARY_MODELS = {
        "analysis": "gpt-4",
        "drafting": "gpt-4",
        "chat": "gpt-3.5-turbo"
    }

    FALLBACK_MODELS = {
        "analysis": "claude-3-sonnet",
        "drafting": "claude-3-sonnet",
        "chat": "rule_based"
    }

    CONFIDENCE_THRESHOLDS = {
        "analysis": 0.7,
        "drafting": 0.8,
        "chat": 0.6
    }
```

## Monitoring & Analytics

### Metrics Tracked

1. **Usage Metrics**
   - Requests per endpoint
   - Token consumption
   - Response times
   - Error rates

2. **Quality Metrics**
   - Confidence score distribution
   - Fallback usage rates
   - User satisfaction ratings
   - Accuracy measurements

3. **Business Metrics**
   - Revenue per AI feature
   - User engagement
   - Feature adoption rates
   - Customer retention

### Prometheus Metrics

```python
# Request counters
ai_requests_total = Counter('ai_requests_total',
                           'Total AI requests',
                           ['endpoint', 'user_type', 'status'])

# Response time histogram
ai_response_time = Histogram('ai_response_time_seconds',
                            'AI response time in seconds',
                            ['endpoint', 'model'])

# Confidence score gauge
ai_confidence_score = Gauge('ai_confidence_score',
                           'AI confidence score',
                           ['endpoint', 'model'])
```

## Error Handling

### Fallback Mechanisms

1. **Model Fallback**
   - Primary model failure → Secondary model
   - Secondary model failure → Rule-based system
   - Complete failure → Graceful error message

2. **Confidence-Based Fallback**
   - Confidence < 0.6 → Automatic fallback
   - Confidence < 0.4 → Rule-based system
   - Manual fallback option available

3. **Service Degradation**
   - High load → Rate limiting
   - Model unavailable → Cache previous responses
   - Network issues → Retry with exponential backoff

### Error Response Format

```json
{
  "error": {
    "code": "AI_SERVICE_UNAVAILABLE",
    "message": "AI service temporarily unavailable",
    "fallback_available": true,
    "retry_after": 60
  },
  "fallback_response": {
    "content": "Rule-based analysis available...",
    "confidence_score": 0.5,
    "model_used": "rule_based"
  }
}
```

## Testing

### Unit Tests

```bash
# Run AI service tests
pytest apps/api/tests/test_llm_assist.py -v

# Run specific test categories
pytest -k "test_confidence_scoring" -v
pytest -k "test_fallback_mechanisms" -v
```

### Integration Tests

```bash
# Test full AI workflow
pytest apps/api/tests/test_ai_integration.py -v

# Test API endpoints
pytest apps/api/tests/test_ai_routes.py -v
```

### Load Testing

```bash
# Load test AI endpoints
k6 run tests/load/ai_endpoints.js

# Test rate limiting
k6 run tests/load/ai_rate_limiting.js
```

## Deployment

### Docker Configuration

```dockerfile
# AI service container
FROM python:3.11-slim

# Install AI dependencies
RUN pip install openai anthropic transformers

# Copy AI service files
COPY apps/api/app/services/llm_assist.py /app/services/
COPY apps/api/app/routes/ai.py /app/routes/

# Environment configuration
ENV AI_MODEL_PRIMARY=gpt-4
ENV AI_CONFIDENCE_THRESHOLD=0.6
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lcopilot-ai-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lcopilot-ai
  template:
    spec:
      containers:
      - name: ai-service
        image: lcopilot/ai-service:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## Roadmap

### Phase 1 (Current)
- ✅ Basic discrepancy analysis
- ✅ Bank draft generation
- ✅ Amendment drafting
- ✅ Chat assistance

### Phase 2 (Q2 2024)
- 📋 Multi-language support (Arabic, Chinese)
- 📋 Document image analysis
- 📋 Voice-to-text integration
- 📋 Advanced compliance checking

### Phase 3 (Q3 2024)
- 📋 Predictive analytics
- 📋 Risk assessment integration
- 📋 Automated workflow suggestions
- 📋 Machine learning model training

### Phase 4 (Q4 2024)
- 📋 Custom model fine-tuning
- 📋 Real-time collaboration features
- 📋 Advanced reporting
- 📋 White-label solutions

## Support

### Documentation
- API Reference: `/docs/api/ai`
- Frontend Components: `/docs/components/ai`
- Deployment Guide: `/docs/deployment/ai`

### Troubleshooting
- Common Issues: `/docs/troubleshooting/ai`
- Performance Tuning: `/docs/performance/ai`
- Security Best Practices: `/docs/security/ai`

### Contact
- Technical Support: ai-support@lcopilot.com
- Business Inquiries: sales@lcopilot.com
- Security Issues: security@lcopilot.com

---

*Last updated: September 17, 2024*
*Version: 1.0.0*