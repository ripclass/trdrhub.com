# Document Extraction Debugging Guide

## Problem

The frontend is showing:
- `extraction_status: "empty"`
- `extracted_data: {}`
- No text extracted from uploaded documents

## What Was Done

### 1. Enhanced Logging

Added comprehensive diagnostic logging throughout the extraction pipeline with emoji prefixes for easy scanning:

- 🔍 Starting extraction
- ✓ Success (e.g., "✓ Read 125,432 bytes", "✓ pdfminer extracted 5,432 characters")
- ✗ Failure (e.g., "✗ pdfminer extraction failed")
- ⚠ Warning (e.g., "⚠ pdfminer returned empty text")
- ❌ Critical failure (e.g., "❌ ALL extraction methods failed")

### 2. Logging Points

The logs now show:
1. File reading (`Read N bytes from filename`)
2. pdfminer extraction attempt (success/empty/failure)
3. PyPDF2 extraction attempt (success/empty/failure, with page count)
4. OCR fallback decision (`OCR_ENABLED`, `OCR_PROVIDER_ORDER`, page count)
5. OCR provider attempts (health check, timeout, success/failure)
6. Final status (success with character count OR failure with summary)

### 3. Created Test Script

`apps/api/test_extraction_debug.py` - Run this locally to test extraction:

```bash
cd apps/api
python test_extraction_debug.py path/to/document.pdf
```

## How to Diagnose

### Step 1: Check Render Logs

After the next deployment (triggered by the git push), check the Render logs for a validation attempt:

```
Look for these log patterns:

🔍 Starting text extraction for: invoice.pdf (type: application/pdf)
✓ Read 125432 bytes from invoice.pdf
  → Trying pdfminer extraction...
  ⚠ pdfminer returned empty text for invoice.pdf
  → Trying PyPDF2 extraction...
  ⚠ PyPDF2 returned empty text for invoice.pdf (3 pages)
  → Text extraction returned empty, attempting OCR fallback...
     OCR_ENABLED: True
     OCR_PROVIDER_ORDER: ['gdocai', 'textract']
     Page count: 3
  → Attempting OCR with providers: ['gdocai', 'textract']
  ✗ OCR extraction returned empty
❌ ALL extraction methods failed for invoice.pdf
   Summary: pdfminer=empty, PyPDF2=empty, OCR=attempted
   File details: content-type=application/pdf, size=125432 bytes
```

### Step 2: Identify the Failure Point

Based on the logs, determine which method failed:

#### Scenario A: pdfminer/PyPDF2 returned empty
**Cause**: Document is likely a scanned image (no embedded text)
**Solution**: OCR should kick in

#### Scenario B: OCR not enabled
**Log**: `⚠ OCR is DISABLED (OCR_ENABLED=False)`
**Solution**: Set `OCR_ENABLED=true` in Render env vars

#### Scenario C: OCR providers failing
**Log**: `OCR provider google_documentai health check failed` or `OCR provider google_documentai failed: ...`
**Cause**: Missing credentials or misconfiguration
**Solution**: Check Google Cloud / AWS credentials

#### Scenario D: File reading fails
**Log**: `✗ Failed to read file invoice.pdf: ...`
**Cause**: Upload issue or file corruption
**Solution**: Check file upload mechanism

### Step 3: Check Environment Variables

In Render dashboard, verify these are set:

**Required for OCR:**
- `OCR_ENABLED=true`
- `OCR_PROVIDER_ORDER=gdocai,textract` (or your preferred order)

**For Google Document AI:**
- `GOOGLE_CLOUD_PROJECT` (your GCP project ID)
- `GOOGLE_DOCUMENTAI_LOCATION` (e.g., "us")
- `GOOGLE_DOCUMENTAI_PROCESSOR_ID` (your processor ID)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` (service account JSON as string)

**For AWS Textract:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (e.g., "us-east-1")

### Step 4: Test Locally (Optional)

If you have access to the problematic PDF:

```bash
cd apps/api
# Set up environment variables
export GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type": "service_account", ...}'
export OCR_ENABLED=true

# Run test script
python test_extraction_debug.py /path/to/problem.pdf
```

This will show exactly which extraction method works/fails.

## Common Fixes

### Fix 1: Enable OCR

```bash
# In Render dashboard, add/update:
OCR_ENABLED=true
```

### Fix 2: Configure Google Document AI

1. Go to Google Cloud Console
2. Enable Document AI API
3. Create a processor (Document OCR)
4. Create a service account with Document AI permissions
5. Generate JSON key
6. Add to Render:
   ```
   GOOGLE_APPLICATION_CREDENTIALS_JSON=<paste entire JSON here>
   GOOGLE_CLOUD_PROJECT=<your-project-id>
   GOOGLE_DOCUMENTAI_PROCESSOR_ID=<processor-id>
   GOOGLE_DOCUMENTAI_LOCATION=us
   ```

### Fix 3: Use AWS Textract Instead

```bash
# In Render dashboard:
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_REGION=us-east-1
OCR_PROVIDER_ORDER=textract,gdocai
```

### Fix 4: Increase OCR Limits

If documents are being skipped:

```bash
OCR_MAX_PAGES=100  # Default: 50
OCR_MAX_BYTES=104857600  # 100MB (default: 50MB)
OCR_TIMEOUT_SEC=120  # Default: 60
```

## Expected Behavior After Fix

Once OCR is properly configured, logs should show:

```
🔍 Starting text extraction for: invoice.pdf
✓ Read 125432 bytes from invoice.pdf
  → Trying pdfminer extraction...
  ⚠ pdfminer returned empty text for invoice.pdf
  → Trying PyPDF2 extraction...
  ⚠ PyPDF2 returned empty text for invoice.pdf (3 pages)
  → Text extraction returned empty, attempting OCR fallback...
  → Attempting OCR with providers: ['gdocai', 'textract']
  ✓ OCR extraction successful: 4523 characters
✅ Extraction complete for invoice.pdf: 4523 characters
```

And the frontend will show:
- `extraction_status: "success"` or `"partial"`
- `extracted_data: { lc: {...}, invoice: {...}, ... }`
- Document OCR Overview with status="success" for each document

## Next Steps

1. **Wait for Render deployment** (~2-3 minutes after git push)
2. **Upload documents** in the exporter dashboard
3. **Check Render logs** for the extraction attempt
4. **Identify failure point** based on log patterns above
5. **Apply appropriate fix** (enable OCR, configure credentials, etc.)
6. **Re-test** after fix is applied

## Troubleshooting

### "No logs appearing"

- Check Render deployment status
- Ensure deployment succeeded
- Try uploading a document to trigger validation
- Look for "🔍 Starting text extraction" in logs

### "OCR health check failed"

- Verify credentials are correctly set
- Check quotas in Google Cloud / AWS console
- Test credentials with a simple API call

### "Still getting empty results"

- Check if files are actually PDFs (not images renamed to .pdf)
- Try a different OCR provider
- Test with a simple text-based PDF first
- Run the debug script locally to isolate the issue

## Contact

If extraction is still failing after following this guide, provide:
1. Render logs showing the extraction attempt
2. Environment variable configuration (redact sensitive values)
3. Sample document (if possible)
4. Error messages from the logs

