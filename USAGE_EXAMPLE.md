# Document Processing Endpoint Usage

## Overview

The `/documents/process-document` endpoint provides end-to-end document processing:

1. **Upload files** to S3 (or local storage in stub mode)
2. **Process with Google Cloud Document AI** (Form Parser processor)
3. **Save results** to PostgreSQL database
4. **Return structured JSON** with extracted text and fields

## API Endpoint

```
POST /documents/process-document
```

### Request Format

- **Content-Type**: `multipart/form-data`
- **Files**: 1-3 files (PDF, JPEG, PNG, TIFF)
- **Optional**: `session_id` form field to add to existing session

### Example Using curl

```bash
# Single document
curl -X POST http://localhost:8000/documents/process-document \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "files=@letter_of_credit.pdf"

# Multiple documents
curl -X POST http://localhost:8000/documents/process-document \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "files=@letter_of_credit.pdf" \
  -F "files=@commercial_invoice.pdf" \
  -F "files=@bill_of_lading.pdf"

# Add to existing session
curl -X POST http://localhost:8000/documents/process-document \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "files=@additional_document.pdf" \
  -F "session_id=550e8400-e29b-41d4-a716-446655440000"
```

### Example Using Python requests

```python
import requests

# Prepare files
files = [
    ('files', ('lc.pdf', open('lc.pdf', 'rb'), 'application/pdf')),
    ('files', ('invoice.pdf', open('invoice.pdf', 'rb'), 'application/pdf'))
]

# Make request
response = requests.post(
    'http://localhost:8000/documents/process-document',
    files=files,
    headers={'Authorization': 'Bearer YOUR_JWT_TOKEN'}
)

# Process response
if response.status_code == 200:
    data = response.json()
    print(f"Session ID: {data['session_id']}")
    print(f"Documents processed: {len(data['processed_documents'])}")

    for doc in data['processed_documents']:
        print(f"- {doc['document_type']}: {doc['ocr_confidence']:.3f} confidence")
        print(f"  Fields: {len(doc['extracted_fields'])}")
        print(f"  Text preview: {doc['extracted_text_preview'][:100]}...")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

## Response Format

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "processor_id": "42d3342d260e1bf2",
  "processed_documents": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "document_type": "letter_of_credit",
      "original_filename": "lc.pdf",
      "s3_url": "https://bucket.s3.region.amazonaws.com/uploads/session/lc.pdf",
      "s3_key": "uploads/session_id/letter_of_credit/file_id.pdf",
      "file_size": 1024768,
      "extracted_text_preview": "IRREVOCABLE DOCUMENTARY CREDIT This credit is subject to...",
      "extracted_fields": {
        "amount": {
          "value": "USD 100,000.00",
          "confidence": 0.95
        },
        "beneficiary": {
          "value": "ABC Trading Company",
          "confidence": 0.88
        },
        "expiry_date": {
          "value": "2024-12-31",
          "confidence": 0.92
        }
      },
      "ocr_confidence": 0.91,
      "page_count": 2,
      "entity_count": 15
    }
  ],
  "discrepancies": [],
  "processing_summary": {
    "total_files_processed": 1,
    "average_confidence": 0.91,
    "total_entities_extracted": 15,
    "total_pages_processed": 2,
    "processor_used": "42d3342d260e1bf2",
    "processing_completed_at": "2025-09-13T12:34:56.789Z"
  },
  "created_at": "2025-09-13T12:30:00.000Z"
}
```

## Document Type Detection

The system automatically determines document types based on:

1. **Filename patterns**:
   - `lc`, `letter`, `credit` → Letter of Credit
   - `invoice`, `inv` → Commercial Invoice
   - `bl`, `bill`, `lading`, `shipping` → Bill of Lading

2. **Upload order** (fallback):
   - 1st file → Letter of Credit
   - 2nd file → Commercial Invoice
   - 3rd file → Bill of Lading

## Error Handling

### Common Error Responses

```json
// No files provided
{
  "detail": "At least one file must be provided",
  "status_code": 400
}

// Too many files
{
  "detail": "Maximum 3 files allowed",
  "status_code": 400
}

// Unsupported file type
{
  "detail": "File type text/plain not supported. Use PDF, JPEG, PNG, or TIFF.",
  "status_code": 400
}

// S3 upload failure
{
  "detail": "Failed to process filename.pdf: S3 upload failed",
  "status_code": 500
}

// Document AI failure
{
  "detail": "Document AI processing failed: Permission denied",
  "status_code": 500
}
```

## Configuration

### Environment Variables

```bash
# Google Cloud Document AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_LOCATION=eu
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# AWS S3
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name

# Development mode (uses local storage)
USE_STUBS=true
```

## Testing

### Run the Test Suite

```bash
cd apps/api
python -m pytest tests/test_process_document.py -v
```

### Manual Testing Script

```bash
cd apps/api
python test_process_endpoint.py
```

### Quick Smoke Test

```bash
# Start the API server
cd apps/api
python main.py

# In another terminal, test with sample PDF
curl -X POST http://localhost:8000/documents/process-document \
  -F "files=@../../sample.pdf"
```

## Database Storage

Processed documents are stored in the `documents` table with:

- **File metadata**: filename, size, S3 location
- **OCR results**: extracted text, confidence scores
- **Structured data**: extracted fields as JSON
- **Processing info**: timestamps, processor used
- **Relationships**: linked to validation sessions and users

## Next Steps

1. **Authentication**: Add JWT token authentication
2. **Validation Rules**: Implement cross-document validation
3. **Discrepancy Detection**: Add Fatal Four validation rules
4. **Report Generation**: Create PDF reports with findings
5. **Webhooks**: Add async processing notifications