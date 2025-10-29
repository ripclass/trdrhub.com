# ISBP 745 Compliance Mapping

**Document Version:** 1.0
**Standard:** ICC International Standard Banking Practice for the Examination of Documents (ISBP 745)
**Last Updated:** September 17, 2025
**LCopilot Version:** Sprint 8.2

## Executive Summary

This document maps LCopilot platform capabilities to the International Chamber of Commerce (ICC) International Standard Banking Practice for the Examination of Documents under Documentary Credits (ISBP 745), effective 2013. ISBP provides detailed guidance for banks examining documents presented under UCP 600.

## Coverage Heatmap

| Section | Topic | Status | Implementation |
|---------|-------|--------|----------------|
| A1-A9 | General Principles | ✅ Implemented | Document examination framework |
| B1-B8 | Commercial Invoice | ✅ Implemented | Invoice validation engine |
| C1-C5 | Draft/Bill of Exchange | 🟡 Partial | Draft examination rules |
| D1-D2 | Transport Documents General | ✅ Implemented | Transport doc framework |
| E1-E12 | Bill of Lading | ✅ Implemented | B/L examination engine |
| F1-F7 | Charter Party B/L | 🟡 Partial | Charter party validation |
| G1-G10 | Air Waybill | ✅ Implemented | AWB validation |
| H1-H6 | Road Transport | ✅ Implemented | CMR validation |
| I1-I6 | Rail Transport | 🟡 Partial | Rail document validation |
| J1-J6 | Multimodal Transport | ✅ Implemented | Multimodal validation |
| K1-K13 | Insurance | ✅ Implemented | Insurance validation |
| L1-L4 | Certificate of Origin | ✅ Implemented | Origin certificate validation |
| M1-M2 | Packing List | ✅ Implemented | Packing list validation |
| N1-N4 | Weight List/Certificate | ✅ Implemented | Weight document validation |
| O1-O2 | Inspection Certificate | ✅ Implemented | Inspection validation |

## Section Mappings

### Section A: General Principles

#### A1: Presentation Completeness
**Canonical Reference:** ISBP 745 A1
**Plain-English Summary:** All documents called for in the credit must be presented. Documents not called for will not be examined unless they form part of another document.

**LCopilot Enforcement:**
- **Deterministic checks:** Document checklist validation, required document presence verification
- **AI assist:** Missing document identification, presentation completeness scoring
- **Evidence in audit trail:** Document presentation logging, completeness verification records

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/presentation-check`, `/api/validation/document-completeness`
**Notes/Limitations:** Comprehensive document checklist with configurable requirements

---

#### A2: Consistent Data
**Canonical Reference:** ISBP 745 A2
**Plain-English Summary:** Data in documents must be consistent with each other and with the credit terms. Inconsistent data constitutes a discrepancy.

**LCopilot Enforcement:**
- **Deterministic checks:** Cross-document data consistency validation, field matching algorithms
- **AI assist:** Inconsistency pattern detection, data correlation analysis
- **Evidence in audit trail:** Consistency check logging, discrepancy identification records

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/data-consistency`, `/api/validation/cross-document`
**Notes/Limitations:** Advanced data correlation with configurable tolerance levels

---

#### A3: Document Conditions
**Canonical Reference:** ISBP 745 A3
**Plain-English Summary:** Documents must not contain conditions or terms that are inconsistent with the credit or UCP 600 requirements.

**LCopilot Enforcement:**
- **Deterministic checks:** Condition parsing, term compatibility validation
- **AI assist:** Contract term analysis, condition impact assessment
- **Evidence in audit trail:** Condition analysis logging, compatibility verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/document-conditions`, `/api/validation/terms`
**Notes/Limitations:** Natural language processing for condition extraction and analysis

---

### Section B: Commercial Invoice

#### B1: Invoice Requirements
**Canonical Reference:** ISBP 745 B1
**Plain-English Summary:** Commercial invoices must be made out to the applicant, describe goods consistent with the credit, and show the required currency and amount.

**LCopilot Enforcement:**
- **Deterministic checks:** Invoice header validation, applicant name verification, goods description matching
- **AI assist:** Invoice completeness assessment, description consistency analysis
- **Evidence in audit trail:** Invoice validation logging, field verification records

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/invoice-validation`, `/api/validation/commercial-invoice`
**Notes/Limitations:** Comprehensive invoice validation with multi-currency support

---

#### B2: Goods Description
**Canonical Reference:** ISBP 745 B2
**Plain-English Summary:** Goods description in the invoice must be consistent with the credit but may show additional details not inconsistent with the credit description.

**LCopilot Enforcement:**
- **Deterministic checks:** Description consistency validation, additional detail verification
- **AI assist:** Semantic description matching, consistency scoring
- **Evidence in audit trail:** Description analysis logging, consistency verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/goods-description`, `/api/validation/description-matching`
**Notes/Limitations:** AI-powered semantic analysis for description consistency

---

#### B3: Invoice Amount
**Canonical Reference:** ISBP 745 B3
**Plain-English Summary:** Invoice amount must not exceed the credit amount. Multiple invoices are acceptable if the credit permits partial shipments.

**LCopilot Enforcement:**
- **Deterministic checks:** Amount validation, credit limit verification, partial shipment rules
- **AI assist:** Amount optimization recommendations, shipment planning
- **Evidence in audit trail:** Amount calculation logging, limit verification records

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/amount-validation`, `/api/validation/invoice-amounts`
**Notes/Limitations:** Automatic tolerance calculations with partial shipment support

---

### Section E: Bill of Lading

#### E1: B/L Essentials
**Canonical Reference:** ISBP 745 E1
**Plain-English Summary:** Bills of lading must show goods shipped on board, be dated, signed, and indicate the carrying vessel and ports of loading and discharge.

**LCopilot Enforcement:**
- **Deterministic checks:** On-board notation validation, signature verification, port matching
- **AI assist:** B/L quality assessment, shipping route analysis
- **Evidence in audit trail:** B/L examination logging, compliance verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/bill-of-lading`, `/api/validation/bl-essentials`
**Notes/Limitations:** Complete B/L validation including electronic B/L support

---

#### E2: On-Board Notation
**Canonical Reference:** ISBP 745 E2
**Plain-English Summary:** Bills of lading must evidence that goods have been shipped on board. Pre-printed on-board language is acceptable.

**LCopilot Enforcement:**
- **Deterministic checks:** On-board notation detection, pre-printed language validation
- **AI assist:** Notation quality assessment, shipping evidence verification
- **Evidence in audit trail:** On-board verification logging, notation analysis

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/onboard-notation`, `/api/validation/shipping-evidence`
**Notes/Limitations:** OCR and pattern recognition for on-board notation detection

---

#### E3: Shipped Date
**Canonical Reference:** ISBP 745 E3
**Plain-English Summary:** Date of shipment is evidenced by the on-board notation date or, if pre-printed, the date of the B/L itself.

**LCopilot Enforcement:**
- **Deterministic checks:** Date extraction, shipment date validation, timeline verification
- **AI assist:** Date consistency analysis, timeline optimization
- **Evidence in audit trail:** Date validation logging, shipment timeline records

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/shipment-dates`, `/api/validation/bl-dates`
**Notes/Limitations:** Automated date extraction with business day calculations

---

### Section K: Insurance

#### K1: Insurance Requirements
**Canonical Reference:** ISBP 745 K1
**Plain-English Summary:** Insurance documents must cover the goods described in the credit, show appropriate coverage amounts, and be issued in the same currency as the credit.

**LCopilot Enforcement:**
- **Deterministic checks:** Coverage validation, amount verification, currency matching
- **AI assist:** Coverage adequacy analysis, risk assessment
- **Evidence in audit trail:** Insurance validation logging, coverage verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/insurance-validation`, `/api/validation/coverage`
**Notes/Limitations:** Comprehensive insurance validation with risk analysis

---

#### K2: Coverage Amount
**Canonical Reference:** ISBP 745 K2
**Plain-English Summary:** Insurance must cover at least 110% of the CIF or CIP value, unless the credit states otherwise.

**LCopilot Enforcement:**
- **Deterministic checks:** Coverage percentage calculation, CIF/CIP value verification
- **AI assist:** Optimal coverage recommendations, risk-based adjustments
- **Evidence in audit trail:** Coverage calculation logging, value verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/insurance-coverage`, `/api/validation/coverage-amounts`
**Notes/Limitations:** Automatic coverage calculations with configurable percentages

---

### Section L: Certificate of Origin

#### L1: Origin Requirements
**Canonical Reference:** ISBP 745 L1
**Plain-English Summary:** Certificates of origin must identify the goods and their country of origin, be properly issued by authorized bodies, and meet any specific credit requirements.

**LCopilot Enforcement:**
- **Deterministic checks:** Origin verification, issuing authority validation, goods identification
- **AI assist:** Origin compliance assessment, trade agreement verification
- **Evidence in audit trail:** Origin validation logging, authority verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/certificate-origin`, `/api/validation/origin`
**Notes/Limitations:** Integration with trade agreement databases for origin verification

---

### Section M: Packing List

#### M1: Packing Details
**Canonical Reference:** ISBP 745 M1
**Plain-English Summary:** Packing lists must provide details of goods packed, including package types, quantities, weights, and marks consistent with other documents.

**LCopilot Enforcement:**
- **Deterministic checks:** Package detail validation, quantity verification, weight consistency
- **AI assist:** Packing optimization analysis, consistency verification
- **Evidence in audit trail:** Packing validation logging, detail verification

**Status:** ✅ Implemented
**Related Endpoints/Modules:** `/api/lc/packing-list`, `/api/validation/packing-details`
**Notes/Limitations:** Automated consistency checking across transport and commercial documents

---

## Advanced Examination Features

### Document Intelligence
- **OCR Integration:** Automatic text extraction from scanned documents
- **Pattern Recognition:** Identification of document types and critical fields
- **Quality Assessment:** Document clarity and completeness scoring
- **Discrepancy Detection:** Automated identification of potential issues

### Cross-Reference Validation
- **Data Consistency:** Multi-document field verification
- **Timeline Validation:** Date sequence and business day verification
- **Amount Reconciliation:** Cross-document amount and calculation verification
- **Geographic Validation:** Port, country, and route consistency checking

### AI-Powered Analysis
- **Semantic Matching:** Intelligent goods description comparison
- **Risk Assessment:** Document risk scoring and flagging
- **Completeness Scoring:** Presentation quality assessment
- **Recommendation Engine:** Optimization suggestions for document preparation

## Implementation Summary

**Total Sections Mapped:** 15
**Fully Implemented (✅):** 12 (80%)
**Partially Implemented (🟡):** 3 (20%)
**Planned (❌):** 0 (0%)

## Change Log for This Mapping

### v1.0 - September 17, 2025
- Initial ISBP 745 mapping document
- Core sections A (General), B (Invoice), E (B/L), K (Insurance), L (Origin), M (Packing) mapped
- Partial implementation noted for Charter Party B/L and Rail Transport
- Document intelligence features documented
- AI-powered analysis capabilities defined

## Next Steps

1. **Charter Party B/L (F1-F7)**: Complete specialized charter party validation
2. **Rail Transport (I1-I6)**: Enhance rail document examination capabilities
3. **Draft/Bill of Exchange (C1-C5)**: Complete draft examination framework
4. **Verification Needed**: Cross-reference with latest ISBP interpretations
5. **Enhancement**: Add jurisdiction-specific examination variations

---

*This mapping reflects the current state of ISBP 745 implementation in LCopilot and is updated with each product release to maintain alignment with international banking practices.*