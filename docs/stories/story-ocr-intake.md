---
id: story-ocr-intake
status: done
effort: M
risk: Low
owners: ["Ripon"]
links:
  code: ["glob://apps/api/app/ocr/", "glob://apps/api/ocr/"]
  docs: ["../prd/5-feature-specs.md#f1", "../architecture/2-components-and-dataflow.md"]
---

# Story: OCR Document Intake Pipeline

## BMAD Framework

### Background
SME exporters need to quickly upload and process Letter of Credit documents in various formats (PDF, JPG, PNG) to extract key data fields for compliance validation. The current manual process is slow and error-prone.

### Motivation
- **Business Value:** Enable 30-second document processing vs 2-5 day manual review
- **User Pain:** Complex documents with poor quality scans need reliable text extraction
- **Technical Driver:** Need scalable OCR pipeline to handle bank-scale document volumes

### Approach
Integrate Google DocumentAI for enterprise-grade OCR with async processing queue to handle large files without blocking the API. Store documents securely with lifecycle management and audit trails.

### Details
Implement FastAPI endpoints for multi-format file upload, async Celery workers for OCR processing, and PostgreSQL storage for extracted data with full audit logging.

## User Story

**As an** SME export manager
**I want to** upload LC documents in PDF, JPG, or PNG format
**So that** key fields are automatically extracted for compliance checking

## Acceptance Criteria

### Given-When-Then Scenarios

**AC1: Successful Document Upload**
```gherkin
Given I have a valid LC document (PDF, JPG, PNG) under 10MB
When I upload the document through the web interface
Then the file is accepted and processing begins immediately
And I receive a processing status indicator
And the upload completes within 5 seconds
```

**AC2: OCR Text Extraction**
```gherkin
Given a document has been uploaded successfully
When the OCR pipeline processes the document
Then key fields are extracted with >90% accuracy
And extracted data is stored in the database
And processing completes within 30 seconds
```

**AC3: Error Handling**
```gherkin
Given I upload an invalid file (wrong format, too large, corrupted)
When the system validates the file
Then I receive a clear error message
And the system suggests corrective actions
And no partial data is stored
```

**AC4: Security & Audit**
```gherkin
Given any document upload operation
When the action is performed
Then all actions are logged in the audit trail
And documents are encrypted at rest
And access is restricted by tenant isolation
```

## SM Checklist
- [ ] Document upload API endpoint implemented
- [ ] File validation (format, size, security)
- [ ] Google DocumentAI integration working
- [ ] Async processing with Celery queues
- [ ] PostgreSQL schema for extracted data
- [ ] Error handling and user feedback
- [ ] Security controls and audit logging
- [ ] Multi-tenant isolation enforced

## Dev Tasks

### Task 1: Upload API Implementation
- [ ] FastAPI endpoint `/api/v1/documents/upload`
- [ ] File validation middleware (format, size, security scan)
- [ ] Tenant isolation in upload path
- [ ] Error handling with user-friendly messages

### Task 2: OCR Service Integration
- [ ] Google DocumentAI client configuration
- [ ] Async Celery task for OCR processing
- [ ] Field extraction mapping (LC-specific fields)
- [ ] Retry logic for failed OCR attempts

### Task 3: Data Storage & Lifecycle
- [ ] PostgreSQL schema for documents and extracted data
- [ ] Document metadata storage
- [ ] File lifecycle management (retention policies)
- [ ] Cleanup automation for expired documents

### Task 4: Security Implementation
- [ ] Document encryption at rest
- [ ] Access control validation
- [ ] Audit trail for all document operations
- [ ] Secure file storage with proper permissions

## QA Test Plan

### Unit Tests
- [ ] File upload validation (format, size limits)
- [ ] OCR service integration with mock responses
- [ ] Database operations (insert, update, delete)
- [ ] Error handling for edge cases

### Integration Tests
- [ ] End-to-end upload to OCR processing
- [ ] Google DocumentAI real service testing
- [ ] Multi-tenant data isolation verification
- [ ] Audit trail completeness

### Performance Tests
- [ ] Large file upload (up to 10MB)
- [ ] Concurrent upload handling (100 users)
- [ ] OCR processing time measurement
- [ ] Memory usage during processing

### Security Tests
- [ ] File type validation bypass attempts
- [ ] Malicious file upload testing
- [ ] Cross-tenant data access attempts
- [ ] Audit log tampering verification

## Test Fixtures

### Golden Sample Documents
- `tests/fixtures/documents/valid_lc.pdf` - Standard LC document
- `tests/fixtures/documents/poor_quality.jpg` - Low-quality scan test
- `tests/fixtures/documents/large_file.pdf` - 10MB size limit test
- `tests/fixtures/documents/malformed.pdf` - Corrupted file test

### Expected Extraction Results
```json
{
  "lc_number": "LC2025-001234",
  "amount": "USD 50,000.00",
  "expiry_date": "2025-12-31",
  "beneficiary": "ABC Textiles Ltd",
  "applicant": "XYZ Importers Inc"
}
```

### Pass/Fail Criteria
- **PASS:** >90% field extraction accuracy on golden samples
- **PASS:** Processing time <30 seconds for standard documents
- **PASS:** Zero cross-tenant data leaks in isolation tests
- **FAIL:** Any security bypass or audit trail gaps

## Environment Variables
```bash
GOOGLE_CLOUD_PROJECT=lcopilot-prod
DOCUMENTAI_PROCESSOR_ID=abc123def456
DOCUMENTAI_LOCATION=us
CELERY_BROKER_URL=redis://localhost:6379/0
UPLOAD_MAX_SIZE=10485760  # 10MB
DOCUMENT_RETENTION_DAYS=7
```

## Code Paths
- **Upload API:** `apps/api/app/routers/documents.py`
- **OCR Service:** `apps/api/app/services/ocr_service.py`
- **Celery Tasks:** `apps/api/app/tasks/document_processing.py`
- **Models:** `apps/api/app/models/documents.py`
- **Tests:** `apps/api/tests/test_document_upload.py`

## Evidence of Completion
- ✅ Upload endpoint returns 200 with processing ID
- ✅ OCR extracts key fields from sample LC documents
- ✅ Documents encrypted and stored with audit trail
- ✅ Multi-tenant isolation verified through testing
- ✅ Performance targets met (<30 second processing)
- ✅ Security tests pass (no bypass vulnerabilities)

## Effort Estimation
- **Development:** 5 days (Medium complexity)
- **Testing:** 2 days
- **Documentation:** 1 day
- **Total:** 8 days

## Risk Assessment: Low
- **Technical Risk:** Google DocumentAI is proven technology
- **Integration Risk:** Well-documented APIs with good support
- **Performance Risk:** Async processing handles scale requirements
- **Security Risk:** Standard file upload security practices applied