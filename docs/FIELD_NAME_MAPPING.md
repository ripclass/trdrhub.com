# Field Name Mapping Document

## Purpose
This document identifies field name inconsistencies across the codebase and defines the CANONICAL name that should be used everywhere.

---

## 🔴 CRITICAL: 47A Additional Conditions

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| `lc_extractor.py:252` | `clauses_47a` | `additional_conditions` |
| `lc_baseline.py:247` | `additional_conditions` | ✅ CANONICAL |
| `lc_baseline.py:647` | reads `clauses_47a` | ✅ Fixed (maps to canonical) |
| `crossdoc_validator.py:1627` | reads `additional_conditions` | ✅ CANONICAL |
| `validate.py:3831` | looks for multiple names | ⚠️ Band-aid fix |
| `structured_lc_builder.py:142` | maps `clauses_47a` → `additional_conditions` | ✅ Correct |
| `swift_mt700_full.py:176` | `additional_conditions` | ✅ CANONICAL |
| `iso20022_parser.py:177` | `additional_conditions` | ✅ CANONICAL |

### ✅ CANONICAL NAME: `additional_conditions`

### ✅ FIXED:
```python
# lc_extractor.py line 252 - CHANGED:
"additional_conditions": clauses47a.get("conditions", []),  # Canonical name for 47A

# structured_lc_builder.py line 142 - CHANGED:
"additional_conditions": extractor_outputs.get("additional_conditions"),  # Canonical name

# lc_baseline.py line 647 - CHANGED:
conditions = extraction_result.get("additional_conditions", []) or extraction_result.get("clauses_47a", [])
```

---

## 🔴 CRITICAL: Compliance Score/Rate

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| `processing_summary` | `compliance_rate` | ✅ CANONICAL |
| `analytics` | `lc_compliance_score` | Should be `compliance_rate` |
| `analytics` | `compliance_score` | Should be `compliance_rate` |
| Frontend `resultsMapper.ts:207` | checks `compliance_score` | Should be `compliance_rate` |
| Frontend `validationState.ts:86-88` | checks 3 different names | ⚠️ Band-aid |
| `compliance_scorer.py` | `compliance_rate` property | ✅ CANONICAL |
| `response_schema.py:145` | `lc_compliance_score` | Should be `compliance_rate` |
| `response_schema.py:182` | `compliance_rate` | ✅ CANONICAL |

### ✅ CANONICAL NAME: `compliance_rate` (integer 0-100)

### Current Mess:
```typescript
// Frontend has to check 3 places!
response.compliance_rate ??
response.processing_summary?.compliance_rate ??
response.analytics?.lc_compliance_score ??
```

### 🔧 FIX NEEDED:
1. Backend should ALWAYS return `compliance_rate` in `processing_summary`
2. Remove `lc_compliance_score` from `analytics`
3. Frontend should only check `processing_summary.compliance_rate`

---

## 🟡 IMPORTANT: Document Status Counts

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| `processing_summary` | `verified` | ✅ Keep |
| `processing_summary` | `warnings` | ✅ Keep |
| `processing_summary` | `errors` | ✅ Keep |
| `processing_summary` | `document_status` | ✅ Keep (object with success/warning/error counts) |
| `processing_summary` | `status_counts` | Redundant with `document_status` |

### ✅ CANONICAL STRUCTURE:
```typescript
processing_summary: {
  documents: number,           // Total document count
  verified: number,            // Documents with no issues (same as document_status.success)
  warnings: number,            // Documents with warnings
  errors: number,              // Documents with errors
  compliance_rate: number,     // 0-100
  document_status: {
    success: number,
    warning: number,
    error: number
  }
}
```

### 🔧 FIX NEEDED:
- Remove `status_counts` (duplicate of `document_status`)
- Ensure `verified` === `document_status.success`

---

## 🟡 IMPORTANT: Document Types

| Variation | Should Be |
|-----------|-----------|
| `"lc"` | `"letter_of_credit"` |
| `"LC"` | `"letter_of_credit"` |
| `"l/c"` | `"letter_of_credit"` |
| `"invoice"` | `"commercial_invoice"` |
| `"bl"` | `"bill_of_lading"` |
| `"b/l"` | `"bill_of_lading"` |
| `"bol"` | `"bill_of_lading"` |
| `"coo"` | `"certificate_of_origin"` |
| `"pl"` | `"packing_list"` |

### ✅ CANONICAL NAMES (from `shared-types/python/document_types.py`):
- `letter_of_credit`
- `commercial_invoice`
- `bill_of_lading`
- `packing_list`
- `certificate_of_origin`
- `insurance_certificate`
- `inspection_certificate`
- `beneficiary_certificate`
- `weight_certificate`
- `phytosanitary_certificate`

### ✅ Already Fixed:
- `normalize_document_type()` function exists in `shared-types`
- Should be used at EVERY boundary (upload, extraction, validation, display)

---

## 🟡 IMPORTANT: Issue/Discrepancy Fields

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| CrossDoc issues | `documents` | Keep for display context |
| CrossDoc issues | `affected_documents` | ✅ NEW - for stats attribution |
| Issue cards | `document_name` | ✅ Keep |
| Issue cards | `document_type` | ✅ Keep |
| Issue cards | `severity` | ✅ Keep (`critical`, `major`, `minor`) |

### ✅ CANONICAL ISSUE STRUCTURE:
```typescript
interface Issue {
  id: string;
  rule_id: string;
  title: string;
  severity: "critical" | "major" | "minor";
  
  // For display
  documents: string[];           // ["letter_of_credit", "bill_of_lading"]
  document_names: string[];      // ["Letter of Credit", "Bill of Lading"]
  
  // For stats attribution (which doc has the problem)
  affected_documents: string[];  // ["bill_of_lading"] - only the doc with issue
  
  // Discrepancy details
  expected: string;
  actual: string;
  suggestion: string;
}
```

---

## 🟢 MINOR: Processing Time

| Location | Current Name | Should Be |
|----------|--------------|-----------|
| `processing_summary` | `processing_time_seconds` | ✅ Keep |
| `processing_summary` | `processing_time_display` | ✅ Keep |
| `processing_summary` | `processing_time_ms` | Remove (redundant) |

---

## 📋 Summary: What To Rename

### High Priority (Causing Bugs):
1. `lc_extractor.py`: `clauses_47a` → `additional_conditions`
2. `analytics.lc_compliance_score` → Remove, use `processing_summary.compliance_rate`

### Medium Priority (Cleanup):
3. Remove `status_counts` from `processing_summary`
4. Remove `processing_time_ms` from `processing_summary`

### Already Fixed:
- Document type normalization (use `normalize_document_type()`)
- Issue attribution (use `affected_documents` field)

---

## 🎯 Action Items

### ✅ Fix 1: Rename clauses_47a - DONE
```python
# Files updated:
# - apps/api/app/services/extraction/lc_extractor.py (line 252)
# - apps/api/app/services/extraction/structured_lc_builder.py (line 142)
# - apps/api/app/services/extraction/lc_baseline.py (line 647)
```

### Fix 2: Standardize compliance field (15 minutes)
```python
# File: apps/api/app/services/validation/response_schema.py
# Remove lc_compliance_score from AnalyticsSchema
# Keep only compliance_rate in ProcessingSummarySchema
```

### Fix 3: Frontend cleanup (10 minutes)
```typescript
// File: apps/web/src/lib/validation/validationState.ts
// BEFORE:
response.compliance_rate ??
  response.processing_summary?.compliance_rate ??
  response.analytics?.lc_compliance_score ??

// AFTER:
response.processing_summary.compliance_rate
```

---

## 📁 Files Status

| File | Status | Change |
|------|--------|--------|
| `apps/api/app/services/extraction/lc_extractor.py` | ✅ DONE | `clauses_47a` → `additional_conditions` |
| `apps/api/app/services/extraction/structured_lc_builder.py` | ✅ DONE | Updated to use canonical name |
| `apps/api/app/services/extraction/lc_baseline.py` | ✅ DONE | Reads canonical name first |
| `apps/api/app/services/validation/response_schema.py` | ⏳ TODO | Remove `lc_compliance_score` |
| `apps/api/app/routers/validate.py` | ⏳ TODO | Can simplify 47A lookups (still has fallbacks) |
| `apps/web/src/lib/validation/validationState.ts` | ⏳ TODO | Simplify compliance lookup |
| `apps/web/src/lib/exporter/resultsMapper.ts` | ⏳ TODO | Simplify compliance lookup |
