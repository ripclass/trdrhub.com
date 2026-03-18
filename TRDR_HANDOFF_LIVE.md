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

## 2026-03-18 — deploy repair for `f163ddb`
The first deployment of commit `f163ddb` failed in Vercel with an esbuild syntax error (`Unexpected "}"`).

### Actual cause
`apps/web/src/hooks/use-lcopilot.ts` still contained a duplicated tail fragment after the real file end (same class of file-tail corruption seen earlier in other exporter files). The duplicate block started after the real `useValidationHistory` return and introduced an extra closing brace sequence.

### Repair
- removed the duplicated tail fragment from `apps/web/src/hooks/use-lcopilot.ts`
- reran `npm run build` inside `apps/web`
- local production build succeeds now

### Important lesson
When exporter fixes touch this file, always check the file tail for duplicate append junk before trusting a deploy/build failure at face value.

## 2026-03-18 — architecture/performance framing correction
Ripon clarified the correct engine framing for the backend:
- `AI-first`
- `deterministic`
- `veto`

This is the actual 3-layer model.
Do **not** describe it as “AI-first + 3 more layers”.

## 2026-03-18 — fresh audit direction on validation speed
A later architecture audit was started after Ripon pushed back on the earlier simplification. Confirmed code facts from the repo:
- AI-first extraction is already on the hot path in `apps/api/app/routers/validate.py`
- launch extraction boundary exists in `apps/api/app/services/extraction/launch_pipeline.py`
- AI-first extractors exist for LC / invoice / BL / packing list / COO / insurance / inspection
- validate route still appears to combine many heavy responsibilities in one request path:
  - OCR/text extraction
  - launch-pipeline / AI-first extraction
  - two-stage validation / normalization
  - requirement parsing
  - sanctions / policy / risk work
  - response shaping / final contract assembly
  - persistence/session updates

### Working conclusion
The current likely performance problem is **not** that AI-first is missing.
The likely problem is that AI-first is embedded inside a very large synchronous validation route, so first useful review is delayed by downstream deterministic/veto/shaping work.

### Next best step
Run a proper code audit of the exporter validation hot path using the correct 3-layer framing:
- AI-first
- deterministic
- veto

The goal of that audit should be:
1. confirm the real hot path
2. identify what is already good and worth preserving
3. rank actual bottlenecks
4. separate confirmed facts from inference
5. produce a refactor-first plan before implementation starts

### Team/work style reminder
How Ripon and the assistant are working together right now:
- Ripon sets direction, product truth, and quality bar
- assistant implements and verifies directly in code/live product
- Codex can be used as a **thorough reviewer/auditor**, but not as a substitute for clear direct implementation work
- no hardcoded patches
- no shortcuts
- no shallow surface-only fixes
- deepest correct seam first
- finish the last mile properly
- update handoff + memory on every real commit
- be genuinely helpful, not performative

## 2026-03-18 — extraction architecture correction: multimodal-first seam started
Ripon clarified the extraction intent unambiguously:
- extraction must be **true file-native multimodal first**
- PDFs/images should go to the frontier model first
- OCR/native text should be fallback/support evidence, not the primary extraction gate
- this is separate from the validation engine; validation remains the 3-layer model:
  1. AI-first
  2. deterministic
  3. veto

### Confirmed repo truth before refactor
The live extraction path was audited and confirmed to be:
- `file -> OCR/native parse -> text -> AI extraction`

That meant the existing "AI-first extraction" implementation was actually **text-first in runtime terms**, because the model was receiving OCR/native text (`raw_text`) rather than the original PDF/image as the primary input.

### Why this mattered
This explained both major complaints:
- slow extraction on messy PDFs/images
- extraction failures despite strong frontier models

The root issue was not frontier capability; it was that the live extraction seam still depended on OCR/text recovery before AI saw the document.

### Refactor started in repo
A real extraction-only refactor was started in the backend to move the live path toward multimodal-first.

#### New file added
- `apps/api/app/services/extraction/multimodal_document_extractor.py`

What this new module does:
- accepts real uploaded PDF/image bytes
- renders PDFs to page images
- sends document pages directly to multimodal models
- uses OCR/native text only as secondary support context in the multimodal prompt
- covers the finite supported trade-doc family map rather than a tiny pilot:
  - LC / SWIFT / LC application
  - invoice / proforma
  - transport docs
  - packing list
  - COO / regulatory / customs / licenses
  - insurance / beneficiary / special certificates
  - inspection / testing / weight / measurement
  - generic supporting docs

#### Live-path wiring completed so far
- `apps/api/app/routers/validate.py`
  - `LaunchExtractionPipeline.process_document(...)` now receives real `file_bytes` + `content_type`
  - extraction timing instrumentation was also added for:
    - OCR
    - launch pipeline
    - two-stage validation
    - total per-document time
- `apps/api/app/services/extraction/launch_pipeline.py`
  - now imports the new multimodal extractor
  - now attempts multimodal-first before the old text-fed AI extractor for:
    - LC-like docs
    - invoice
    - transport/BL
    - packing list
    - COO/regulatory
    - insurance/beneficiary
    - inspection/weight families
    - generic supporting docs

### Current status at handoff
- code compiled successfully after the seam change (`py_compile` on `multimodal_document_extractor.py`, `launch_pipeline.py`, and `validate.py`)
- the live extraction route is now structurally capable of handing real upload bytes into a multimodal-first extractor before falling back to the old text-fed path
- this is a real root-seam move, not a toy side-path

### Important unfinished truth
This pass is **not finished yet**.
Still pending:
1. reduce/remove duplicate route-owned extraction logic that still exists downstream of the launch pipeline
2. verify the new multimodal-first path on real LC-first + bulk supporting-document uploads
3. decide whether any doc-family-specific shaping/verification needs tightening after real runs
4. only then commit/deploy the next clean extraction stage

### Next session starting point
Resume from the extraction seam, not from validation.
Immediate next move:
- continue making `LaunchExtractionPipeline` the authoritative extraction boundary
- reduce route-owned duplicate extraction after launch-pipeline handling
- test real LC-first intake + unlocked supporting-doc bulk upload against the new multimodal-first path

## 2026-03-18 — extraction boundary cleanup + LC-first mixed-batch regression locked
A real follow-up pass was completed on the multimodal-first extraction seam.

Files changed:
- `apps/api/app/routers/validate.py`
- `apps/api/app/services/extraction/launch_pipeline.py`
- `apps/api/tests/test_build_document_context_boundary.py`

### What this pass fixed
1. **Route-owned duplicate extraction removed after launch-pipeline handling**
   - `_build_document_context()` no longer runs a second AI/regex extractor stack for LC/invoice/BL/packing/COO/insurance/inspection after `LaunchExtractionPipeline.process_document(...)`
   - practical effect: launch pipeline is now the authoritative structured-extraction boundary for handled docs
   - route fallback is now limited to preserving raw/native evidence for unhandled docs instead of re-owning structured extraction

2. **LC-first batch-state continuity tightened**
   - once an LC lands through the launch pipeline, `_build_document_context()` now refreshes `lc_required_document_types` from the extracted LC payload in the same batch
   - this fixes the stale-state seam where LC-required supporting-doc expectations could remain empty while later files in the same batch were processed

3. **Broader trade-document family canonicalization tightened inside launch pipeline**
   - launch pipeline now canonicalizes more aliases into the right structured families instead of silently falling through:
     - transport family additions include `forwarder_certificate_of_receipt`, `warehouse_receipt`, `cargo_manifest`
     - regulatory family aliases route through the COO/regulatory boundary
     - insurance/special-certificate aliases route through the insurance boundary
     - inspection/weight/testing aliases route through the inspection boundary
   - naming mismatches like `manufacturer_certificate` / `conformity_certificate` were also normalized so subtype detection and completeness logic stop drifting

4. **Focused regression added for the real intended upload pattern**
   - new test: `apps/api/tests/test_build_document_context_boundary.py`
   - verifies `_build_document_context()` on:
     - LC uploaded first
     - mixed supporting-doc batch after
     - launch pipeline mocked as the sole structured extractor boundary
   - test proves the LC-first batch behavior survives with no route-owned structured-extraction fallback

### Verification state
Focused extraction regression slice passes:
- `tests/mt700_required_docs_continuity_test.py`
- `tests/test_mt_pipeline_contract.py`
- `tests/test_iso_runtime_shape.py`
- `tests/test_build_document_context_boundary.py`

Result at verification time:
- `12 passed`

### Important current truth
This is a meaningful boundary cleanup, not the full extraction refactor finish line.
Still not yet proven in this pass:
- true end-to-end live `/api/validate` multipart verification with real LC-first + bulk supporting files
- real production behavior of the multimodal-first path on messy PDFs/images across the broad trade-doc universe

### Best next move after this commit
- deploy this extraction-boundary cleanup
- then run a real LC-first + mixed supporting-doc upload against live/staging to verify the multimodal-first path behaves correctly beyond focused regression coverage

## 2026-03-18 — live results crash follow-up: `terminalResultsTimedOut` runtime regression
A later live validation run exposed a separate frontend regression after validation completed.

### Live symptom
Ripon hit a post-validation results crash with runtime error:
- `ReferenceError: terminalResultsTimedOut is not defined`

This appeared after validation, so it was a **results rendering regression**, not proof that extraction had failed.

### Root cause
In:
- `apps/web/src/hooks/use-lcopilot.ts`

`useCanonicalJobResult()` still referenced `terminalResultsTimedOut` inside its returned `isLoading` computation, but the timeout state itself was no longer defined in the hook.

### Follow-up fix prepared
The local fix restores the missing terminal-results timeout state/logic so that:
- terminal job + missing canonical results payload + hung `/api/results` path
- no longer crashes on undefined state
- no longer keeps pretending the results page is still generically loading forever

Also cleaned another duplicated/corrupted tail fragment in the same hook file while patching.

### Important truth
This fix addresses the concrete runtime crash Ripon saw live.
However, focused web tests in this branch are already broadly noisy/red in unrelated areas, so do **not** overstate this as a fully green frontend test pass. Treat it as a source-level runtime fix for the observed crash.

### Immediate next move after push
- redeploy
- rerun live validation
- confirm results page renders instead of crashing on `terminalResultsTimedOut`
- only then continue performance / multimodal-first proof work

## 2026-03-18 — backend results seam fix: completed job with no canonical payload
After the frontend crash was fixed, live validation exposed the next honest seam: results page could show a completed job but still say canonical results were unavailable.

### Root cause
In `apps/api/app/routers/jobs_public.py`:
- `/api/jobs/{job_id}` could report the session as completed whenever `validation_results` existed
- but `/api/results/{job_id}` only accepted a narrow version-tagged `structured_result_v1` payload shape via `_extract_option_e_payload()`

That meant a job could be **Completed** while the results route still 404'd with:
- `error_code: no_structured_result`

if the stored payload was valid-but-unversioned or nested differently.

### Fix applied
- broadened structured-result detection to accept legacy/unversioned but clearly valid structured payloads
- normalized accepted payloads into canonical shape
- backfilled `version: structured_result_v1`
- synchronized `documents` / `documents_structured`
- self-healed the stored session payload by writing normalized nested `structured_result` back when served

Files changed:
- `apps/api/app/routers/jobs_public.py`
- `apps/api/tests/test_jobs_public_results_payload_shape.py`

### Verification
Focused API slice passed:
- `apps/api/tests/test_jobs_public_debug_trace.py`
- `apps/api/tests/test_jobs_public_results_payload_shape.py`
- result: `4 passed`

### Immediate next move after this push
- redeploy
- rerun the same live validation case
- verify completed jobs now actually resolve through `/api/results/{job_id}` instead of landing in the terminal no-results state

## 2026-03-18 — deeper results recovery fix: completed sessions with no persisted canonical results
A live job (`93f0fd67-cc0a-408d-a903-735f96d83dc1`) showed that even after payload-shape normalization, `/api/jobs/{job_id}` could still prove only that the session row, documents, and extraction trace existed — not that `validation_results` had actually been persisted.

### What the live evidence proved
The job status payload showed:
- `status: completed`
- `documentCount: 8`
- non-empty `debug_extraction_trace`

That means:
- session row exists
- documents are persisted
- extraction trace is persisted in `extracted_data`

But it still does **not** guarantee canonical `validation_results` exists.

### Deeper fix applied
In `apps/api/app/routers/jobs_public.py`:
- if `/api/results/{job_id}` cannot extract canonical results for a completed session,
- it now builds a minimal fallback `structured_result_v1` from persisted session data:
  - session documents
  - document extracted fields
  - discrepancies
  - extracted_data / LC number
  - basic analytics
  - processing summary
  - submission eligibility / bank verdict placeholders
- then self-heals the session by writing that fallback into `validation_results["structured_result"]`

This is stronger than the prior fix because it recovers even when the canonical results payload was never persisted at all.

Files changed:
- `apps/api/app/routers/jobs_public.py`
- `apps/api/tests/test_jobs_public_results_payload_shape.py`

### Verification
Focused API slice passed:
- `apps/api/tests/test_jobs_public_debug_trace.py`
- `apps/api/tests/test_jobs_public_results_payload_shape.py`
- result: `5 passed`

### Immediate next move after this push
- redeploy
- rerun the exact same live validation URL/job
- confirm completed session now renders results instead of terminal no-results fallback

## 2026-03-18 — production routing seam found: root Vercel config swallowing `/api/*`
After multiple backend fixes still failed live, direct probing of `https://trdrhub.com/api/results/{job_id}` returned:
- `{"detail":"Not Found"}`

That proved the live request was **not reaching** the backend results route at all.

### Root cause
Repo contains two Vercel configs with conflicting behavior:
- one config correctly rewrites `/api/(.*)` to `https://trdrhub-api.onrender.com/$1`
- but the **root `vercel.json`** used for the main deploy only rewrote:
  - `/(.*)` -> `/index.html`

So production `trdrhub.com` swallowed `/api/results/*` into the SPA deployment instead of forwarding it to Render.

### Fix applied
Patched root `vercel.json` to add the missing API proxy rewrite before the SPA catch-all:
- `/api/(.*)` -> `https://trdrhub-api.onrender.com/api/$1`
- then fallback `/(.*)` -> `/index.html`

### Why this matters
This is the real production fix for the live symptom where:
- frontend called `/api/results/{job_id}`
- but `trdrhub.com` returned `{"detail":"Not Found"}`

No backend payload/result fixes can help until this routing seam is deployed.

### Immediate next move after this push
- redeploy web on Vercel
- probe `https://trdrhub.com/api/results/{job_id}` directly again
- verify it now reaches Render instead of 404ing at the web origin
- then re-open the same live results page

## 2026-03-18 — actual active Vercel rewrite fixed in `apps/web/vercel.json`
After confirming production was already on commit `7d3ea08`, direct probing clarified the last routing mismatch:

### Live probe results
- `https://trdrhub.com/api/results/{job_id}` -> `404 Not Found`
- `https://trdrhub-api.onrender.com/api/results/{job_id}` -> `403 Not authenticated`
- `https://trdrhub-api.onrender.com/results/{job_id}` -> `404 Not Found`

### What that proved
The backend route is real at:
- `/api/results/{job_id}`

So if the web origin had been rewriting correctly, `trdrhub.com/api/results/...` should have surfaced the backend response shape instead of a plain 404.

### Root cause
The **active app-level Vercel config** in `apps/web/vercel.json` had this rewrite:
- `/api/(.*)` -> `https://trdrhub-api.onrender.com/$1`

That strips the `/api` prefix and incorrectly turns:
- `/api/results/{job_id}` into `https://trdrhub-api.onrender.com/results/{job_id}`

which does not exist.

### Fix applied
Patched `apps/web/vercel.json` to:
- `/api/(.*)` -> `https://trdrhub-api.onrender.com/api/$1`

This is the actual live production rewrite fix for the web origin.

### Immediate next move after this push
- redeploy web again
- probe `https://trdrhub.com/api/results/{job_id}`
- confirm the web origin now returns the backend-style response instead of 404
- then re-open the same live results page

## 2026-03-18 — auth-hydration mitigation on terminal results fetch
After production routing was fixed, direct browser probing of `https://trdrhub.com/api/results/{job_id}` returned:
- `{"detail":"Not authenticated"}`

That is expected for a direct address-bar hit, because the endpoint requires bearer auth and the browser location bar does not send the JS-added Authorization header.

### Remaining likely seam
Inside the actual app flow, terminal results fetch can still race with frontend auth/session hydration:
- results page calls `/api/results/{job_id}`
- Supabase/backend token is not yet attached on the first terminal fetch
- backend returns 401/403
- UI falls too quickly into terminal no-results/error state

### Mitigation applied
In `apps/web/src/hooks/use-lcopilot.ts`:
- detect auth-hydration style results errors (401/403 / not authenticated)
- when they occur during automatic terminal results fetch, retry instead of surfacing immediately
- track a short auth-retry window (`authRetryCount`)
- keep terminal results in a loading/retrying state while auth settles instead of immediately concluding no-results

### Important truth
This is a frontend resilience mitigation for likely auth-hydration races. It does not change backend auth rules. Direct unauthenticated hits to `/api/results/{job_id}` should still return auth errors.

### Immediate next move after this push
- redeploy web
- open the in-app results page again (not the raw URL directly)
- confirm the page either resolves after auth settles or at least no longer falls prematurely into terminal no-results due to an early 401/403 race

## 2026-03-18 — frontend results-shape normalization fix for real API payload
Live network evidence finally showed the strongest truth yet:
- in-app request to `https://api.trdrhub.com/api/results/{job_id}` succeeds with a **full valid payload**
- response shape is `{ job_id, jobId, structured_result, telemetry, ... }`
- but the page still fell into the terminal no-results state anyway

### Root cause
The frontend hook/page contract was still too strict about result shape.
`useCanonicalJobResult()` could store/use results as though a loaded payload had already been transformed into the exact `ValidationResults` object the page expects.
In reality, the API was returning a valid wrapped payload with `structured_result`, but the hook was not normalizing that shape decisively enough before downstream gating logic.

### Fix applied
In `apps/web/src/hooks/use-lcopilot.ts`:
- added explicit `normalizeValidationResultsResponse()`
- if API returns `{ structured_result, jobId/job_id, ... }`, normalize it into the expected `ValidationResults` shape
- normalize cached query data the same way
- normalize fresh fetches before storing them in hook state
- if payload truly lacks usable structured result, then surface a real results error instead of silently treating it like absent loaded state

### Why this matters
At this point:
- routing is fixed
- auth reaches backend
- results payload exists

So the remaining blocker became a frontend normalization/render contract bug, not a backend availability issue.

### Immediate next move after this push
- redeploy web
- reopen the same in-app results page
- verify that the successful `/api/results/{job_id}` payload now renders instead of falling into the terminal no-results branch
