# API Specification

This document covers the beta-critical interfaces that define LCopilot runtime truth.

## Canonical auth and onboarding interfaces

### `GET /auth/me`

Purpose:

- return the authenticated user profile used by the web app
- normalize role through backend logic rather than trusting frontend assumptions

Beta expectation:

- the frontend should treat this as the primary identity source
- role normalization should stay aligned with onboarding and company metadata

### `GET /onboarding/status`

Purpose:

- return onboarding completeness, details, requirements, and effective role context

Current repo truth:

- backend restoration logic may hydrate company and onboarding state heuristically
- this is useful, but it is also part of the launch-risk surface and must stay predictable

## Canonical validation interfaces

### `POST /api/validate`

Purpose:

- accept uploaded documents and workflow metadata
- run the LC validation pipeline
- return validation response data and a job identifier
- persist canonical result truth for later fetches

Current frontend usage:

- exporter and importer both post multipart form data through `use-lcopilot`
- request fields include files, LC number, document tags, user type, and workflow type

### `GET /api/jobs/{jobId}`

Purpose:

- poll high-level job state
- support route transitions and result readiness checks

### `GET /api/results/{jobId}`

Purpose:

- return the persisted validation result used by the review UI

This is the canonical results endpoint for beta.

## Canonical result contract

The frontend review UI should assume:

- `structured_result` is present
- `structured_result.version` is `structured_result_v1`
- the payload came from backend persistence, not UI reconstruction

The following result areas are beta-critical:

- `processing_summary` and `processing_summary_v2`
- `documents` and `documents_structured`
- `issues`
- `analytics`
- `timeline`
- gate and validation status fields
- submission and readiness fields
- secondary intelligence surfaces such as `bank_profile` and `amendments_available`

## Frontend consumption rule

The frontend should render from `structured_result` and shared types directly.

It should not:

- invent contradictory summary state
- silently override backend verdicts
- treat fallback values as a second source of truth

## Transitional or non-canonical interfaces

- `POST /api/validate/v2`
- `GET /api/validate/v2/session/{session_id}`

These can remain in the codebase, but they are not the primary public-beta contract. The beta contract is the `structured_result` flow served through `GET /api/results/{jobId}`.
