# Semantic AI Environment Variables - Quick Reference

## Required for Production

```bash
# Enable semantic AI feature (defaults to true)
AI_SEMANTIC_ENABLED=true

# OpenAI API key (required if AI_SEMANTIC_ENABLED=true)
OPENAI_API_KEY=sk-your-key-here
```

## Optional Configuration

```bash
# Model for semantic comparisons (default: gpt-4o-mini)
AI_SEMANTIC_MODEL=gpt-4o-mini

# Confidence threshold 0.0-1.0 (default: 0.82 = 82%)
AI_SEMANTIC_THRESHOLD_DEFAULT=0.82

# Timeout in milliseconds (default: 6000 = 6 seconds)
AI_SEMANTIC_TIMEOUT_MS=6000
```

## Defaults

If variables are **not set**, these defaults apply:

- ✅ `AI_SEMANTIC_ENABLED=true` (feature ON)
- ✅ `AI_SEMANTIC_MODEL=gpt-4o-mini`
- ✅ `AI_SEMANTIC_THRESHOLD_DEFAULT=0.82`
- ✅ `AI_SEMANTIC_TIMEOUT_MS=6000`

**Note**: You still need `OPENAI_API_KEY` for the feature to work.

## Render Deployment

1. Go to **Render Dashboard** → Your API service → **Environment** tab
2. Add variables (or verify they're set):
   - `AI_SEMANTIC_ENABLED=true`
   - `OPENAI_API_KEY=sk-...` (if not already set)
3. **Save** and **Redeploy**

## Disable Feature

To disable semantic AI (e.g., for cost control):

```bash
AI_SEMANTIC_ENABLED=false
```

When disabled, rules fall back to deterministic fuzzy matching (no LLM calls).

## See Also

- Full deployment guide: `docs/SEMANTIC_AI_DEPLOYMENT.md`
- Render production env: `docs/RENDER_PRODUCTION_ENV.md`
- Example config: `apps/api/env.example`

