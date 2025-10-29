# Multi-Language Reports with AI-Assisted Translation

This document provides comprehensive guidance on LCopilot's multi-language report generation system, including AI-assisted translation workflow and cross-border expansion capabilities.

## Overview

LCopilot supports generating Letter of Credit compliance reports in multiple languages with three distinct modes:
- **Single Language**: Reports in one language only
- **Bilingual**: Side-by-side English and local language
- **Parallel**: Separate pages for each language

### Supported Languages

| Language | Code | Direction | Status |
|----------|------|-----------|--------|
| English | `en` | LTR | ✅ Primary |
| Bengali/Bangla | `bn` | LTR | ✅ Full Support |
| Arabic | `ar` | RTL | ✅ Full Support |
| Hindi | `hi` | LTR | 🔄 AI-Ready |
| Urdu | `ur` | RTL | 🔄 AI-Ready |
| Mandarin | `zh` | LTR | 🔄 AI-Ready |
| French | `fr` | LTR | 🔄 AI-Ready |
| German | `de` | LTR | 🔄 AI-Ready |
| Malay | `ms` | LTR | 🔄 AI-Ready |

## Architecture

### Database Schema

```sql
-- Add preferred_language to Company table
ALTER TABLE companies ADD COLUMN preferred_language languagetype NOT NULL DEFAULT 'en';

-- Language enum
CREATE TYPE languagetype AS ENUM ('en', 'bn', 'ar', 'hi', 'ur', 'zh', 'fr', 'de', 'ms');
```

### Translation System Structure

```
locales/
├── en.json                 # Source language (English)
├── bn.json                 # Manual translations (Bengali)
├── ar.json                 # Manual translations (Arabic)
├── auto_generated/         # AI-generated translations
│   ├── bn.json
│   ├── ar.json
│   └── hi.json
└── verified/               # Human-verified translations
    ├── bn.json
    └── ar.json
```

### Translation Priority

1. **Verified** (highest) - Human-approved translations
2. **Auto-generated** - AI-generated translations
3. **Base** - Manual translations
4. **English fallback** (lowest) - Always available

## API Reference

### Report Generation

#### Get/Generate Report
```http
GET /api/sessions/{session_id}/report?languages=en,bn&report_mode=bilingual&regenerate=false
```

**Parameters:**
- `languages` - Comma-separated language codes (e.g., "en,bn")
- `report_mode` - Report format: "single", "bilingual", or "parallel"
- `regenerate` - Force regenerate report with new settings (boolean)

**Example Response:**
```json
{
  "download_url": "https://s3.../report_en-bn_bilingual.pdf",
  "expires_at": "2025-09-17T12:00:00Z",
  "report_info": {
    "id": "uuid",
    "languages": ["en", "bn"],
    "report_mode": "bilingual",
    "file_size": 2048576
  }
}
```

### Translation Management

#### Get Supported Languages
```http
GET /api/translations/supported
```

#### Generate AI Translations
```http
POST /api/translations/generate
Content-Type: application/json

{
  "target_language": "bn",
  "force_regenerate": false
}
```

#### Get Pending Translations
```http
GET /api/translations/pending?language=bn
```

#### Verify Translation
```http
POST /api/translations/verify
Content-Type: application/json

{
  "language": "bn",
  "key": "report.title",
  "verified_value": "এলসি কমপ্লায়েন্স রিপোর্ট"
}
```

#### Clear Translation Cache
```http
POST /api/translations/cache/clear
```

## Role-Based Access Control (RBAC)

### Language Access Rules

| Role | Allowed Languages | Notes |
|------|------------------|-------|
| **Admin** | All requested | Full override capability |
| **Bank** | English only | Mandatory for compliance |
| **Exporter/Importer** | English + Company preferred | Based on company settings |

### Example Scenarios

```python
# Exporter with Bengali company preference
user.role = "EXPORTER"
user.company.preferred_language = "bn"
requested = ["en", "bn", "ar"]
result = ["en", "bn"]  # Only company language + English

# Bank user
user.role = "BANK"
requested = ["en", "bn"]
result = ["en"]  # English only for regulatory compliance

# Admin user
user.role = "ADMIN"
requested = ["en", "bn", "ar"]
result = ["en", "bn", "ar"]  # All requested languages
```

## Frontend Integration

### React i18n Setup

```typescript
// src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    resources: {
      en: { translation: enTranslations },
      bn: { translation: bnTranslations },
      ar: { translation: arTranslations }
    }
  });
```

### Language Selector Component

```tsx
import { LanguageSelector } from '@/components/LanguageSelector';

// Usage
<LanguageSelector />
```

### Report Download with Language Options

```tsx
import { ReportDownloadDialog } from '@/components/ReportDownloadDialog';

// Usage
<ReportDownloadDialog sessionId={sessionId}>
  <Button>Download Report</Button>
</ReportDownloadDialog>
```

## AI-Assisted Translation Workflow

### 1. Automatic Generation

```python
# Generate missing translations
result = await translation_service.generate_missing_translations(
    target_language="bn",
    db=db_session,
    user=admin_user
)
```

### 2. Human Verification Process

1. **AI generates** translations for missing keys
2. **Admin reviews** auto-generated translations
3. **Human verifies** or edits translations
4. **System promotes** verified translations to production

### 3. Translation Management Dashboard

Access via `/admin/translations`:
- View pending AI translations
- Verify/edit translations
- Generate new translations
- Monitor translation status

## PDF Generation Modes

### Single Language
- One language only
- Compact format
- Fastest generation

```python
await report_service.generate_report(
    session=session,
    user=user,
    languages=["bn"],
    report_mode="single"
)
```

### Bilingual (Side-by-Side)
- English left, local language right
- Professional layout
- Optimal for comparison

```python
await report_service.generate_report(
    session=session,
    user=user,
    languages=["en", "bn"],
    report_mode="bilingual"
)
```

### Parallel (Separate Pages)
- Each language on separate pages
- Complete independence
- Best for different audiences

```python
await report_service.generate_report(
    session=session,
    user=user,
    languages=["en", "bn", "ar"],
    report_mode="parallel"
)
```

## Adding New Languages

### Step 1: Update Database Enum

```sql
-- Add new language to enum
ALTER TYPE languagetype ADD VALUE 'hi';  -- Hindi
```

### Step 2: Update Models

```python
# app/models/company.py
class LanguageType(str, enum.Enum):
    # ... existing languages
    HINDI = "hi"
```

### Step 3: Create Translation Files

```bash
# Create base translation file
touch locales/hi.json

# Add initial translations
{
  "report": {
    "title": "एलसी अनुपालन रिपोर्ट"
  }
}
```

### Step 4: Generate AI Translations

```python
# Use admin interface or API
POST /api/translations/generate
{
  "target_language": "hi",
  "force_regenerate": false
}
```

### Step 5: Update Frontend

```typescript
// Add to language selector
const languages = [
  // ... existing
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' }
];
```

## Testing

### Run Translation Tests

```bash
# Backend tests
pytest test_multilanguage_reports.py -v

# Frontend tests
npm test -- --testPathPattern=i18n
```

### Test Coverage Areas

- ✅ Translation utility functions
- ✅ AI translation service
- ✅ Report generation (all modes)
- ✅ RBAC language filtering
- ✅ API endpoints
- ✅ Error handling
- ✅ Edge cases

## Configuration

### Environment Variables

```bash
# AI Translation
ANTHROPIC_API_KEY=your_api_key_here

# Language Settings
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,bn,ar,hi,ur,zh,fr,de,ms

# Cache Settings
TRANSLATION_CACHE_TTL=3600
```

### Company Preferences

```python
# Set company language preference
company.preferred_language = LanguageType.BANGLA
db.commit()
```

## Best Practices

### Translation Quality

1. **Always use human verification** for legal/financial terms
2. **Review AI translations** before production use
3. **Test with native speakers** for accuracy
4. **Maintain consistency** across similar terms

### Performance Optimization

1. **Cache translations** in memory for frequently used keys
2. **Pre-generate reports** for common language combinations
3. **Use CDN** for static translation files
4. **Implement lazy loading** for large translation sets

### Security Considerations

1. **Audit all translations** with detailed logging
2. **Restrict admin access** to translation management
3. **Validate user inputs** in translation verification
4. **Sanitize translations** to prevent XSS

## Troubleshooting

### Common Issues

#### Translation Not Found
```bash
# Check file exists
ls locales/bn.json

# Verify translation key structure
cat locales/bn.json | jq '.report.title'

# Clear cache and retry
POST /api/translations/cache/clear
```

#### PDF Generation Fails
```bash
# Check language support in PDF generator
# Verify font availability for non-Latin scripts
# Test with single language first

# Debug with minimal example
languages=["en"] # Start simple
report_mode="single" # Use basic mode
```

#### AI Translation Errors
```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Check network connectivity
curl -I https://api.anthropic.com

# Review error logs
tail -f logs/translation_service.log
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('app.utils.i18n').setLevel(logging.DEBUG)
logging.getLogger('app.services.translation').setLevel(logging.DEBUG)
```

## Migration Guide

### From Single Language to Multi-Language

1. **Backup existing reports**
2. **Run database migration**
3. **Set company language preferences**
4. **Test report generation**
5. **Train users on new interface**

### Deployment Checklist

- [ ] Database migration applied
- [ ] Translation files deployed
- [ ] Environment variables set
- [ ] AI service configured
- [ ] Frontend assets built
- [ ] Admin users trained
- [ ] Monitoring enabled
- [ ] Rollback plan ready

## Monitoring and Analytics

### Key Metrics

- Translation completion rate by language
- Report generation time by mode
- AI translation accuracy (human verification rate)
- Language preference distribution
- Error rates by language/mode

### Alerts

- Failed AI translation generations
- High report generation times
- Missing translation keys
- Cache hit rate below threshold

## Support and Maintenance

### Regular Tasks

- **Weekly**: Review pending translations
- **Monthly**: Analyze language usage patterns
- **Quarterly**: Update translation coverage
- **Annually**: Review supported languages list

### Emergency Procedures

1. **Translation service down**: Fall back to English only
2. **AI service unavailable**: Use cached translations
3. **Font rendering issues**: Fall back to basic fonts
4. **Performance degradation**: Scale translation cache

---

## Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `app/utils/i18n.py` | Translation utilities |
| `app/services/translation.py` | AI translation service |
| `app/reports/generator.py` | PDF generation |
| `app/routers/translations.py` | Translation API |
| `locales/*.json` | Translation files |

### Key Commands

```bash
# Generate translations
curl -X POST /api/translations/generate -d '{"target_language":"bn"}'

# Download bilingual report
GET /api/sessions/{id}/report?languages=en,bn&report_mode=bilingual

# Clear cache
curl -X POST /api/translations/cache/clear
```

For additional support, contact the development team or refer to the API documentation at `/docs`.

🚀 **Ready for cross-border expansion with enterprise-grade multilingual compliance reporting!**