# 🔒 Audit Trail & Digital Locker - Product Spec

## Overview
**Product Name:** TRDR Vault  
**Tagline:** "Your trade documents, secured and organized"  
**Priority:** MEDIUM (Compliance value, stickiness)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
Traders struggle with document management:
- Documents scattered across emails, drives, systems
- Can't prove compliance history (audit risk)
- No version control (which is the latest?)
- Searching for old LCs takes hours
- Bank/customs audits are stressful

## Solution
A secure document vault with:
- Organized storage by transaction
- Complete audit trail
- Version history
- Search and retrieval
- Compliance reporting

---

## Core Features

### 1. Document Vault Dashboard
```
┌───────────────────────────────────────────────────────────┐
│  🔒 TRDR VAULT                                            │
│                                                           │
│  📊 Storage Overview                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Used: 2.3 GB of 10 GB  │  Transactions: 156       │  │
│  │ ██████████░░░░░░░░░░░  │  Documents: 1,247        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  🔍 [Search documents...________________________] 🔎     │
│                                                           │
│  📁 RECENT TRANSACTIONS                    [+ New Folder] │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 📂 LC-2024-156 | Shanghai Fashion | $500K | Nov 24│ │
│  │    └── 12 documents                                │ │
│  │                                                     │ │
│  │ 📂 LC-2024-155 | Mumbai Textiles | $320K | Nov 20 │ │
│  │    └── 9 documents                                 │ │
│  │                                                     │ │
│  │ 📂 LC-2024-154 | Dhaka Knitwear | $450K | Nov 15  │ │
│  │    └── 14 documents                                │ │
│  │                                                     │ │
│  │ 📂 LC-2024-153 | Vietnam Elec. | $280K | Nov 10   │ │
│  │    └── 8 documents                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📅 QUICK FILTERS:                                       │
│  [This Month] [This Quarter] [This Year] [All Time]      │
│  [LCs] [Guarantees] [Collections] [Customs]              │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 2. Transaction Folder
```
┌───────────────────────────────────────────────────────────┐
│  📂 LC-2024-156 | Shanghai Fashion Import Co              │
│                                                           │
│  LC Number: EXP2024112900001                             │
│  Amount: USD 500,000                                      │
│  Status: ✅ Completed | Paid: 25 Nov 2024                │
│                                                           │
│  📋 DOCUMENTS (12)                                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Category          │ Document           │ Uploaded   │ │
│  ├───────────────────┼────────────────────┼────────────┤ │
│  │ 📄 LC             │                    │            │ │
│  │  └── LC_original  │ LC_EXP2024.pdf     │ 01 Nov     │ │
│  │  └── LC_amendment │ LC_AMD1.pdf        │ 10 Nov     │ │
│  │                   │                    │            │ │
│  │ 📄 Commercial     │                    │            │ │
│  │  └── Invoice      │ INV-2024-001.pdf   │ 20 Nov     │ │
│  │  └── Packing List │ PL-2024-001.pdf    │ 20 Nov     │ │
│  │                   │                    │            │ │
│  │ 📄 Transport      │                    │            │ │
│  │  └── B/L Original │ BL_MSKU123.pdf     │ 22 Nov     │ │
│  │  └── B/L Copy     │ BL_MSKU123_copy.pdf│ 22 Nov     │ │
│  │                   │                    │            │ │
│  │ 📄 Origin         │                    │            │ │
│  │  └── CoO          │ COO_2024-156.pdf   │ 21 Nov     │ │
│  │                   │                    │            │ │
│  │ 📄 Banking        │                    │            │ │
│  │  └── Discrepancy  │ DISC_notice.pdf    │ 23 Nov     │ │
│  │  └── Payment Adv. │ SWIFT_payment.pdf  │ 25 Nov     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📤 Upload] [📥 Download All] [🔗 Share] [📋 Audit Log] │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 3. Audit Trail View
```
┌───────────────────────────────────────────────────────────┐
│  📋 AUDIT TRAIL | LC-2024-156                            │
│                                                           │
│  Complete history of all actions on this transaction     │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Timestamp           │ User    │ Action              │ │
│  ├─────────────────────┼─────────┼─────────────────────┤ │
│  │ 25 Nov 14:32       │ System  │ Payment confirmed   │ │
│  │ 25 Nov 10:15       │ John    │ Uploaded payment    │ │
│  │                     │         │ advice              │ │
│  │ 23 Nov 16:45       │ System  │ Validation passed   │ │
│  │ 23 Nov 16:40       │ Mary    │ Ran LCopilot check │ │
│  │ 23 Nov 11:20       │ John    │ Uploaded discrepancy│ │
│  │                     │         │ notice from bank    │ │
│  │ 22 Nov 09:30       │ Mary    │ Uploaded B/L        │ │
│  │ 21 Nov 14:15       │ Mary    │ Uploaded CoO        │ │
│  │ 20 Nov 11:00       │ John    │ Uploaded Invoice &  │ │
│  │                     │         │ Packing List        │ │
│  │ 10 Nov 16:30       │ John    │ Uploaded LC         │ │
│  │                     │         │ amendment           │ │
│  │ 01 Nov 09:00       │ Mary    │ Created transaction │ │
│  │ 01 Nov 09:00       │ Mary    │ Uploaded original LC│ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📥 Export Audit Log]  [🖨️ Print]  [📧 Email Report]   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 4. Document Version History
```
┌───────────────────────────────────────────────────────────┐
│  📄 VERSION HISTORY | Commercial_Invoice.pdf              │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Version │ Uploaded By │ Date       │ Notes         │ │
│  ├─────────┼─────────────┼────────────┼───────────────┤ │
│  │ v3 ⭐   │ John        │ 22 Nov     │ Final signed  │ │
│  │ v2      │ John        │ 21 Nov     │ Corrected amt │ │
│  │ v1      │ Mary        │ 20 Nov     │ Initial draft │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⭐ = Current version                                    │
│                                                           │
│  [View v3]  [Compare v2↔v3]  [Restore v2]               │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 5. Compliance Report
```
┌───────────────────────────────────────────────────────────┐
│  📊 COMPLIANCE REPORT                                     │
│                                                           │
│  Period: 01 Jan 2024 - 30 Nov 2024                       │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ SUMMARY                                             │ │
│  │                                                     │ │
│  │ Total Transactions:     156                        │ │
│  │ Total Value:            $18.5M                     │ │
│  │ Documents Stored:       1,247                      │ │
│  │                                                     │ │
│  │ Compliance Rate:        98.7%                      │ │
│  │ - All docs on file:     154/156                   │ │
│  │ - Complete audit trail: 156/156                   │ │
│  │                                                     │ │
│  │ ⚠️ Attention Needed:                               │ │
│  │ - 2 transactions missing CoO                      │ │
│  │ - 1 transaction > 7 years (archive?)             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 DOCUMENT RETENTION STATUS                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Doc Type        │ Required │ On File │ Status      │ │
│  ├─────────────────┼──────────┼─────────┼─────────────┤ │
│  │ LCs             │ 156      │ 156     │ ✅ 100%     │ │
│  │ Invoices        │ 156      │ 156     │ ✅ 100%     │ │
│  │ B/Ls            │ 156      │ 156     │ ✅ 100%     │ │
│  │ CoO             │ 156      │ 154     │ ⚠️ 98.7%   │ │
│  │ Customs Entries │ 156      │ 155     │ ⚠️ 99.4%   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📥 Download Full Report]  [📧 Schedule Monthly Report] │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Storage
- AWS S3 / Azure Blob (encrypted at rest)
- Multi-region replication
- 7+ year retention
- Automatic archival to cold storage

### Security
- AES-256 encryption
- Access control (role-based)
- MFA for sensitive operations
- Immutable audit log (blockchain-anchored optional)

### Data Model
```typescript
interface Transaction {
  id: string;
  type: "lc" | "guarantee" | "collection" | "customs";
  reference: string; // LC number, etc.
  counterparty: string;
  amount: { value: number; currency: string };
  status: TransactionStatus;
  dates: {
    created: Date;
    completed?: Date;
    archived?: Date;
  };
  documents: Document[];
  auditLog: AuditEntry[];
}

interface Document {
  id: string;
  name: string;
  category: DocumentCategory;
  version: number;
  mimeType: string;
  size: number;
  hash: string; // SHA-256 for integrity
  uploadedBy: string;
  uploadedAt: Date;
  metadata: Record<string, any>;
  versions: DocumentVersion[];
}

interface AuditEntry {
  timestamp: Date;
  userId: string;
  userName: string;
  action: AuditAction;
  details: Record<string, any>;
  ipAddress: string;
  userAgent: string;
}
```

---

## Auto-Filing Rules

```
Documents are automatically filed based on:
├── File name patterns
│   └── "INV", "Invoice" → Commercial/Invoice
│   └── "BL", "B/L", "Bill of Lading" → Transport/B/L
│   └── "LC", "Letter of Credit" → LC Documents
│
├── TRDR ecosystem integration
│   └── LCopilot uploads → auto-categorized
│   └── CustomsMate declarations → Customs folder
│
└── AI classification (future)
    └── Analyze document content
    └── Suggest category
```

---

## Pricing Model

| Tier | Storage | Price | Features |
|------|---------|-------|----------|
| Free | 1 GB | $0 | Basic storage, 30-day history |
| Starter | 10 GB | $19/mo | Audit trail, 1-year retention |
| Professional | 50 GB | $49/mo | Version history, 7-year retention |
| Business | 200 GB | $99/mo | Team access, compliance reports |
| Enterprise | Unlimited | Custom | Custom retention, API |

---

## Integration Points

### Auto-Upload from TRDR Products
```
LCopilot → Vault:
- LC documents uploaded
- Validation results stored
- Discrepancy reports filed

CustomsMate → Vault:
- Customs declarations archived
- Entry confirmations stored
- Duty payment receipts

Shipping Tracker → Vault:
- B/L copies linked
- Delivery confirmations
```

---

## MVP Features (Week 1-2)

- [ ] Document upload and storage
- [ ] Transaction folders
- [ ] Basic audit trail
- [ ] Search functionality

## V2 Features (Week 3-4)

- [ ] Version history
- [ ] Compliance reports
- [ ] Auto-filing rules
- [ ] Team access controls
- [ ] Email-to-upload

## V3 Features (Future)

- [ ] AI document classification
- [ ] Blockchain-anchored audit
- [ ] External sharing (banks, auditors)
- [ ] Retention policy automation
- [ ] OCR search inside documents

---

## Compliance Value Proposition

### Regulatory Requirements
- UK HMRC: 6 years retention
- US CBP: 5 years retention
- EU Customs: 7 years retention
- Banks (AML): 7+ years retention

### Audit Readiness
```
When auditor asks: "Show me all LCs from 2022 with X supplier"

Without TRDR Vault:
- Search emails (2 hours)
- Check old drives (1 hour)
- Ask colleagues (30 mins)
- Compile manually (1 hour)
= 4.5 hours

With TRDR Vault:
- Search "2022 + X supplier" (10 seconds)
- Export zip (30 seconds)
= 1 minute
```

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Documents stored | 10,000 |
| Active transactions | 500 |
| Compliance reports | 50 |
| Paid subscribers | 40 |

