# Exporter LC Upload Diagnostic Checklist

**Date:** 2025-01-27  
**Issue:** Exporter LC upload not working  
**Status:** Fixed - Real API call enabled

## What Was Fixed

### Frontend (`apps/web/src/pages/ExportLCUpload.tsx`)
- ✅ **Enabled real API call** - Removed mock jobId generation
- ✅ **Added proper userType** - Now sends `userType: "exporter"` and `workflowType: "export-lc-upload"`
- ✅ **Fixed navigation** - Uses real `jobId` from API response instead of mock
- ✅ **Error handling** - Properly handles quota exceeded and rate limit errors

### Backend (`apps/api/app/routers/validate.py`)
- ✅ **Create ValidationSession for exporter/importer** - Previously only created for bank users
- ✅ **Store exporter metadata** - LC number and workflow type stored in `extracted_data`
- ✅ **Proper jobId generation** - Uses ValidationSession ID as jobId for tracking

## How to Test

### 1. Basic Upload Flow
1. Navigate to `/lcopilot/exporter-dashboard?section=upload`
2. Enter an LC number (e.g., "BD-2024-001")
3. Upload at least one document (PDF, JPEG, PNG, or TIFF)
4. Select document type for each file
5. Click "Process LC" button
6. **Expected:** Should show "Validation In Progress" toast and redirect to `/lcopilot/results/{jobId}?lc={lcNumber}`

### 2. Verify Backend Processing
1. Check browser console for:
   - `✅ Validation started, jobId: {uuid}`
   - No errors in network tab
2. Check backend logs for:
   - ValidationSession created with `user_type: "exporter"`
   - `extracted_data` contains `lc_number` and `workflow_type`
   - Validation processing started

### 3. Verify Results Page
1. After upload, should redirect to `/lcopilot/results/{jobId}`
2. Results page should:
   - Display LC number from URL params
   - Show job status (processing/completed)
   - Display validation results when completed

### 4. Error Scenarios
- **Quota Exceeded:** Should show "Upgrade Required" toast with quota info
- **Rate Limit:** Should show rate limit notice
- **Invalid File:** Should show file validation error
- **No Files:** Should show "No Files Selected" error
- **No LC Number:** Should show "LC Number Required" error

## Common Issues & Solutions

### Issue: "Validation Failed" error
**Check:**
- Backend API is running and accessible
- User is authenticated (check auth token)
- Files are valid PDF/image formats
- LC number is provided

**Solution:**
- Check browser console for error details
- Check backend logs for validation errors
- Verify file formats are supported

### Issue: Navigation doesn't happen
**Check:**
- API response contains `jobId` or `job_id`
- No JavaScript errors in console
- Navigation timeout (1.5s) completes

**Solution:**
- Check API response structure matches expected format
- Verify `response.jobId || response.job_id` resolves correctly

### Issue: Results page shows "No jobId found"
**Check:**
- URL contains jobId parameter
- JobId format is valid UUID
- ValidationSession exists in database

**Solution:**
- Verify jobId is passed correctly in navigation
- Check database for ValidationSession with matching ID

## Database Verification

After successful upload, verify in database:

```sql
-- Check ValidationSession was created
SELECT id, user_id, company_id, status, extracted_data, created_at
FROM validation_sessions
WHERE user_id = '{your_user_id}'
ORDER BY created_at DESC
LIMIT 1;

-- Should show:
-- - status: 'processing' or 'completed'
-- - extracted_data: {"lc_number": "...", "user_type": "exporter", "workflow_type": "export-lc-upload"}
```

## API Endpoint Details

**Endpoint:** `POST /api/validate`  
**Content-Type:** `multipart/form-data`

**Form Fields:**
- `files`: Array of File objects
- `lc_number`: LC number string
- `notes`: Optional notes string
- `document_tags`: JSON string mapping filenames to document types
- `user_type`: "exporter" | "importer" | "bank"
- `workflow_type`: "export-lc-upload" | "draft-lc-risk" | "supplier-document-check"

**Response:**
```json
{
  "status": "ok",
  "results": [...],
  "job_id": "{uuid}",
  "jobId": "{uuid}",
  "quota": {...}
}
```

## Next Steps

1. ✅ **Fixed:** Real API call enabled
2. ✅ **Fixed:** Backend creates ValidationSession for exporter
3. ⏳ **To Test:** Full end-to-end flow with real documents
4. ⏳ **To Verify:** Results page displays correctly
5. ⏳ **To Monitor:** Error rates and user feedback

## Related Files

- `apps/web/src/pages/ExportLCUpload.tsx` - Upload UI component
- `apps/api/app/routers/validate.py` - Validation endpoint
- `apps/web/src/hooks/use-lcopilot.ts` - Validation hook
- `apps/web/src/pages/Results.tsx` - Results display page

