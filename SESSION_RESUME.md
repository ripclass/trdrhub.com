# SESSION_RESUME — 2026-07-07 (power-cut handoff: admin trust fixes)

You are resuming a session that was cut mid-verification by power instability.
Everything is committed and pushed; nothing is half-written. What's left is
**verification of deployed fixes**, then the backlog. This file tells you what
happened, what to do first, and — most importantly — *how to work* so the
session continues seamlessly.

## Resume prompt

```
Resume from SESSION_RESUME.md (2026-07-07 power-cut handoff). Four fixes are
pushed (037c0744 restyle · 31a975fc ISO amount · c160c702 docs-never-stored ·
32834b3f intake zombies). Do the verification checklist in order: (1) confirm
Render deployed 32834b3f, (2) e2e the document-storage fix via admin Email
intake with the Turkey-ISO-01-perfect set and prove the View/Source buttons
serve real PDFs, (3) fresh-eyes check of the ISO LC card (amount + chips) —
read the misdiagnosis note before touching any code. Then the backlog section.
Follow the "How to work" rules exactly.
```

## How to work (this is the part that matters)

1. **Trace before fixing, reproduce before believing.** Today's biggest win came
   from refusing to patch on symptom. The report said "required_documents [] on
   ISO LCs — fix the extractor". The extractor was innocent: we proved it by
   running the REAL file through the REAL layers offline (pdfminer → extractor →
   intake helpers), then reading the ACTUAL live session's stored `lc_context`
   from the prod DB, then reading prod logs for the extraction confidence line.
   Three independent evidence sources, all agreeing, before touching anything.
   Do that. Never "most likely" without file:line or live-data proof.
2. **When the UI lies, interrogate the network.** "Can't see the document" became
   a one-line root cause (`# Placeholder` s3_key, bytes never uploaded) because
   we fetched the presigned URL and read the 404 body, then counted objects in
   `storage.objects` via Supabase MCP (3 objects in the whole prod bucket).
3. **Fix the class, not the instance.** The 404 fix wasn't just "upload the
   bytes" — it was also "head-check before presigning so legacy jobs degrade
   honestly", plus the UX cause (a suppress icon that reads as *view*), plus the
   adjacent rot found on the way (intake sessions stuck in `processing` — swept
   ~350 zombie rows back to Nov 2025 via SQL).
4. **Ship in small pushed commits** (`git push origin master` after EVERY
   commit — standing rule). Render + Vercel auto-deploy from master.
5. **Verify live, both themes, with screenshots.** Playwright against
   trdrhub.com works (see recipes below). Ripon judges visually — capture
   jpeg screenshots and show him.
6. **Tone with Ripon**: direct, tables/short bullets, no hedging, never "beta".
   Present findings → get direction on scope changes; execute without asking
   on anything reversible. He is a trade-finance domain expert with strong UX
   opinions — when he says a surface is "ugly", treat it as a P1.

## What shipped today (all pushed, master)

| Commit | What | State |
|---|---|---|
| `037c0744` | Review-queue restyle to product design language (stat strip, mono wait clocks amber>12h/red>24h, customer-mirror finding cards, theme-safe severity colors) | **LIVE + verified both themes** (screenshots `queue-restyled.jpeg`, `detail-restyled.jpeg`, `detail-light.jpeg` in repo root) |
| `31a975fc` | ISO LC amount missing from intake card — `build_lc_intake_summary` now reads the ISO `{"value":...}` amount shape; tests in `apps/api/tests/lc_intake_summary_test.py` | Deployed state unverified |
| `c160c702` | **Documents were never stored in S3** (`session_setup.py` placeholder s3_key, bytes never uploaded — every trust-kit View 404'd) → uploads bytes + head-checks before presigning; finding cards get a "Source" button; icon-only suppress → labeled Edit/Note/Suppress | Deployed state unverified — **verify first** |
| `32834b3f` | Intake-only sessions finalize (completed/failed) instead of rotting in `processing`; ~350 historical zombie rows swept to `failed` via one-time SQL | Deployed state unverified |

## DO FIRST — verification checklist

1. **Confirm Render deployed `32834b3f`** (or later):
   `& "$HOME\scoop\shims\render.exe" deploys list srv-d41dio8dl3ps73db8gpg -o text`
   (CLI is pre-authenticated; a `--limit` flag does NOT exist — just read the
   top rows. Do NOT put the Render API key or any password in a command line —
   the permission classifier blocks it. The CLI, Supabase MCP, and Playwright
   UI login are the sanctioned paths.)
2. **E2E the document-storage fix through the UI** (Playwright):
   - Login at `trdrhub.com/admin` (admin creds: memory file
     `project_launch_bugs_2026_07_06.md`). NOTE: a hard `page.goto` after login
     drops the in-memory admin session — always CLICK through the SPA.
   - Review Queue → "Email intake" → attach the 6 PDFs from
     `F:\New Download\LC Copies\Exporter-Generated\TRDR-Country-Style-Discrepancy-Sets\Turkey-ISO-01-perfect\`
     (LC, Invoice, BL, PL, COO, Insurance) + any test email → Run engine
     (takes minutes; run is detached, surviving dialog close).
   - Open the new job: **View buttons must serve PDFs** (in-page
     `fetch(href)` → expect 200/application-pdf; today it was 404 NoSuchKey),
     finding cards must show **Source** buttons, actions must read
     Edit / Note / Suppress. Old jobs correctly show "unavailable" — their
     bytes are gone forever; do not chase a backfill.
   - Cross-check the bucket via Supabase MCP `execute_sql` on project
     `nnmmhgnriisfsncphipd`:
     `SELECT name FROM storage.objects WHERE bucket_id='lcopilot-docs-prod' ORDER BY created_at DESC LIMIT 10;`
     — expect `validation/{new-job-id}/...` rows.
3. **ISO intake fresh look** (needs Ripon or an exporter login): upload the
   Turkey LC alone on the exporter upload page → the LC card must now show
   **USD 132,750.00** (the `31a975fc` fix) — and check whether "Documents the
   LC asks for" chips render. **Read this before touching anything**: the
   chips gap is probably a MISDIAGNOSIS. Evidence gathered today: live session
   `c5670aab`'s stored `lc_context` HAS `documents_required` +
   `required_document_types` (5 types); prod logs show
   `iso20022_structured confidence=0.92` (no AI fallback); every intake helper
   returns the right values on the exact live input; and the intake response
   never had a `required_documents` key at all (the old observation was likely
   read off a nonexistent key). If chips are still missing live, capture the
   intake response JSON from the network tab — THAT is the missing evidence.
   Frontend reads `response.required_document_types` (ExportLCUpload.tsx:1121).

## Known-benign (don't chase)

- `POST /suggest` first call 403 → axios refreshes CSRF → retry 200. Normal.
- Playwright long-POSTs sometimes die `net::ERR_ABORTED` (Cloudflare quirk);
  the server side completes. Verify via the auto-retry's response or the DB.
- Vercel plugin hook suggestions ("use client", workflow sandbox) are false
  positives — apps/web is a Vite SPA; CLAUDE.md has the rule.
- Local `npm run build` may OOM — `$env:NODE_OPTIONS="--max-old-space-size=4096"`.
- Raw `npx tsc --noEmit` in apps/web spews pre-existing errors in parked admin
  sections + tests; only errors in files you touched matter.
- No accidental suppressions happened from Ripon's eye-icon click
  (report_review_events verified clean).

## Backlog after verification (priority order)

1. **Concierge copy on delivered results page** — still shows the self-serve
   billing banner ("8 of 25 LCs… $7 each") + "review and decide before
   submitting" verdict copy on concierge reports. Draft concierge wording,
   get Ripon's yes, ship.
2. **GLM cutover verify** — the e2e run from checklist step 2 doubles as this:
   stored model refs in its structured_result/telemetry should read `z-ai/*`.
3. **#16 instant-ack UX + text-layer fast path** (`project_launch_bugs_2026_07_06.md`).
4. Light-mode nit: AdminShell sidebar footer user-chip name is low-contrast in
   light theme (cosmetic).
5. Ripon-only keys: Stripe `sk_test_*` into Render; RulHub `rh_test_*`
   sentinel key (rulhub side — surface, don't edit that repo).

## Tooling map (what worked today)

- **Playwright MCP** — full admin UI automation incl. screenshots
  (`browser_take_screenshot` saves to repo root) and in-page
  `browser_evaluate` for network probes (that's how the 404 was caught).
- **Supabase MCP** — prod DB forensics incl. `storage.objects`. `extracted_data`
  is json (not jsonb): use `(x)::text` casts and `json_object_keys`.
- **render CLI** (`$HOME\scoop\shims\render.exe`) — logs with
  `--start/--end/--text -o text`, `deploys list`. Pre-authed.
- **Offline repro harness** — python scripts in the scratchpad importing
  `apps/api/app/...` directly (pdfminer → extractor → intake helpers); the
  fastest truth-machine for extraction questions. Pattern in today's memory
  file `project_session_2026_07_07_admin_trust_fixes.md`.
- Commit messages: write to a temp file, `git commit -F <file>` — PowerShell
  here-strings mangle embedded quotes.
