# Core Workflows

## 1. Authentication and route resolution

Canonical beta intent:

- authenticate the user through the shared auth path
- resolve role and onboarding truth through backend state
- route the user to the correct dashboard
- keep logout behavior singular and destructive

Current repo truth:

- `useAuth` and `/auth/me` are the intended primary path
- `/onboarding/status` restores onboarding state and computes effective role
- legacy auth contexts still exist in the frontend and are a launch risk

## 2. Exporter gold path

The exporter loop is the primary launch workflow:

1. login
2. land on exporter dashboard
3. upload LC-related documents
4. call `POST /api/validate`
5. receive a job id and validation response
6. fetch persisted truth through `GET /api/results/{jobId}`
7. render summary, documents, issues, analytics, and readiness from `structured_result`
8. reopen later through history using the same result path
9. enforce quota or paywall as needed

## 3. Importer shared-spine path

Importer is in scope for beta, but it should not become a second architecture.

Importer should:

- use the same auth and routing machinery
- use the same validation entrypoint
- use the same persisted `structured_result`
- use the same results fetch and mapping path
- change framing and actions only where importer intent differs from exporter intent

## 4. Results reopen and history

Persisted results matter because the beta is not only a one-time validation tool.

The canonical reopen path is:

- stored validation session
- persisted `structured_result`
- `GET /api/results/{jobId}`
- shared frontend result mapping

Any history view that bypasses that path risks drift.

## 5. Quota and paywall loop

Beta assumes a hard paywall with an initial free-entry allowance.

That means the user workflow must include:

- clear usage state
- predictable blocking when quota is exhausted
- consistent frontend and backend enforcement
- a visible next action when access is restricted

## 6. Secondary surfaces

Combined and enterprise may remain visible only if they reuse the same core workflow. Bank is not a launch-critical workflow for this beta.
