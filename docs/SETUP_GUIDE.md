# LCOPILOT Setup Guide

**Date:** 2025-01-27  
**Purpose:** Complete setup guide for production deployment

## Critical Issues Found

### 1. Stub Mode is Active
**Problem:** `USE_STUBS=true` in environment variables  
**Impact:** System uses mock data instead of real OCR/storage  
**Solution:** Set `USE_STUBS=false` in production

### 2. UTF-8 Decoding Error
**Problem:** Form field values may contain non-UTF-8 bytes  
**Status:** ✅ Fixed in code, but may need environment restart

### 3. Missing Google OCR Configuration
**Problem:** Google Document AI not configured  
**Impact:** OCR processing will fail  
**Solution:** Configure Google Cloud credentials

### 4. ICC Rules Not Loaded
**Problem:** Rules may not be loaded from database/storage  
**Impact:** Validation uses empty/default rules  
**Solution:** Upload ICC rules to database or storage

## Environment Variables Setup

### Required for Production

Create or update `.env` file in `apps/api/`:

```bash
# ============================================
# CRITICAL: Disable Stub Mode for Production
# ============================================
USE_STUBS=false

# ============================================
# Google Cloud Document AI (OCR)
# ============================================
# Get these from Google Cloud Console:
# 1. Create a project: https://console.cloud.google.com/
# 2. Enable Document AI API
# 3. Create a processor (Form Parser or Document OCR)
# 4. Download service account JSON key

GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_DOCUMENTAI_LOCATION=us  # or eu, asia
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# ============================================
# Database (Supabase)
# ============================================
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:6543/postgres
DIRECT_DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres

# ============================================
# AWS S3 (File Storage)
# ============================================
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=lcopilot-documents

# ============================================
# Rules System
# ============================================
# Option 1: Use JSON rulesets (recommended)
USE_JSON_RULES=true

# Option 2: Use database rules (legacy)
USE_JSON_RULES=false
# Then seed rules: python scripts/seed_rules.py
```

## Step-by-Step Setup

### Step 1: Disable Stub Mode

**Check current status:**
```bash
cd apps/api
# Check if .env exists
cat .env | grep USE_STUBS
```

**Set to false:**
```bash
# Edit .env file
USE_STUBS=false
```

**Restart backend:**
```bash
# Stop current backend
# Start backend again
# The stub mode indicator should disappear
```

### Step 2: Configure Google Cloud Document AI

#### 2.1 Create Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Note the Project ID

#### 2.2 Enable Document AI API
1. Navigate to "APIs & Services" > "Library"
2. Search for "Document AI API"
3. Click "Enable"

#### 2.3 Create a Processor
1. Go to "Document AI" > "Processors"
2. Click "Create Processor"
3. Choose processor type:
   - **Form Parser** (recommended for structured documents)
   - **Document OCR** (for general text extraction)
4. Select location (us, eu, asia)
5. Note the Processor ID from the processor details page

#### 2.4 Create Service Account
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name: `lcopilot-ocr`
4. Grant role: "Document AI API User"
5. Click "Create Key" > "JSON"
6. Download the JSON file
7. Save to secure location: `/path/to/service-account-key.json`

#### 2.5 Set Environment Variables
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_DOCUMENTAI_LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
```

#### 2.6 Test OCR Configuration
```bash
cd apps/api
python docai_smoketest.py
```

**Expected output:**
```
✓ Project ID configured
✓ Processor ID configured
✓ Credentials file found
✓ Document AI client initialized
✓ Processor accessible
```

### Step 3: Upload ICC Rules

#### Option A: Upload via Admin UI (Recommended)
1. Navigate to `/admin` (admin login required)
2. Go to "Rules" section
3. Upload ICC rules JSON file
4. Set domain: `icc`
5. Set jurisdiction: `global`
6. Set rulebook version: `UCP600:2007` (or your version)
7. Publish ruleset

#### Option B: Upload via API
```bash
# Use the rules_admin API endpoint
POST /admin/rules/upload
Content-Type: multipart/form-data

file: <icc-rules.json>
domain: icc
jurisdiction: global
rulebook_version: UCP600:2007
```

#### Option C: Seed Database Rules (Legacy)
```bash
cd apps/api
python scripts/seed_rules.py
```

### Step 4: Verify Configuration

#### 4.1 Check Health Endpoint
```bash
curl http://localhost:8000/health/info
```

**Expected response:**
```json
{
  "configuration": {
    "use_stubs": false,
    "ocr": "google_documentai",
    "storage": "s3"
  },
  "services": {
    "database": "ok",
    "s3": "ok",
    "documentai": "ok"
  }
}
```

#### 4.2 Check Stub Mode Status
```bash
curl http://localhost:8000/health/info | jq '.configuration.use_stubs'
# Should return: false
```

#### 4.3 Test File Upload
1. Go to `/lcopilot/exporter-dashboard?section=upload`
2. Upload a test PDF
3. Check browser console for errors
4. Check backend logs for processing

## Troubleshooting

### Stub Mode Still Showing

**Check:**
1. `.env` file has `USE_STUBS=false`
2. Backend was restarted after changing `.env`
3. No environment variable override in deployment platform
4. Check `/health/info` endpoint response

**Fix:**
```bash
# Verify env var is set
cd apps/api
python -c "from app.config import settings; print(f'USE_STUBS: {settings.USE_STUBS}')"

# Should print: USE_STUBS: False
```

### UTF-8 Error Still Happening

**Check backend logs for exact error location:**
```bash
# Look for the exact line causing the error
# The fix was applied to validate.py form parsing
# But error might be in file processing
```

**If error persists:**
- Check file encoding of uploaded documents
- Verify form data is being sent correctly
- Check if error happens during OCR processing

### Google OCR Not Working

**Check:**
1. Service account JSON file path is correct and absolute
2. File permissions allow reading
3. Service account has "Document AI API User" role
4. Processor ID matches the one in Google Cloud Console
5. Location matches processor location

**Test:**
```bash
cd apps/api
python docai_smoketest.py
```

**Common errors:**
- `FileNotFoundError`: Check `GOOGLE_APPLICATION_CREDENTIALS` path
- `Permission denied`: Check service account has correct role
- `Processor not found`: Verify Processor ID is correct

### ICC Rules Not Loading

**Check:**
1. Rules are uploaded to database or storage
2. `USE_JSON_RULES` matches your rules storage method
3. Ruleset is published/active
4. Domain and jurisdiction match

**Verify rules are loaded:**
```sql
-- Check database rules
SELECT COUNT(*) FROM rules WHERE domain = 'icc';

-- Check rulesets
SELECT * FROM rulesets WHERE domain = 'icc' AND status = 'active';
```

## Production Checklist

Before going live:

- [ ] `USE_STUBS=false` is set
- [ ] Google Cloud Document AI configured and tested
- [ ] AWS S3 bucket created and accessible
- [ ] Database migrations applied
- [ ] ICC rules uploaded and active
- [ ] Health endpoint shows all services OK
- [ ] Stub mode indicator not showing in UI
- [ ] Test file upload works end-to-end
- [ ] OCR processing works (not using stubs)
- [ ] Validation results are generated correctly

## Next Steps After Setup

1. **Test Full Flow:**
   - Upload export LC document
   - Verify OCR processing
   - Check validation results
   - Verify customs pack generation

2. **Monitor Logs:**
   - Watch for errors during processing
   - Check OCR success rate
   - Monitor storage uploads

3. **Performance:**
   - Check OCR processing time
   - Monitor database query performance
   - Verify S3 upload speeds

## Support

If issues persist:
1. Check backend logs: `apps/api/logs/`
2. Check browser console for frontend errors
3. Verify all environment variables are set correctly
4. Test each service individually (OCR, S3, Database)

