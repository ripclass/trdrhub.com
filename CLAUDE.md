# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

TRDR Hub is a Turbo monorepo (`lcopilot`) shipping **LCopilot** — a production-quality LC (Letter of Credit) validation engine for trade finance. Exporter-first, with importer converging on the same spine. Bank is parked. **Do not call it "beta"** — one tool, production quality, not 16 half-done tools.

## Monorepo Layout

| Path | Stack | Role |
|---|---|---|
| `apps/api` | FastAPI, SQLAlchemy, Alembic, PostgreSQL | Auth, validation pipeline, result persistence, exporter/importer APIs |
| `apps/web` | React 18, Vite 7, TailwindCSS, shadcn/ui | Login, dashboards, upload, results, customs pack, history |
| `packages/shared-types` | TypeScript + Zod | Shared API contracts; also generates Python stubs |

## Commands

### Root (Turbo orchestration)

```bash
npm install              # Install all workspaces
npm run build            # Build all apps/packages
npm run dev              # Dev servers for all apps
npm run test             # Tests across monorepo
npm run type-check       # TypeScript checking
npm run lint             # Lint all
```

### Frontend (`apps/web`)

```bash
npm run dev              # Vite dev server (port 5173)
npm run build            # Production build → dist/
npm run test             # vitest run
npm run type-check       # tsc --noEmit
npm run lint             # eslint
npm run test:e2e         # Playwright end-to-end
npm run test:e2e:ui      # Playwright with UI
npm run test:e2e:lcopilot # LCopilot-specific E2E tests
```

### Backend (`apps/api`)

```bash
uvicorn main:app --reload                  # Dev server (port 8000)
pytest tests/ -v                           # All tests
pytest tests/ -v -m "not slow"             # Fast tests only
pytest tests/integration/ -v               # Integration tests
pytest tests/test_textract_fallback.py -v  # OCR tests
make lint                                  # flake8 + black + isort + mypy
make format                                # black + isort auto-fix
alembic upgrade head                       # Apply DB migrations
alembic revision --autogenerate -m "msg"   # Create migration
```

Python formatting: `black --line-length=127`, `isort --profile black`.

### Shared Types (`packages/shared-types`)

```bash
npm run build            # tsc compile
npm run dev              # tsc --watch
npm run generate-python  # Generate Python schema stubs
```

## Canonical Architecture

### The 3-part mental model

LCopilot's validation flow is split into three discrete stages. When a bug or feature lands, classify it by part before touching anything.

```
 ┌────────────────────────────────────────┐
 │  PART 1 — AI-first Extraction          │   ← current focus
 │   Vision LLM → swift_mt700_full regex  │
 │   → ai_first text fallback → canonical │
 │   LCDocument → Extract & Review screen │
 └────────────────────────────────────────┘
                  │
                  ▼ user confirms fields
 ┌────────────────────────────────────────┐
 │  PART 2 — AI-first Validation          │   ← frozen, don't touch
 │   L1 (cheap GPT, 75%) → L2 (Sonnet,    │
 │   20%) → L3 (Opus, 5% for TBML/fraud)  │
 │   → Deterministic rules → Veto         │
 └────────────────────────────────────────┘
                  │
                  ▼
 ┌────────────────────────────────────────┐
 │  PART 3 — Output / Customs Pack        │   ← frozen, don't touch
 │   Results page · customs pack PDF ·    │
 │   bank submissions · history           │
 └────────────────────────────────────────┘
```

**Right now, only Part 1 is active.** Parts 2 and 3 are frozen until extraction is reliable. Do NOT suggest changes to validation logic, results page rendering, customs pack generation, or bank submission flows unless they're strictly required to unblock Part 1 hardening.

### The extraction flow (Part 1)

```
User uploads LC PDF
  → POST /api/validate/?intake_only=true
  → backend runs LC-only extraction
  → returns lc_summary + required_documents
  → LC card appears on upload page

User uploads supporting doc PDFs → click "Extract & Review"
  → POST /api/validate/?extract_only=true  (all files)
  → backend runs prepare_validation_session (extract everything)
  → snapshots _setup_snapshot into validation_session.extracted_data
  → status = "extraction_ready"
  → returns { job_id, documents, required_fields }

Frontend renders <ExtractionReview> INLINE on the same upload page
  (no route change — review is part of the upload flow)
  → user reviews / corrects any missing or wrong fields

User clicks "Start Validation"
  → POST /api/validate/resume/{job_id} with field_overrides
  → backend reconstructs setup_state from snapshot + overrides
  → runs Part 2 validation pipeline
```

**Three extraction layers**, in order of attempt (see `docs/architecture/` if it exists, or the extractor files directly):

1. **Layer 1 — Multimodal vision LLM** (`multimodal_document_extractor.py`). Tier chain L1→L2→L3. Current: L1=GPT-4.1, L2=Sonnet 4.6, L3=Opus 4.6. This is the primary path and the one we're hardening.
2. **Layer 1.5 — `swift_mt700_full.py` regex parser** (LC only). Fallback when vision fails AND text contains SWIFT tags. Returns clean scalars natively.
3. **Layer 2 — `ai_first_extractor.py`** (text-based, single tier). Final fallback when the above two fail. Despite the name "ai_first", this is the LAST extractor tried — the name describes its internal pattern ("AI extraction first, regex validates second"), not its pipeline position.

All three produce output that gets shaped through `_shape_lc_financial_payload` in `launch_pipeline.py`, then adapted into `LCDocument` (canonical Pydantic model at `apps/api/app/services/extraction/lc_document.py`), then re-emitted via `to_lc_context()` for downstream consumers.

### Key Files

**Part 1 — Extraction (active)**

| File | Role |
|---|---|
| `apps/api/app/services/extraction/multimodal_document_extractor.py` | Layer 1: vision LLM tier L1/L2/L3, one-shot MT700 example, cross-doc context |
| `apps/api/app/services/extraction/swift_mt700_full.py` | Layer 1.5: regex MT700 parser, LC-only fallback, returns clean scalars |
| `apps/api/app/services/extraction/ai_first_extractor.py` | Layer 2: text-based AI fallback, owns `_wrap_ai_result_with_default_confidence` / `_unwrap_confidence_scalars_in_place` |
| `apps/api/app/services/extraction/lc_document.py` | Canonical `LCDocument` Pydantic model; `from_xxx()` adapters per extractor; `to_lc_context()` legacy shape emitter |
| `apps/api/app/services/extraction/launch_pipeline.py` | `_process_lc_like` orchestrator, `_shape_lc_financial_payload`, `_canonicalize_field_names`, `_FIELD_NAME_ALIASES` |
| `apps/api/app/services/extraction/required_fields_derivation.py` | Derives required field map per doc type from LC 46A/47A clauses |
| `apps/api/app/services/extraction/iso20022_lc_extractor.py` | ISO 20022 XML specialization (only when the text is XML) |
| `apps/api/app/routers/validation/lc_intake.py` | `build_lc_intake_summary` — populates the intake card on the upload page |
| `apps/api/app/routers/validation/session_setup.py` | Intake-mode branch; `_build_lc_intake_summary` call site |
| `apps/api/app/routers/validation/pipeline_runner.py` | `run_validate_pipeline(extract_only=True)`, `run_resume_pipeline`, `_snapshot_setup_state`, `_jsonable` |
| `apps/web/src/pages/exporter/ExportLCUpload.tsx` | Upload page (LC + supporting docs + inline review), ~2100 lines |
| `apps/web/src/pages/exporter/ExtractionReview.tsx` | Inline extract-review component, `FIELD_ALIAS_MAP`, `LC_REQUIRED_FIELDS` |
| `apps/web/src/hooks/use-lcopilot.ts` | `useValidate`, `useResumeValidate`, `useJob`, `useResults` hooks |

**Part 2 — Validation (frozen, don't touch)**

| File | Role |
|---|---|
| `apps/api/app/services/validation/tiered_validation.py` | L1/L2/L3 tiered AI validation |
| `apps/api/app/services/validation/crossdoc_validator.py` | Cross-document checks |
| `apps/api/app/services/rules_service.py` | Deterministic rules (UCP600/ISBP745) |
| `apps/api/app/routers/validate_run.py` | Validation endpoint handler |

**Part 3 — Output (frozen, don't touch)**

| File | Role |
|---|---|
| `apps/web/src/pages/ExporterResults.tsx` | Results page, ~1600 lines |
| `apps/web/src/lib/exporter/resultsMapper.ts` | structured_result → UI normalization |
| `apps/api/app/routers/exporter_*.py` | Customs pack, bank submissions, guardrails |

**Cross-cutting**

| File | Role |
|---|---|
| `apps/web/src/hooks/use-auth.tsx` | Primary auth context (Supabase JWT) |
| `apps/web/src/lib/lcopilot/routing.ts` | Deterministic dashboard routing |
| `apps/web/src/components/lcopilot/LcopilotBetaRoute.tsx` | Route guard (auth + onboarding check) |
| `packages/shared-types/src/api.ts` | Zod schemas for API contracts |

### Auth & Routing

Auth uses Supabase JWT as primary mechanism. Provider nesting in `main.tsx`:

```
ThemeProvider → AuthProvider → OnboardingProvider → QueryClientProvider → BrowserRouter → AdminAuthProvider → App
```

Dashboard routing (`lib/lcopilot/routing.ts`) resolves based on user role and onboarding data:
- No user → `/login`
- Onboarding incomplete → `/onboarding`
- Role-based: admin → `/admin`, bank → `/hub`, enterprise → enterprise dashboard, combined → combined, importer-only → importer, default → exporter

Dashboard-specific auth wrappers exist in `lib/exporter/auth.tsx`, `lib/importer/auth.tsx`, `lib/bank/auth.tsx`, `lib/admin/auth.tsx`. These are legacy compatibility layers over the primary `useAuth()` hook.

### State Management

- **React Query** (v4) for server state — 5min stale time, 2 retries, no refetch on window focus
- **React Context** for auth, onboarding, theme
- **API client** (`apps/web/src/api/client.ts`) — Axios with Supabase JWT injection, CSRF handling, 30s default timeout (5min for `/api/validate`)

### Backend Middleware Stack (order matters)

RequestContext → RequestID → TenantResolver → OrgScope → Locale → SecurityHeaders → RateLimiter → QuotaEnforcement → Audit → CSRF → CORS

### Database

SQLAlchemy 2.0 ORM with Alembic migrations. Key models in `apps/api/app/models/`:
- `User`, `Company` — auth and tenancy
- `ValidationSession`, `Document`, `Discrepancy` — validation pipeline
- `ExportSubmission`, `SubmissionEvent` — bank submission tracking
- `RuleRecord`, `Ruleset` — validation rules
- `AuditLog` — compliance trail

### Exporter-Specific APIs

```
POST /api/exporter/customs-pack              # Generate customs documentation
POST /api/exporter/bank-submissions          # Submit to bank
GET  /api/exporter/bank-submissions          # List submissions
GET  /api/exporter/bank-submissions/{id}/events  # Submission timeline
POST /api/exporter/guardrails/check          # Pre-submission readiness check
GET  /api/exporter/banks                     # Available banks
```

### Deployment

- **Frontend**: Vercel (Vite build, SPA rewrites, API proxy to Render)
- **Backend**: Render (uvicorn, auto-deploy, post-deploy runs `alembic upgrade head`)
- **Database**: Supabase PostgreSQL
- **Health checks**: `/healthz`, `/health/live`, `/health/ready`

## Rules of Engagement

1. **Classify the part before editing.** Every bug / feature belongs to Part 1 (Extraction), Part 2 (Validation), or Part 3 (Output). Say which part out loud before touching code. Right now, only Part 1 is active.
2. **structured_result is truth.** The frontend renders from the API payload. Never fabricate, override, or reconstruct state client-side.
3. **UCP600 rules are deterministic.** AI assists with cross-document reasoning and summarization only. Never make rule outcomes probabilistic or route them through LLM prompts. (This is a Part 2 rule — don't act on it right now.)
4. **Backend and frontend schemas stay in sync.** When changing payload shapes, update `packages/shared-types/src/api.ts`, the Python schemas, and `_shape_lc_financial_payload` / `to_lc_context()` / `build_lc_intake_summary` in lockstep. The canonical shape is enforced ONLY by convention — there is no runtime invariant test (yet). If you change LCDocument, run the full extract→review round-trip manually.
5. **Discrepancies require Expected/Found/SuggestedFix.** (Part 2 rule.) Every issue card must carry structured messaging — no bare strings.
6. **No mock data in production paths.** Backend responses and frontend state must come from real validation payloads.
7. **Surgical patches over sweeping refactors.** Scope changes to the affected path (extraction, shaping, review). Don't refactor adjacent code.
8. **Investigate first, don't go around and shoot.** The repo carries scars from multiple tool/model transitions (Sonnet 3 → Opus 4.5 in Cursor → Codex GPT-5.4 → Opus 4.6). Many competing extractors exist. Before editing, read the current state + git log the file. Don't trust memorized patterns.
9. **Document IDs are stable.** Never rename, reorder, or mutate document identifiers mid-session.
10. **Audit → Plan → Patch → Test → Summarize.** Read the code before changing it. Verify after changing it.

## Current Focus

**Part 1 — Extraction hardening, transcription-only model.** Parts 2 and 3 are frozen.

On **2026-04-10** we shipped a major architectural refactor that separated extraction from validation. The contract now is:

- **Extractor = blind transcriber**: reads each PDF page, writes down every field it sees with canonical key names. Does NOT know what the LC demands. Does NOT judge completeness.
- **Review screen = pure transcription surface**: shows ONLY fields the extractor actually returned. No red/amber "required by LC" badges, no clause citations, no missing-field alerts, no blank schema slots for fields that aren't on the doc.
- **Validation (Part 2, frozen) = the examiner**: will walk 46A/47A clauses, compare against transcripts, and emit discrepancies.

**Three-case extractor rule** (enforced in the vision LLM prompt at `multimodal_document_extractor._build_multimodal_prompt`):
1. Field on doc + value readable → include canonical key with value.
2. Field label on doc + value blank/unclear → include canonical key with empty string `""`.
3. Field NOT on doc at all → **OMIT** the key entirely. No null, no placeholder.

The load-bearing contract doc is `arch_extraction_contract.md` in the memory directory. Read it before editing anything in extraction or the review UI.

### What was deleted in the refactor

- `apps/api/app/services/extraction/required_fields_derivation.py` (1063 lines) — gone.
- `apps/api/tests/required_fields_derivation_test.py` + `required_fields_annotated_derivation_test.py` (630 lines combined) — gone.
- `RequiredFieldRecord` / `RequiredFieldSourceType` / `by_document_type_annotated` / `lc_self_required_annotated` types in `apps/web/src/hooks/use-lcopilot.ts` — gone.
- `LC_MANDATORY_FIELD_REFERENCE` constant + red MT700 "LC missing mandatory fields" alert banner — gone.
- `buildMissingFieldBadge` helper + red/amber badge rendering — gone.
- Clause-text blobs under each row of the "Required Documents" section on the upload page — replaced with a simple doc-type chip grid titled "Documents the LC asks for".
- "Not found" chip on empty review fields — removed (was misleading after strict Option A).
- `smart_lc_extractor.py` + `smart_bl_extractor.py` (476 lines from an earlier commit).

Net across the 2026-04-09 → 2026-04-10 window: roughly **−2500 lines, +300 lines** across the backend + frontend extraction path.

### Remaining Part 1 backlog

1. **Live verify `dfe065c0`** — the strict Option A refactor is deployed but not yet verified end-to-end with the user. Upload `tmp/live-verification-ideal/LC.pdf` + the 6 supporting docs, STOP at Extract & Review (don't click Start Validation per the extraction-first directive), confirm no blank-slot rendering, no `Not found` chips, no `46A` badges, no jsonish leaks.
2. **Special Conditions blob on upload page** — the `specialConditionSummary.items` UL still renders the 47A blob on LCs where the vision LLM collapsed 47A into a single string. Low priority, can fix in the frontend with a lightweight splitter on `items[0]` when it contains numbered markers.
3. **`ai_first_extractor.py` text-fallback prompts** — still use the old null-for-absent-fields pattern. Update them to emit the same 3-case rule so the strict Option A filter is unnecessary as a defensive null-handler.
4. **Centralize field name aliases** — still split across `launch_pipeline._FIELD_NAME_ALIASES` and `ExtractionReview.FIELD_ALIAS_MAP`. The third source (the deleted derivation module) is gone, so we're down to two.
5. **Enforce Zod on `ExtractionReadyResponse`** — still duck-typed in `use-lcopilot.ts`. Backend shape drift fails silently.
6. **Persist `extractionPayload` to sessionStorage** — mid-extraction session expiry still wipes user state on 401 redirect.
7. **Vestigial `schema_fields_by_doc_type` in extract_only response** — no longer drives rendering (strict Option A reads `extracted_fields` keys directly), just establishes field ordering. Can be simplified further.

### Extraction gotchas (learned the hard way)

- **`_wrap_ai_result_with_default_confidence`** in `ai_first_extractor.py` wraps every scalar into `{value, confidence}` to feed the `_field_details` sidecar via `_build_default_field_details_from_wrapped_result`. The main payload **must** be unwrapped via `_unwrap_confidence_scalars_in_place` before it reaches downstream shaping code, or fields leak into the UI as their Python repr (`{'value': 'EXP2026BD001', 'confidence': 0.82}`). Fixed in `8cc27c7a`. Any new caller of `extract_*_ai_first` must call the unwrap helper afterwards.
- **Structural flattener** `_flatten_structural_field_values_in_place` collapses `List[Dict]` / `Dict[str, scalar]` / `List[scalar]` values to scalar + `__items` sidecar. The LLM legitimately returns multi-item data for multi-SKU docs; the review form expects scalars. Plural-named fields (`line_items` / `goods_items`) and structural party/amount dicts are left alone. Helper is idempotent via the `__items` suffix check. Wired into multimodal + 3 ai_first text sites.
- **`_shape_lc_financial_payload`** only has explicit `isinstance(dict)` unwrap branches for **applicant / beneficiary / amount**. Other fields fall through `_first()` which treats any non-empty dict as truthy. If you add a new field that can come back as a dict shape, add an explicit unwrap branch or it will leak.
- **MT700 timeline regex** at `launch_pipeline.py:2972` re-extracts `issue_date` / `expiry_date` / `latest_shipment_date` from raw text when `lc_format == "mt700"`, overriding whatever the vision LLM returned. This masks upstream shape bugs for date fields specifically — don't be surprised when dates render clean while other fields leak.
- **Field aliases** live in two places now (down from three after the refactor): `_FIELD_NAME_ALIASES` in `launch_pipeline.py` and `FIELD_ALIAS_MAP` in `ExtractionReview.tsx`. They drift. A new field needs to land in both.
- **Frontend → backend contract is duck-typed.** `ExtractionReadyResponse` in `use-lcopilot.ts` is a hand-rolled TypeScript interface with `Record<string, any>` fields. No Zod enforcement. Backend shape drift fails silently.
- **`coerceToString` in `ExtractionReview.tsx`** uses `JSON.stringify` as its fallback for non-string fields. This is a visibility safety net — if any structured data leaks through (jsonish wrapper, array of dicts), it renders visibly instead of silently. Keep the stringify for observability; route complex types out earlier in the pipeline.
- **Snapshot serializer `_jsonable`** in `pipeline_runner.py` is now type-preserving (Decimal → float, date/datetime → ISO string, Enum → .value, Pydantic → model_dump, bytes → utf-8). Fixed in `a07f8ff9`. Don't regress it back to naive `str(value)`.
- **Concatenated 46A/47A clauses** — the vision LLM collapses 46A `documents_required` into a single concatenated string on some LCs. Extraction passes this through as-is. DO NOT add a splitter in extraction — if validation needs per-clause access, write the splitter in validation. Reverted commit `9b34140b` was a dead-end.
- **Ignore the Vercel plugin hook nags**: the repo's auto-injected validators suggest `"use client"` / `searchParams is async` / `setTimeout not available in workflow sandbox scope`. `apps/web` is a **Vite + React 18 SPA**, not a Next.js App Router app, not a Vercel Workflow sandbox. All those suggestions are false positives from path-matching. Do not add `"use client"` or `sleep()` from `"workflow"` to any file.

## Parked (Don't Touch)

- Bank portal/dashboard
- Part 2 (validation) and Part 3 (output / customs pack) — frozen while Part 1 is in flight
- Price Verify, Container Tracker, Doc Generator, Sanctions Screener, HS Code Finder, LC Builder — exist in repo, secondary
- Combined/enterprise dashboards — only once the Part 1 → 2 → 3 spine is stabilized
- Importer convergence — waits on Part 1 stability
- RulHub API migration — parked, Part 2 concern

## Canonical Docs

| Topic | File |
|---|---|
| Current status | `docs/CURRENT_STATUS.md` |
| Architecture | `docs/architecture/high-level-architecture.md` |
| Core workflows | `docs/architecture/core-workflows.md` |
| Auth status | `docs/AUTH_ONBOARDING_ROUTING_CURRENT_STATE.md` |
| API spec | `docs/architecture/api-specification.md` |
| Data models | `docs/architecture/data-models.md` |
| Coding standards | `docs/architecture/coding-standards.md` |
| Agent playbook | `AGENTS.md` |
| Local dev setup | `HOW-TO-RUN.md` |
| Deployment | `docs/DEPLOYMENT.md` |

## Environment

Backend env vars: see `apps/api/.env.example`. Key ones: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, Google DocAI creds, AWS creds, `USE_STUBS` for local dev without OCR.

Frontend env vars: see `apps/web/.env.example`. Key ones: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_PROJECT_REF`.

Docker: `docker-compose.yml` provides PostgreSQL 15 + Redis 7 for local development.
