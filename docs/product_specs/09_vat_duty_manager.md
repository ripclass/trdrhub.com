# 💰 VAT & Duty Manager - Product Spec

## Overview
**Product Name:** TRDR VAT & Duty Manager  
**Tagline:** "Never miss a VAT refund or duty claim again"  
**Priority:** MEDIUM (High value for UK/EU exporters)  
**Estimated Dev Time:** 4-6 weeks  

---

## Problem Statement
Exporters lose money on VAT and duties:
- Complex VAT refund processes
- Missed duty relief opportunities
- Manual record-keeping errors
- Different rules per country
- Expiring claim deadlines

## Solution
A unified tool to:
- Track VAT paid on imports
- Calculate eligible refunds
- Generate VAT return data
- Monitor duty relief schemes
- Alert on claim deadlines

---

## Core Features

### 1. VAT Refund Tracker
```
┌───────────────────────────────────────────────────────────┐
│  💰 VAT REFUND TRACKER                                    │
│                                                           │
│  Summary (Jan - Dec 2024)                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Total VAT Paid:           £45,230.00                │ │
│  │ Claimed:                  £38,500.00                │ │
│  │ Pending Claims:           £4,230.00                 │ │
│  │ Unclaimed (expiring!):    £2,500.00  ⚠️            │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 Recent Transactions                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Date    │ Invoice    │ VAT Paid │ Status    │ Due   │ │
│  ├─────────┼────────────┼──────────┼───────────┼───────┤ │
│  │ Nov 15  │ INV-2024-89│ £1,200   │ ✅ Claimed│ -     │ │
│  │ Nov 10  │ INV-2024-88│ £850     │ 🟡 Pending│ Dec 1 │ │
│  │ Oct 28  │ INV-2024-85│ £2,500   │ ⚠️ Expiring│ Nov 30│ │
│  │ Oct 15  │ INV-2024-82│ £3,100   │ ✅ Claimed│ -     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📤 Export for VAT Return]  [📧 Set Alerts]             │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 2. Duty Relief Monitor
```
┌───────────────────────────────────────────────────────────┐
│  📦 DUTY RELIEF SCHEMES                                   │
│                                                           │
│  Your Eligible Schemes:                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ✅ Inward Processing Relief (IPR)                   │ │
│  │    Status: Active | Authorization: IPR/2024/001    │ │
│  │    Duty saved this year: £12,450                   │ │
│  │    Renewal due: 31 Mar 2025                        │ │
│  │                                                     │ │
│  │ ✅ Temporary Admission                              │ │
│  │    Status: Active | For exhibition goods           │ │
│  │    Re-export deadline: 15 Dec 2024  ⚠️             │ │
│  │                                                     │ │
│  │ 🔵 GSP (Generalized System of Preferences)         │ │
│  │    Eligible imports from: Bangladesh, Vietnam      │ │
│  │    Savings this year: £8,200                       │ │
│  │                                                     │ │
│  │ ⚪ FTA Preferences (Not utilized)                   │ │
│  │    You may be eligible for EU-UK TCA relief       │ │
│  │    [Learn More]                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 3. VAT Return Generator
```
┌───────────────────────────────────────────────────────────┐
│  📊 VAT RETURN GENERATOR                                  │
│                                                           │
│  Period: Q4 2024 (Oct - Dec)                             │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Box 1: VAT due on sales          │ £45,230.00      │ │
│  │ Box 2: VAT due on acquisitions   │ £0.00           │ │
│  │ Box 3: Total VAT due             │ £45,230.00      │ │
│  │ Box 4: VAT reclaimed on purchases│ £38,500.00      │ │
│  │ Box 5: Net VAT to pay/reclaim    │ £6,730.00 PAY   │ │
│  │ Box 6: Total value of sales      │ £226,150.00     │ │
│  │ Box 7: Total value of purchases  │ £192,500.00     │ │
│  │ Box 8: Total value of EU supplies│ £0.00           │ │
│  │ Box 9: Total value of EU acquis. │ £0.00           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  Supporting Documents:                                    │
│  📎 45 invoices attached                                 │
│  📎 12 import declarations linked                        │
│  📎 3 credit notes included                              │
│                                                           │
│  [📥 Download CSV] [📄 Export to Xero] [📤 Submit MTD]   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 4. Duty Calculator
```
┌───────────────────────────────────────────────────────────┐
│  🧮 IMPORT DUTY CALCULATOR                                │
│                                                           │
│  Product: Cotton T-Shirts                                 │
│  HS Code: 6109.10.00                                      │
│  Origin:  Bangladesh                                      │
│  Destination: United Kingdom                              │
│  CIF Value: £50,000                                       │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ DUTY CALCULATION                                    │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │                                                     │ │
│  │ Standard Duty Rate:     12%      £6,000.00         │ │
│  │                                                     │ │
│  │ 🎉 GSP ZERO PREFERENCE AVAILABLE!                  │ │
│  │ Bangladesh qualifies for GSP zero rate             │ │
│  │ Required: GSP Form A certificate                   │ │
│  │                                                     │ │
│  │ With GSP:              0%       £0.00              │ │
│  │ VAT (20%):                      £10,000.00         │ │
│  │                                                     │ │
│  │ TOTAL TO PAY:                   £10,000.00         │ │
│  │ YOU SAVE:                       £6,000.00 💰       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ Ensure CoO mentions "Wholly obtained" or            │
│     sufficient processing criteria met                   │
│                                                           │
│  [📋 Save Calculation] [🔗 Check Origin Rules]           │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Country Support

### Phase 1 (MVP)
| Country | VAT | Duty | Relief Schemes |
|---------|-----|------|----------------|
| 🇬🇧 UK | ✅ MTD ready | ✅ | IPR, TA, OPR |
| 🇸🇬 Singapore | ✅ GST | ✅ | MES, AIS |
| 🇦🇪 UAE | ✅ VAT | ✅ | FZ |

### Phase 2
| Country | VAT | Duty | Relief Schemes |
|---------|-----|------|----------------|
| 🇪🇺 EU (multi) | ✅ | ✅ | IPR, OPR, customs warehousing |
| 🇭🇰 Hong Kong | N/A | ✅ | Free port |
| 🇦🇺 Australia | ✅ GST | ✅ | TAFESA |

---

## Integrations

### Accounting Software
- Xero (export VAT data)
- QuickBooks
- Sage
- SAP Business One

### Customs Systems
- UK CHIEF/CDS
- Singapore TradeNet
- EU ICS2

### TRDR Ecosystem
- LCopilot (import invoice data)
- HS Code Calculator (duty rates)
- CustomsMate (declarations)

---

## Pricing Model

| Tier | Transactions/Mo | Price | Features |
|------|----------------|-------|----------|
| Free | 10 | $0 | Basic VAT tracking |
| Professional | 100 | $49/mo | + Duty calculator, alerts |
| Business | 500 | $149/mo | + MTD filing, integrations |
| Enterprise | Unlimited | Custom | + Multi-entity, API |

---

## MVP Features (Week 1-3)

- [ ] VAT transaction tracker
- [ ] UK VAT return generator
- [ ] Basic duty calculator
- [ ] Deadline alerts

## V2 Features (Week 4-6)

- [ ] Singapore GST
- [ ] UAE VAT
- [ ] Xero integration
- [ ] Relief scheme tracker
- [ ] MTD submission

## V3 Features (Future)

- [ ] EU multi-country
- [ ] Customs warehouse tracking
- [ ] Duty drawback claims
- [ ] AI receipt scanning

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Transactions tracked | 5,000 |
| VAT returns generated | 100 |
| Duty saved (identified) | £50,000 |
| Paid subscribers | 30 |

