# Semantic AI Deployment Checklist

This document outlines the environment variables required for the new `semantic_check` operator feature.

## Required Environment Variables

### Core AI Configuration

These variables control whether semantic AI is enabled and which model to use:

| Variable | Default | Description | Required |
|----------|---------|-------------|-----------|
| `AI_SEMANTIC_ENABLED` | `true` | Enable/disable semantic_check operator | No (defaults to enabled) |
| `AI_SEMANTIC_MODEL` | `gpt-4o-mini` | OpenAI model for semantic comparisons | No (uses default) |
| `AI_SEMANTIC_LOW_COST_MODEL` | `gpt-4o-mini` | Fallback model (currently unused) | No |
| `AI_SEMANTIC_THRESHOLD_DEFAULT` | `0.82` | Confidence threshold (0.0-1.0) for matches | No |
| `AI_SEMANTIC_TIMEOUT_MS` | `6000` | Timeout in milliseconds for AI calls | No |

### Prerequisites

The semantic AI feature requires:

1. **OpenAI API Key** (if using OpenAI):
   ```bash
   OPENAI_API_KEY=sk-...
   ```

2. **AI Enrichment Enabled** (recommended):
   ```bash
   AI_ENRICHMENT=true
   ```

## Deployment Steps

### 1. Local Development

Add to your `.env` file:

```bash
# Semantic AI Configuration
AI_SEMANTIC_ENABLED=true
AI_SEMANTIC_MODEL=gpt-4o-mini
AI_SEMANTIC_THRESHOLD_DEFAULT=0.82
AI_SEMANTIC_TIMEOUT_MS=6000

# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-key-here
```

### 2. Production (Render)

In your Render dashboard:

1. Go to your **API service** → **Environment** tab
2. Add or update these environment variables:

   ```
   AI_SEMANTIC_ENABLED=true
   AI_SEMANTIC_MODEL=gpt-4o-mini
   AI_SEMANTIC_THRESHOLD_DEFAULT=0.82
   AI_SEMANTIC_TIMEOUT_MS=6000
   ```

3. Ensure `OPENAI_API_KEY` is already set (required for AI features)

4. **Redeploy** the service after adding variables

### 3. Verification

After deployment, verify the feature is working:

1. **Check logs** for semantic comparison calls:
   ```bash
   # Look for log entries like:
   # "Semantic comparison: match=True, confidence=0.95"
   ```

2. **Test with a validation job**:
   - Upload LC + Invoice with slightly different goods descriptions
   - Check that semantic comparison runs (not just exact string match)
   - Verify `issue_cards` include `expected`/`found`/`suggested_fix` fields

3. **Monitor AI usage**:
   - Check `ai_usage_records` table for `feature='semantic_rule'` entries
   - Verify quota limits are being enforced

## Feature Flags

### Disable Semantic AI

If you need to disable semantic comparisons (e.g., for cost control):

```bash
AI_SEMANTIC_ENABLED=false
```

When disabled:
- Rules using `semantic_check` operator will fall back to deterministic fuzzy matching
- Uses `rapidfuzz` library for similarity scoring
- No LLM calls are made
- Results are still structured (expected/found/suggested_fix)

### Adjust Confidence Threshold

Lower threshold = more lenient matches (more false positives):
```bash
AI_SEMANTIC_THRESHOLD_DEFAULT=0.75  # 75% confidence required
```

Higher threshold = stricter matches (more false negatives):
```bash
AI_SEMANTIC_THRESHOLD_DEFAULT=0.90  # 90% confidence required
```

## Default Behavior

If environment variables are **not set**, the system uses these defaults:

- ✅ `AI_SEMANTIC_ENABLED=true` (feature is ON by default)
- ✅ `AI_SEMANTIC_MODEL=gpt-4o-mini` (cost-effective model)
- ✅ `AI_SEMANTIC_THRESHOLD_DEFAULT=0.82` (82% confidence)
- ✅ `AI_SEMANTIC_TIMEOUT_MS=6000` (6 second timeout)

**Note**: Even with defaults, you still need `OPENAI_API_KEY` set for the feature to work.

## Troubleshooting

### Semantic comparisons not running

1. **Check `AI_SEMANTIC_ENABLED`**:
   ```python
   # In Python shell or logs
   from app.config import settings
   print(settings.AI_SEMANTIC_ENABLED)  # Should be True
   ```

2. **Verify OpenAI API key**:
   ```bash
   # Test API key is valid
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Check rule definitions**:
   - Ensure rules in `Data/lcopilot_crossdoc.json` use `operator: "semantic_check"`
   - Verify `requires_llm: true` is set for semantic rules

### AI calls timing out

Increase timeout:
```bash
AI_SEMANTIC_TIMEOUT_MS=10000  # 10 seconds
```

### High costs

1. **Disable feature**:
   ```bash
   AI_SEMANTIC_ENABLED=false
   ```

2. **Use cheaper model** (if available):
   ```bash
   AI_SEMANTIC_MODEL=gpt-3.5-turbo  # If supported
   ```

3. **Increase threshold** (fewer AI calls):
   ```bash
   AI_SEMANTIC_THRESHOLD_DEFAULT=0.90  # Stricter = fewer matches = fewer AI calls
   ```

## Related Documentation

- `apps/api/app/services/semantic_compare.py` - Implementation details
- `apps/api/app/config.py` - Configuration schema
- `Data/lcopilot_crossdoc.json` - Example semantic rules

