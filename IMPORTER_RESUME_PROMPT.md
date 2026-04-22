# Importer Parity — Fresh Session Resume

Brainstorm + 4-phase plan done on **2026-04-21**. Not yet executed. This prompt hands you the full design in a self-contained brief.

## What exists

- **Spec:** `docs/superpowers/specs/2026-04-21-importer-parity-design.md`
- **Phase 1 plan** (shared extraction, pure refactor): `docs/superpowers/plans/2026-04-21-phase-1-shared-extraction.md`
- **Phase 2 plan** (importer flows + `workflow_type`): `docs/superpowers/plans/2026-04-21-phase-2-importer-flows.md`
- **Phase 3 plan** (4 action endpoints): `docs/superpowers/plans/2026-04-21-phase-3-importer-actions.md`
- **Phase 4 plan** (sidebars + dashboard wire-up): `docs/superpowers/plans/2026-04-21-phase-4-shell-wireup.md`
- **Memory recap:** `memory/project_importer_parity_brainstorm_2026_04_21.md`

## Goal in one sentence

Bring the importer frontend to parity with exporter's modern plumbing (AI-first extraction pipeline, inline ExtractionReview, LC intake card, sessionStorage, Zod, 4-tab results via `resultsMapper`). Backend is already unified — almost all work is frontend.

## Two moments (both shipped together)

- **Moment 1 — Draft LC Risk Analysis** (`/lcopilot/importer-dashboard/draft-lc`): importer reviews the bank's draft LC before issuance.
- **Moment 2 — Supplier Document Review** (`/lcopilot/importer-dashboard/supplier-docs`): importer reviews shipping docs received from exporter against the issued LC.

Same extraction + validation pipeline underneath; differences are UI copy and post-validation action palette.

## Seven locked decisions (don't re-litigate)

1. Sessions are **independent** (no Moment 1 ↔ Moment 2 linkage) — billing clarity + stale-LC protection.
2. Two moments = two routes = two sidebar items.
3. Shared home: `apps/web/src/components/lcopilot/`.
4. Execution: **extract-first** (refactor exporter into shared, THEN build importer).
5. `ValidationSession.workflow_type` enum: `exporter_presentation` / `importer_draft_lc` / `importer_supplier_docs`. Default `exporter_presentation`.
6. Sidebars: **4 items exporter** (Dashboard · Upload · Billing · Settings), **5 items importer** (Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings). Reviews page stays at `/reviews` but is NOT in the sidebar.
7. The 5-second dashboard-update smoke test (Plan 4 Task 7) is the real exit gate — "nothing updates" has been a persistent complaint.

## Execution mode

**INLINE**. Ripon has recurring bad experiences with subagents — inline carries the full brainstorm context + memory rules forward without re-briefing per task.

## First action

```
cat docs/superpowers/plans/2026-04-21-phase-1-shared-extraction.md
cd apps/web && npm run type-check && npm run lint && npm run test
```

If all green, start Phase 1 Task 0 (baseline capture), then Task 1 (extract ExtractionReview). One commit per piece. Playwright regression on `tests/e2e/lcopilot/exporter-validation.spec.ts` before AND after each commit — any diff = revert.

## Reminders

- Don't touch `J:\Enso Intelligence\ICC Rule Engine`.
- No hardcoded validators (AI Examiner is the pattern).
- Extraction is a blind transcriber.
- Vercel plugin hook nags are false positives (Vite + FastAPI repo).
