# LCopilot Stub Mode

LCopilot includes a comprehensive stub mode that allows you to run the system end-to-end without requiring real AWS or Google Cloud credentials. This is perfect for local development, demos, and testing.

## Quick Start

1. **Enable Stub Mode**:
   ```bash
   export USE_STUBS=true
   # or set in .env file: USE_STUBS=true
   ```

2. **Start the API**:
   ```bash
   cd apps/api
   python main.py
   ```

3. **Start the Frontend**:
   ```bash
   cd apps/web
   npm run dev
   ```

4. **Look for the Stub Indicator**: The frontend will show a yellow badge in the bottom-right corner indicating stub mode is active.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_STUBS` | `false` | Enable/disable stub mode |
| `STUB_SCENARIO` | `lc_happy.json` | Which scenario file to use |
| `STUB_FAIL_OCR` | `false` | Simulate OCR failures |
| `STUB_FAIL_STORAGE` | `false` | Simulate storage failures |
| `STUB_DATA_DIR` | `./stubs` | Directory containing scenario files |
| `STUB_UPLOAD_DIR` | `/tmp/lcopilot_uploads` | Local file storage directory |

### Available Scenarios

#### `lc_happy.json` - Perfect Validation
- **Use case**: Demo successful LC validation
- **Expected result**: No discrepancies, all documents consistent
- **Documents**: LC + Invoice + Bill of Lading with matching data

#### `lc_mismatch.json` - Fatal Four Violations
- **Use case**: Test all validation rules
- **Expected result**: 8 discrepancies (2 critical, 6 major)
- **Violations**:
  - Invoice date after LC expiry (critical)
  - Invoice amount exceeds LC amount (critical)
  - Different parties across documents (major)
  - Port mismatches between documents (major)

#### `lc_expired.json` - Critical Date Failure
- **Use case**: Test expired LC handling
- **Expected result**: 1 critical discrepancy
- **Issue**: LC expired in December 2023

## What's Stubbed

### OCR Services
- **Real**: Google Document AI (primary) + AWS Textract (fallback)
- **Stub**: Returns predefined extracted fields from JSON scenarios
- **Realistic**: Includes confidence scores, processing delays, bounding boxes

### Storage Services  
- **Real**: AWS S3 with pre-signed URLs
- **Stub**: Local filesystem storage with fake URLs served by FastAPI
- **Files**: Stored in `/tmp/lcopilot_uploads/{session_id}/{document_type}/`

## Testing Different Scenarios

### Switch Scenarios
```bash
export STUB_SCENARIO=lc_mismatch.json
# Restart API to apply changes
```

### Test Error Conditions
```bash
# Simulate OCR failures
export STUB_FAIL_OCR=true

# Simulate storage failures  
export STUB_FAIL_STORAGE=true
```

### Monitor Stub Status
```bash
# Check current configuration
curl http://localhost:8000/health/stub-status

# List available scenarios
curl http://localhost:8000/health/stub-scenarios
```

## Adding New Scenarios

1. **Create JSON file** in `apps/api/stubs/`:
   ```json
   {
     "scenario_name": "My Test Case",
     "description": "Custom scenario for testing XYZ",
     "documents": [
       {
         "document_type": "letter_of_credit",
         "ocr_confidence": 0.95,
         "processing_time_ms": 1200,
         "extracted_fields": [
           {
             "field_name": "lc_amount",
             "field_type": "amount", 
             "value": "100000.00",
             "confidence": 0.98
           }
         ]
       }
     ],
     "expected_discrepancies": 0,
     "tags": ["custom", "test"]
   }
   ```

2. **Set environment variable**:
   ```bash
   export STUB_SCENARIO=my-test-case.json
   ```

3. **Restart the API** to load the new scenario.

## End-to-End Testing

### Happy Path Test
```bash
export USE_STUBS=true
export STUB_SCENARIO=lc_happy.json
# Upload documents → Should show 0 discrepancies
```

### Validation Error Test  
```bash
export STUB_SCENARIO=lc_mismatch.json
# Upload documents → Should show 8 discrepancies
```

### System Error Test
```bash
export STUB_FAIL_OCR=true
# Upload documents → Should show OCR processing error
```

## Production Toggle

To switch back to real services:
```bash
export USE_STUBS=false
# Ensure AWS/GCP credentials are configured
```

## File Structure

```
apps/api/
├── stubs/                    # Scenario JSON files
│   ├── lc_happy.json
│   ├── lc_mismatch.json
│   └── lc_expired.json
├── app/
│   ├── stubs/               # Stub implementation code
│   │   ├── models.py        # Pydantic models for scenarios
│   │   ├── ocr_stub.py      # Stub OCR adapter
│   │   └── storage_stub.py  # Stub S3 service
│   ├── config.py           # Environment configuration
│   └── routers/
│       ├── health.py       # Health/monitoring endpoints
│       └── fake_s3.py      # File serving for stub mode
└── /tmp/lcopilot_uploads/  # Local file storage (created automatically)
```

This stub system ensures LCopilot can run completely offline while providing realistic behavior for development and testing.