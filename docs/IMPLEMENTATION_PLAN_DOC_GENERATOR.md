# 📄 Shipping Doc Generator - Implementation Plan

> **Created:** December 5, 2024  
> **Estimated Effort:** 4-5 weeks  
> **Goal:** Generate LC-compliant shipping documents in minutes

---

## Executive Summary

Build a document generator that creates trade finance documents (Commercial Invoice, Packing List, Beneficiary Certificate, Bill of Exchange) from a single data entry, ensuring consistency and UCP600/ISBP compliance.

---

## Phase 1: MVP (Week 1-2)
**Goal:** Basic document generation with Commercial Invoice and Packing List

### Task 1.1: Database Models
**Effort:** 0.5 day

```python
# apps/api/app/models/doc_generator.py

class DocumentSet(Base):
    """A set of related shipping documents"""
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    company_id = Column(UUID, ForeignKey("companies.id"))
    
    # LC Reference
    lc_number = Column(String(100))
    lc_date = Column(Date)
    lc_amount = Column(Numeric)
    lc_currency = Column(String(3))
    
    # Parties
    beneficiary_name = Column(String(500))
    beneficiary_address = Column(Text)
    applicant_name = Column(String(500))
    applicant_address = Column(Text)
    notify_party = Column(Text)
    
    # Shipment
    vessel_name = Column(String(200))
    voyage_number = Column(String(50))
    bl_number = Column(String(100))
    bl_date = Column(Date)
    container_number = Column(String(50))
    seal_number = Column(String(50))
    port_of_loading = Column(String(200))
    port_of_discharge = Column(String(200))
    incoterms = Column(String(10))
    
    # Packing
    total_cartons = Column(Integer)
    gross_weight = Column(Numeric)
    net_weight = Column(Numeric)
    cbm = Column(Numeric)
    shipping_marks = Column(Text)
    
    # Metadata
    invoice_number = Column(String(100))
    invoice_date = Column(Date)
    status = Column(String(20))  # draft, generated, finalized
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class DocumentLineItem(Base):
    """Line items for a document set"""
    id = Column(UUID, primary_key=True)
    document_set_id = Column(UUID, ForeignKey("document_sets.id"))
    
    line_number = Column(Integer)
    description = Column(Text)
    hs_code = Column(String(20))
    quantity = Column(Integer)
    unit = Column(String(20))  # PCS, KG, MTR, etc.
    unit_price = Column(Numeric)
    total_price = Column(Numeric)
    
    # Packing details
    cartons = Column(Integer)
    carton_dimensions = Column(String(50))
    gross_weight = Column(Numeric)
    net_weight = Column(Numeric)


class GeneratedDocument(Base):
    """Generated PDF documents"""
    id = Column(UUID, primary_key=True)
    document_set_id = Column(UUID, ForeignKey("document_sets.id"))
    
    document_type = Column(String(50))  # invoice, packing_list, coo, draft
    file_path = Column(String(500))
    file_size = Column(Integer)
    generated_at = Column(DateTime)
    version = Column(Integer, default=1)
```

### Task 1.2: API Endpoints
**Effort:** 1 day

```python
# apps/api/app/routers/doc_generator.py

@router.post("/document-sets")
async def create_document_set(request: CreateDocumentSetRequest):
    """Create a new document set"""

@router.get("/document-sets")
async def list_document_sets(user):
    """List user's document sets"""

@router.get("/document-sets/{id}")
async def get_document_set(id):
    """Get document set details"""

@router.put("/document-sets/{id}")
async def update_document_set(id, request):
    """Update document set"""

@router.post("/document-sets/{id}/line-items")
async def add_line_item(id, request):
    """Add line item to document set"""

@router.post("/document-sets/{id}/generate")
async def generate_documents(id, document_types: List[str]):
    """Generate selected documents as PDFs"""

@router.get("/document-sets/{id}/download")
async def download_documents(id, format: str = "zip"):
    """Download generated documents"""
```

### Task 1.3: Frontend - Document Wizard
**Effort:** 2 days

```
/doc-generator/dashboard     - List of document sets
/doc-generator/new           - Create new set (wizard)
/doc-generator/edit/{id}     - Edit existing set
/doc-generator/preview/{id}  - Preview generated docs
```

### Task 1.4: Commercial Invoice PDF
**Effort:** 1.5 days

Using ReportLab (already installed):
- Professional layout matching spec
- Dynamic line items table
- Amount in words
- Signature block
- Company letterhead support

### Task 1.5: Packing List PDF
**Effort:** 1 day

Similar structure to invoice:
- Carton breakdown
- Weight totals
- Dimension details
- Shipping marks

---

## Phase 2: Additional Documents (Week 3)

### Task 2.1: Beneficiary Certificate
**Effort:** 0.5 day

Simple template with:
- Declaration text
- Signature block
- LC reference

### Task 2.2: Bill of Exchange (Draft)
**Effort:** 1 day

Financial instrument with:
- Drawer/Drawee
- Tenor (at sight, 30/60/90 days)
- Amount in words
- Maturity date

### Task 2.3: Consistency Validation
**Effort:** 1 day

Cross-document validation:
- LC numbers match
- Beneficiary names match
- Quantities match
- Weights within tolerance
- Amounts match

---

## Phase 3: Advanced Features (Week 4-5)

### Task 3.1: LCopilot Integration
- Import LC data from validated LCs
- Auto-populate document set

### Task 3.2: MT700 Parser
- Parse SWIFT MT700 text
- Extract LC fields automatically

### Task 3.3: Certificate of Origin
- Chamber of Commerce formats
- Country-specific templates

### Task 3.4: Custom Templates
- Upload company letterhead
- Brand colors
- Custom layouts

---

## Frontend Pages

```
apps/web/src/pages/tools/doc-generator/
├── index.ts                    # Exports
├── DocGeneratorLanding.tsx     # Landing page (existing)
├── DocGeneratorDashboard.tsx   # Dashboard with document sets
├── DocGeneratorLayout.tsx      # Sidebar layout
├── CreateDocumentWizard.tsx    # Step-by-step wizard
├── EditDocumentSet.tsx         # Edit existing set
├── DocumentPreview.tsx         # PDF preview
└── components/
    ├── LCDetailsForm.tsx       # Step 1: LC info
    ├── ShipmentDetailsForm.tsx # Step 2: Shipment info
    ├── LineItemsEditor.tsx     # Step 2: Goods table
    ├── PackingDetailsForm.tsx  # Step 2: Packing info
    ├── DocumentSelector.tsx    # Step 3: Select docs
    └── ValidationResults.tsx   # Validation display
```

---

## API Response Models

```python
class DocumentSetResponse(BaseModel):
    id: str
    lc_number: str
    beneficiary_name: str
    applicant_name: str
    total_amount: float
    currency: str
    status: str
    documents_generated: int
    created_at: str
    line_items: List[LineItemResponse]


class GenerateResponse(BaseModel):
    document_set_id: str
    documents: List[GeneratedDocumentInfo]
    validation_result: ValidationResult
    download_url: str
```

---

## Pricing Integration

| Tier | Documents/Month | Price |
|------|----------------|-------|
| Free | 5 sets | $0 |
| Professional | 50 sets | $49/mo |
| Business | Unlimited | $99/mo |

Track usage in `HubUsage.doc_sets_generated`

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Can create document set with LC details
- [ ] Can add line items
- [ ] Commercial Invoice PDF generates correctly
- [ ] Packing List PDF generates correctly
- [ ] Download as ZIP works

### Phase 2 Complete When:
- [ ] Beneficiary Certificate generates
- [ ] Bill of Exchange generates
- [ ] Consistency validation runs
- [ ] Validation errors displayed

### Phase 3 Complete When:
- [ ] LCopilot data import works
- [ ] MT700 parsing works
- [ ] Certificate of Origin generates

---

## Files to Create

### Backend
- `apps/api/app/models/doc_generator.py`
- `apps/api/app/routers/doc_generator.py`
- `apps/api/app/services/document_generator.py`
- `apps/api/alembic/versions/YYYYMMDD_add_doc_generator.py`

### Frontend
- `apps/web/src/pages/tools/doc-generator/` (multiple files)
- `apps/web/src/components/doc-generator/` (form components)

---

*Ready for implementation. Start with Task 1.1: Database Models*

