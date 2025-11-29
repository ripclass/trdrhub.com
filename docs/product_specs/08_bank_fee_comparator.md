# 🏦 Bank Fee Comparator - Product Spec

## Overview
**Product Name:** TRDR Bank Fee Comparator  
**Tagline:** "Find the best bank for your trade finance needs"  
**Priority:** MEDIUM (Sticky tool, partnership revenue potential)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
Trade finance fees vary wildly between banks:
- Same LC can cost 0.5% at one bank, 2% at another
- Hidden fees (amendment, discrepancy, courier) add up
- No transparency in bank pricing
- SMEs don't know which bank to use

## Solution
A comparison tool showing:
- Estimated total cost across multiple banks
- Fee breakdown by category
- Bank ratings and reviews
- Lead generation to banks/brokers

---

## User Interface

### Input Screen
```
┌───────────────────────────────────────────────────────────┐
│  🏦 BANK FEE COMPARATOR                                   │
│                                                           │
│  Compare trade finance costs across banks                 │
│                                                           │
│  💰 TRANSACTION DETAILS                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Type:    [Letter of Credit ▼]                       │ │
│  │          [Bank Guarantee]                           │ │
│  │          [Documentary Collection]                   │ │
│  │          [Forfaiting]                               │ │
│  │                                                     │ │
│  │ Amount:  [USD ▼] [$500,000____]                    │ │
│  │ Tenor:   [At Sight ▼] [30 days] [60 days] [90 days]│ │
│  │ Validity: [90 days___]                              │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🌍 TRADE ROUTE                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Your Location:   [Singapore ▼]                      │ │
│  │ Counterparty:    [Bangladesh ▼]                     │ │
│  │ Need Confirmation? [Yes ▼]                          │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🏢 YOUR COMPANY                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Annual Trade Volume: [$1-5M ▼]                      │ │
│  │ Current Bank(s):     [DBS ▼] [+ Add]                │ │
│  │ Industry:            [Retail/Fashion ▼]             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│                    [ 🔍 Compare Banks ]                   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results Screen
```
┌───────────────────────────────────────────────────────────┐
│  🏦 BANK COMPARISON RESULTS                               │
│                                                           │
│  Transaction: USD 500,000 LC | 90 days | Singapore→BD    │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    TOTAL COST COMPARISON             │ │
│  │                                                     │ │
│  │  🥇 DBS Bank                                        │ │
│  │  ████████████░░░░░░░░░░  $1,850  (0.37%)          │ │
│  │  ⭐⭐⭐⭐⭐ 4.8  "Fast processing, good rates"       │ │
│  │                                                     │ │
│  │  🥈 OCBC Bank                                       │ │
│  │  █████████████░░░░░░░░░  $2,100  (0.42%)          │ │
│  │  ⭐⭐⭐⭐☆ 4.5  "Reliable, good for SMEs"          │ │
│  │                                                     │ │
│  │  🥉 UOB Bank                                        │ │
│  │  ██████████████░░░░░░░░  $2,350  (0.47%)          │ │
│  │  ⭐⭐⭐⭐☆ 4.3  "Strong BD correspondent network"  │ │
│  │                                                     │ │
│  │  Standard Chartered                                 │ │
│  │  ████████████████░░░░░░  $2,800  (0.56%)          │ │
│  │  ⭐⭐⭐⭐⭐ 4.7  "Premium service, higher fees"     │ │
│  │                                                     │ │
│  │  HSBC                                               │ │
│  │  █████████████████░░░░░  $3,100  (0.62%)          │ │
│  │  ⭐⭐⭐⭐☆ 4.4  "Global coverage, strict docs"     │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💰 POTENTIAL SAVINGS: Up to $1,250 (40%) vs most       │
│                        expensive option                   │
│                                                           │
│  [View Detailed Breakdown]  [📧 Get Quotes]               │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Detailed Breakdown
```
┌───────────────────────────────────────────────────────────┐
│  🏦 DBS BANK - DETAILED FEE BREAKDOWN                    │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Fee Type              │ Rate      │ Amount          │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ LC Issuance           │ 0.15% p.a.│ $187.50         │ │
│  │ LC Advising           │ 0.05%     │ $250.00         │ │
│  │ Confirmation          │ 0.40% p.a.│ $500.00         │ │
│  │ Negotiation           │ 0.10%     │ $500.00         │ │
│  │ Payment Commission    │ 0.05%     │ $250.00         │ │
│  │ SWIFT Charges         │ Flat      │ $75.00          │ │
│  │ Courier               │ Flat      │ $87.50          │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ SUBTOTAL              │           │ $1,850.00       │ │
│  └───────────────────────┴───────────┴─────────────────┘ │
│                                                           │
│  ⚠️ POTENTIAL ADDITIONAL FEES:                           │
│  • Amendment: $75 per amendment                          │
│  • Discrepancy: $100 per set (if any discrepancies)      │
│  • Extension: 0.10% per month                            │
│  • Cancellation: $150                                    │
│                                                           │
│  💡 DBS BENEFITS:                                        │
│  ✓ Strong Bangladesh correspondent network              │
│  ✓ Fast processing (typically 2-3 days)                 │
│  ✓ Online LC tracking portal                            │
│  ✓ Dedicated trade finance team for SMEs                │
│                                                           │
│  📋 REQUIREMENTS:                                        │
│  • Minimum relationship: SGD 100K deposit               │
│  • Account opening: 3-5 business days                   │
│  • Documents: ACRA, ID, address proof                   │
│                                                           │
│  [📞 Request Callback] [📧 Email Quote] [🌐 Visit Bank] │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Data Model

### Bank Fee Database
```typescript
interface BankProfile {
  id: string;
  name: string;
  country: string;
  swiftCode: string;
  tradefinanceRating: number; // 1-5
  reviewCount: number;
  
  lcFees: {
    issuance: FeeStructure;
    advising: FeeStructure;
    confirmation: FeeStructure;
    negotiation: FeeStructure;
    amendment: number; // flat
    discrepancy: number; // flat
    swift: number; // flat
    courier: number; // flat
  };
  
  guaranteeFees: {
    commission: FeeStructure;
    issuance: number;
  };
  
  collectionFees: {
    handling: FeeStructure;
    release: number;
  };
  
  minimumFees: {
    lc: number;
    guarantee: number;
    collection: number;
  };
  
  correspondentNetwork: {
    country: string;
    strength: "strong" | "moderate" | "limited";
  }[];
  
  requirements: {
    minimumDeposit: number;
    accountOpeningDays: number;
    documentsRequired: string[];
  };
  
  specialties: string[];
  limitations: string[];
}

interface FeeStructure {
  type: "percentage" | "flat" | "tiered";
  rate?: number; // for percentage
  amount?: number; // for flat
  tiers?: { upTo: number; rate: number }[]; // for tiered
  minimum?: number;
  maximum?: number;
  period?: "annual" | "quarterly" | "one_time";
}
```

### Sample Data
```json
{
  "dbs_singapore": {
    "name": "DBS Bank",
    "country": "SG",
    "swiftCode": "DBSSSGSG",
    "tradefinanceRating": 4.8,
    "lcFees": {
      "issuance": { "type": "percentage", "rate": 0.15, "period": "annual", "minimum": 150 },
      "advising": { "type": "percentage", "rate": 0.05, "minimum": 100 },
      "confirmation": { "type": "percentage", "rate": 0.40, "period": "annual", "minimum": 200 },
      "negotiation": { "type": "percentage", "rate": 0.10, "minimum": 150 },
      "amendment": 75,
      "discrepancy": 100,
      "swift": 75,
      "courier": 87.50
    },
    "correspondentNetwork": [
      { "country": "BD", "strength": "strong" },
      { "country": "CN", "strength": "strong" },
      { "country": "IN", "strength": "strong" }
    ]
  }
}
```

---

## Revenue Model

### 1. Lead Generation (Primary)
```
Bank pays TRDR for qualified leads:
- Quote request: $10-50 per lead
- Account opened: $100-500 per account
- Transaction completed: Revenue share (0.01-0.05%)
```

### 2. Premium Features
```
| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 3 comparisons/month |
| Pro | $29/mo | Unlimited, detailed breakdown |
| Business | $99/mo | + API, white-label |
```

### 3. Bank Listings
```
Banks pay for premium placement:
- Featured listing: $500/mo
- Enhanced profile: $200/mo
- Priority display: $300/mo
```

---

## Data Collection Strategy

### Phase 1: Manual Research
- Publicly available tariff sheets
- Mystery shopping
- User-submitted data (verified)

### Phase 2: Bank Partnerships
- Direct data feeds from partner banks
- API integrations
- Real-time rates

### Phase 3: Crowdsourced
- User transaction reports
- Verified fee receipts
- Community ratings

---

## MVP Features (Week 1-2)

- [ ] Basic comparison UI
- [ ] 5 major banks per region (SG, HK, UK, UAE, US)
- [ ] LC cost calculation
- [ ] Lead capture form

## V2 Features (Week 3-4)

- [ ] Bank Guarantees
- [ ] Collections
- [ ] Reviews/ratings
- [ ] Detailed breakdowns
- [ ] Email quotes

## V3 Features (Future)

- [ ] Real-time rate feeds
- [ ] Bank onboarding portal
- [ ] Transaction tracking
- [ ] API for partners

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Comparisons run | 5,000 |
| Quote requests | 500 |
| Bank partnerships | 5 |
| Lead revenue | $5,000/mo |

