# 🔢 HS Code & Duty Calculator - Product Spec

## Overview
**Product Name:** TRDR HS Code Finder  
**Tagline:** "Find the right HS code, calculate duties instantly"  
**Priority:** HIGH (SEO magnet, utility tool)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
HS code classification is confusing:
- 5,000+ codes, complex hierarchy
- Wrong code = wrong duties (over or under)
- Different interpretations by country
- Changes over time (2022 amendments)
- Penalties for misclassification

## Solution
An intelligent HS code lookup tool with:
- AI-powered product classification
- Multi-country duty rates
- FTA preference calculator
- History and favorites
- Classification rulings database

---

## User Interface

### Search Screen
```
┌───────────────────────────────────────────────────────────┐
│  🔢 HS CODE FINDER                                        │
│                                                           │
│  Find the right HS code for your products                 │
│                                                           │
│  🔍 Describe your product:                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Cotton t-shirts for men, with printed designs       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  Or enter HS code directly:                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ [6109.10.0000_____]                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🌍 Countries:                                            │
│  Import to:  [United States ▼]                           │
│  Export from: [Bangladesh ▼]                             │
│                                                           │
│                    [ 🔍 Search ]                          │
│                                                           │
│  💡 Popular searches:                                    │
│  [Cotton garments] [Electronics] [Machinery] [Food]      │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results Screen
```
┌───────────────────────────────────────────────────────────┐
│  🔢 HS CODE RESULTS                                       │
│                                                           │
│  Search: "Cotton t-shirts for men, with printed designs" │
│                                                           │
│  🎯 BEST MATCH (95% confidence)                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 6109.10.00.12                                       │ │
│  │ ──────────────────────────────────────────────────  │ │
│  │                                                     │ │
│  │ T-shirts, singlets, tank tops and similar          │ │
│  │ garments, knitted or crocheted                     │ │
│  │ Of cotton                                          │ │
│  │ Men's or boys'                                      │ │
│  │                                                     │ │
│  │ Chapter: 61 - Knitted or crocheted clothing        │ │
│  │ Heading: 6109 - T-shirts, singlets, tank tops      │ │
│  │ Subheading: 6109.10 - Of cotton                    │ │
│  │                                                     │ │
│  │ [Select This Code]                                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 OTHER POSSIBLE CODES:                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 6109.10.00.10 - Women's or girls' (if unisex)     │ │
│  │ 6109.90.10.00 - Of other textile materials         │ │
│  │ 6105.10.00.10 - Polo shirts (if has collar)       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Duty Calculation Screen
```
┌───────────────────────────────────────────────────────────┐
│  💰 DUTY CALCULATION                                      │
│                                                           │
│  HS Code: 6109.10.00.12                                  │
│  Route: Bangladesh → United States                        │
│                                                           │
│  📊 DUTY RATES                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Rate Type          │ Rate    │ Notes                │ │
│  ├────────────────────┼─────────┼──────────────────────┤ │
│  │ MFN (Standard)     │ 16.5%   │ Normal rate          │ │
│  │ GSP (Bangladesh)   │ 0%      │ ✅ Eligible!         │ │
│  │ Column 2           │ 45%     │ Non-NTR countries    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                           │
│  🧮 YOUR CALCULATION                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ CIF Value:         $50,000                          │ │
│  │                                                     │ │
│  │ Standard Duty:     $8,250 (16.5%)                  │ │
│  │ With GSP:          $0 (0%)                         │ │
│  │                                                     │ │
│  │ 💰 YOU SAVE: $8,250 with GSP preference           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 GSP REQUIREMENTS:                                    │
│  ✓ Product must be wholly obtained or substantially     │
│    transformed in Bangladesh                             │
│  ✓ Direct shipment from Bangladesh                      │
│  ✓ GSP Form A certificate required                      │
│  ✓ US GSP program active for this product               │
│                                                           │
│  ⚠️ Note: US GSP expired Dec 2020, pending renewal      │
│     Check current status before shipping                 │
│                                                           │
│  [📄 Generate Duty Report]  [🔗 Check FTA Options]       │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### HS Code Browser
```
┌───────────────────────────────────────────────────────────┐
│  📚 HS CODE BROWSER                                       │
│                                                           │
│  Navigate the HS code hierarchy:                          │
│                                                           │
│  Section XI: Textiles and Textile Articles               │
│  └── Chapter 61: Articles of apparel, knitted           │
│      └── 6109: T-shirts, singlets, tank tops            │
│          ├── 6109.10: Of cotton                         │
│          │   ├── 6109.10.00.10: Women's or girls'       │
│          │   ├── 6109.10.00.12: Men's or boys' ◄────    │
│          │   └── 6109.10.00.20: Other                   │
│          └── 6109.90: Of other textile materials        │
│              ├── 6109.90.10: Of man-made fibers         │
│              └── 6109.90.80: Other                      │
│                                                           │
│  [Expand All] [Collapse All] [Export to Excel]           │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## AI Classification Engine

```python
class HSCodeClassifier:
    """
    AI-powered HS code classification
    """
    
    def classify(self, description: str, context: dict) -> ClassificationResult:
        # Step 1: Extract product features
        features = self.extract_features(description)
        # - Material (cotton, polyester, metal)
        # - Form (garment, raw material, machinery)
        # - Use (wearing apparel, industrial)
        # - Gender/age (men's, women's, children's)
        
        # Step 2: Rule-based chapter selection
        possible_chapters = self.match_chapters(features)
        
        # Step 3: LLM refinement
        refined_codes = self.llm_classify(
            description=description,
            chapters=possible_chapters,
            context=context
        )
        
        # Step 4: Validate against WCO database
        validated = self.validate_codes(refined_codes)
        
        # Step 5: Rank by confidence
        return self.rank_results(validated)
```

---

## Data Sources

### HS Code Database
- WCO (World Customs Organization) 2022 edition
- US HTS (Harmonized Tariff Schedule)
- EU TARIC
- UK Trade Tariff
- Singapore Trade Classification

### Duty Rates
- US ITC (International Trade Commission)
- EU TARIC API
- Singapore TradeNet
- FTA preference databases

### Classification Rulings
- US Customs rulings database
- EU BTI (Binding Tariff Information)
- WCO Classification Opinions

---

## Pricing Model

| Tier | Searches/Month | Price | Features |
|------|---------------|-------|----------|
| Free | 20 | $0 | Basic search, US only |
| Professional | 200 | $39/mo | Multi-country, duty calc |
| Business | Unlimited | $99/mo | + API, bulk upload, history |
| Enterprise | Unlimited | Custom | + Rulings database, custom |

---

## MVP Features (Week 1-2)

- [ ] Text search for HS codes
- [ ] US HTS database
- [ ] Basic duty rates
- [ ] AI classification (single prompt)

## V2 Features (Week 3-4)

- [ ] EU, UK, SG tariffs
- [ ] FTA preference calculator
- [ ] HS code browser
- [ ] Search history
- [ ] Favorites

## V3 Features (Future)

- [ ] Bulk classification (CSV)
- [ ] Classification rulings
- [ ] Annual tariff updates
- [ ] ERP integrations

---

## SEO Opportunity

| Keyword | Monthly Volume | Competition |
|---------|----------------|-------------|
| "HS code lookup" | 14,800 | Medium |
| "HS code search" | 9,900 | Medium |
| "duty calculator" | 6,600 | Low |
| "harmonized code" | 5,400 | Low |
| "tariff code finder" | 3,600 | Low |

**High-traffic potential!**

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Searches | 20,000 |
| Unique users | 5,000 |
| Paid subscribers | 50 |
| Classification accuracy | > 90% |

