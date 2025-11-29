# 💱 Trade Finance Calculator - Product Spec

## Overview
**Product Name:** TRDR Trade Finance Calculator  
**Tagline:** "Know your costs before you commit"  
**Priority:** HIGH (Lead Generation Magnet)  
**Estimated Dev Time:** 1-2 weeks  

---

## Problem Statement
Exporters don't know the true cost of trade finance until they ask their bank:
- LC issuance fees vary wildly (0.1% to 2%+)
- Hidden charges (amendment, discrepancy, courier)
- No easy way to compare options
- Forfaiting/discounting rates are opaque

## Solution
A **free calculator** that estimates trade finance costs across scenarios:
- LC costs (issuance, confirmation, negotiation)
- Discounting/forfaiting rates
- Bank guarantee costs
- Collections (D/P, D/A) costs

**Business Model:** Free tool → Lead capture → Upsell LCopilot

---

## Calculator Modules

### Module 1: LC Cost Estimator
```
┌───────────────────────────────────────────────────────────┐
│  💳 LC COST CALCULATOR                                    │
│                                                           │
│  LC Amount:        [$ 100,000      ▼]                    │
│  Currency:         [USD ▼]                                │
│  LC Validity:      [90 days ▼]                           │
│  Payment Terms:    [At Sight ▼] [30 Days ▼] [60 Days ▼]  │
│                                                           │
│  Issuing Bank Region:     [Asia ▼]                       │
│  Confirming Bank Needed?  [Yes ▼]                        │
│  Negotiation Required?    [Yes ▼]                        │
│                                                           │
│                    [ Calculate Costs ]                    │
│                                                           │
└───────────────────────────────────────────────────────────┘

                         ▼ RESULTS ▼

┌───────────────────────────────────────────────────────────┐
│  📊 ESTIMATED LC COSTS                                    │
│                                                           │
│  LC Amount:                          $100,000.00          │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Fee Type              │ Rate    │ Amount           │ │
│  ├───────────────────────┼─────────┼──────────────────┤ │
│  │ Issuance Fee          │ 0.15%   │ $150.00          │ │
│  │ Confirmation Fee      │ 0.50%   │ $500.00          │ │
│  │ Negotiation Fee       │ 0.125%  │ $125.00          │ │
│  │ SWIFT Charges         │ Flat    │ $50.00           │ │
│  │ Courier (est.)        │ Flat    │ $75.00           │ │
│  ├───────────────────────┼─────────┼──────────────────┤ │
│  │ TOTAL ESTIMATED       │         │ $900.00          │ │
│  │ % of LC Amount        │         │ 0.90%            │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ Potential Additional Costs:                          │
│  • Amendment fee: ~$50-100 per amendment                 │
│  • Discrepancy fee: ~$50-100 per discrepancy            │
│  • Late presentation: ~$75-150                           │
│                                                           │
│  💡 Pro Tip: Use LCopilot to avoid discrepancy fees!    │
│                                                           │
│  [ 📧 Email Results ] [ 🔗 Share ] [ Try LCopilot Free ] │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Module 2: Forfaiting Calculator
```
┌───────────────────────────────────────────────────────────┐
│  📈 FORFAITING CALCULATOR                                 │
│                                                           │
│  What is Forfaiting?                                      │
│  Sell your receivables at a discount for immediate cash   │
│                                                           │
│  Receivable Amount:    [$ 500,000     ]                  │
│  Currency:             [USD ▼]                            │
│  Days to Maturity:     [180 days      ]                  │
│  Obligor Bank:         [Tier 1 Bank ▼] [Tier 2 ▼] [Tier 3]│
│  Obligor Country:      [Germany ▼]                        │
│                                                           │
│                    [ Calculate ]                          │
│                                                           │
└───────────────────────────────────────────────────────────┘

                         ▼ RESULTS ▼

┌───────────────────────────────────────────────────────────┐
│  📊 FORFAITING ESTIMATE                                   │
│                                                           │
│  Receivable:                         $500,000.00          │
│  Maturity:                           180 days             │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Component             │ Rate      │ Amount          │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ Base Rate (SOFR)      │ 5.25%     │ -               │ │
│  │ Country Risk Margin   │ 0.50%     │ -               │ │
│  │ Bank Risk Margin      │ 0.25%     │ -               │ │
│  │ Forfaiter Margin      │ 0.75%     │ -               │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ All-in Discount Rate  │ 6.75% p.a.│ -               │ │
│  │ Discount Amount       │           │ $16,875.00      │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ YOU RECEIVE TODAY     │           │ $483,125.00     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💡 Compare: Holding to maturity earns $16,875 more     │
│     but ties up capital for 180 days.                    │
│                                                           │
│  [ 📧 Get Quote ] [ 🔗 Connect with Forfaiter ]          │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Module 3: Bank Guarantee Cost
```
┌───────────────────────────────────────────────────────────┐
│  🏦 BANK GUARANTEE CALCULATOR                             │
│                                                           │
│  Guarantee Type:    [Bid Bond ▼]                         │
│                     [Performance Guarantee]               │
│                     [Advance Payment Guarantee]           │
│                     [Retention Guarantee]                 │
│                                                           │
│  Amount:            [$ 50,000      ]                     │
│  Validity:          [365 days      ]                     │
│  Beneficiary Country: [Saudi Arabia ▼]                   │
│  Cash Margin Held:  [25% ▼]                              │
│                                                           │
│                    [ Calculate ]                          │
│                                                           │
└───────────────────────────────────────────────────────────┘

                         ▼ RESULTS ▼

┌───────────────────────────────────────────────────────────┐
│  📊 GUARANTEE COST ESTIMATE                               │
│                                                           │
│  Guarantee Amount:                   $50,000.00           │
│  Validity:                           365 days             │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Fee Component         │ Rate/Amt  │ Annual Cost     │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ Commission            │ 1.5% p.a. │ $750.00         │ │
│  │ Issuance Fee          │ Flat      │ $100.00         │ │
│  │ SWIFT/Courier         │ Flat      │ $50.00          │ │
│  ├───────────────────────┼───────────┼─────────────────┤ │
│  │ TOTAL COST            │           │ $900.00         │ │
│  │ Effective Rate        │ 1.8% p.a. │                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💰 Cash Margin: $12,500 (blocked in account)            │
│  📝 Note: URDG 758 format recommended for Saudi Arabia   │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Module 4: Collections Cost (D/P, D/A)
```
┌───────────────────────────────────────────────────────────┐
│  📄 DOCUMENTARY COLLECTION CALCULATOR                     │
│                                                           │
│  Collection Type:   [D/P (Documents against Payment) ▼]  │
│                     [D/A (Documents against Acceptance)]  │
│                                                           │
│  Invoice Amount:    [$ 75,000      ]                     │
│  Collecting Bank Country: [India ▼]                      │
│                                                           │
│                    [ Calculate ]                          │
│                                                           │
└───────────────────────────────────────────────────────────┘

                         ▼ RESULTS ▼

┌───────────────────────────────────────────────────────────┐
│  📊 COLLECTION COST ESTIMATE                              │
│                                                           │
│  Invoice Amount:                     $75,000.00           │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Fee Type              │ Rate    │ Amount            │ │
│  ├───────────────────────┼─────────┼───────────────────┤ │
│  │ Remitting Bank Fee    │ 0.10%   │ $75.00            │ │
│  │ Collecting Bank Fee   │ 0.15%   │ $112.50           │ │
│  │ Courier (estimate)    │ Flat    │ $50.00            │ │
│  ├───────────────────────┼─────────┼───────────────────┤ │
│  │ TOTAL                 │         │ $237.50           │ │
│  │ % of Invoice          │         │ 0.32%             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ Collections are CHEAPER than LC but NO BANK GUARANTEE│
│  📝 Governed by URC 522                                  │
│                                                           │
│  [ 📧 Email Results ] [ Compare with LC ]                │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Fee Data Structure
```typescript
interface BankFeeSchedule {
  region: "asia" | "europe" | "americas" | "mena" | "africa";
  bankTier: "tier1" | "tier2" | "tier3";
  
  lcFees: {
    issuance: { min: number; max: number; typical: number }; // % p.a.
    confirmation: { min: number; max: number; typical: number };
    negotiation: { min: number; max: number; typical: number };
    amendment: number; // flat fee
    discrepancy: number; // flat fee
    swift: number; // flat fee
    courier: number; // flat fee
  };
  
  guaranteeFees: {
    commission: { min: number; max: number; typical: number }; // % p.a.
    issuance: number; // flat fee
  };
  
  forfaitingMargins: {
    countryRisk: Record<string, number>; // by country
    bankRisk: Record<"tier1" | "tier2" | "tier3", number>;
    forfaiterMargin: number;
  };
}
```

### Sample Fee Database
```json
{
  "asia_tier1": {
    "lcFees": {
      "issuance": { "min": 0.10, "max": 0.25, "typical": 0.15 },
      "confirmation": { "min": 0.30, "max": 0.75, "typical": 0.50 },
      "negotiation": { "min": 0.10, "max": 0.15, "typical": 0.125 },
      "amendment": 75,
      "discrepancy": 75,
      "swift": 50,
      "courier": 75
    }
  },
  "mena_tier2": {
    "lcFees": {
      "issuance": { "min": 0.20, "max": 0.50, "typical": 0.30 },
      "confirmation": { "min": 0.75, "max": 1.50, "typical": 1.00 },
      "negotiation": { "min": 0.15, "max": 0.25, "typical": 0.20 }
    }
  }
}
```

### API Endpoints
```
POST /api/calculator/lc
POST /api/calculator/forfaiting
POST /api/calculator/guarantee
POST /api/calculator/collection

// Lead capture
POST /api/calculator/email-results
POST /api/calculator/request-quote
```

---

## Lead Generation Strategy

### Funnel
```
┌─────────────────────────────────────────────────────────┐
│                     AWARENESS                            │
│  SEO: "LC fees calculator", "trade finance costs"       │
│  Ads: Google, LinkedIn targeting trade managers         │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│                     INTEREST                             │
│  Free calculator - no signup required                   │
│  Results shown immediately                               │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│                     CAPTURE                              │
│  "Email me these results" → Capture email               │
│  "Get actual quote" → Capture company details           │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│                     CONVERT                              │
│  Email sequence:                                        │
│  Day 1: Results + LCopilot intro                       │
│  Day 3: "How to reduce discrepancy fees" blog          │
│  Day 7: LCopilot free trial offer                      │
│  Day 14: Case study + demo offer                        │
└─────────────────────────────────────────────────────────┘
```

### Email Capture Points
1. "📧 Email me these results"
2. "💬 Get actual quote from forfaiter"
3. "📊 Download full fee comparison PDF"
4. "🔔 Alert me when rates change"

---

## Pricing

**FREE** - This is a lead generation tool, not a revenue product.

Optional premium features:
- API access for bulk calculations
- Custom fee schedule upload
- White-label embed for banks/brokers

---

## MVP Features (Week 1)

- [ ] LC Cost Calculator
- [ ] Basic UI
- [ ] Email results
- [ ] LCopilot CTA

## V2 Features (Week 2)

- [ ] Forfaiting Calculator
- [ ] Bank Guarantee Calculator
- [ ] Collection Calculator
- [ ] Lead capture flow
- [ ] Email sequences

## V3 Features (Future)

- [ ] Compare multiple banks
- [ ] Real-time rate feeds
- [ ] Connect to forfaiter marketplace
- [ ] Embed widget for partners

---

## SEO Keywords

| Keyword | Monthly Volume | Competition |
|---------|----------------|-------------|
| "LC fees" | 2,400 | Medium |
| "letter of credit cost" | 1,900 | Medium |
| "bank guarantee fees" | 1,600 | Low |
| "forfaiting rates" | 800 | Low |
| "trade finance calculator" | 500 | Low |
| "documentary collection fees" | 400 | Low |

---

## Success Metrics

| Metric | Target (Month 1) | Target (Month 6) |
|--------|------------------|------------------|
| Unique visitors | 2,000 | 20,000 |
| Calculations | 5,000 | 50,000 |
| Email captures | 200 | 4,000 |
| LCopilot signups (attributed) | 20 | 500 |

---

## Competitor Analysis

| Tool | LC Calc | Forfait | Guarantee | Free? |
|------|---------|---------|-----------|-------|
| Trade Finance Global | ❌ | ✅ | ❌ | ✅ |
| ICC Trade Finance | ❌ | ❌ | ❌ | ❌ |
| Bank websites | ⚠️ Basic | ❌ | ❌ | ✅ |
| **TRDR Calculator** | ✅ | ✅ | ✅ | ✅ |

**Opportunity:** No comprehensive free calculator exists!

