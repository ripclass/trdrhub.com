# Proofline repository audit

**Date:** 2026-07-16  
**Repository:** TRDR Hub (`master` at `b4584949`)  
**Scope:** Read-only architecture, security, payload, workflow, billing, review, testing, and deployment audit before Proofline design or implementation.  
**Worktree note:** The pre-existing untracked JPEG screenshots in the repository root were not modified.

## Executive summary

Proofline belongs inside the existing TRDR Hub monorepo and can reuse most of the operational spine already built for LCopilot's service-as-software launch. The repository already has Supabase-backed authentication, company tenancy, member roles, Stripe Checkout, S3 document storage, OCR/extraction, LC validation, sanctions screening, CBAM/EUDR readiness checks, RulHub connectivity, a human review queue, remediation requests, notifications, audit events, and PDF/report storage.

Proofline should not be represented as another `ValidationSession` workflow type. A complete trade case can contain several module runs, multiple document versions, correction rounds, a workflow status, and a separately approved final decision. The smallest safe boundary is therefore a new `TradeCase` aggregate that **references** existing users, companies, documents, validation sessions, screening results, reports, payments, and module-native output.

The largest reuse blocker is not validation logic; it is orchestration coupling. `run_validate_pipeline` is callable from Python, but it still consumes FastAPI `Request`, multipart file objects, request audit context, and route-shaped payloads. Proofline needs a small internal LCopilot runner interface around that existing pipeline. The standalone `/api/validate` path must become an adapter to the same interface without changing current LCopilot behavior.

The second material risk is background execution. Redis and Celery are dependencies, and bulk-job tables exist, but deployed validation work currently relies mainly on FastAPI `BackgroundTasks` and `asyncio.create_task`; `render.yaml` does not deploy a worker. Proofline check runs therefore need persisted, idempotent run records and a retry-safe runner boundary before they can be treated as durable. A full queue migration is not required for the first vertical slice, but case processing must be resumable from database state.

## 1. Frontend and backend architecture

- The repository is a Turbo/npm monorepo with three active workspaces.
  - `apps/api`: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis, boto3/S3, Stripe, OCR providers, WeasyPrint/ReportLab.
  - `apps/web`: React 18, Vite 7, React Router 6, React Query 4, Tailwind 3, shadcn/Radix components.
  - `packages/shared-types`: Zod/TypeScript and manually synchronized Pydantic definitions.
- `apps/api/main.py` composes the API from many routers and installs request context, request ID, tenant resolution, organization scope, locale, security headers, rate limiting, quota, audit, CSRF, and CORS middleware.
- The canonical LC result is persisted at `ValidationSession.validation_results["structured_result"]` and fetched through results endpoints. The current frontend mapper is `apps/web/src/lib/lcopilot/resultsMapper.ts`; the path in `AGENTS.md` is stale.
- The shared-types manifest references `packages/shared-types/scripts/generate-python-schemas.js`, but that script is absent. Proofline types must be edited and tested in both languages until generation is repaired.

## 2. Routes and navigation

- Public tool discovery is centralized in `apps/web/src/pages/ToolsPage.tsx` and `apps/web/src/components/sections/tools-section.tsx`.
- The four currently advertised tools are LCopilot, Sanctions Screener, CBAM Check, and EUDR Check. Proofline should become the fifth live tool in these registries and in `TRDRFooter` product links.
- `apps/web/src/App.tsx` owns the SPA route table. Existing live tool landings use public routes, while operational screens use `RequireAuth` and existing dashboard/auth providers.
- Proofline should use one authenticated case-detail route with tabs, rather than separate route components for every tab. Recommended public/authenticated route shape:
  - `/proofline` public landing
  - `/proofline/new` staged authenticated intake
  - `/proofline/cases` authenticated list
  - `/proofline/cases/:caseId` authenticated detail with Overview, Documents, Findings, Actions, and Report tabs
- The internal analyst surface already lives under `/admin` and exposes a Review Queue section. Proofline queue and detail views should extend this shell rather than create a second admin application.

## 3. Design system and UI inventory

- Public pages use `TRDRHeader` and `TRDRFooter`; authenticated workspaces use `DashboardLayout`, `AppShell`, role-specific shells, and the shared user menu.
- Brand colors are already established in code and tokens: deep green `#00261C`, green `#00382E`, lime `#B2F273`, and pale foreground `#EDF5F2`, with light/dark CSS variables in `apps/web/src/index.css`.
- Reusable shadcn/Radix primitives include accordion, alerts, alert dialogs, badges, breadcrumbs, buttons, cards, checkboxes, dialogs, drawers, dropdowns, forms, inputs, labels, pagination, progress, radio groups, selects, sheets, sidebars, skeletons, status badges, tables, tabs, textareas, toasts, and tooltips.
- Existing Proofline-relevant product patterns include:
  - tool cards and dedicated landings (`ToolsPage`, `ReadinessLanding`);
  - staged upload/extraction review (`ExportLCUpload`, `ExtractionReview`);
  - result tabs and finding cards (`ExporterResults`, `resultsMapper`);
  - status timelines (`/lcopilot/status/:jobId`);
  - admin queue/detail split (`ReviewQueue`);
  - report download/status surfaces (`ReportPage`, LC report delivery endpoints).
- Proofline must use these patterns and tokens unchanged. No new palette, typography system, shell, or component library is justified.

## 4. Authentication, tenants, roles, subscriptions, API keys, and billing

- Supabase JWT is the primary authentication source; local JWT support remains for compatibility. `get_current_user` and role dependencies live in `apps/api/app/core/security.py`.
- `Company` is the main customer/tenant record. `User.company_id` and `CompanyMember` provide company membership and owner/admin/member/viewer roles with tool access.
- Tenant and organization context are resolved in middleware, but application-layer query filters remain mandatory because the production service-role database path bypasses Postgres RLS.
- Platform analysts are currently `system_admin` users through `require_sysadmin`. Proofline should initially reuse that gate and later introduce a narrower reviewer permission if the existing admin RBAC service becomes authoritative.
- API key models exist in both the platform admin domain and integration-specific domains. Proofline V1 does not need a new API-key model.
- Billing has overlapping historical layers:
  - `Company.plan`/quota and `UsageRecord`;
  - `HubPlan`, `HubSubscription`, `HubUsage`, and `HubUsageLog` for multi-tool usage;
  - concierge one-off Stripe Checkout products in `app/services/checkout.py`;
  - frontend price registries in `apps/web/src/lib/pricing.ts`.
- The current one-off checkout catalog is duplicated between Python and TypeScript and hardcodes prices. Proofline must not add a third duplicated catalog. A single backend service-package registry (database-backed or settings-backed) should be authoritative, exposed read-only to the web client, and consumed by the existing hosted Checkout/webhook path.
- LCopilot upgrade credits should reference the paid source `ValidationSession`, calculate eligibility from configurable settings (launch default 30 days), and persist the applied adjustment. Stripe remains the payment processor; Proofline should not create a parallel payment model.

## 5. Existing LCopilot workflow

1. `POST /api/validate` parses and validates multipart uploads.
2. `prepare_validation_session` creates the `ValidationSession` and `Document` records, uploads files, classifies/extracts content, and can stop at intake-only or extraction-ready state.
3. The frontend renders inline extraction review and submits field overrides to the resume endpoint.
4. `execute_validation_pipeline` runs deterministic/rules-based document and cross-document checks, optional RulHub evaluation, sanctions integration, and AI layers where allowed.
5. `finalize_validation_result` builds and persists the canonical `structured_result` payload.
6. Concierge sessions advance through the separate report-review state machine: submitted, processing, engine complete, under review, needs info, delivered.
7. The system-admin Review Queue lets an analyst inspect source documents, edit/annotate/suppress findings, request information, rerun readiness checks, record offline payment, and approve/deliver.
8. Delivery generates an LC report, stores it in S3, records a `Report`, opens the customer gate, and sends a notification.

Direct reuse:

- extraction adapters, canonical document types, validation rules, cross-document checks, sanctions integration, persisted `structured_result`, review event pattern, notifications, and report storage.

Required extraction:

- introduce an internal LCopilot case-runner contract that accepts persisted document references and typed context rather than HTTP `Request`/multipart objects;
- keep the existing `/api/validate` behavior by adapting its request into that contract;
- persist the linked LCopilot `ValidationSession` on a Proofline check run and reuse its completed result instead of rerunning it.

## 6. Documents and storage

- `Document` already stores the stable UUID, validation-session reference, type, original filename, S3 key, size, content type, OCR text/confidence, extracted fields, timestamps, and soft-delete timestamp.
- Upload paths validate supported formats, calculate SHA-256 for audit, upload to S3, and use presigned delivery URLs. The recent review-queue fix head-checks objects before presenting links.
- The existing `Document` belongs to one `ValidationSession` and has no generic logical-document/version lineage. Re-papering preserves originals by creating a replacement validation session, but that is not enough for a multi-round trade case.
- Proofline should keep file bytes and OCR data in existing `Document` rows. A case-document association should add case role, logical document key, version number, predecessor reference, active flag, submission round, and evidence metadata. Corrected uploads create new `Document` rows and new associations; originals are never overwritten.
- Stable backend IDs and document ordering must pass through all Proofline APIs unchanged.

## 7. Sanctions, CBAM, EUDR, RulHub, and EIN

### Sanctions

- The sanctions router exposes party, vessel, goods, batch, history, certificate, watchlist, API key, and webhook surfaces.
- `sanctions_lcopilot.py` already extracts LC parties and produces LC-compatible findings.
- RulHub screening is fail-closed: transport, timeout, malformed, or incomplete-coverage responses become unavailable rather than clear.
- Proofline should invoke the service directly and reference the native screening record/output; it should not call the public HTTP route or copy matching logic.

### CBAM and EUDR

- Both are implemented as `ValidationSession` readiness workflows with scope checks, paid intake, RulHub-backed findings, concierge review, and report delivery.
- Scope logic already supports out-of-scope outcomes. Proofline should show `Not applicable` and omit failure language when the scope engine says a module does not apply.
- `run_readiness_engine` records an `engine_error` when RulHub is unavailable, but still returns findings with fallback rule IDs. A Proofline final-decision guard must prevent a required degraded check from being represented as clear and require rerun or documented reviewer override.

### RulHub

- `RulHubClient` is server-side, uses an API key, has typed error classes and timeouts, never caches validation/screening, and caches stable reference data in memory for 24 hours.
- It does not currently retry transient calls, persist request/response audit metadata, or persist rule-version snapshots. Proofline needs an adapter wrapper that adds bounded retry for safe reads, redacted request hashes, response metadata, evaluation timestamps, rule IDs/versions, and an explicit unavailable result. The rule corpus remains external.

### EIN

- No production EIN, DID, verifiable-credential, or product-passport integration exists in this repository. The only `EIN` match is fixture text.
- Proofline therefore needs a new interface and production HTTP adapter, not credential infrastructure. Development fixtures may implement the interface only behind an explicit development flag and must always label themselves simulated.
- Stored data should be limited to EIN references, disclosed claims, verification status, issuer, timestamps, hashes, expiry/revocation status, and consent metadata.

## 8. Reviewer and admin workflows

- The current Review Queue already provides the correct shell, source-document access, findings curation, reviewer summary, needs-info flow, readiness rerun, payment gate, delivery, and append-only state events.
- Current limitations for Proofline:
  - queue filters are narrower than requested;
  - there is no claim/assignment/urgency/service-level model;
  - internal notes and customer-visible findings are not first-class separate records;
  - finding suppression mutates/stashes the canonical JSON rather than recording a normalized reviewer decision;
  - there is no separate recommended-versus-final decision with mandatory override reason;
  - report approval does not validate that every required module is complete.
- Proofline should reuse the UI and state-machine patterns but store reviewer decisions, visibility, assignment, and overrides in case-level tables.

## 9. Background jobs and queues

- Redis is deployed and used for caching/progress/rate-limit concerns.
- Bulk job/item/event/failure tables and processors exist.
- Celery is installed, but no active Celery application/task registration or Render worker deployment was found.
- Long validation work currently uses FastAPI `BackgroundTasks` or detached `asyncio.create_task`, which can be lost during process restart.
- Proofline check runs must have persisted idempotency keys, attempt counts, input hashes, explicit pending/running/succeeded/failed/unavailable states, timestamps, and safe replay behavior. The first slice can execute through the current in-process runner if database state makes recovery explicit; production hardening should add a deployed worker before unattended volume grows.

## 10. Testing and deployment

- Backend tests use pytest with strict markers for security, integration, regression, rate limiting, lifecycle, error handling, correlation, slow, critical, async, and mock tests. The repository also has many focused continuity/contract tests around the split validation pipeline.
- Frontend tests use Vitest/Testing Library. End-to-end tests use Playwright with browser, mobile, trace, screenshot, video, JUnit, JSON, and HTML reporting.
- Proofline tests should follow the existing focused-file style and add factories for tenant, case, document versions, check runs, findings, actions, reviewer decisions, and payments.
- The acceptance scenarios in the product brief should become backend service/API tests plus a smaller Playwright customer/analyst happy path.
- Backend production deploys to Render from `apps/api`, runs Alembic in `preDeployCommand`, and health-checks `/healthz`.
- Frontend deploys the Vite SPA to Vercel and rewrites `/api` to Render. The repository has both root and app-level Vercel configs; the root config is the current documented deploy path.
- Several older CI workflows describe Kubernetes/CDK paths that do not match the current Render/Vercel deployment. Proofline release checks should be added to the current Render/Vercel gate, not all historical workflows.
- The Vercel CLI is not installed in this environment. Install it with `npm i -g vercel` before deployment work to enable `vercel env pull`, `vercel deploy`, and `vercel logs`.

## Security and data-shape constraints for Proofline

- Every customer query must scope by case ID plus `company_id`/owner. System-admin analyst access must be explicit and audited.
- Every state transition must go through one service that validates the transition and writes an append-only event with actor kind, actor ID, reason, and timestamp.
- External requests must send only fields required by the module and must never log document bodies or credential payloads.
- Document and report access must use expiring links after an owner/company/admin check.
- A check that is failed, unavailable, or incomplete must never normalize to clear.
- Every normalized finding must retain the native source-module record/reference and explicit expected, observed/found, and suggested-fix fields.
- Proofline types must be added to both `packages/shared-types/src/api.ts` and `packages/shared-types/python/schemas.py` in the same change.

## Reuse and extraction map

| Capability | Reuse directly | Extract or add |
|---|---|---|
| Auth and tenancy | `User`, `Company`, `CompanyMember`, shared guards/middleware | Proofline permissions and tenant-safe query helpers |
| Documents | `Document`, S3 upload/presign, OCR/extraction | Case association and immutable version lineage |
| LC review | Existing LCopilot extraction/validation/result | Typed internal runner; Proofline check-run reference |
| Cross-document checks | Existing deterministic validator/crossdoc services | Proofline module adapter and normalized finding references |
| Sanctions | Existing service and native screening output | Proofline applicability/run adapter |
| CBAM/EUDR | Existing scope/readiness engines | Applicability adapter and incomplete/unavailable gating |
| RulHub | Existing client | Retries, audit metadata, rule-version evidence snapshot |
| EIN | Nothing production-ready | Interface, HTTP adapter, consent-aware result storage |
| Review | Existing admin shell/queue patterns and event model | Assignment, internal notes, decisions, overrides, module gates |
| Remediation | Existing discrepancy/repapering concepts | Case action records and case-document correction rounds |
| Reports | `Report`, S3 storage, HTML/PDF generators | Proofline renderer, report versioning, verification reference |
| Billing | Hosted Stripe Checkout/webhooks, company subscriptions | Authoritative service packages and upgrade-credit calculation |
| Notifications | Existing dispatcher/templates | Proofline event templates and preference-safe triggers |
| Audit | `AuditService` and append-only event patterns | Case-specific event types and external-evaluation metadata |

## Recommended release decomposition

This brief spans several independently testable subsystems and should not be implemented as one migration-sized change.

1. **Internal alpha vertical slice:** feature flag; TradeCase, party, document-link/version, check-run, normalized finding, action, decision, and event models; customer case create/submit/detail; LCopilot reuse; deterministic cross-document aggregation; analyst queue/detail; correction upload; reviewer-approved HTML/PDF report.
2. **Private pilot:** sanctions and applicable CBAM/EUDR adapters; authoritative Proofline service packages and Stripe checkout; notifications; correction-round entitlements; LCopilot upgrade/credit; operational analytics.
3. **External evidence:** hardened RulHub evaluation records, EIN adapter, buyer requirements, credential/evidence views, and final provenance traversal.
4. **Scale hardening:** deployed durable worker, queue recovery tooling, SLA/assignment analytics, recurring trade-desk plans, and machine-readable report API.

Each increment must leave standalone LCopilot behavior unchanged and must be gated behind a backend and frontend Proofline feature flag until its release checks pass.

## Short implementation plan (pre-design)

1. Define the case aggregate and invariants without changing the LCopilot result contract.
2. Add typed shared contracts and Alembic migrations through test-first model/service tests.
3. Extract the minimal internal LCopilot runner boundary and prove route parity with existing tests.
4. Build case orchestration and normalized finding adapters around native module results.
5. Extend the existing admin queue and TRDR Hub customer shell with feature-gated Proofline views.
6. Add immutable correction rounds, final-decision approval, and a versioned Proofline report.
7. Integrate billing, screeners, external adapters, and notifications in separate reviewed increments.
8. Run tenant-isolation, transition, pricing, module-failure, report, frontend, and LCopilot regression gates before enabling the feature.

## Dev Agent Record

### Audit

- Inspected repository layout, current branch/worktree, recent commits, canonical docs, route tables, models, middleware, LC pipeline, shared contracts, tool landings, reviewer queue, sanctions/readiness/RulHub services, storage, billing, reports, jobs, tests, CI, and deployment configuration.
- Confirmed no production EIN integration exists.
- Confirmed the existing LCopilot runner is logically reusable but request-coupled.
- Confirmed current background work is not backed by a deployed durable worker.
- Confirmed the pre-existing untracked screenshots are unrelated and untouched.

### Plan

- Wrote the implementation design and incremental internal-alpha plan before architectural changes.
- Chose a new `TradeCase` aggregate that references existing tenant, user, document,
  validation-session, report, billing, screening, notification, and audit records.
- Kept standalone LCopilot routes and deterministic UCP600/cross-document contracts
  unchanged; Proofline consumes the existing structured result through an adapter.

### Patch

- Added synchronized TypeScript/Pydantic trade-case contracts, SQLAlchemy models,
  reversible Alembic migrations, tenant-safe repositories/APIs, validated state and
  decision services, immutable evidence lineage, normalized finding provenance,
  remediation rounds, analyst review, versioned reports, and audit events.
- Added payment-method-first customer intake and the existing-shell Proofline
  landing, case list/detail/tabs, Tools placement, reviewer queue/detail, LCopilot
  upgrade action, and report/outcome views without a new design system.
- Added configurable database-backed packages, hosted Stripe checkout reuse,
  configurable LCopilot credit, external RulHub/EIN adapters, buyer requirements,
  applicable sanctions/CBAM/EUDR orchestration, selective notifications, and
  privacy-bounded operational metrics.
- Added deployment/environment documentation in `docs/PROOFLINE_SETUP.md`.

### Test

- Focused model, contract, tenant, workflow, decision, document, orchestration,
  adapter, billing, upgrade, report, reviewer, feature-flag, outcome, analytics,
  notification, and frontend component/API tests were added alongside each slice.
- Consolidated backend Proofline suite: **108 passed** across 25 files.
- Existing LCopilot validation/crossdoc, Stripe webhook, sanctions, and readiness
  regressions: **58 passed**. Existing results mapper: **24 passed**.
- Consolidated Proofline frontend suite: **18 passed** across 11 files.
- Production Vite build: **passed**, 3,260 modules transformed.
- Python compile/import check: **passed**. Alembic reports one head,
  `20260716_add_proofline_outcomes`; the new pricing-to-outcome range renders
  offline SQL successfully.
- Full web type-check still returns the repository's existing baseline (954
  diagnostic lines), with **zero Proofline diagnostics**. The package's declared
  lint command cannot start because no ESLint configuration exists in the web
  package or repository root.
- The legacy `ExporterResults.test.tsx` baseline remains stale against the current
  unchanged results UI (47 of 49 assertions fail); neither that test nor
  `ExporterResults.tsx` is modified by Proofline. Its canonical mapper and backend
  payload compatibility gates pass.
- Full offline migration rendering remains blocked by historical migration
  `20250916_170100_seed_default_companies.py`, which executes `fetchall()` in
  offline mode. The new Proofline outcome revision was rendered independently.
- Local in-app browser verification was attempted, but the installed browser
  runtime could not create its kernel assets. The temporary local Vite process was
  stopped and no alternate browser mechanism was used.
- `git diff --check` passed; unrelated root JPEG screenshots remained untouched.

### Summarize

- Proofline is implemented as case orchestration inside TRDR Hub. LCopilot checks
  the instrument; Proofline combines applicable transaction, document, party,
  regulatory, credential, buyer-policy, analyst, correction, and reporting work to
  assess readiness without claiming guaranteed clearance, acceptance, or payment.
