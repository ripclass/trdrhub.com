# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

TRDR Hub is a Turbo monorepo (`lcopilot`) shipping **LCopilot Public Beta** — an LC (Letter of Credit) validation engine for trade finance. The current sprint is exporter-first, with importer converging on the same spine. Bank is parked.

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

### The Validation Spine

Everything flows through one contract:

```
Upload → POST /api/validate → OCR + rules + AI crossdoc → persist structured_result
                                                                    ↓
                              Frontend ← resultsMapper ← GET /api/results/{jobId}
```

- `POST /api/validate` — canonical validation entrypoint (multipart: files + metadata)
- `GET /api/results/{jobId}` — canonical results fetch
- `structured_result` is the single source of truth. The frontend renders from this payload and must not fabricate contradictory state.
- Pipeline stages: document classification → LC type detection → OCR extraction (Google DocAI primary, AWS Textract fallback) → UCP600/ISBP745 deterministic rules → AI cross-document analysis → result aggregation → persistence

### Key Files

| File | Role |
|---|---|
| `apps/api/app/routers/validate_run.py` | Validation endpoint handler |
| `apps/api/app/services/validator.py` | Core validation orchestration |
| `apps/api/app/services/crossdoc.py` | AI cross-document checks |
| `apps/api/app/services/rules_service.py` | Rule loading (DBRulesAdapter) |
| `apps/web/src/hooks/use-lcopilot.ts` | Frontend validation hooks (useValidate, useResults, useCanonicalJobResult) |
| `apps/web/src/lib/exporter/resultsMapper.ts` | Normalizes structured_result for UI consumption |
| `apps/web/src/pages/ExporterResults.tsx` | Main exporter results page (~1600 lines) |
| `apps/web/src/hooks/use-auth.tsx` | Primary auth context (Supabase JWT) |
| `apps/web/src/lib/lcopilot/routing.ts` | Deterministic dashboard routing (exporter/importer/combined/enterprise) |
| `apps/web/src/components/lcopilot/LcopilotBetaRoute.tsx` | Route guard (auth + onboarding check) |
| `packages/shared-types/src/api.ts` | Zod schemas for all API contracts |

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

These come from `AGENTS.md` and project conventions:

1. **structured_result is truth.** The frontend renders from the API payload. Never fabricate, override, or reconstruct state client-side.
2. **UCP600 rules are deterministic.** AI assists with cross-document reasoning and summarization only. Never make rule outcomes probabilistic or route them through LLM prompts.
3. **Backend and frontend schemas stay in sync.** When changing payload shapes, update `packages/shared-types/src/api.ts`, the Python schemas, and the frontend mapper in lockstep.
4. **Discrepancies require Expected/Found/SuggestedFix.** Every issue card must carry structured messaging — no bare strings.
5. **No mock data in production paths.** Backend responses and frontend state must come from real validation payloads.
6. **Surgical patches over sweeping refactors.** Scope changes to the affected path (OCR, validator, mapper). Don't refactor adjacent code.
7. **Document IDs are stable.** Never rename, reorder, or mutate document identifiers mid-session.
8. **Audit → Plan → Patch → Test → Summarize.** Read the code before changing it. Verify after changing it.

## Current Beta Priorities

See `docs/CURRENT_STATUS.md` for the authoritative source. In brief:

1. **Exporter v1 freeze** — bank submission proof, history verification, UI edge cleanup
2. **Auth/onboarding/routing hardening** — largest launch risk (stale sessions, role mapping inconsistencies, onboarding loaded once)
3. **Importer convergence** — must use same auth + structured_result spine as exporter (currently has mock data in ImportResults.tsx)
4. **RulHub API migration** — validation currently queries DB directly (`DBRulesAdapter`); must migrate to RulHub API. Config scaffolding exists (`USE_RULHUB_API`, `RULHUB_API_URL`) but adapter is unimplemented.

## Parked (Don't Touch)

- Bank portal/dashboard
- Price Verify, Container Tracker, Doc Generator, Sanctions Screener, HS Code Finder, LC Builder — exist in repo, secondary to beta
- Combined/enterprise dashboards — only if they ride the stabilized spine

## Canonical Docs

| Topic | File |
|---|---|
| Beta truth | `docs/CURRENT_STATUS.md` |
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
