# Proofline Internal Alpha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a tenant-safe, payment-method-aware Proofline vertical slice inside TRDRHub that creates complete trade cases, versions evidence, reuses LCopilot and existing checks, aggregates findings, supports analyst remediation/final approval, and generates a versioned report without changing standalone LCopilot behavior.

**Architecture:** Add a `TradeCase` aggregate and append-only decision/event records around existing `Company`, `User`, `Document`, `ValidationSession`, `Report`, billing, audit, and module result records. Typed adapters preserve each engine as the source of truth. Customer and analyst APIs use separate response schemas and one state service enforces lifecycle and decision invariants.

**Tech Stack:** FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL/Supabase, React 18, Vite, TypeScript, React Query, Tailwind/shadcn, Stripe Checkout, S3, pytest, Vitest/RTL.

**Execution status (2026-07-16):** The planned Proofline vertical slice and pilot
capabilities were implemented incrementally. Exact commits, verification results,
known repository baselines, and staged operational follow-ups are recorded in
`docs/audits/2026-07-16-proofline-repository-audit.md`. The checklist below is
retained as the original pre-implementation plan rather than rewritten after the
fact.

## Global Constraints

- Follow Audit → Plan → Patch → Test → Summarize and update the Dev Agent Record.
- Work in the current checkout as explicitly directed; do not stage or edit unrelated image files.
- Begin each production slice with a focused failing test and observe the expected failure.
- Scope every case/document/finding/action query by `company_id` before returning an object.
- Preserve existing document IDs, names, order, LCopilot payloads, UCP600 determinism, and Expected/Found/SuggestedFix semantics.
- Synchronize `packages/shared-types/src/api.ts` and `packages/shared-types/python/schemas.py` for customer-visible contract changes.
- Do not copy RulHub, EIN, sanctions, CBAM, EUDR, report, auth, billing, or LCopilot implementations.
- Never map dependency failure, mock verification, or missing required evidence to `clear`.
- Keep customer and reviewer serializers separate so internal notes cannot leak.
- Use existing TRDRHub components and design tokens. Do not add a Proofline design system.

---

## Task 1: Shared Proofline contract

**Files:**

- Modify: `packages/shared-types/src/api.ts`
- Modify: `packages/shared-types/python/schemas.py`
- Create: `apps/api/tests/proofline_contract_test.py`
- Create: `apps/web/src/lib/proofline/__tests__/contracts.test.ts`

- [ ] Write backend contract tests that assert exact values for payment arrangements, statuses, decisions, check states, finding statuses, and actor/visibility values.
- [ ] Write frontend contract tests that parse an LC case and an open-account case with the same normalized response shape.
- [ ] Run the two tests and confirm imports/schemas are missing.
- [ ] Add matching Pydantic enums/models and Zod schemas/types for:
  - `PaymentArrangement`
  - `TradeCaseStatus`
  - `ProoflineDecision`
  - `ProoflineCheckState`
  - `ProoflineFindingStatus`
  - case summary/detail, parties, documents, checks, findings, remediation, decisions, events, package summary.
- [ ] Require normalized findings to expose `expected`, `observed`, and `suggested_correction`.
- [ ] Rerun focused tests and type-check shared consumers.
- [ ] Commit: `feat(proofline): add shared trade-case contracts`

## Task 2: Database aggregate and migration

**Files:**

- Create: `apps/api/app/models/proofline.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/alembic/versions/20260716_add_proofline_trade_cases.py`
- Create: `apps/api/tests/proofline_models_test.py`

- [ ] Write metadata tests for table names, foreign keys, tenant indexes, unique constraints, decision/event immutability fields, and document version lineage.
- [ ] Run the test and confirm the models do not exist.
- [ ] Define enums and SQLAlchemy models:
  - `TradeCase`
  - `TradeCaseParty`
  - `TradeCaseDocument`
  - `TradeCaseCheckRun`
  - `ProoflineFinding`
  - `RemediationAction`
  - `TradeCaseDecision`
  - `TradeCaseEvent`
  - `BuyerRequirement`
- [ ] Reference existing `companies`, `users`, `documents`, `validation_sessions`, and `reports`; do not duplicate them.
- [ ] Add indexes beginning with `company_id` for tenant list/access paths and uniqueness for case reference, check idempotency, source finding, decision version, and logical document version.
- [ ] Implement the reversible Alembic migration with Postgres-compatible enums/defaults and no Data API grants beyond current repository convention.
- [ ] Verify Alembic can import metadata and render SQL offline.
- [ ] Commit: `feat(proofline): add trade-case persistence`

## Task 3: State, decision, and audit services

**Files:**

- Create: `apps/api/app/services/proofline/__init__.py`
- Create: `apps/api/app/services/proofline/state.py`
- Create: `apps/api/app/services/proofline/decisions.py`
- Create: `apps/api/tests/proofline_state_test.py`
- Create: `apps/api/tests/proofline_decision_test.py`

- [ ] Write transition-table tests for every permitted path and representative forbidden jumps.
- [ ] Test that transitions record actor type/ID, reason, prior/current state, timestamp, event, and `AuditService` call.
- [ ] Test final-decision guards: paid reviewer required; unresolved critical finding blocks `CLEAR`; required unavailable check blocks `CLEAR`; override reason required.
- [ ] Run tests and observe missing services.
- [ ] Implement one transition service and append-only decision service using injected audit hooks.
- [ ] Make repeated transition/decision requests idempotent where the idempotency key matches.
- [ ] Rerun focused tests.
- [ ] Commit: `feat(proofline): enforce review lifecycle and decisions`

## Task 4: Tenant-safe case repository and customer APIs

**Files:**

- Create: `apps/api/app/repositories/proofline.py`
- Create: `apps/api/app/schemas/proofline.py`
- Create: `apps/api/app/routers/proofline.py`
- Modify: `apps/api/app/routers/__init__.py`
- Modify: `apps/api/main.py`
- Create: `apps/api/tests/proofline_api_test.py`
- Create: `apps/api/tests/proofline_tenant_isolation_test.py`

- [ ] Write API tests for create/list/detail/update draft and exact payment-arrangement serialization.
- [ ] Write attacker tests proving another company cannot read/update/submit a case or infer its existence.
- [ ] Test role restrictions for owner/admin/member/viewer using existing company membership semantics.
- [ ] Run tests and observe 404/import failures.
- [ ] Implement repository methods that require `company_id` as an argument; no unscoped `get(case_id)` helper.
- [ ] Add `/api/proofline/cases` create/list and `/api/proofline/cases/{case_id}` detail/update endpoints.
- [ ] Generate a stable human case reference without exposing sequential tenant counts.
- [ ] Separate public customer response models from internal ORM fields.
- [ ] Call existing audit hooks for creation and material updates.
- [ ] Rerun API and isolation tests.
- [ ] Commit: `feat(proofline): add tenant-safe case APIs`

## Task 5: Payment-method applicability and open-account checks

**Files:**

- Create: `apps/api/app/services/proofline/applicability.py`
- Create: `apps/api/app/services/proofline/open_account.py`
- Create: `apps/api/tests/proofline_applicability_test.py`
- Create: `apps/api/tests/proofline_open_account_test.py`

- [ ] Write applicability tests for all ten payment arrangements.
- [ ] Assert LCopilot is applicable only for LC cases, and non-applicability does not create a failure.
- [ ] Write deterministic open-account tests for missing PO/contract, payment terms, invoice approval conditions, undertaking/insurance, chargeback clauses, expected payment date, and Bangladesh export documentary reminder.
- [ ] Require each discrepancy to contain Expected/Found/SuggestedFix-compatible fields and evidence/rule references.
- [ ] Run tests and observe missing engines.
- [ ] Implement deterministic applicability profiles and evidence checks without legal conclusions.
- [ ] Store Bangladesh Bank circular URLs/version/date as rule references, not unversioned copied corpus.
- [ ] Map missing facts to `evidence_incomplete`/`pending_review`, never fabricated values.
- [ ] Rerun tests.
- [ ] Commit: `feat(proofline): route open-account trade clearance`

## Task 6: Evidence association, upload, and version lineage

**Files:**

- Create: `apps/api/app/services/proofline/documents.py`
- Modify: `apps/api/app/routers/proofline.py`
- Create: `apps/api/tests/proofline_documents_test.py`

- [ ] Write tests associating an existing company-owned `Document` with a case.
- [ ] Test rejection of cross-company/session document access.
- [ ] Test duplicate hash detection and a correction upload that creates version 2 with `supersedes_id` while version 1 remains retrievable.
- [ ] Run tests and confirm missing behavior.
- [ ] Reuse existing upload/S3/OCR helpers and stable `Document` IDs.
- [ ] Add document list/associate/upload-correction endpoints with version metadata.
- [ ] Make current-version resolution deterministic; never delete or overwrite originals.
- [ ] Emit case and existing audit records without logging file contents.
- [ ] Rerun tests.
- [ ] Commit: `feat(proofline): version trade-case evidence`

## Task 7: Persisted check orchestration and normalized findings

**Files:**

- Create: `apps/api/app/services/proofline/orchestrator.py`
- Create: `apps/api/app/services/proofline/findings.py`
- Create: `apps/api/app/integrations/proofline/base.py`
- Create: `apps/api/tests/proofline_orchestrator_test.py`
- Create: `apps/api/tests/proofline_findings_test.py`

- [ ] Write tests for input hashing/idempotency, retry-safe attempts, crash-recoverable runs, explicit not-applicable results, and dependency failures.
- [ ] Test normalized findings preserve source module/ID/detail and Required Expected/Found/SuggestedFix fields.
- [ ] Run tests and observe missing orchestrator.
- [ ] Implement a module-adapter protocol, persisted run state, applicability execution, source-result references, and finding upsert by source identity.
- [ ] Ensure a failed adapter yields `unable_to_assess` and a safe error code/message.
- [ ] Keep detailed source payloads in their owning records; store only bounded summaries/references.
- [ ] Rerun tests.
- [ ] Commit: `feat(proofline): orchestrate reusable checks`

## Task 8: LCopilot adapter and upgrade path

**Files:**

- Create: `apps/api/app/integrations/proofline/lcopilot.py`
- Create: `apps/api/app/services/proofline/upgrades.py`
- Modify minimally: `apps/api/app/routers/validate.py` or its existing extracted runner module only if required to expose a route-independent call
- Modify: completed LCopilot result response/action contract only additively
- Create: `apps/api/tests/proofline_lcopilot_adapter_test.py`
- Create: `apps/api/tests/proofline_upgrade_test.py`
- Add/modify focused LCopilot regression tests near existing validation continuity tests

- [ ] Write a golden test showing standalone LCopilot output is byte/shape compatible before and after extraction.
- [ ] Test prior-result reuse when document hash, LC identity, and engine version match.
- [ ] Test a new LC case invokes the existing runner, preserves source document IDs, and normalizes results without copying validation rules.
- [ ] Test upgrade carries session/documents/extracted fields/findings/report references and does not rerun matching work.
- [ ] Test default 30-day credit policy is configuration-driven and rejects different LC/company or expired reviews.
- [ ] Run tests and observe missing adapter/upgrade service.
- [ ] Extract only the minimum route-independent interface required; keep `/api/validate` behavior unchanged.
- [ ] Add an authenticated upgrade endpoint and completed-review action metadata.
- [ ] Rerun adapter, upgrade, and LCopilot regression tests.
- [ ] Commit: `feat(proofline): reuse and upgrade LCopilot reviews`

## Task 9: Sanctions, readiness, RulHub, and EIN adapters

**Files:**

- Create: `apps/api/app/integrations/proofline/sanctions.py`
- Create: `apps/api/app/integrations/proofline/readiness.py`
- Create: `apps/api/app/integrations/proofline/rulhub.py`
- Create: `apps/api/app/integrations/proofline/ein.py`
- Modify: `apps/api/app/core/config.py`
- Create: `apps/api/tests/proofline_integrations_test.py`

- [ ] Write tests for sanctions issue, CBAM not applicable, EUDR evidence incomplete, expired EIN credential, and RulHub timeout.
- [ ] Test external request metadata excludes full documents/credentials and records version/hash/timing.
- [ ] Test EIN development mock is disabled by default, labeled simulated when enabled, and cannot support final clear.
- [ ] Run tests and observe missing adapters.
- [ ] Wrap existing sanctions/readiness services and current RulHub client without duplicating rules.
- [ ] Define EIN interface and production HTTP adapter; return unavailable when unconfigured.
- [ ] Add bounded retry/timeout behavior only where idempotent and retain fail-closed/manual-review state.
- [ ] Rerun tests.
- [ ] Commit: `feat(proofline): connect existing and external checks`

## Task 10: Remediation and analyst APIs

**Files:**

- Create: `apps/api/app/routers/proofline_admin.py`
- Modify: `apps/api/app/routers/__init__.py`
- Modify: `apps/api/main.py`
- Create: `apps/api/app/services/proofline/remediation.py`
- Create: `apps/api/tests/proofline_admin_api_test.py`
- Create: `apps/api/tests/proofline_remediation_test.py`

- [ ] Write tests for queue filters, atomic claim/assign, internal notes, customer-visible finding edits, false-positive disposition, correction request, resubmission, comparison metadata, and final approval.
- [ ] Prove customer endpoints never serialize internal notes/sensitive screening fields.
- [ ] Prove override reason and reviewer identity are mandatory.
- [ ] Run tests and observe missing routes.
- [ ] Add `/api/admin/proofline/cases` queue/detail/claim/assign/findings/actions/decision endpoints using existing internal role dependencies.
- [ ] Add customer response/correction/final-review endpoints.
- [ ] Enforce correction-round package limits through service policy, not UI only.
- [ ] Emit existing notification events only for meaningful customer states.
- [ ] Rerun tests.
- [ ] Commit: `feat(proofline): add verified analyst remediation`

## Task 11: Pricing, checkout, and service packages

**Files:**

- Create: `apps/api/app/services/proofline/pricing.py`
- Modify: `apps/api/app/services/checkout.py`
- Modify: relevant existing checkout/webhook router and tests
- Modify: `apps/web/src/lib/pricing.ts` only to consume/expose server Proofline packages without altering existing LCopilot prices
- Create: `apps/api/tests/proofline_pricing_test.py`
- Create: `apps/api/tests/proofline_checkout_test.py`

- [ ] Write package tests for Standard, Managed, custom quote, negotiated trade-desk plans, limits, correction rounds, and turnaround support.
- [ ] Test checkout totals, eligible LCopilot credit, zero/partial credit, idempotency, Stripe webhook settlement, and BDT/manual invoice state.
- [ ] Run tests and confirm missing catalog.
- [ ] Add one backend-authoritative Proofline package registry using settings/database conventions.
- [ ] Extend existing hosted Checkout Session creation; omit hardcoded payment method lists and reuse current webhook truth.
- [ ] Do not change current production LCopilot prices.
- [ ] Rerun billing tests including existing `checkout_webhook_test.py`.
- [ ] Commit: `feat(proofline): configure case-based billing`

## Task 12: Report view model, web report, and PDF

**Files:**

- Create: `apps/api/app/services/proofline/report.py`
- Create: `apps/api/app/templates/proofline_report.html` or the repository-equivalent template location
- Modify: `apps/api/app/routers/proofline.py`
- Create: `apps/api/tests/proofline_report_test.py`

- [ ] Write a representative final case fixture and golden assertions for all required sections, decision/version/reference, rule/evidence provenance, reviewer approval, and disclaimers.
- [ ] Test report generation is rejected before final reviewer approval.
- [ ] Test new decision version creates a new report version and leaves the prior report accessible.
- [ ] Run tests and observe missing report service.
- [ ] Reuse existing report rendering, S3 storage, presigned delivery, and `Report` association conventions.
- [ ] Generate HTML/PDF/structured views from one immutable report view model.
- [ ] Add web/download endpoints with tenant-safe authorization.
- [ ] Rerun report tests.
- [ ] Commit: `feat(proofline): generate verified clearance reports`

## Task 13: Proofline landing, navigation, and staged intake UI

**Files:**

- Create: `apps/web/src/pages/ProoflineLanding.tsx`
- Create: `apps/web/src/pages/proofline/ProoflineCases.tsx`
- Create: `apps/web/src/pages/proofline/ProoflineNewCase.tsx`
- Create: `apps/web/src/lib/proofline/api.ts`
- Create: `apps/web/src/hooks/use-proofline.ts`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/pages/ToolsPage.tsx`
- Modify: `apps/web/src/components/sections/tools-section.tsx`
- Modify: existing header/footer product-link configuration
- Create: `apps/web/src/pages/proofline/__tests__/ProoflineLanding.test.tsx`
- Create: `apps/web/src/pages/proofline/__tests__/ProoflineNewCase.test.tsx`

- [ ] Write UI tests asserting Proofline appears alongside existing tools and uses approved copy/CTA.
- [ ] Test payment arrangement is the first staged decision and changes LC vs open-account fields without losing draft values.
- [ ] Test draft save, validation errors, known-data prefill/confirmation, and submission review.
- [ ] Run tests and observe missing routes/components.
- [ ] Build the landing and wizard from existing TRDRHeader/TRDRFooter/DashboardLayout, Card, Form, Select/Radio, Alert, Badge, Button, and upload patterns.
- [ ] Keep all prices/package limits server-driven.
- [ ] Add authenticated route guards consistent with existing customer pages.
- [ ] Rerun UI tests and web type-check.
- [ ] Commit: `feat(proofline): add trade-case intake experience`

## Task 14: Customer case workspace and analyst UI

**Files:**

- Create: `apps/web/src/pages/proofline/ProoflineCaseDetail.tsx`
- Create: `apps/web/src/pages/admin/ProoflineQueue.tsx`
- Create: `apps/web/src/pages/admin/ProoflineReview.tsx`
- Modify: existing admin route/navigation definitions
- Create: `apps/web/src/pages/proofline/__tests__/ProoflineCaseDetail.test.tsx`
- Create: `apps/web/src/pages/admin/__tests__/ProoflineReview.test.tsx`

- [ ] Write case-detail tests for overview/documents/findings/actions/report tabs all fed by one real case payload.
- [ ] Test only applicable modules render, internal fields do not, and correction versions are visible.
- [ ] Write analyst tests for filters, assignment, evidence inspection links, internal vs visible notes, false-positive action, correction request, and approval/override reason.
- [ ] Run tests and observe missing UI.
- [ ] Implement existing-shell tabbed case detail and extend the current admin review navigation/workspace.
- [ ] Reuse status badge/card/table/timeline/report styles and responsive conventions.
- [ ] Add clear empty/error/degraded states without mock data.
- [ ] Rerun UI tests, type-check, and lint touched files.
- [ ] Commit: `feat(proofline): add customer and analyst workspaces`

## Task 15: Feature flags, metrics, documentation, and release verification

**Files:**

- Modify: `apps/api/app/core/config.py`
- Modify: feature-flag/config surfaces used by `apps/web`
- Create: `docs/runbooks/PROOFLINE_SETUP.md`
- Create: `docs/reports/2026-07-16-proofline-dev-agent-record.md`
- Modify: `.env.example` and deployment config only for non-secret variable names/defaults
- Add: representative Proofline factories/fixtures in existing test conventions

- [ ] Add backend/frontend Proofline flags with safe environment-aware defaults and no production simulated integrations.
- [ ] Add structured operational metrics without document content: counts, timings, outcomes, correction rounds, conversion/revenue/analyst time where available.
- [ ] Document migration, flags, RulHub/EIN settings, Stripe package/price IDs, storage/report prerequisites, background execution limitations, and release-stage gates.
- [ ] Run migration offline validation and import checks.
- [ ] Run focused Proofline backend suite, permission/tenant suite, checkout/report tests, and named LCopilot/readiness/sanctions regressions.
- [ ] Run frontend Proofline tests, existing touched-navigation tests, type-check, lint, and production build with bounded Node memory.
- [ ] If the app can run locally, use the browser verification skill to exercise landing → case creation → customer case → analyst review → report with real local API/fixtures.
- [ ] Run `git diff --check`, inspect `git status`, and confirm unrelated screenshots remain untouched.
- [ ] Update the Dev Agent Record with exact commands/results and staged follow-up items.
- [ ] Use `superpowers:requesting-code-review`, address verified findings, then use `superpowers:verification-before-completion` before claiming completion.
- [ ] Commit: `docs(proofline): add setup and verification record`
