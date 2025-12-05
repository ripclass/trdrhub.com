# 📄 Shipping Doc Generator - Product Spec

## Overview
**Product Name:** TRDR Shipping Doc Generator  
**Tagline:** "Generate LC-compliant shipping documents in minutes"  
**Priority:** MEDIUM (Complements LCopilot nicely)  
**Estimated Dev Time:** 4-5 weeks  

---

## Problem Statement
After getting LC approved, exporters struggle to create compliant documents:
- Each document must match LC exactly
- Manual typing leads to errors
- Discrepancies cost $75-150 each
- No single tool generates all required docs
- Inconsistencies across documents cause rejections

## Solution
A unified document generator that:
- Creates all shipping documents from one data entry
- Pre-populates from LC requirements
- Ensures consistency across all documents
- Validates against UCP600/ISBP745
- Exports to PDF ready for bank submission

---

## Supported Documents

### Phase 1 (MVP)
| Document | Priority | Complexity |
|----------|----------|------------|
| Commercial Invoice | ⭐⭐⭐ | Low |
| Packing List | ⭐⭐⭐ | Low |
| Beneficiary Certificate | ⭐⭐ | Low |

### Phase 2
| Document | Priority | Complexity |
|----------|----------|------------|
| Bill of Exchange (Draft) | ⭐⭐⭐ | Medium |
| Certificate of Origin | ⭐⭐ | Medium |
| Shipping Instructions | ⭐⭐ | Low |

### Phase 3
| Document | Priority | Complexity |
|----------|----------|------------|
| Insurance Declaration | ⭐ | Medium |
| Inspection Request | ⭐ | Low |
| Weight Certificate | ⭐ | Low |

---

## User Flow

### Step 1: Import LC Data
```
┌───────────────────────────────────────────────────────────┐
│  📄 SHIPPING DOC GENERATOR                                │
│                                                           │
│  Start by importing your LC details:                      │
│                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ 📋 Paste   │  │ 📁 Upload  │  │ 🔗 From    │         │
│  │ MT700     │  │ LC PDF     │  │ LCopilot   │         │
│  └────────────┘  └────────────┘  └────────────┘         │
│                                                           │
│  Or enter manually:                                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ LC Number: [EXP2024112900001____]                   │ │
│  │ LC Date:   [28 Nov 2024____📅]                      │ │
│  │ Amount:    [USD ▼] [$500,000.00____]               │ │
│  │ Beneficiary: [Auto-filled or enter...]             │ │
│  │ Applicant:   [Auto-filled or enter...]             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│                              [Next: Enter Shipment →]     │
└───────────────────────────────────────────────────────────┘
```

### Step 2: Shipment Details
```
┌───────────────────────────────────────────────────────────┐
│  📄 SHIPMENT DETAILS                                      │
│                                                           │
│  📦 Goods (from LC):                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Line │ Description    │ Qty   │ Unit Price│ Amount │ │
│  ├──────┼────────────────┼───────┼───────────┼────────┤ │
│  │ 1    │ Cotton T-Shirts│ 30000 │ $8.50     │$255,000│ │
│  │ 2    │ Polo Shirts    │ 12000 │ $12.00    │$144,000│ │
│  │ 3    │ Jackets        │ 8500  │ $12.00    │$102,000│ │
│  ├──────┼────────────────┼───────┼───────────┼────────┤ │
│  │      │ TOTAL          │ 50500 │           │$501,000│ │
│  └─────────────────────────────────────────────────────┘ │
│  [+ Add Line Item]                                        │
│                                                           │
│  🚢 Shipping Details:                                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ B/L Number:     [MSKU7788990123____]                │ │
│  │ B/L Date:       [24 Sep 2024____📅]                 │ │
│  │ Vessel:         [MAERSK INFINITY____]               │ │
│  │ Voyage:         [V-2024-123____]                    │ │
│  │ Container:      [MSKU7788990____]                   │ │
│  │ Seal:           [ABC123456____]                     │ │
│  │ Port Loading:   [Chittagong, Bangladesh]            │ │
│  │ Port Discharge: [Shanghai, China]                   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📦 Packing Details:                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Total Cartons:  [1,850____]                         │ │
│  │ Gross Weight:   [20,400 KG____]                     │ │
│  │ Net Weight:     [18,950 KG____]                     │ │
│  │ CBM:            [145.5____]                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│                    [← Back]  [Generate Documents →]       │
└───────────────────────────────────────────────────────────┘
```

### Step 3: Select Documents
```
┌───────────────────────────────────────────────────────────┐
│  📄 SELECT DOCUMENTS TO GENERATE                          │
│                                                           │
│  Required by LC (46A):                                    │
│  ☑️ Commercial Invoice (3 originals)                     │
│  ☑️ Packing List (3 copies)                              │
│  ☑️ Certificate of Origin (1 original)                   │
│  ☑️ Beneficiary Certificate (1 original)                 │
│                                                           │
│  Optional:                                                │
│  ☐ Bill of Exchange / Draft                              │
│  ☐ Shipping Instructions                                 │
│  ☐ Weight Certificate                                    │
│                                                           │
│  📋 Document Settings:                                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Invoice Number:  [INV-2024-001____] (auto-suggest)  │ │
│  │ Invoice Date:    [24 Sep 2024____]                  │ │
│  │ Your Reference:  [PO-88776____]                     │ │
│  │ Shipping Marks:  [SHANGHAI FASHION / MADE IN BD]   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│                    [← Back]  [Preview Documents →]        │
└───────────────────────────────────────────────────────────┘
```

### Step 4: Preview & Validate
```
┌───────────────────────────────────────────────────────────┐
│  📄 DOCUMENT PREVIEW                                      │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  [Invoice] [Packing List] [CoO] [Ben.Cert]         │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐   │ │
│  │  │         COMMERCIAL INVOICE                  │   │ │
│  │  │                                             │   │ │
│  │  │  Invoice No: INV-2024-001                  │   │ │
│  │  │  Date: 24 September 2024                    │   │ │
│  │  │  L/C No: EXP2024112900001                  │   │ │
│  │  │                                             │   │ │
│  │  │  SELLER:                                    │   │ │
│  │  │  Dhaka Knitwear Exports Ltd                │   │ │
│  │  │  123 Export Zone, Dhaka, Bangladesh        │   │ │
│  │  │                                             │   │ │
│  │  │  BUYER:                                     │   │ │
│  │  │  Shanghai Fashion Import Co                │   │ │
│  │  │  456 Trade Center, Shanghai, China         │   │ │
│  │  │                                             │   │ │
│  │  │  ... [Preview continues]                   │   │ │
│  │  └─────────────────────────────────────────────┘   │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ✅ VALIDATION PASSED                                     │
│  ├── LC number matches ✓                                 │
│  ├── Beneficiary matches LC ✓                            │
│  ├── Amount within tolerance ✓                           │
│  ├── Goods description corresponds ✓                     │
│  └── All required fields present ✓                       │
│                                                           │
│  ⚠️ SUGGESTIONS:                                         │
│  • Consider adding HS codes to invoice                   │
│  • CoO consignee field is optional but recommended       │
│                                                           │
│  [📥 Download All as ZIP]  [📧 Email]  [🖨️ Print]       │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Document Templates

### Commercial Invoice
```
┌─────────────────────────────────────────────────────────────┐
│                    COMMERCIAL INVOICE                        │
│                                                              │
│  Invoice No: INV-2024-001                Date: 24 Sep 2024  │
│  L/C No: EXP2024112900001                L/C Date: 28 Nov 24│
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  SELLER/BENEFICIARY:           BUYER/APPLICANT:             │
│  Dhaka Knitwear Exports Ltd    Shanghai Fashion Import Co   │
│  123 Export Zone               456 Trade Center             │
│  Dhaka, Bangladesh             Shanghai, China              │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  NOTIFY PARTY:                 DELIVERY TERMS:              │
│  Shanghai Fashion Import Co    FOB CHITTAGONG               │
│  Same as buyer                                              │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  SHIPPING DETAILS:                                          │
│  Vessel: MAERSK INFINITY       Voyage: V-2024-123          │
│  Port of Loading: Chittagong, Bangladesh                    │
│  Port of Discharge: Shanghai, China                         │
│  Container: MSKU7788990        Seal: ABC123456             │
│  B/L No: MSKU7788990123        B/L Date: 24 Sep 2024       │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  DESCRIPTION OF GOODS                                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Item │ Description      │ HS Code  │ Qty   │ Unit $  │ │
│  ├──────┼──────────────────┼──────────┼───────┼─────────┤ │
│  │ 1    │ 100% Cotton      │ 6109.10  │ 30000 │ $8.50   │ │
│  │      │ T-Shirts M/L/XL  │          │ PCS   │         │ │
│  │      │ HS: 6109.10.00   │          │       │$255,000 │ │
│  ├──────┼──────────────────┼──────────┼───────┼─────────┤ │
│  │ 2    │ 100% Cotton Polo │ 6105.10  │ 12000 │ $12.00  │ │
│  │      │ Shirts S/M/L     │          │ PCS   │         │ │
│  │      │ HS: 6105.10.00   │          │       │$144,000 │ │
│  ├──────┼──────────────────┼──────────┼───────┼─────────┤ │
│  │ 3    │ Cotton Blend     │ 6201.12  │ 8500  │ $12.00  │ │
│  │      │ Jackets M/L/XL   │          │ PCS   │         │ │
│  │      │ HS: 6201.12.00   │          │       │$102,000 │ │
│  └──────┴──────────────────┴──────────┴───────┴─────────┘ │
│                                                              │
│  TOTAL QUANTITY: 50,500 PCS                                 │
│  TOTAL VALUE: USD 501,000.00 (FOB CHITTAGONG)              │
│  SAY: US DOLLARS FIVE HUNDRED ONE THOUSAND ONLY            │
│                                                              │
│  TOTAL CARTONS: 1,850       GROSS WT: 20,400 KG            │
│                              NET WT:   18,950 KG            │
│                                                              │
│  SHIPPING MARKS:                                            │
│  SHANGHAI FASHION                                           │
│  MADE IN BANGLADESH                                         │
│  CARTON NO. 1-1850                                         │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  AS PER PROFORMA INVOICE NO. PI-2024-001 DATED 15 NOV 2024 │
│  COUNTRY OF ORIGIN: BANGLADESH                              │
│                                                              │
│  WE CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT          │
│                                                              │
│  For Dhaka Knitwear Exports Ltd                             │
│                                                              │
│  _______________________                                    │
│  Authorized Signature                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Consistency Engine

```python
class ConsistencyValidator:
    """
    Ensures all documents have matching data
    """
    
    def validate_consistency(self, documents: List[Document]) -> ValidationResult:
        checks = []
        
        # Check 1: LC number on all docs
        lc_numbers = {doc.lc_number for doc in documents}
        if len(lc_numbers) > 1:
            checks.append(Error("LC numbers don't match across documents"))
        
        # Check 2: Beneficiary name consistency
        beneficiaries = {doc.beneficiary_name for doc in documents}
        if len(beneficiaries) > 1:
            checks.append(Error("Beneficiary names don't match"))
        
        # Check 3: Amounts match
        invoice = find_doc(documents, "invoice")
        packing_list = find_doc(documents, "packing_list")
        
        if invoice.total_quantity != packing_list.total_quantity:
            checks.append(Error("Quantity mismatch: Invoice vs Packing List"))
        
        # Check 4: Weights match (within tolerance)
        if abs(invoice.gross_weight - packing_list.gross_weight) > 0.03 * invoice.gross_weight:
            checks.append(Warning("Weight discrepancy > 3%"))
        
        # Check 5: Shipping marks identical
        marks = {doc.shipping_marks for doc in documents if doc.shipping_marks}
        if len(marks) > 1:
            checks.append(Error("Shipping marks differ across documents"))
        
        return ValidationResult(checks)
```

---

## Pricing Model

| Tier | Documents/Month | Price | Features |
|------|----------------|-------|----------|
| Free | 5 sets | $0 | Invoice, Packing List |
| Professional | 50 sets | $49/mo | + All documents, templates |
| Business | Unlimited | $99/mo | + Custom templates, API |

---

## MVP Features (Week 1-3) ✅ COMPLETE

- [x] Commercial Invoice generator
- [x] Packing List generator
- [x] LC data import (manual)
- [x] PDF export
- [x] Basic validation

## V2 Features (Week 4-5) ✅ COMPLETE

- [x] Beneficiary Certificate
- [x] Bill of Exchange
- [ ] MT700 import parser
- [ ] LCopilot integration
- [ ] Consistency validation

## V3 Features (Future)

- [ ] Certificate of Origin (Chamber formats)
- [ ] Custom templates
- [x] Multi-currency
- [ ] Digital signatures

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Document sets generated | 1,000 |
| Paid subscribers | 40 |
| Validation errors caught | 500+ |
| Time saved per set | 2+ hours |

