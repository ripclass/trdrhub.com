# TRDR Live Handoff — 2026-03-17

## Current state
Work today centered on LCopilot classification / requirement-contract integrity and real-set audits.

### Canonical classification refactor
A major refactor was designed and reportedly committed around:
- `cc6c093606022fb883f9a7e00d8d0cc44609ff75`
- message: `refactor(lcopilot): canonicalize lc classification and required-document contract`

Core model intention:
- separate `format_family`
- separate `format_variant`
- separate `instrument_type`
- separate `workflow_orientation`
- preserve attributes separately
- preserve canonical `required_documents[]`
- treat legacy `lc_type` as workflow-only alias

## Important truth
Even after this refactor, live/real-sample behavior still showed that extraction can be substantially correct while top-line workflow/type presentation remains wrong or overly scary.

Key preserved conclusion:
- extraction layer is increasingly capable
- product-truth / workflow-orientation / cross-surface consistency is still the fragile seam

## High-value real samples / paths
### 1) MT700 generated set audit
Audited set:
- `F:\New Download\LC Copies\Exporter-Generated\all-v3-mixed-lc-40iso\set_022_100924060096`

Critical clarification:
- despite earlier assumptions, this is **not ISO**
- it is an **MT700** set

### Findings from that set
Three failure layers were identified:
1. **Generator-loss upstream**
   - original MT source richer than generated `LC.pdf`
   - `46A/47A` materially reduced before LCopilot even sees the file
2. **Backend defects**
   - compact `46A` normalization inconsistent
   - `INSURANCE` could degrade to `other_specified_document`
   - `PL` could disappear
   - beneficiary / weight dispatch missing
   - inspection extraction too shallow
   - MT block payload could be dropped downstream
3. **Frontend/product-contract defects**
   - workflow alias shown as generic `Type`
   - supporting-doc labels/icons incomplete/corrupted
   - warning severity and readiness could drift from backend truth

### Reported surgical fix pass outcome
A later surgical fix pass claimed these seams were moved:
- compact MT700 required-doc normalization improved
- beneficiary + weight docs gained explicit dispatch/extraction
- upload wording changed from misleading `Type`
- placeholder `47A` handling became more honest
- MT blocks hydrated from raw text
- readiness / severity distortion reduced

### Remaining limitation
Still preserve this explicitly:
- generator-loss remains upstream
- LCopilot cannot recover 46A/47A detail that never made it into generated PDFs

### 2) Ideal exporter sample — still-open seam
Sample:
- `F:\New Download\LC Copies\Synthetic\Export LC\IDEAL SAMPLE`

Live truth before the latest route-level diagnosis:
- production rerun still returned `workflow_orientation: unknown`
- production rerun still returned `lc_type: unknown`
- applicant / beneficiary / ports / instrument / required docs were all present
- this proved the problem was still a **backend truth-path issue on live**, not stale frontend cache

## Stronger route-level diagnosis
The stronger likely live seam identified later was in:
- `apps/api/app/services/lc_classifier.py`
- `detect_lc_type()`

Diagnosis summary:
- exporter-lane fallback required explicit normalized `*_country` fields
- live sample used country-bearing raw port strings like:
  - `CHITTAGONG SEA PORT, BANGLADESH`
  - `NEW YORK, USA`
- those raw strings were not treated as valid country signals
- result: the real `/api/validate` path never computed `export` in the first place, so `LC-TYPE-UNKNOWN` propagated cleanly all the way through

### Reported patch readiness for that seam
A subsequent focused patch was reported as `FIX_READY` for exactly that route-level issue:
- extend country-signal detection to accept explicit country suffixes embedded in raw port strings
- add focused regression coverage (`lc_workflow_live_route_test.py`)
- preserve ambiguity only when ports truly lack country-bearing evidence

### Important current status
This specific route-level fix still needed real live redeploy + retest confirmation after the report. Preserve this as the immediate next truth test.

## TBML / rulesets context
### Repo/local rule inventory
`trdrhub.com\Data` contains large local rule inventories; `_UPLOAD_GUIDE.md` says roughly:
- 110 files
- 3230+ rules

### Live/admin evidence
Active AML-TBML rulesets were reported in admin/live context, including:
- `AML-TBML:real-case-high-signal`
- `AML-TBML:sanctions-pep-enhanced`
- `AML-TBML:document-behavioral-signals`
- `AML-TBML:counterparty-network-risk`
- `AML-TBML:route-logistics-anomaly`
- `AML-TBML:quantity-weight-mismatch`
- `AML-TBML:pricing-anomaly`

### Local-source reality
Their exact local JSON source files were **not** found in obvious repo/data locations.
Interpretation preserved:
- this does **not** mean DB is wrong
- likely manually created copies live somewhere else across local drives
- current need is recovery/location, not curation/governance cleanup yet

Notable filesystem clue found:
- `F:\New Download\LC Copies\Real Sample-Flagged-TBML\`
contains TBML-related sample documents, but not obvious ruleset JSON filenames.

## Recommended next moves
1. Deploy/retest the **route-level raw-port-country workflow fix** for the IDEAL SAMPLE and verify live payload no longer returns `workflow_orientation = unknown` / `lc_type = unknown`.
2. If still broken after that, trace the exact live `/api/validate` payload build path again — but only after confirming the route-level fix actually reached production.
3. If the set_022 surgical fixes are not yet fully live, deploy them and rerun that set too.
4. For TBML source recovery, do targeted filename/path searches around likely non-repo working folders instead of broad full-drive crawls.

## Tone reminder
Ripon is frustrated by repeated shallow passes and contradictory “beta ready” claims. For future work:
- prefer truth over optimism
- say plainly when something is only partly working
- verify on real sets, not just fixtures
- do the work directly in-session; no agent delegation unless explicitly asked
- prefer global/canonical fixes over hard-coded shortcut patches

## 2026-03-18 — exporter review truth pass (results shell + issues + documents + overview)
A focused exporter review-truth pass was completed locally and prepared for clean commit/push.

Files changed:
- `apps/web/src/pages/ExporterResults.tsx`
- `apps/web/src/lib/exporter/resultsMapper.ts`
- `apps/web/src/pages/exporter/results/tabs/IssuesTab.tsx`
- `apps/web/src/lib/exporter/overviewTruth.ts`
- `apps/web/src/__tests__/ExporterResults.test.tsx`

### What this pass fixes
1. **Terminal results-shell truth**
   - if job status is already terminal but canonical results payload is missing, exporter results no longer lies with `Validation in progress`
   - page now shows a terminal no-results / route-state mismatch state with explicit retry and return-to-review-shell actions
   - this was identified from live same-browser verification of job `e2d4b924-16a7-46cf-9e99-e93243dcae67`

2. **Issue count semantics**
   - mapped issues now carry `count_class` and `presentation_impact`
   - documentary discrepancy totals no longer silently include compliance/manual-review items
   - Issues tab summary now separates:
     - documentary discrepancy severity counts
     - compliance alerts
     - manual review items
     - total issues

3. **Document card truth layering**
   - document cards now explicitly separate:
     - `Extraction truth`
     - `Requirement coverage`
     - `Review consequence`
   - this replaces the older vague single-badge feel (`Verified` / warnings) that could blur extraction success with presentation readiness

4. **Overview duplication cleanup**
   - top-level summary ownership stays with `SummaryStrip`
   - Overview body no longer re-renders the same top-line metrics again through duplicated summary cards
   - support metrics now act as secondary context instead of competing with readiness

### Verification state
- focused tests for the implemented seams were updated and used during the session
- document-truth focused test slice passed after cleanup
- broader overview tests still contain older expectations tied to prior copy/layout and should be normalized later
- live same-browser verification against production confirmed the deployed app was still on the old route/shell behavior, meaning local fixes were not yet live at the time of this handoff

### Important repo-state note
While implementing these seams, several files were found with pre-existing duplicated tail fragments / corrupted appended blocks that caused misleading syntax/transform failures. These had to be surgically cleaned while preserving the actual logic changes. If similar compile failures recur in these exact exporter files, inspect file tails for accidental duplicate append blocks before assuming a new logic regression.

## 2026-03-18 — follow-up live stuck-state fix in `useCanonicalJobResult`
After deploy, live verification on job `3f26aba2-6ce9-464d-a65e-d3454391ea12` still showed:
- `Validation in progress`
- `Current status: Completed`

That proved the earlier page-level terminal no-results branch was not sufficient by itself.

### Root cause
The remaining seam was in `apps/web/src/hooks/use-lcopilot.ts` inside `useCanonicalJobResult`:
- hook-level `isLoading` still trusted lingering polling/loading state
- so a terminal job with no results payload could continue to surface as generic loading
- consequence: `ExporterResults.tsx` never escaped the loading shell, even though job status was already terminal

### Follow-up fix
`useCanonicalJobResult` now derives:
- `isAwaitingInitialState`
- `isTerminalWithoutResults`

and `isLoading` is now suppressed for the terminal-without-results case.

Effectively:
- terminal completion without canonical results is no longer allowed to masquerade as ordinary loading
- this allows the already-shipped terminal no-results UI state in `ExporterResults.tsx` to actually render on live routes

### Verification
Focused test passes:
- `shows a terminal no-results state instead of pretending validation is still running`

### File changed
- `apps/web/src/hooks/use-lcopilot.ts`

## 2026-03-18 — follow-up hung results-request escape hatch
A later live report on job `065b3748-c5cc-48ea-863b-5261f48725af` showed the same contradictory state still persisting even after long delay:
- `Validation in progress`
- `Current status: Completed`
- still stuck after ~30 minutes

### Stronger diagnosis
That narrowed the remaining seam further:
- this was not only lingering poll state
- the terminal results request path itself can hang long enough to keep the shell in perpetual loading

### Follow-up fix
`apps/web/src/hooks/use-lcopilot.ts`
- added `terminalResultsTimedOut`
- when job status is terminal, results are still absent, and results-loading remains stuck, the hook now times out that generic loading state after 4 seconds
- this prevents a hung `/api/results` path from keeping the review shell in fake in-progress mode forever

### Verification
Focused test still passes:
- `shows a terminal no-results state instead of pretending validation is still running`
