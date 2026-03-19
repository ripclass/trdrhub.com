# Auth / Onboarding / Routing Current State

This is the canonical auth, onboarding, and routing document for the LCopilot Public Beta.

## Beta rule

- Exporter is the primary launch path.
- Importer is launch-critical only if it rides the same auth and routing spine.
- Bank exists in the repo but is parked from launch-critical beta scope.

## Current backend truth

### `GET /auth/me`

- the backend validates the current session or token
- the backend normalizes role through `infer_effective_role`
- the frontend should treat this endpoint as the primary identity source

### `GET /onboarding/status`

- the backend restores onboarding details when possible
- the backend may link or auto-create company state when onboarding metadata is missing
- the backend returns onboarding status plus effective role context

This restoration behavior is useful, but it is also a launch risk because it can hide incomplete or inconsistent user state.

### Logout behavior

- the shared frontend auth hook now clears multiple stored tokens and redirects to `/login`
- this is the correct direction for beta
- any launch-critical surface still depending on an alternative auth context remains a risk

## Current frontend truth

The intended beta auth path is:

1. authenticate through the shared auth system
2. fetch `/auth/me`
3. fetch `/onboarding/status`
4. resolve the correct dashboard
5. guard dashboards with the same route logic

Current problem:

- legacy exporter and bank auth contexts still exist in the web app
- some dashboards and sidebars still reference them
- this creates wrong-dashboard, mixed-identity, and stale-token risk

## Current launch risks

### 1. Multiple auth sources

If different dashboards trust different auth contexts, the product can appear to work while routing users incorrectly.

### 2. Stale session state

If old tokens or local state survive logout, users can see the wrong account or the wrong dashboard.

### 3. Route-decision inconsistency

If login, onboarding, and dashboard guards do not use the same decision logic, routing trust breaks.

### 4. Heuristic onboarding restoration

Automatic restoration is helpful, but it is not a substitute for stable, explicit onboarding truth.

## Target beta state

Before beta opens, launch-critical dashboards should share:

- one auth source
- one route-decision helper
- one logout path
- one onboarding truth path

Canonical beta sources:

- identity: `/auth/me`
- onboarding and effective role context: `/onboarding/status`
- dashboard access control: shared route-resolution and shared guards

## Route policy for beta

### Exporter

- default gold path
- highest reliability requirement

### Importer

- allowed and launch-critical only if it uses the same shared auth and results spine

### Combined and enterprise

- may remain visible only if they do not fork auth, onboarding, routing, validation, or results behavior
- otherwise they should be hidden or deprioritized

### Bank

- parked from launch-critical beta scope
- bank-specific auth and dashboard behavior should not drive the beta routing plan

## Pre-beta must-haves

- all launch-critical dashboards use the shared auth path
- login and dashboard guards produce the same routing outcome
- logout clears enough state to prevent user bleed
- onboarding restoration no longer produces surprising dashboard outcomes
- exporter and importer both route through the same trusted decision path
