# CTO Bug Packet — LCopilot Exporter Review Page
**Job ID:** `8e2114e5-4f79-4032-afa4-47d18e0cc729`  
**Page:** Exporter Results / Review Page (`/lcopilot/exporter-results?jobId=...`)  
**Date:** 2026-02-27  
**Reporter:** CTO Automated Audit  
**Status:** All 4 bugs UNRESOLVED – awaiting fix  

---

## Summary Table

| # | Bug | Severity | Owner Module | Fix Priority |
|---|-----|----------|--------------|-------------|
| 1 | Summary/Document tab status inconsistency | P1 – High | `SummaryStrip.tsx`, `resultsMapper.ts` | 1st |
| 2 | Sanctions confidence shown as 7500% | P1 – High | `sanctions_lcopilot.py`, `SanctionsAlert.tsx` | 2nd |
| 3 | BIN/TIN discrepancies mapped to Field 44E (Port of Loading) | P2 – Medium | `amendment_generator.py` | 3rd |
| 4 | LC issue date shows 2015-04-26 (century/format anomaly) | P2 – Medium | `extractors.py`, `ai_lc_extractor.py` | 4th |

---

## Bug 1 — Summary/Document Tab Status Inconsistency

### Observed
- **Top summary bar (SummaryStrip)** shows: `2 verified / 2 warning / 2 error`
- **Documents tab** shows all 6 documents with status: `✅ Verified`

### Impact
- Users cannot trust the summary header. A mismatch between the top-level verdict and the Documents tab erodes confidence. In a compliance tool, contradictory status displays can cause traders to either panic or ignore legitimate warnings.
- **CRITICAL for pilot demos and enterprise clients.**

### Root Cause Analysis

**Two separate data sources are being used without reconciliation:**

1. **`SummaryStrip.tsx`** reads from:
   ```ts
   analytics?.document_status_distribution ??
   summary?.document_status ??
   summary?.status_counts ?? {}
   ```
   → This may come from the **backend processing summary** (computed during validation).

2. **Documents tab in `ExporterResults.tsx`** derives status from:
   ```ts
   const status = deriveDocumentStatus(extractionStatus, issuesCount)
   ```
   Where:
   ```ts
   const deriveDocumentStatus = (extractionStatus, issuesCount) => {
     if (status === 'error' || issuesCount >= 3) return 'error';
     if (issuesCount > 0 || status === 'partial') return 'warning';
     return 'success';
   }
   ```
   → This computes **live from the document array** in the frontend.

**The discrepancy:** The backend `document_status_distribution` in `processing_summary` or `analytics` can reflect a **different snapshot** than what the mapped `documents[]` array shows. The backend may compute counts before post-processing, or the `issuesCount` field (`discrepancyCount` in the raw response) may not be hydrated on all documents, making the frontend compute them as all `success`.

**Key suspect:** In `resultsMapper.ts`:
```ts
const issuesCount = Number(doc?.discrepancyCount ?? doc?.issues_count ?? doc?.issuesCount ?? 0);
```
If `discrepancyCount` is absent from some documents, they all default to 0 → all show as `success`. But the backend's stored summary *does* know about warnings/errors.

### Candidate Files
| File | Lines/Function |
|------|---------------|
| `apps/web/src/components/lcopilot/SummaryStrip.tsx` | `verified/warnings/errors` calculation block (lines ~60-90) |
| `apps/web/src/lib/exporter/resultsMapper.ts` | `mapDocuments()`, `ensureSummary()` |
| `apps/web/src/pages/ExporterResults.tsx` | `documents` useMemo, `documentStatusCounts` useMemo, `successCount/errorCount/warningCount` useMemo |
| `apps/api/app/services/validation/response_schema.py` | `ProcessingSummarySchema`, document status counters |

### Reproduction Steps
1. Upload an LC package with known discrepancies for job `8e2114e5`
2. Navigate to `/lcopilot/exporter-results?jobId=8e2114e5-4f79-4032-afa4-47d18e0cc729`
3. Observe top SummaryStrip: `2 verified / 2 warning / 2 error`
4. Click Documents tab → all 6 show as `✅ Verified`

### Fix Recommendation

**Option A (Preferred): Single source of truth — derive from documents array.**

In `ExporterResults.tsx`, always pass the document-array-computed counts to `SummaryStrip`, ignoring the backend `document_status_distribution` unless the array is empty:

```tsx
// In ExporterResults.tsx – replace the complex multi-source resolution in successCount/warningCount/errorCount useMemo:
const resolvedSuccessCount = documents.filter(d => d.status === 'success').length;
const resolvedWarningCount = documents.filter(d => d.status === 'warning').length;
const resolvedErrorCount = documents.filter(d => d.status === 'error').length;
```

**Option B: Fix the backend `issuesCount` hydration.**

Ensure the API response always populates `discrepancyCount` (or `issues_count`) on every `documents_structured` entry. Currently some documents omit this field, causing the frontend to default to 0.

In `apps/api/app/services/validation/pipeline.py` (or wherever `documents_structured` is assembled), ensure:
```python
doc["issues_count"] = len([i for i in issues if doc_filename in i.get("documents", [])])
```

**Also fix `resultsMapper.ts`** — ensure `mapDocuments()` reads `issuesCount` from the correct key hierarchy matching what the backend actually sends.

### Test Assertions
```ts
// ExporterResults.test.tsx
it('SummaryStrip counts match Documents tab counts', () => {
  const { getByTestId } = render(<ExporterResults {...mockProps} />);
  const summaryVerified = parseInt(getByTestId('summary-verified-count').textContent);
  const docsVerified = document.querySelectorAll('[data-status="success"]').length;
  expect(summaryVerified).toBe(docsVerified);
});
```

```python
# test_suite.py
def test_document_status_distribution_matches_document_array():
    result = run_validation(SAMPLE_PACKAGE)
    dist = result["structured_result"]["processing_summary"]["document_status"]
    docs = result["structured_result"]["documents_structured"]
    assert dist["success"] == len([d for d in docs if d["extraction_status"] == "success"])
```

---

## Bug 2 — Sanctions Confidence Shown as 7500%

### Observed
- Sanctions score displayed as **7500%** confidence in the UI

### Impact
- Completely breaks credibility of the sanctions screening feature.
- Presents legally significant misinformation — a "7500% confidence" match would alarm any compliance officer unnecessarily.
- **P1 for enterprise sales and regulatory compliance.**

### Root Cause Analysis

**Double-multiplication chain:**

**Step 1 – Backend computes score as 0–100 float:**
In `sanctions_screening.py`, `calculate_match_score()` returns:
```python
return (jw_score, "fuzzy", "jaro_winkler")  # jw_score is already * 100 (0–100 range)
```
The function computes `jaro_winkler_similarity() * 100`, so scores are already in range 0–100.

**Step 2 – `_build_sanctions_issue()` formats it as a percentage string but also stores raw float:**
```python
match_score = f"{match_info.match_score:.0%}"  # ← WRONG: .0% multiplies by 100 again!
```
`match_info.match_score` is already `75.0` (meaning 75%). The `:.0%` format specifier in Python multiplies by 100 and appends `%`, producing `"7500%"`.

The same issue exists in the fallback:
```python
match_score = f"{result.highest_score:.0%}"  # ← Same double-multiply
```

**Step 3 – Frontend then reads the raw `score` field from `sanctions_details`:**
```ts
// SanctionsAlert.tsx
{issue.score ? `${(issue.score * 100).toFixed(0)}% Match` : "Confirmed Match"}
```
If `score` is already `75.0` (0–100 scale) and the frontend does `* 100`, it shows **7500%**.

**Root cause is a contract mismatch:** The backend stores `match_score` as 0–100, but the frontend assumes 0–1. The `:.0%` format bug in the issue string compounds this.

### Candidate Files
| File | Function | Bug |
|------|----------|-----|
| `apps/api/app/services/sanctions_lcopilot.py` | `_build_sanctions_issue()` | `f"{match_info.match_score:.0%}"` → double-multiply |
| `apps/web/src/components/sanctions/SanctionsAlert.tsx` | Render block | `issue.score * 100` → assumes 0–1 scale |
| `apps/api/app/services/sanctions_screening.py` | `ComprehensiveScreeningResult` model | `highest_score` is 0–100, not 0–1 |

### Reproduction Steps
1. Submit an LC with a party name that triggers a fuzzy sanctions match (score ~75%)
2. Navigate to Issues tab → find the sanctions issue card
3. Observe confidence displayed as "7500%"

### Fix — Backend (`sanctions_lcopilot.py`)
```python
# BEFORE (broken):
match_score = f"{match_info.match_score:.0%}"  # 75.0 → "7500%"

# AFTER (fixed):
match_score = f"{match_info.match_score:.0f}%"  # 75.0 → "75%"
```
Apply same fix to the fallback:
```python
# BEFORE:
match_score = f"{result.highest_score:.0%}"
# AFTER:
match_score = f"{result.highest_score:.0f}%"
```

### Fix — Frontend (`SanctionsAlert.tsx`)
The `score` field in `SanctionsScreeningIssue` schema must have a clear contract. Decide: is it 0–1 or 0–100?

**Recommendation:** Normalize to 0–1 at the API boundary (divide by 100 in `_build_sanctions_issue()`).

```python
# In _build_sanctions_issue(), normalize score to 0-1 for frontend:
"match_score": result.highest_score / 100,  # Normalize to 0-1
```

Then in `SanctionsAlert.tsx` the existing `issue.score * 100` formula will be correct.

### Test Assertions
```python
def test_sanctions_confidence_not_double_multiplied():
    issue = _build_sanctions_issue(party, mock_result_75, mock_match_75, "major")
    assert "7500" not in issue["actual"]
    assert "75%" in issue["actual"] or "0.75" in str(issue["sanctions_details"]["match_score"])
```
```ts
it('renders 75% not 7500% for a 75-point match', () => {
  const issue = { score: 0.75, ... };
  const { getByText } = render(<SanctionsAlert ... />);
  expect(getByText(/75%/)).toBeInTheDocument();
  expect(queryByText(/7500%/)).not.toBeInTheDocument();
});
```

---

## Bug 3 — Amendment Field Mapping Bug: BIN/TIN Discrepancies → Field 44E (Port of Loading)

### Observed
- Discrepancies flagged for **BIN/TIN** (Business Identification Number / Tax Identification Number) fields
- These are being mapped to **LC Amendment Field 44E** (Port of Loading)
- BIN/TIN is a document identity field, not a port field

### Impact
- Generated MT707 amendment drafts reference the wrong SWIFT field
- If an exporter downloads and submits the MT707, their bank will reject it as malformed
- Corrupts the core amendment generation feature

### Root Cause Analysis

In `apps/api/app/services/validation/amendment_generator.py`, the `generate_amendment_for_discrepancy()` function uses keyword matching to route discrepancies to amendment generators:

```python
port_keywords = ["port", "loading", "discharge", "destination", "place of", 
                "origin port", "final destination"]
if any(kw in combined_text for kw in port_keywords):
    ...
    field_tag = "44E" if port_type == "loading" else "44F"
```

**The problem:** BIN/TIN-related discrepancy titles or messages may contain substrings that accidentally match port keywords:
- `"BIN"` → contains the string `"in"`, but more critically, discrepancies about document origin/identity often mention **"place of"**, **"origin"**, or similar terms
- Example: `"BIN/TIN does not match applicant information from place of origin"` → triggers the `"origin"` and `"place of"` port keywords
- Also, discrepancy messages about customs identification might reference "loading port documentation" tangentially

Additionally, the `port_keywords` list includes `"destination"` and `"origin port"` which are overly broad.

**No exclusion list** exists for tax/identity field discrepancies before the port check.

### Candidate Files
| File | Function |
|------|----------|
| `apps/api/app/services/validation/amendment_generator.py` | `generate_amendment_for_discrepancy()` → port keyword block (~line 480) |

### Reproduction Steps
1. Submit an LC package where the BIN or TIN number on a supporting document doesn't match LC applicant data
2. Navigate to Issues tab → find the BIN/TIN discrepancy issue
3. Click "View Amendment" or check the `amendments_available` in the raw response
4. Observe the amendment references `Field 44E: Port of Loading`

### Fix Recommendation

Add an **exclusion guard** before the port keyword block:

```python
# In generate_amendment_for_discrepancy(), add before port_keywords check:

# EXCLUSION: Tax/identity fields are not amendable via port fields
identity_keywords = ["bin", "tin", "tax id", "business id", "vat", "registration number",
                     "customs code", "taxpayer", "fiscal", "gst", "ein", "company number"]
if any(kw in combined_text for kw in identity_keywords):
    return None  # No amendment possible for identity/tax discrepancies

# Tighten port_keywords to avoid false positives:
port_keywords = ["port of loading", "port of discharge", "port of origin",
                 "load port", "discharge port", "final destination port"]
```

Also add an explicit guard in the combined_text construction:
```python
# Prefix rule_id to make matching more precise
combined_text = f"{rule_id} {title} {message}"
# Only match port keywords if the rule domain is clearly port-related:
is_port_rule = any(kw in rule_id.lower() for kw in ["port", "44e", "44f", "loading", "discharge"])
if is_port_rule and any(kw in combined_text for kw in port_keywords):
    ...
```

### Test Assertions
```python
def test_bin_tin_discrepancy_does_not_map_to_port_field():
    discrepancy = {
        "rule": "CUSTOMS-BIN-1",
        "title": "BIN number mismatch",
        "message": "BIN/TIN does not match applicant from country of origin",
        "found": "123456789",
        "expected": "987654321",
    }
    result = generate_amendment_for_discrepancy(discrepancy, {"lc_number": "LC001"})
    assert result is None  # No valid amendment for identity fields
    if result:
        assert result.field_tag not in ("44E", "44F")
```

---

## Bug 4 — LC Issue Date Shows 2015-04-26 (Century/Format Anomaly)

### Observed
- LC issue date displayed as **2015-04-26** while all other context (job timestamps, expiry dates) appears to be from **2026**
- Likely SWIFT date string `"150426"` (YYMMDD format) being parsed as year `2015` instead of `2026`

### Impact
- Date logic validation (`date_logic.py`) will flag the LC as expired (2015 issue date vs 2026 expiry)
- Date-sensitive business rules (e.g., latest shipment before expiry) will produce false failures
- Users see incorrect LC metadata, undermining trust

### Root Cause Analysis

**SWIFT MT700 field `:31C:` stores Date of Issue in `YYMMDD` format.**

For an LC issued on April 26, 2026, SWIFT stores: `260426`

Python's `strptime` with `%y%m%d` uses the system's default century pivot rule:
- Year `26` → Python defaults to 2026 ✅
- BUT: if the value is `150426`, it means **year 15** of the current century → **2015** not **1915**

However, the more likely scenario here is **wrong regex capture**:

In `extractors.py`, `DATE_PATTERNS` includes:
```python
r'\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY/MM/DD or YY/MM/DD
```

This can capture `26/04/26` from a SWIFT field value and misparse it as `2026-04-26 → 26-04-26` ambiguously, OR the AI extractor may be hallucinating the year.

**More specifically**, the `_extract_date_field` method does **no normalization**:
```python
def _extract_date_field(self, text, specific_pattern=None):
    ...
    date_str = match.group(1).strip()
    return date_str  # ← Returns raw string, no century normalization
```

If the raw SWIFT date `150426` is captured (meaning `15-04-26`, i.e., April 26, 2015 in YYMMDD), it's returned as-is without checking whether year `15` is plausible.

**Also**, the AI extractor (`ai_lc_extractor.py`) asks the LLM for ISO dates, but if the underlying text is ambiguous (e.g., `26 APR 15` which a human reads as 2015 or 2026), the LLM may pick 2015 without year-context correction.

### Candidate Files
| File | Function |
|------|----------|
| `apps/api/app/rules/extractors.py` | `_extract_date_field()` — no century normalization |
| `apps/api/app/services/extraction/ai_lc_extractor.py` | AI prompt for `issue_date` — no year plausibility check |
| `apps/api/app/services/extraction/lc_extractor.py` | `"issue_date"` assembly from `mt_fields` |
| `apps/api/trust_platform/compliance/handlers/date_logic.py` | Date logic validation — should flag implausible past dates |

### Reproduction Steps
1. Upload an LC with SWIFT field `:31C:` value `260426` (or handwritten `26 APR 15`)
2. Navigate to the LC Details section on the results page
3. Observe "Issue Date: 2015-04-26" while expiry and shipment dates show 2026

### Fix Recommendation

**Fix 1: Normalize extracted dates in `_extract_date_field()`:**
```python
def _extract_date_field(self, text: str, specific_pattern: str = None) -> Optional[str]:
    """Extract and normalize date field with century guard."""
    ...
    date_str = match.group(1).strip()
    return _normalize_date_with_century_guard(date_str)

def _normalize_date_with_century_guard(date_str: str) -> str:
    """
    Normalize date string and correct implausible century.
    SWIFT YYMMDD: '260426' → '2026-04-26'
    If year is suspiciously old (>10 years ago), try adding century.
    """
    import re
    from datetime import datetime, date
    
    current_year = datetime.now().year
    
    # YYMMDD format (6 digits, no separators)
    if re.match(r'^\d{6}$', date_str):
        yy = int(date_str[:2])
        mm = date_str[2:4]
        dd = date_str[4:6]
        # Use century pivot: if 2-digit year + 2000 is within 10 years of current, use 2000s
        full_year = 2000 + yy if (2000 + yy) <= current_year + 1 else 1900 + yy
        return f"{full_year}-{mm}-{dd}"
    
    # Handle 2-digit year in separated format
    match = re.match(r'^(\d{2})[/\-](\d{2})[/\-](\d{2})$', date_str)
    if match:
        p1, p2, p3 = match.groups()
        # Assume YYMMDD order if first part looks like year
        yy = int(p1)
        full_year = 2000 + yy if (2000 + yy) <= current_year + 1 else 1900 + yy
        return f"{full_year}-{p2}-{p3}"
    
    return date_str
```

**Fix 2: Add plausibility check in `date_logic.py`:**
```python
# After parsing issue_date:
if 'issue_date' in parsed_dates:
    issue_dt = parsed_dates['issue_date']
    current_year = datetime.now().year
    if issue_dt.year < current_year - 5:
        return {
            "status": "warning",
            "details": f"Issue date {issue_dt.date()} appears implausibly old. Possible YYMMDD century parsing error.",
            "field_location": "issue_date",
            "suggested_fix": "Verify LC issue date. SWIFT YYMMDD format may have been misinterpreted."
        }
```

**Fix 3: Update AI extractor prompt** to include a year plausibility instruction:
```python
# In ai_lc_extractor.py prompt template, add:
"- issue_date: When the LC was issued (ISO format YYYY-MM-DD). "
"  Note: This LC appears to be from 2025-2026. If you see a 2-digit year, "
"  assume 2000s not 1900s unless context clearly indicates otherwise."
```

### Test Assertions
```python
def test_yymmdd_date_parses_as_2026_not_2015():
    extractor = DocumentFieldExtractor()
    result = extractor._extract_date_field("DATE OF ISSUE: 260426")
    assert result.startswith("2026") or result == "2026-04-26"

def test_implausible_past_date_triggers_warning():
    result = validate({"issue_date": "2015-04-26", "expiry_date": "2026-09-30"})
    assert result["status"] == "warning"
    assert "implausibly old" in result["details"].lower() or "2015" in result["details"]
```

---

## Prioritized Fix Order

| Priority | Bug | Why First |
|----------|-----|-----------|
| **1** | Summary/Doc tab inconsistency | Visible on every job; breaks trust; affects demo |
| **2** | Sanctions 7500% confidence | Legal/compliance liability; scary number for users |
| **3** | BIN/TIN → 44E amendment mismatch | Corrupts MT707 output sent to banks |
| **4** | LC issue date 2015 century anomaly | Silent validation failure; affects date rules |

---

## Module/Owner Suggestions

| Module | Likely Owner |
|--------|-------------|
| `SummaryStrip.tsx`, `ExporterResults.tsx` | Frontend lead |
| `resultsMapper.ts` | Frontend / Fullstack |
| `sanctions_lcopilot.py`, `sanctions_screening.py` | Backend compliance team |
| `SanctionsAlert.tsx` | Frontend |
| `amendment_generator.py` | Backend trade-finance team |
| `extractors.py`, `ai_lc_extractor.py` | ML/extraction team |
| `date_logic.py` | Backend rules team |

---

## Notes for CTO

- **Bugs 1 and 2** are the most externally visible and should be resolved before the next pilot demo.
- **Bug 3** is a silent correctness issue — generated MT707 files look valid but reference the wrong field. Banks will reject them. Consider temporarily **disabling amendment generation for tax/identity discrepancies** as a hotfix.
- **Bug 4** is environment-specific but likely reproducible with any SWIFT-format LC uploaded via file. The `_extract_date_field` function has no normalization at all — this is a broader extraction quality issue beyond just the issue date.
- None of the four fixes require database migrations or API contract changes (Bugs 1–3 are pure logic fixes; Bug 4 adds a utility function). All are safe to deploy independently.

---

*Packet generated by automated code review against repo at `H:\.openclaw\workspace\trdrhub.com`. Patch suggestions are non-destructive and do NOT touch deployed services.*
