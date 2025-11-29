# 📨 SWIFT Message Decoder - Product Spec

## Overview
**Product Name:** TRDR SWIFT Decoder  
**Tagline:** "Decode any SWIFT message in seconds"  
**Priority:** MEDIUM (SEO Traffic Driver)  
**Estimated Dev Time:** 1 week  

---

## Problem Statement
Trade professionals receive SWIFT messages (MT700, MT707, MT760, etc.) from banks but:
- The format is cryptic (Field 45A, 46A, 47A...)
- No easy way to understand what each field means
- Copy-paste errors when extracting data
- Need to reference SWIFT documentation manually

## Solution
A **free online tool** to paste SWIFT messages and get:
- Human-readable breakdown
- Field-by-field explanation
- Extracted data in JSON/CSV
- Validation against SWIFT standards

---

## User Interface

### Input Screen
```
┌───────────────────────────────────────────────────────────┐
│  📨 SWIFT MESSAGE DECODER                                 │
│                                                           │
│  Paste your SWIFT message below:                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ :20:LC2024112900001                                 │ │
│  │ :31C:241128                                         │ │
│  │ :31D:250228SINGAPORE                                │ │
│  │ :50:DHAKA KNITWEAR EXPORTS LTD                     │ │
│  │ DHAKA BANGLADESH                                    │ │
│  │ :59:SHANGHAI FASHION IMPORT CO                     │ │
│  │ SHANGHAI CHINA                                      │ │
│  │ :32B:USD500000,00                                   │ │
│  │ :41D:ANY BANK                                       │ │
│  │ BY NEGOTIATION                                      │ │
│  │ :42C:SIGHT                                          │ │
│  │ :43P:ALLOWED                                        │ │
│  │ :44A:CHITTAGONG, BANGLADESH                        │ │
│  │ :44E:SHANGHAI, CHINA                                │ │
│  │ :44C:250215                                         │ │
│  │ :45A:100PCT COTTON KNITWEAR                        │ │
│  │ AS PER PROFORMA INV 2024-001                       │ │
│  │ :46A:+SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS    │ │
│  │ +FULL SET CLEAN ON BOARD B/L                       │ │
│  │ +PACKING LIST IN 3 COPIES                          │ │
│  │ :47A:ALL DOCUMENTS MUST INDICATE LC NUMBER        │ │
│  │ :48:21                                              │ │
│  │ :49:CONFIRM                                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  Message Type: [Auto-detect ▼] [MT700] [MT707] [MT760]   │
│                                                           │
│                    [ 🔍 Decode Message ]                  │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results Screen
```
┌───────────────────────────────────────────────────────────┐
│  📊 DECODED: MT700 - Issue of Documentary Credit         │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ SUMMARY                                             │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │ LC Number:      LC2024112900001                     │ │
│  │ Amount:         USD 500,000.00                      │ │
│  │ Beneficiary:    Dhaka Knitwear Exports Ltd         │ │
│  │ Applicant:      Shanghai Fashion Import Co         │ │
│  │ Expiry:         28 Feb 2025 in Singapore           │ │
│  │ Latest Ship:    15 Feb 2025                        │ │
│  │ Goods:          100% Cotton Knitwear               │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ FIELD BREAKDOWN                                     │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │                                                     │ │
│  │ Field 20 - Documentary Credit Number               │ │
│  │ Value: LC2024112900001                             │ │
│  │ 📝 Unique identifier assigned by issuing bank      │ │
│  │                                                     │ │
│  │ Field 31C - Date of Issue                          │ │
│  │ Value: 28 Nov 2024                                 │ │
│  │ 📝 Date the LC was issued (YYMMDD format)          │ │
│  │                                                     │ │
│  │ Field 31D - Date and Place of Expiry               │ │
│  │ Value: 28 Feb 2025 in SINGAPORE                    │ │
│  │ 📝 LC must be utilized by this date at this place  │ │
│  │                                                     │ │
│  │ Field 32B - Currency Code, Amount                  │ │
│  │ Value: USD 500,000.00                              │ │
│  │ 📝 Maximum amount available under this LC          │ │
│  │                                                     │ │
│  │ Field 41D - Available With ... By ...              │ │
│  │ Value: ANY BANK BY NEGOTIATION                     │ │
│  │ 📝 Freely negotiable at any bank                   │ │
│  │                                                     │ │
│  │ Field 42C - Drafts at ...                          │ │
│  │ Value: SIGHT                                       │ │
│  │ 📝 Payment due immediately upon compliant docs     │ │
│  │                                                     │ │
│  │ Field 43P - Partial Shipments                      │ │
│  │ Value: ALLOWED                                     │ │
│  │ 📝 Beneficiary may ship in multiple parts         │ │
│  │                                                     │ │
│  │ Field 44A - Port of Loading                        │ │
│  │ Value: CHITTAGONG, BANGLADESH                      │ │
│  │ 📝 Goods must be shipped from this port            │ │
│  │                                                     │ │
│  │ Field 44E - Port of Discharge                      │ │
│  │ Value: SHANGHAI, CHINA                             │ │
│  │ 📝 Goods destination port                          │ │
│  │                                                     │ │
│  │ Field 44C - Latest Date of Shipment                │ │
│  │ Value: 15 Feb 2025                                 │ │
│  │ 📝 B/L must be dated on or before this date       │ │
│  │                                                     │ │
│  │ Field 45A - Description of Goods/Services          │ │
│  │ Value: 100PCT COTTON KNITWEAR                      │ │
│  │        AS PER PROFORMA INV 2024-001                │ │
│  │ 📝 Invoice must match this description exactly     │ │
│  │                                                     │ │
│  │ Field 46A - Documents Required                     │ │
│  │ Value:                                             │ │
│  │   • SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS      │ │
│  │   • FULL SET CLEAN ON BOARD B/L                   │ │
│  │   • PACKING LIST IN 3 COPIES                      │ │
│  │ 📝 All these documents must be presented          │ │
│  │                                                     │ │
│  │ Field 47A - Additional Conditions                  │ │
│  │ Value: ALL DOCUMENTS MUST INDICATE LC NUMBER       │ │
│  │ 📝 Non-documentary conditions - review carefully   │ │
│  │                                                     │ │
│  │ Field 48 - Period for Presentation                 │ │
│  │ Value: 21 days                                     │ │
│  │ 📝 Docs must be presented within 21 days of B/L    │ │
│  │                                                     │ │
│  │ Field 49 - Confirmation Instructions               │ │
│  │ Value: CONFIRM                                     │ │
│  │ 📝 Advising bank is requested to add confirmation │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [ 📋 Copy as JSON ] [ 📥 Download CSV ] [ 📄 PDF ]      │
│                                                           │
│  💡 Want to validate this LC? Try LCopilot →            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Supported Message Types

### Phase 1 (MVP)
| Message | Description | Priority |
|---------|-------------|----------|
| **MT700** | Issue of Documentary Credit | ⭐⭐⭐ |
| **MT707** | Amendment to Documentary Credit | ⭐⭐⭐ |
| **MT760** | Demand Guarantee / SBLC | ⭐⭐ |

### Phase 2
| Message | Description | Priority |
|---------|-------------|----------|
| MT710 | Advice of Third Bank's Documentary Credit | ⭐⭐ |
| MT720 | Transfer of Documentary Credit | ⭐⭐ |
| MT730 | Acknowledgement | ⭐ |
| MT734 | Advice of Refusal | ⭐⭐ |
| MT740 | Authorization to Reimburse | ⭐ |
| MT747 | Amendment to Authorization to Reimburse | ⭐ |
| MT750 | Advice of Discrepancy | ⭐⭐ |
| MT752 | Authorization to Pay/Accept/Negotiate | ⭐⭐ |
| MT754 | Advice of Payment/Acceptance/Negotiation | ⭐ |
| MT756 | Advice of Reimbursement or Payment | ⭐ |

### Phase 3 (Collections)
| Message | Description | Priority |
|---------|-------------|----------|
| MT400 | Advice of Payment | ⭐ |
| MT410 | Acknowledgement | ⭐ |
| MT412 | Advice of Acceptance | ⭐ |
| MT416 | Advice of Non-Payment/Non-Acceptance | ⭐ |

---

## Field Reference Database

### MT700 Fields
```typescript
const MT700_FIELDS = {
  "20": {
    name: "Documentary Credit Number",
    mandatory: true,
    format: "16x",
    description: "Unique identifier assigned by the issuing bank",
    validation: "Must be unique within the bank"
  },
  "31C": {
    name: "Date of Issue",
    mandatory: true,
    format: "6!n (YYMMDD)",
    description: "The date the documentary credit was issued",
    validation: "Must be a valid date"
  },
  "31D": {
    name: "Date and Place of Expiry",
    mandatory: true,
    format: "6!n29x",
    description: "Expiry date and the place where the credit expires",
    validation: "Date must be after issue date"
  },
  "32B": {
    name: "Currency Code, Amount",
    mandatory: true,
    format: "3!a15d",
    description: "The currency and amount of the documentary credit",
    validation: "ISO 4217 currency code"
  },
  // ... all 50+ fields
};
```

### Export Formats

#### JSON Export
```json
{
  "messageType": "MT700",
  "parsed": {
    "documentaryCreditNumber": "LC2024112900001",
    "dateOfIssue": "2024-11-28",
    "expiryDate": "2025-02-28",
    "expiryPlace": "SINGAPORE",
    "beneficiary": {
      "name": "DHAKA KNITWEAR EXPORTS LTD",
      "address": "DHAKA BANGLADESH"
    },
    "applicant": {
      "name": "SHANGHAI FASHION IMPORT CO",
      "address": "SHANGHAI CHINA"
    },
    "amount": {
      "currency": "USD",
      "value": 500000.00
    },
    "availableWith": "ANY BANK",
    "availableBy": "NEGOTIATION",
    "draftsAt": "SIGHT",
    "partialShipments": "ALLOWED",
    "portOfLoading": "CHITTAGONG, BANGLADESH",
    "portOfDischarge": "SHANGHAI, CHINA",
    "latestShipmentDate": "2025-02-15",
    "goodsDescription": "100PCT COTTON KNITWEAR AS PER PROFORMA INV 2024-001",
    "documentsRequired": [
      "SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS",
      "FULL SET CLEAN ON BOARD B/L",
      "PACKING LIST IN 3 COPIES"
    ],
    "additionalConditions": [
      "ALL DOCUMENTS MUST INDICATE LC NUMBER"
    ],
    "presentationPeriod": 21,
    "confirmationInstructions": "CONFIRM"
  },
  "rawFields": {
    "20": "LC2024112900001",
    "31C": "241128",
    "31D": "250228SINGAPORE",
    // ... all raw fields
  }
}
```

---

## Technical Architecture

### Parser Logic
```python
class SWIFTParser:
    def parse(self, message: str) -> ParsedMessage:
        # 1. Detect message type from header
        msg_type = self._detect_type(message)
        
        # 2. Split into fields
        fields = self._extract_fields(message)
        
        # 3. Validate field formats
        validation = self._validate_fields(fields, msg_type)
        
        # 4. Transform to human-readable
        parsed = self._transform(fields, msg_type)
        
        return ParsedMessage(
            type=msg_type,
            fields=fields,
            parsed=parsed,
            validation=validation
        )
    
    def _extract_fields(self, message: str) -> Dict[str, str]:
        # Parse :XX: field patterns
        pattern = r':(\d{2}[A-Z]?):(.+?)(?=:\d{2}|$)'
        matches = re.findall(pattern, message, re.DOTALL)
        return {field: value.strip() for field, value in matches}
```

### API Endpoints
```
POST /api/swift/decode
{
  "message": "raw SWIFT message text",
  "type": "auto" | "MT700" | "MT707" | "MT760"
}

Response:
{
  "type": "MT700",
  "title": "Issue of Documentary Credit",
  "summary": { ... },
  "fields": [ ... ],
  "validation": { ... },
  "export": {
    "json": { ... },
    "csv": "..."
  }
}
```

---

## Lead Generation

### CTA Placements
1. **After decoding:** "Want to validate this LC? Try LCopilot →"
2. **Email results:** Capture email to send decoded message
3. **Download:** Require email for PDF export
4. **Embed widget:** Banks can embed on their sites (brand awareness)

### SEO Strategy
| Keyword | Volume | Competition |
|---------|--------|-------------|
| "MT700 decoder" | 500 | Low |
| "SWIFT message parser" | 400 | Low |
| "decode MT707" | 200 | Low |
| "MT760 format" | 300 | Low |
| "SWIFT field reference" | 600 | Medium |

---

## Pricing

**FREE** - Traffic driver, not a revenue product.

---

## MVP Features (Week 1)

- [ ] MT700 parser
- [ ] Field explanations
- [ ] JSON export
- [ ] Basic UI
- [ ] LCopilot CTA

## V2 Features (Week 2-3)

- [ ] MT707 parser
- [ ] MT760 parser
- [ ] PDF export
- [ ] Email results
- [ ] Validation warnings
- [ ] Embed widget

## V3 Features (Future)

- [ ] All MT7xx messages
- [ ] MT4xx (Collections)
- [ ] ISO 20022 converter
- [ ] API access
- [ ] Bulk processing

---

## Integration with LCopilot

```
SWIFT Decoder → LCopilot Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. User pastes MT700 in SWIFT Decoder                  │
│ 2. Gets decoded result                                  │
│ 3. Clicks "Validate this LC" →                         │
│ 4. Opens LCopilot with pre-filled LC data             │
│ 5. User uploads supporting docs                        │
│ 6. Full validation runs                                │
└─────────────────────────────────────────────────────────┘
```

---

## Success Metrics

| Metric | Target (Month 1) | Target (Month 6) |
|--------|------------------|------------------|
| Unique visitors | 1,000 | 10,000 |
| Decodes | 2,000 | 30,000 |
| LCopilot click-throughs | 50 | 1,000 |
| Email captures | 100 | 2,000 |

---

## Competitive Landscape

| Tool | Free? | MT700 | MT707 | MT760 | Export |
|------|-------|-------|-------|-------|--------|
| Paiementor | ❌ $$ | ✅ | ✅ | ✅ | ✅ |
| SWIFT Reference | ✅ | Docs only | Docs | Docs | ❌ |
| Bank tools | ❌ Internal | ✅ | ✅ | ❌ | ❌ |
| **TRDR Decoder** | ✅ | ✅ | ✅ | ✅ | ✅ |

**Opportunity:** No free, comprehensive SWIFT decoder exists!

