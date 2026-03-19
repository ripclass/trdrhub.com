# TRDR Hub / LCopilot Current Status

> Last updated: 2026-03-15

## Current beta position

LCopilot Public Beta is the current ship target for this repository.

- Exporter is the primary launch path.
- Importer is in scope, but it must reuse the same shared core rather than become a second product.
- Bank is parked from launch-critical scope.
- Other TRDR Hub tools remain in the repo, but they are not the focus of the LCopilot beta sprint.

## Launch-critical scope

In scope for beta:

- signup, login, onboarding, and deterministic dashboard routing
- exporter upload -> validate -> results -> history -> quota/paywall -> repeat
- importer on the same validation and results spine
- one canonical backend payload and one canonical frontend result contract
- hard paywall with an initial free-check or free-token allowance
- English-only public beta operations

Secondary only if they ride the same stabilized spine:

- combined and enterprise dashboards
- workspace and side-surface productivity features

Parked for this beta:

- bank workflow completion and bank launch readiness
- bank-specific beta criteria
- any parallel product lane that forks auth or results from exporter/importer

## Current strengths

- The validation core is the strongest asset in the repo.
- The backend already persists a rich `structured_result` payload.
- The frontend already has a shared results fetch and mapping path through `use-lcopilot` and `resultsMapper`.
- Exporter has the deepest end-to-end surface and the most recent hardening.

## Current blockers

- Auth, onboarding, and routing trust remain the largest launch risk.
- Legacy auth contexts and dashboard-specific auth behavior still create wrong-dashboard and stale-session risk.
- Result-contract drift is still possible because the frontend contains compatibility and fallback logic.
- Importer maturity still trails exporter and must converge on the same shared spine rather than expand independently.

## Canonical runtime truth

- `POST /api/validate` is the canonical validation entrypoint.
- Validation results are persisted as `structured_result` on the backend.
- `GET /api/results/{jobId}` is the canonical results fetch path for the web app.
- `structured_result` is the source of truth for summary, documents, issues, analytics, timeline, and secondary intelligence surfaces such as `bank_profile` and `amendments_available`.
- The frontend should render from that payload directly and should not fabricate contradictory state.

## Beta release gate

The beta should not open until the following are true:

- exporter auth and routing are trustworthy
- importer uses the same auth and results spine
- `structured_result` invariants are frozen and documented
- paywall and quota behavior are deterministic
- release smoke checks cover login, upload, validation, results, history, and gating

## Immediate execution order

1. Freeze documentation and canonical repo truth.
2. Consolidate auth, onboarding, and routing.
3. Freeze the result contract and frontend consumption path.
4. Productionize exporter as the reference loop.
5. Converge importer onto the same spine.
6. Harden paywall, release checks, and telemetry.
