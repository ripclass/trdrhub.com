# 🔍 Export Control Checker - Product Spec

## Overview
**Product Name:** TRDR Export Control Checker  
**Tagline:** "Know before you ship - check export restrictions instantly"  
**Priority:** HIGH (Compliance critical, pairs with Sanctions Screener)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
Exporters risk serious penalties for shipping controlled goods:
- Dual-use items require licenses (EAR, EU 2021/821)
- Military/defense items are restricted
- Encryption technology has special rules
- Each country has different control lists
- Penalties: Up to $1M+ fines, prison, loss of export privileges

## Solution
A tool to check if your goods require export licenses:
- HS Code/product description lookup
- Cross-reference multiple control lists
- Destination country risk assessment
- License requirement determination
- End-use/end-user screening

---

## User Interface

### Search Screen
```
┌───────────────────────────────────────────────────────────┐
│  🔍 EXPORT CONTROL CHECKER                                │
│                                                           │
│  Check if your goods require an export license            │
│                                                           │
│  📦 Product Information:                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ HS Code:    [8471.30____] or                        │ │
│  │ Description: [CNC milling machine with 5-axis...]   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🌍 Export Details:                                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ From Country:  [United States ▼]                    │ │
│  │ To Country:    [China ▼]                            │ │
│  │ End User:      [Manufacturing Company_____]         │ │
│  │ End Use:       [Industrial production____]          │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 Control Lists to Check:                              │
│  ☑️ US EAR (Export Administration Regulations)           │
│  ☑️ US ITAR (Munitions List)                             │
│  ☑️ EU Dual-Use (2021/821)                               │
│  ☑️ Wassenaar Arrangement                                │
│  ☑️ UK Strategic Export Controls                         │
│  ☐ Country-specific lists                                │
│                                                           │
│                    [ 🔍 Check Export Controls ]           │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results Screen - License Required
```
┌───────────────────────────────────────────────────────────┐
│  🔍 EXPORT CONTROL CHECK RESULTS                          │
│                                                           │
│  ⚠️ LICENSE LIKELY REQUIRED                               │
│                                                           │
│  Product: CNC Milling Machine, 5-axis                     │
│  HS Code: 8459.61                                         │
│  Route:   USA → China                                     │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ CONTROL LIST MATCHES                                │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │                                                     │ │
│  │ ❌ US EAR - CONTROLLED                              │ │
│  │    ECCN: 2B001.b.2                                  │ │
│  │    Category: Machine Tools                          │ │
│  │    Reason: "5-axis simultaneous contouring"        │ │
│  │    License: Required for China (Country Group D:1)  │ │
│  │    License Exception: None available               │ │
│  │                                                     │ │
│  │ ❌ WASSENAAR - CONTROLLED                           │ │
│  │    Category: 2.B.1.b                               │ │
│  │    "Machine tools for removing metal..."           │ │
│  │                                                     │ │
│  │ ❌ EU DUAL-USE - CONTROLLED                         │ │
│  │    Category: 2B001.b                               │ │
│  │    "Numerically controlled machine tools"          │ │
│  │                                                     │ │
│  │ ✅ ITAR - NOT CONTROLLED                            │ │
│  │    Not on US Munitions List                        │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 RECOMMENDED ACTIONS:                                  │
│  1. Apply for BIS export license (Form BIS-748P)         │
│  2. Processing time: 30-90 days typically                 │
│  3. Consider license exception eligibility               │
│  4. Document end-user and end-use certifications         │
│                                                           │
│  ⚠️ DESTINATION RISK: HIGH                               │
│  China is subject to enhanced controls under EAR §744    │
│  Additional scrutiny for semiconductor equipment         │
│                                                           │
│  [ 📄 Download Report ] [ 📧 Email to Compliance ]       │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Results Screen - No License Required
```
┌───────────────────────────────────────────────────────────┐
│  🔍 EXPORT CONTROL CHECK RESULTS                          │
│                                                           │
│  ✅ NO LICENSE REQUIRED                                   │
│                                                           │
│  Product: Cotton T-Shirts                                 │
│  HS Code: 6109.10                                         │
│  Route:   Bangladesh → USA                                │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ CONTROL LIST CHECK                                  │ │
│  │ ─────────────────────────────────────────────────── │ │
│  │                                                     │ │
│  │ ✅ US EAR - NOT CONTROLLED                          │ │
│  │    Classification: EAR99                            │ │
│  │    "Items not elsewhere classified"                │ │
│  │                                                     │ │
│  │ ✅ EU DUAL-USE - NOT CONTROLLED                     │ │
│  │    Not on Annex I                                  │ │
│  │                                                     │ │
│  │ ✅ WASSENAAR - NOT CONTROLLED                       │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ⚠️ STILL CHECK:                                         │
│  • Sanctions on buyer/end-user (use Sanctions Screener)  │
│  • Import restrictions in destination country            │
│  • Product-specific regulations (textiles have quotas)   │
│                                                           │
│  [ 📄 Download Certificate ] [ 🔍 Run Sanctions Check ]  │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Control Lists Database

### Data Sources
```
Data/sanctions/ (existing) +
├── EAR Commerce Control List (CCL)
│   ├── Categories 0-9
│   ├── ECCNs
│   └── License exceptions
│
├── ITAR US Munitions List (USML)
│   ├── Categories I-XXI
│   └── Technical data controls
│
├── EU Dual-Use Regulation
│   ├── Annex I (controlled items)
│   ├── Annex IV (intra-EU controls)
│   └── Catch-all provisions
│
├── Wassenaar Arrangement
│   ├── Dual-Use List
│   └── Munitions List
│
├── UK Export Control Order
│   └── Strategic Export Control Lists
│
└── Country-Specific
    ├── US Entity List
    ├── US Unverified List
    ├── Denied Persons List
    └── Military End-User List
```

### ECCN Structure
```typescript
interface ECCN {
  code: string;           // e.g., "2B001.b.2"
  category: number;       // 0-9
  productGroup: string;   // A-E
  description: string;
  technicalParameters: TechnicalParameter[];
  controlReasons: ControlReason[];
  licenseExceptions: LicenseException[];
  destinationControls: CountryControl[];
}

interface CountryControl {
  countryGroup: string;   // A:1, D:1, etc.
  countries: string[];
  licenseRequired: boolean;
  licenseException?: string;
}
```

---

## Matching Algorithm

```python
def check_export_controls(product: Product, route: Route) -> ControlResult:
    """
    Multi-stage export control check
    """
    results = []
    
    # Stage 1: HS Code → ECCN mapping
    potential_eccns = map_hs_to_eccn(product.hs_code)
    
    # Stage 2: Technical parameter check
    for eccn in potential_eccns:
        if matches_technical_params(product, eccn):
            results.append(create_match(eccn, "technical_match"))
    
    # Stage 3: Description-based AI matching
    ai_matches = ai_classify_product(product.description)
    results.extend(ai_matches)
    
    # Stage 4: Destination country check
    destination_risk = check_country_controls(route.to_country)
    
    # Stage 5: End-user check
    end_user_risk = check_end_user(route.end_user)
    
    # Stage 6: Determine license requirement
    license_required = evaluate_license_requirement(
        results, 
        destination_risk, 
        end_user_risk
    )
    
    return ControlResult(
        matches=results,
        destination_risk=destination_risk,
        end_user_risk=end_user_risk,
        license_required=license_required,
        exceptions_available=find_exceptions(results, route)
    )
```

---

## Integration Points

### With Sanctions Screener
```
Export Control → Sanctions Flow:
1. User checks export controls
2. If destination is high-risk, prompt: "Also check sanctions?"
3. Auto-run sanctions check on:
   - Destination country
   - End-user company
   - Ultimate consignee
```

### With LCopilot
```
LCopilot → Export Control Flow:
1. LCopilot extracts goods description + HS code
2. Extracts destination country
3. Auto-run export control check
4. Flag if license may be required:
   "⚠️ These goods may require export license"
```

---

## Pricing Model

| Tier | Checks/Month | Price | Features |
|------|-------------|-------|----------|
| Free | 5 | $0 | Basic US EAR |
| Professional | 50 | $79/mo | + EU, UK, Wassenaar |
| Business | 200 | $199/mo | + Entity lists, API |
| Enterprise | Unlimited | Custom | + Custom integrations |

---

## MVP Features (Week 1-2)

- [ ] HS Code → ECCN lookup
- [ ] US EAR basic check
- [ ] Country group classification
- [ ] Results UI

## V2 Features (Week 3-4)

- [ ] EU Dual-Use
- [ ] Wassenaar
- [ ] UK controls
- [ ] Entity List screening
- [ ] AI-based product classification

## V3 Features (Future)

- [ ] ITAR (requires registration)
- [ ] License application assistant
- [ ] Compliance program templates
- [ ] Real-time list updates

---

## Compliance Disclaimer

```
⚠️ IMPORTANT DISCLAIMER

TRDR Export Control Checker is a screening aid, not legal advice.

• Results should be verified by qualified export compliance counsel
• Control list interpretations may vary
• Technical parameters require expert assessment
• We update databases regularly but cannot guarantee real-time accuracy
• Exporter remains solely responsible for compliance

For complex items or uncertain classifications, consult:
• US: Bureau of Industry and Security (BIS)
• EU: Your national licensing authority
• UK: Export Control Joint Unit (ECJU)
```

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Checks performed | 2,000 |
| Paid subscribers | 30 |
| False positive rate | < 5% |
| Integration with LCopilot | 50% of users |

