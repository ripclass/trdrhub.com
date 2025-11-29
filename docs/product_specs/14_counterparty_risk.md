# ⚠️ Counterparty Risk (RiskRecon) - Product Spec

## Overview
**Product Name:** TRDR RiskRecon  
**Tagline:** "Know your trade partners before you commit"  
**Priority:** MEDIUM (Value-add for due diligence)  
**Estimated Dev Time:** 4-5 weeks  

---

## Problem Statement
Traders face counterparty risks:
- New suppliers may be fraudulent
- Buyers may not pay
- Limited visibility into financial health
- Expensive due diligence ($500+ per report)
- Payment terms negotiated blindly

## Solution
Automated counterparty risk assessment:
- Company verification
- Financial health scoring
- Trade history (where available)
- Red flag detection
- Payment recommendation

---

## User Interface

### Search Screen
```
┌───────────────────────────────────────────────────────────┐
│  ⚠️ RISKRECON - COUNTERPARTY CHECK                       │
│                                                           │
│  Check a company before you trade                         │
│                                                           │
│  🔍 Enter company details:                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Company Name:  [Shanghai Fashion Import Co____]     │ │
│  │ Country:       [China ▼]                            │ │
│  │ Registration:  [Optional: company reg number]       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 What do you want to check?                           │
│  ☑️ Company verification (is it real?)                   │
│  ☑️ Financial health (can they pay?)                     │
│  ☑️ Sanctions screening                                  │
│  ☑️ Adverse media                                        │
│  ☐ Credit score (premium)                                │
│  ☐ Detailed financials (premium)                         │
│                                                           │
│                    [ 🔍 Run Check ]                       │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results - Good Risk
```
┌───────────────────────────────────────────────────────────┐
│  ⚠️ RISKRECON REPORT                                      │
│                                                           │
│  Company: Shanghai Fashion Import Co Ltd                  │
│  Country: China                                           │
│  Report Date: 29 Nov 2024                                │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ OVERALL RISK SCORE                                  │ │
│  │                                                     │ │
│  │     ████████████████░░░░  72/100                   │ │
│  │                                                     │ │
│  │     🟢 LOW-MEDIUM RISK                             │ │
│  │     Recommendation: PROCEED WITH STANDARD TERMS    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 VERIFICATION                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ✅ Company exists in China registry                │ │
│  │ ✅ Registration: 91310115MA1K4XAX6D                │ │
│  │ ✅ Registered: 15 Mar 2015 (9 years)              │ │
│  │ ✅ Status: Active                                  │ │
│  │ ✅ Registered capital: RMB 10,000,000             │ │
│  │ ✅ Address verified                                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💰 FINANCIAL INDICATORS                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Company Size:      Medium                          │ │
│  │ Est. Revenue:      RMB 50-100M ($7-14M)           │ │
│  │ Years in Business: 9 years                        │ │
│  │ Employee Count:    50-100 (est.)                  │ │
│  │ Industry:          Textile import/export          │ │
│  │                                                     │ │
│  │ ⚠️ Note: Detailed financials require upgrade      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🔒 COMPLIANCE                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ✅ Not on OFAC SDN list                            │ │
│  │ ✅ Not on EU sanctions list                        │ │
│  │ ✅ No adverse media found                          │ │
│  │ ✅ Not in high-risk industry                       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  💡 SUGGESTED PAYMENT TERMS                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Based on this risk profile, consider:              │ │
│  │                                                     │ │
│  │ • LC at sight ✅ (recommended for new relationship)│ │
│  │ • LC 30 days ✅ (acceptable after 2-3 transactions)│ │
│  │ • D/P ⚠️ (only after established track record)    │ │
│  │ • Open account ❌ (not recommended initially)      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📄 Download Report]  [💳 Get Credit Score]  [🔄 Refresh]│
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results - High Risk
```
┌───────────────────────────────────────────────────────────┐
│  ⚠️ RISKRECON REPORT                                      │
│                                                           │
│  Company: Global Trade Solutions FZE                      │
│  Country: UAE                                             │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ OVERALL RISK SCORE                                  │ │
│  │                                                     │ │
│  │     ████░░░░░░░░░░░░░░░░  28/100                   │ │
│  │                                                     │ │
│  │     🔴 HIGH RISK                                   │ │
│  │     Recommendation: ENHANCED DUE DILIGENCE REQUIRED│ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🚨 RED FLAGS DETECTED                                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ❌ Company registered < 1 year ago                 │ │
│  │ ❌ Minimal registered capital (AED 10,000)         │ │
│  │ ❌ Free zone entity (limited liability)            │ │
│  │ ⚠️ Directors linked to dissolved companies        │ │
│  │ ⚠️ Adverse media: mentioned in fraud case (2023)  │ │
│  │ ⚠️ High-risk jurisdiction for shell companies     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ RECOMMENDED ACTIONS                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Before proceeding, you should:                     │ │
│  │                                                     │ │
│  │ 1. Request audited financial statements           │ │
│  │ 2. Verify directors' identities                   │ │
│  │ 3. Request bank references                        │ │
│  │ 4. Consider 100% advance payment only             │ │
│  │ 5. Verify physical office location               │ │
│  │                                                     │ │
│  │ If trading: Use CONFIRMED LC only                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📄 Full Report]  [📞 Request Investigation]            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Risk Scoring Model

```python
class RiskScorer:
    """
    Multi-factor counterparty risk scoring
    """
    
    WEIGHTS = {
        "company_age": 15,          # Older = lower risk
        "registered_capital": 10,    # Higher = lower risk
        "financial_health": 20,      # Revenue, profit trends
        "jurisdiction_risk": 15,     # Country/structure risk
        "sanctions_clear": 20,       # Binary: clear or not
        "adverse_media": 10,         # Negative news
        "industry_risk": 5,          # High-risk sectors
        "director_checks": 5,        # Director history
    }
    
    def calculate_score(self, company_data: dict) -> RiskScore:
        scores = {}
        
        # Company Age Score (0-15)
        years = company_data["years_in_business"]
        scores["company_age"] = min(years * 1.5, 15)
        
        # Capital Score (0-10)
        capital = company_data["registered_capital_usd"]
        if capital > 1_000_000:
            scores["registered_capital"] = 10
        elif capital > 100_000:
            scores["registered_capital"] = 7
        else:
            scores["registered_capital"] = 3
        
        # Sanctions (binary)
        scores["sanctions_clear"] = 20 if not company_data["sanctions_hit"] else 0
        
        # ... other factors
        
        total = sum(scores.values())
        
        return RiskScore(
            score=total,
            grade=self._get_grade(total),
            recommendation=self._get_recommendation(total),
            factors=scores
        )
```

---

## Data Sources

### Company Registries
| Country | Source | Coverage |
|---------|--------|----------|
| UK | Companies House | ✅ Full |
| US | State registries | ✅ Full |
| EU | National registries | ✅ Varies |
| China | SAIC/Tianyancha | ⚠️ Basic |
| India | MCA | ✅ Full |
| UAE | DED/Free zones | ⚠️ Limited |
| Singapore | ACRA | ✅ Full |

### Financial Data
- Dun & Bradstreet (partnership)
- Credit bureaus
- Public filings

### Compliance Data
- OFAC, EU, UN sanctions
- PEP databases
- Adverse media APIs

---

## Pricing Model

| Tier | Checks/Month | Price | Features |
|------|-------------|-------|----------|
| Free | 3 | $0 | Basic verification |
| Starter | 20 | $49/mo | + Sanctions, scoring |
| Professional | 50 | $129/mo | + Adverse media, history |
| Business | 150 | $299/mo | + Credit score, API |
| Enterprise | Unlimited | Custom | + Detailed financials |

---

## Integration Points

### With LCopilot
```
LC Builder → RiskRecon:
1. User enters beneficiary/applicant
2. Auto-run basic risk check
3. Flag if high risk
4. Recommend payment terms
```

### With Sanctions Screener
```
RiskRecon includes sanctions check
- OFAC, EU, UN, UK screening
- Free with every risk report
```

---

## MVP Features (Week 1-3)

- [ ] Company verification (UK, US, SG)
- [ ] Basic sanctions check
- [ ] Risk scoring algorithm
- [ ] Report generation

## V2 Features (Week 4-5)

- [ ] More countries (EU, India, UAE)
- [ ] Adverse media screening
- [ ] Director checks
- [ ] Payment term suggestions
- [ ] History tracking

## V3 Features (Future)

- [ ] Credit scoring integration
- [ ] Trade credit insurance quotes
- [ ] Monitoring (ongoing alerts)
- [ ] Portfolio risk dashboard

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Risk checks performed | 1,000 |
| High-risk flags | 100 |
| Paid subscribers | 30 |
| False positive rate | < 5% |

