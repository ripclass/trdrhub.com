# LCopilot Public Beta Regression Test Plan

This document defines the release verification bar for the LCopilot Public Beta.

## Release focus

The regression plan is centered on the launch spine:

- auth, onboarding, and routing
- exporter validation loop
- importer on the same shared core
- canonical results fetch and rendering
- quota or paywall behavior

Bank-specific launch testing is not part of the public beta release gate.

## Required automated coverage

### 1. Auth and routing

Tests should prove:

- `/auth/me` and `/onboarding/status` produce consistent role and routing inputs
- launch-critical dashboards do not rely on conflicting auth contexts
- logout clears enough state to prevent identity bleed

### 2. Validation and results contract

Tests should prove:

- `POST /api/validate` returns usable validation responses
- persisted `structured_result` is available through `GET /api/results/{jobId}`
- `structured_result.version` stays stable
- required result surfaces are present for the UI

### 3. Exporter gold path

Tests should prove:

- exporter upload submits correctly
- results render from the persisted contract
- history or reopen path works

### 4. Importer shared-spine path

Tests should prove:

- importer uses the same validation and result infrastructure
- importer results do not fork away from canonical payload truth

### 5. Quota and paywall

Tests should prove:

- free-entry allowance works
- quota exhaustion is deterministic
- frontend and backend blocking behavior agree

## Required manual smoke checks

Before opening beta, run these manually on the deployed environment:

1. exporter login -> dashboard -> upload -> results -> reopen
2. importer login -> dashboard -> upload -> results -> reopen
3. logout and login with a different user without identity bleed
4. quota or paywall path
5. refresh results pages and confirm state matches persisted truth

## Current caution

Some existing tests in the repo are useful but stale. They should not be mistaken for a sufficient beta gate unless they directly cover:

- auth and routing truth
- canonical results contract
- exporter and importer launch paths

## Release criteria

Do not open beta until:

- launch-critical automated checks pass
- manual smoke passes
- auth and routing trust issues are closed
- result-contract drift is contained
- exporter remains the most reliable path

## Rollback expectation

If a release breaks auth, routing, validation persistence, or canonical results rendering:

- rollback the release
- confirm `/auth/me`, `/onboarding/status`, `/api/validate`, and `/api/results/{jobId}` recover
- rerun smoke checks before re-promoting
