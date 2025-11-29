# 📝 LC Application Builder - Product Spec

## Overview
**Product Name:** TRDR LC Application Builder  
**Tagline:** "Create bank-ready LC applications in minutes"  
**Priority:** HIGH (Extends LCopilot ecosystem)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
Exporters struggle to create LC applications:
- Each bank has different forms
- Fields are confusing (MT700 terminology)
- Errors lead to amendments ($75+ each)
- No templates for common trade routes

## Solution
A **guided wizard** that creates perfect LC applications:
- Step-by-step form with explanations
- Smart defaults based on trade route
- Auto-populates from previous LCs
- Exports to bank-specific formats

---

## User Flow

### Step 1: Basic Details
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 1 of 6 │
│                                                           │
│  BASIC DETAILS                                            │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  LC Type:                                                 │
│  ○ Irrevocable Documentary Credit (most common)          │
│  ○ Standby Letter of Credit (SBLC)                       │
│  ○ Revolving Credit                                       │
│  ○ Transferable Credit                                    │
│                                                           │
│  Currency & Amount:                                       │
│  [USD ▼] [$____________]                                 │
│                                                           │
│  ☑️ Include tolerance? [± 5% ▼]                          │
│     💡 Allows flexibility for quantity/amount             │
│                                                           │
│                              [Continue →]                 │
└───────────────────────────────────────────────────────────┘
```

### Step 2: Parties
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 2 of 6 │
│                                                           │
│  PARTIES                                                  │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  👤 Applicant (Buyer - You)                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Company: [Your Company Name____________]            │ │
│  │ Address: [_________________________________]        │ │
│  │          [_________________________________]        │ │
│  │ Country: [Select ▼]                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│  [📋 Load from saved profiles]                           │
│                                                           │
│  🏭 Beneficiary (Seller)                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Company: [Supplier Company Name________]            │ │
│  │ Address: [_________________________________]        │ │
│  │          [_________________________________]        │ │
│  │ Country: [Select ▼]                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│  [🔍 Search previous beneficiaries]                      │
│                                                           │
│  🏦 Advising Bank (Optional)                             │
│  [Search by SWIFT code or name...]                       │
│                                                           │
│                    [← Back]  [Continue →]                 │
└───────────────────────────────────────────────────────────┘
```

### Step 3: Shipment Details
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 3 of 6 │
│                                                           │
│  SHIPMENT DETAILS                                         │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  📍 Port of Loading:                                      │
│  [Search port... e.g., Shanghai, Chittagong]             │
│                                                           │
│  📍 Port of Discharge:                                    │
│  [Search port...]                                         │
│                                                           │
│  📅 Latest Shipment Date:                                │
│  [Select date 📅]                                        │
│  💡 Allow enough time for production & booking           │
│                                                           │
│  🚢 Shipment Terms (Incoterms 2020):                     │
│  [FOB ▼] [Port of Loading ▼]                            │
│                                                           │
│  ☐ Partial Shipments Allowed                             │
│  ☐ Transhipment Allowed                                  │
│  💡 Usually allow both for flexibility                   │
│                                                           │
│                    [← Back]  [Continue →]                 │
└───────────────────────────────────────────────────────────┘
```

### Step 4: Goods Description
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 4 of 6 │
│                                                           │
│  GOODS DESCRIPTION                                        │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  📦 Description of Goods:                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 100% COTTON KNITWEAR                                │ │
│  │ - T-SHIRTS: 30,000 PCS                             │ │
│  │ - POLO SHIRTS: 12,000 PCS                          │ │
│  │ - JACKETS: 8,500 PCS                               │ │
│  │ AS PER PROFORMA INVOICE NO. PI-2024-001            │ │
│  │ DATED 15 NOVEMBER 2024                              │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💡 Tips:                                                │
│  • Be specific but not overly restrictive                │
│  • Include reference to PI/Contract                      │
│  • Avoid brand names unless required                     │
│                                                           │
│  📋 HS Code (optional):                                  │
│  [Search HS code...] → Opens HS Code Calculator          │
│                                                           │
│                    [← Back]  [Continue →]                 │
└───────────────────────────────────────────────────────────┘
```

### Step 5: Documents Required
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 5 of 6 │
│                                                           │
│  DOCUMENTS REQUIRED                                       │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  📑 Standard Documents (recommended):                    │
│  ☑️ Commercial Invoice (3 originals)                     │
│  ☑️ Full Set Clean On Board Bill of Lading               │
│  ☑️ Packing List (3 copies)                              │
│                                                           │
│  📑 Additional Documents:                                │
│  ☐ Certificate of Origin (Chamber of Commerce)           │
│  ☐ Insurance Certificate/Policy (110% CIF value)         │
│  ☐ Inspection Certificate (SGS/Bureau Veritas)          │
│  ☐ Fumigation Certificate                                │
│  ☐ Beneficiary Certificate                               │
│  ☐ Weight Certificate                                    │
│  ☐ Quality Certificate                                   │
│                                                           │
│  📑 Custom Document:                                     │
│  [+ Add custom document requirement]                     │
│                                                           │
│  💡 Template: [Bangladesh RMG ▼] [China Electronics ▼]  │
│                                                           │
│                    [← Back]  [Continue →]                 │
└───────────────────────────────────────────────────────────┘
```

### Step 6: Payment & Validity
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION BUILDER                    Step 6 of 6 │
│                                                           │
│  PAYMENT TERMS & VALIDITY                                │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  💳 Payment Terms:                                       │
│  ○ At Sight (immediate payment)                          │
│  ○ Usance: [30 ▼] days from [B/L Date ▼]               │
│  ○ Deferred Payment                                      │
│                                                           │
│  📅 LC Expiry Date:                                      │
│  [Select date 📅]                                        │
│  💡 Should be at least 21 days after latest shipment    │
│                                                           │
│  📍 Expiry Place:                                        │
│  [Beneficiary's Country ▼]                               │
│  💡 Usually beneficiary's country for their convenience │
│                                                           │
│  ⏱️ Presentation Period:                                 │
│  [21 ▼] days after shipment                             │
│  💡 21 days is UCP600 default                           │
│                                                           │
│  🔒 Confirmation:                                        │
│  ○ Without (cheaper)                                     │
│  ○ May Add (advising bank's option)                      │
│  ○ Confirm (beneficiary requests confirmation)           │
│                                                           │
│                    [← Back]  [Review Application →]      │
└───────────────────────────────────────────────────────────┘
```

### Review & Export
```
┌───────────────────────────────────────────────────────────┐
│  📝 LC APPLICATION - REVIEW                               │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ LC SUMMARY                                          │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │ Type:         Irrevocable Documentary Credit        │ │
│  │ Amount:       USD 500,000.00 (+/- 5%)              │ │
│  │ Beneficiary:  Dhaka Knitwear Ltd, Bangladesh       │ │
│  │ Applicant:    Shanghai Fashion Co, China           │ │
│  │ Goods:        100% Cotton Knitwear                 │ │
│  │ Shipment:     Chittagong → Shanghai                │ │
│  │ Latest Ship:  15 Feb 2025                          │ │
│  │ Expiry:       28 Feb 2025 in Bangladesh            │ │
│  │ Payment:      At Sight                              │ │
│  │ Documents:    Invoice, B/L, Packing List, CoO      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ VALIDATION WARNINGS:                                 │
│  • Consider adding inspection cert for first-time vendor │
│  • Shipment-to-expiry gap is only 13 days (tight!)      │
│                                                           │
│  📤 Export Options:                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │ 📄 PDF     │ │ 🏦 HSBC    │ │ 🏦 Citi    │          │
│  │ Universal  │ │ Format     │ │ Format     │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │ 🏦 ICBC    │ │ 🏦 DBS     │ │ 📋 MT700   │          │
│  │ Format     │ │ Format     │ │ Text       │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│                                                           │
│  [💾 Save as Template] [📧 Email] [📤 Download]         │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Smart Features

### 1. Trade Route Templates
```
Pre-configured templates for common routes:
├── Bangladesh → USA (RMG exports)
├── China → Europe (Electronics)
├── India → UAE (Textiles, Food)
├── Vietnam → Japan (Garments)
├── Turkey → UK (Textiles)
└── [+ Create custom template]
```

### 2. Bank Format Library
```
Export to bank-specific formats:
├── HSBC Trade Transaction Form
├── Citi LC Application Form
├── Standard Chartered Template
├── ICBC Application Form
├── DBS TradeFinance Portal
├── Generic PDF
└── MT700 SWIFT format
```

### 3. Validation Engine
```
Before export, check for:
├── Date logic (shipment < expiry)
├── Document consistency
├── Incoterms vs insurance requirements
├── Port name validation
├── Missing critical fields
└── Potential discrepancy risks
```

---

## Technical Architecture

### Data Model
```typescript
interface LCApplication {
  id: string;
  status: "draft" | "submitted" | "approved";
  
  // Basic
  type: "documentary" | "standby" | "revolving" | "transferable";
  amount: { value: number; currency: string; tolerance?: string };
  
  // Parties
  applicant: Party;
  beneficiary: Party;
  advisingBank?: Bank;
  confirmingBank?: Bank;
  
  // Shipment
  portOfLoading: Port;
  portOfDischarge: Port;
  latestShipmentDate: Date;
  incoterms: string;
  partialShipments: boolean;
  transhipment: boolean;
  
  // Goods
  goodsDescription: string;
  hsCode?: string;
  
  // Documents
  documentsRequired: DocumentRequirement[];
  additionalConditions: string[];
  
  // Payment
  paymentTerms: "sight" | "usance" | "deferred";
  usanceDays?: number;
  usanceFrom?: "bl_date" | "invoice_date" | "presentation";
  
  // Validity
  expiryDate: Date;
  expiryPlace: string;
  presentationPeriod: number;
  confirmationInstructions: "without" | "may_add" | "confirm";
}
```

### API Endpoints
```
POST /api/lc-builder/create
GET  /api/lc-builder/:id
PUT  /api/lc-builder/:id
POST /api/lc-builder/:id/validate
POST /api/lc-builder/:id/export/:format
GET  /api/lc-builder/templates
POST /api/lc-builder/templates
```

---

## Pricing Model

| Tier | Applications/Month | Price | Features |
|------|-------------------|-------|----------|
| Free | 2 | $0 | Basic templates |
| Professional | 20 | $39/mo | All templates, bank formats |
| Business | Unlimited | $99/mo | + Team sharing, custom templates |
| Enterprise | Unlimited | Custom | + API, white-label |

**Bundle:** LCopilot + LC Builder = 25% discount

---

## Integration Points

### With LCopilot
```
LC Builder → LCopilot Flow:
1. Create LC application
2. Receive issued LC from bank
3. Upload LC to LCopilot for validation
4. LCopilot pre-populates expected values from Builder
5. Better validation accuracy!
```

### With Trade Finance Calculator
```
1. User creates LC application
2. Click "Estimate Costs"
3. Opens Calculator with pre-filled values
4. Shows expected bank fees
```

---

## MVP Features (Week 1-2)

- [ ] 6-step wizard UI
- [ ] Basic validation
- [ ] PDF export
- [ ] Save drafts

## V2 Features (Week 3-4)

- [ ] Bank-specific formats (HSBC, Citi)
- [ ] Trade route templates
- [ ] MT700 text export
- [ ] Beneficiary/Applicant profiles

## V3 Features (Future)

- [ ] Bank portal integration
- [ ] Amendment builder
- [ ] Team collaboration
- [ ] Version history

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Applications created | 500 |
| Exports generated | 300 |
| Paid subscribers | 50 |
| Template usage | 60% |

