# 📄 Doc Generator - Implementation Plan

> **Created:** December 5, 2024  
> **Based on:** Gap Analysis from Trade Specialist Assessment

---

## Executive Summary

This document outlines the implementation plan to transform the Doc Generator from a basic PDF template filler into a bank-grade shipping document management system.

---

## Phase 1: Make it Usable ✅ COMPLETED

**Duration:** 2 weeks  
**Status:** ✅ Completed December 5, 2024

### Tasks Completed

| Task | Status | Notes |
|------|--------|-------|
| Company Branding (Logo/Letterhead) | ✅ Done | `CompanyBranding` model, CRUD endpoints, settings page |
| LCopilot Integration | ✅ Done | Import endpoint, pre-fills from validated LC sessions |
| Document Consistency Validation | ✅ Done | `ConsistencyValidator` checks Invoice vs PL vs CoO |
| Certificate of Origin (Basic) | ✅ Done | `CertificateOfOriginGenerator` with chamber format |
| PDF Preview in Browser | ✅ Done | `PDFPreview` component with zoom controls |
| Duplicate Document Set | ✅ Done | Duplicate endpoint with auto-increment invoice number |

### Files Created/Modified

**Backend:**
- `apps/api/app/models/doc_generator.py` - Added `CompanyBranding`, `ValidationStatus`
- `apps/api/app/services/doc_validation.py` - NEW: LC & consistency validation
- `apps/api/app/services/document_generator.py` - Added CoO generator
- `apps/api/app/routers/doc_generator.py` - Added import, validate, duplicate, branding endpoints
- `apps/api/alembic/versions/20251205_add_doc_generator_phase1.py` - Migration

**Frontend:**
- `apps/web/src/pages/tools/doc-generator/ImportFromLCopilot.tsx` - NEW
- `apps/web/src/pages/tools/doc-generator/BrandingSettings.tsx` - NEW
- `apps/web/src/pages/tools/doc-generator/ValidationDisplay.tsx` - NEW
- `apps/web/src/pages/tools/doc-generator/PDFPreview.tsx` - NEW
- `apps/web/src/pages/tools/doc-generator/DocGeneratorDashboard.tsx` - Updated
- `apps/web/src/pages/tools/doc-generator/DocGeneratorLayout.tsx` - Updated

---

## Phase 2: Bank-Ready ✅ COMPLETED

**Duration:** 2 weeks  
**Status:** ✅ Completed December 5, 2024

### Tasks Completed

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | LC Tolerance Checking (UCP600 Art. 30) | ✅ Done | Part of Phase 1 validation |
| 2.2 | Document Storage to S3 | ✅ Done | `DocumentStorageService`, `StoredDocument` model |
| 2.3 | Audit Trail Logging | ✅ Done | `DocumentAuditLog`, `DocumentAuditService` |
| 2.4 | Template System | ✅ Done | `DocumentTemplate` model, `TemplatesPage` |
| 2.5 | Product Catalog | ✅ Done | `ProductCatalogItem` model, `ProductCatalogPage` |
| 2.6 | Buyer/Applicant Directory | ✅ Done | `BuyerProfile` model, `BuyerDirectoryPage` |

### Details

#### 2.1 LC Tolerance Checking
- Implement 5%/10% tolerance rules per UCP600 Article 30
- Warning when invoice approaches LC limit
- Error when exceeds tolerance
- Support "about"/"approximately" 10% rule

#### 2.2 Document Storage to S3
```python
# Store generated PDFs permanently
async def store_document(doc_set_id: str, doc_type: str, pdf_bytes: bytes):
    key = f"doc-generator/{doc_set_id}/{doc_type}_{timestamp}.pdf"
    await s3_client.upload(key, pdf_bytes)
    return key
```

#### 2.3 Audit Trail
```sql
CREATE TABLE document_audit_log (
    id UUID PRIMARY KEY,
    document_set_id UUID,
    user_id UUID,
    action VARCHAR(50),  -- created, updated, generated, downloaded, validated
    field_changed VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP
);
```

#### 2.4 Template System
- Save company defaults (beneficiary info, bank details)
- Save common applicant profiles
- Quick-fill from templates

#### 2.5 Product Catalog
- Save frequently shipped products
- Auto-fill HS codes and descriptions
- Default pricing per product

#### 2.6 Buyer Directory
- Store frequent buyers/applicants
- Include addresses, notify parties
- Quick-select when creating documents

### Files Created

**Backend:**
- `apps/api/app/models/doc_generator_catalog.py` - Audit, templates, products, buyers models
- `apps/api/app/services/document_storage.py` - S3 storage operations
- `apps/api/app/services/document_audit.py` - Audit logging service
- `apps/api/app/routers/doc_generator_catalog.py` - CRUD endpoints
- `apps/api/alembic/versions/20251205_add_doc_generator_phase2.py` - Migration

**Frontend:**
- `apps/web/src/pages/tools/doc-generator/TemplatesPage.tsx`
- `apps/web/src/pages/tools/doc-generator/ProductCatalogPage.tsx`
- `apps/web/src/pages/tools/doc-generator/BuyerDirectoryPage.tsx`

### Success Criteria
- [x] Documents validate against LC without manual checking
- [x] Document storage infrastructure ready (S3 service)
- [x] Full audit history schema and API
- [x] Templates reduce data entry time

---

## Phase 3: Industry Standard ✅ COMPLETED

**Duration:** 3 weeks  
**Status:** ✅ Completed December 5, 2024

### Tasks Completed

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Digital Signatures | ✅ Done | DocuSign, Adobe Sign, local draw/upload |
| 3.2 | Multi-Language Support | ✅ Done | 11 languages inc. Arabic, Chinese, RTL |
| 3.3 | Bank-Specific Formats | ✅ Done | SCB, HSBC, Citi, BB, SBI, HBL |
| 3.4 | GSP Form A / EUR.1 | ✅ Done | PDF generators with standard layouts |
| 3.5 | Export to Word/Excel | ✅ Done | DOCX and XLSX export service |
| 3.6 | Chamber of Commerce API | ✅ Done | Structure ready (needs API key) |

### Files Created

**Backend:**
- `apps/api/app/services/digital_signature.py` - DocuSign/Adobe/local signatures
- `apps/api/app/services/bank_format_registry.py` - Bank format requirements
- `apps/api/app/services/document_translation.py` - Multi-language translations
- `apps/api/app/services/certificate_generators.py` - GSP/EUR.1 generators
- `apps/api/app/routers/doc_generator_advanced.py` - Phase 3 API endpoints

**Frontend:**
- `apps/web/src/pages/tools/doc-generator/SignaturesPage.tsx`
- `apps/web/src/pages/tools/doc-generator/BankFormatsPage.tsx`
- `apps/web/src/pages/tools/doc-generator/CertificatesPage.tsx`

### Success Criteria
- [x] Digital signatures infrastructure ready
- [x] Multi-language support for 11 languages
- [x] Bank-specific format validation
- [x] GSP Form A and EUR.1 generation

---

## Environment Variables Required

```bash
# Phase 1 (Current) - No new variables needed

# Phase 2
AWS_S3_BUCKET_DOCUMENTS=trdr-documents
AWS_S3_REGION=us-east-1

# Phase 3
DOCUSIGN_API_KEY=
DOCUSIGN_ACCOUNT_ID=
ADOBE_SIGN_CLIENT_ID=
ADOBE_SIGN_CLIENT_SECRET=
FBCCI_API_KEY=          # Bangladesh Chamber
FPCCI_API_KEY=          # Pakistan Chamber
FIEO_API_KEY=           # India Export Federation
```

---

## API Endpoints Summary

### Phase 1 (Completed)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/doc-generator/import-from-lcopilot` | Import LC data |
| POST | `/api/doc-generator/document-sets/{id}/validate` | Validate against LC |
| POST | `/api/doc-generator/document-sets/{id}/duplicate` | Duplicate set |
| GET | `/api/doc-generator/document-sets/{id}/preview/{type}` | PDF preview |
| GET | `/api/doc-generator/branding` | Get company branding |
| PUT | `/api/doc-generator/branding` | Update branding |

### Phase 2 (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/doc-generator/templates` | Save template |
| GET | `/api/doc-generator/templates` | List templates |
| GET | `/api/doc-generator/audit-log/{doc_set_id}` | Get audit history |
| POST | `/api/doc-generator/catalog/products` | Add product |
| GET | `/api/doc-generator/catalog/products` | List products |
| POST | `/api/doc-generator/directory/buyers` | Add buyer |
| GET | `/api/doc-generator/directory/buyers` | List buyers |

### Phase 3 (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/doc-generator/sign/{doc_set_id}` | Digital signature |
| POST | `/api/doc-generator/translate/{doc_set_id}` | Translate document |
| POST | `/api/doc-generator/chamber/certify` | Chamber certification |

---

## Success Metrics

### Phase 1 (Achieved)
- ✅ Users can generate 5 document types
- ✅ LCopilot data imports correctly
- ✅ Validation errors shown before generation
- ✅ Company branding configurable

### Phase 2 (Target)
- [ ] 80% of documents pass validation on first try
- [ ] Templates reduce data entry by 50%
- [ ] Full audit trail for every document

### Phase 3 (Target)
- [ ] Bank acceptance rate > 95%
- [ ] Bilingual documents for 3 markets
- [ ] Chamber-certified CoOs in < 24 hours

---

## Pricing Evolution

| Phase | Features | Price Point |
|-------|----------|-------------|
| Phase 1 | Basic PDF generation, validation | $25/month |
| Phase 2 | Templates, storage, audit | $49/month |
| Phase 3 | Signatures, chambers, multi-lang | $99/month |

---

## Future Enhancements (Backlog)

After Phase 3, potential additions:
- [ ] Inspection Certificate (SGS, Bureau Veritas format)
- [ ] Fumigation Certificate
- [ ] Health/Phytosanitary Certificate
- [ ] Weight Certificate (port format)
- [ ] Insurance Certificate with policy integration
- [ ] Dangerous Goods Declaration
- [ ] ATA Carnet support
- [ ] Blockchain notarization
- [ ] AI-assisted goods description

---

*Document maintained by development team*  
*Last updated: December 5, 2024*
