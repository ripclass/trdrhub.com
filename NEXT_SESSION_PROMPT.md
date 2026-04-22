# Next Session Prompt — 2026-04-22 (evening)

Paste to start a fresh Claude session. Self-contained, assumes zero memory of prior conversations.

## Current live state (verify before assuming)

- **master:** `7fed5178` — the corpus generator commit. Check with `git log --oneline origin/master -5`.
- **Backend (Render):** `268726b8` live on `srv-d41dio8dl3ps73db8gpg` — stable. Deploy history: `render deploys list srv-d41dio8dl3ps73db8gpg -o json`.
- **Frontend (Vercel):** `VITE_LCOPILOT_IMPORTER_V2=true` flipped on — new `/lcopilot/importer-dashboard/draft-lc` and `/supplier-docs` routes live.
- **Database:** `validation_sessions.workflow_type` column added live 2026-04-22 via manual `alembic upgrade head` job. Verified 13 columns via `curl https://api.trdrhub.com/health/db-schema`.
- **OpenRouter credits:** unknown — last verified out on 2026-04-17 evening. If examiner returns empty + arithmetic backstop runs alone, credits still out.

## What shipped today (2026-04-22)

Importer parity refactor, all four phases, plus smoke verification + corpus generator.

### Timeline of commits

| Phase | Commits | Effect |
|---|---|---|
| Phases 1-4 of importer parity | `02b58492..5aab9849` (27 commits) | Shared components, workflow_type enum, action endpoints, slim sidebars, dashboard auto-refresh |
| Housekeeping | `395deb4e` | Plans/spec captured in-tree, gitignore fixed |
| UX fixes | `71a61d9d` | Sidebar now shows on moment pages; "Upload Draft LC"/"Upload Supplier Docs" labels; Start New card dropped from dashboard |
| Corpus generator | `7fed5178` | 36 PDFs across 4 trade corridors for Playwright fixtures; zero jurisdiction hardcoding |

### Live state of importer flows

- `/lcopilot/importer-dashboard` → stats + recent activity + quota banner (Start New card removed)
- `/lcopilot/importer-dashboard/draft-lc` → Moment 1 page, sidebar visible
- `/lcopilot/importer-dashboard/supplier-docs` → Moment 2 page, sidebar visible
- Sidebar: Dashboard / Upload Draft LC / Upload Supplier Docs / Billing / Settings
- `workflow_type` persisted on session, echoed on response, drives ImportResults header copy and action slot (DraftLcActions / SupplierDocActions)

## Smoke-verified on live

Both moments drove the full pipeline end-to-end on 2026-04-22:

| Moment | Extract | Resume | Outcome |
|---|---|---|---|
| importer_draft_lc (US-VN/DRAFT_CLEAN/LC.pdf) | HTTP 200, 13.1s | HTTP 200, 11.4s | 4 findings (1 critical, 2 minor, 1 info) |
| importer_supplier_docs (US-VN/SHIPMENT_CLEAN/ × 7 files) | HTTP 200, 11.6s | HTTP 200, 4.4s | 1 critical |

Run again: `bash scripts/smoke_importer.sh`

## Caveat — corpus generator layout bug

`scripts/build_importer_corpus.py` + `scripts/importer_corpus/render.py`
produce MT700 PDFs with the SWIFT tag in one table cell and value in
another. Real MT700s are inline prose. Vision extractor handles inline
fine, stumbles on split cells.

Symptom: smoke flagged "Missing Currency" on a PDF that literally says
`USD 412,500.00`.

Fix scope: rewrite `_tag_pairs()` in `render.py` to emit inline-prose
format (`32B Currency Code, Amount USD 412,500.00` on one line, not a
table row). ~30 min. Regenerate with
`python scripts/build_importer_corpus.py` and re-smoke.

## Render migration gotcha — RESOLVED 2026-04-22 evening

Earlier in the day CLAUDE.md's "post-deploy runs `alembic upgrade head`"
claim was FALSE — service had no pre/post-deploy command, which is why
the Phase 2 migration didn't land automatically and the smoke test
initially 500'd.

Resolved later the same day in commit `07f449a8` ("Add /health/db-schema
check + move alembic to preDeployCommand") — preDeployCommand now runs
migrations on every deploy. Future backend deploys migrate
automatically.

Still useful: verify via `curl https://api.trdrhub.com/health/db-schema`
after any backend deploy that touches the model. The endpoint returns
per-table column counts and a `missing_columns` list. See
`memory/reference_render_migrations.md` for the manual-run fallback if
preDeploy ever fails.

## Next-session candidate work (priority order)

### 1. Fix corpus generator layout (frontend smoke unblocker)

Path: `scripts/importer_corpus/render.py` → `_tag_pairs()` / `_lc_flow()`
Change: render tag/value as inline paragraph, not two-column table
Verify: regenerate, re-smoke. Expect "Missing Currency" false positive
to disappear.

### 2. Write Playwright specs using the new fixtures

Phase 2/8 + 4/7 from the parity plan were deferred for lack of
fixtures. Fixtures exist now at `apps/web/tests/fixtures/importer-corpus/`.
Three specs to write:
- `tests/e2e/lcopilot/importer-draft-lc.spec.ts` — Moment 1 flow
- `tests/e2e/lcopilot/importer-supplier-docs.spec.ts` — Moment 2 flow
- `tests/e2e/lcopilot/dashboard-updates-on-new-session.spec.ts` — the
  5-second smoke (must pass before Phase 4 is truly done per original plan)

### 3. Secondary cleanup

- `apps/web/src/pages/ImporterAnalytics.tsx` — now unreachable (Phase 4/6
  redirects away from `/importer-analytics`). Can be deleted plus
  its route entry.
- `apps/web/src/pages/ImportLCUpload.tsx` — semi-orphaned legacy upload
  page, routes still point at it but new flow is V2 routes.
- Legacy `api/importer.ts` types — may still reference old
  BankPrecheckResponse shape from before Phase 3/4; worth a pass.

### 4. Expand corpus

Currently 4 corridors (US-VN, UK-IN, DE-CN, BD-CN). More corridors =
`corridors.py` dict additions, nothing else. Ripon asked for world
scale — likely candidates: BR-MX, UAE-TR, AU-ID, MY-SG, TH-VN.

## Quick starter commands

```bash
# Pull latest state
git log --oneline -10
curl -s https://api.trdrhub.com/health/db-schema
render deploys list srv-d41dio8dl3ps73db8gpg -o json | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['status'], d[0]['commit']['id'][:8], d[0]['commit']['message'].splitlines()[0])"

# Re-run smoke
bash scripts/smoke_importer.sh

# Regenerate corpus
python scripts/build_importer_corpus.py

# If migration needed (backend commits with model changes):
render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head" --confirm
curl -s https://api.trdrhub.com/health/db-schema   # verify column count
```

## Credentials (still valid from prior sessions)

- Supabase login: `imran@iec.com` / `ripc0722`
- Supabase project: `https://nnmmhgnriisfsncphipd.supabase.co`
- Anon key: `sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3`

## Standing rules (don't violate)

- **Don't touch `J:\Enso Intelligence\ICC Rule Engine\`** — separate
  Claude workspace. If RulHub needs a change, surface to Ripon.
- **No hardcoded Python validators** per discrepancy class — the AI
  Examiner is the pattern. Only exception: `validate_invoice_arithmetic`
  deterministic backstop.
- **Extraction is a blind transcriber** — no format validation at
  extraction time, no jurisdiction hardcoding.
- **Don't skip Opus veto** when USE_RULHUB_API=True.
- **Vercel plugin hook nags are false positives** — Vite + FastAPI
  repo, not Next.js, not Workflow sandbox.
- **TrdrHub is global** — no Bangladesh-specific defaults in UI, copy,
  field extraction, or validators. If a fixture or test needs specific
  geography, make it parametrized per corridor (see
  `scripts/importer_corpus/corridors.py`).

## Memory pointers (read first when touching importer-side code)

- `memory/project_importer_parity_shipped_2026_04_22.md` — full record
  of what's live, what's deferred, env vars to set
- `memory/project_importer_parity_smoke_verified_2026_04_22.md` — live
  verification results + UX fixes + corpus metadata
- `memory/reference_render_migrations.md` — the post-deploy gotcha
- `memory/project_importer_parity_brainstorm_2026_04_21.md` — original
  4-phase design decisions (superseded by shipped entry but kept for
  audit trail)
