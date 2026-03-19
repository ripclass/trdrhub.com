# High-Level Architecture

## Launch spine

LCopilot Public Beta is built around one shared application spine:

1. the web app authenticates the user and resolves the correct dashboard
2. the user uploads documents through the exporter or importer flow
3. `POST /api/validate` runs the validation pipeline
4. the backend persists a `structured_result`
5. `GET /api/results/{jobId}` returns that same persisted result contract
6. the frontend renders review state from the canonical payload

In short:

`Auth -> Upload -> Validate -> Persist structured_result -> Fetch results -> Review -> History -> Paywall/quota -> Repeat`

## Core system components

### Web app

- React + Vite frontend in `apps/web`
- login, onboarding, exporter/importer dashboards, upload flows, results pages
- `use-lcopilot` fetches validation and results data
- `resultsMapper` normalizes the backend payload for the UI

### API

- FastAPI backend in `apps/api`
- owns auth, onboarding, validation, persistence, and results serving
- `POST /api/validate` is the canonical write path
- `GET /api/results/{jobId}` is the canonical read path

### Shared contract

- `packages/shared-types` defines shared result schemas and types
- `structured_result` is the runtime contract that exporter and importer must share

## Current strengths

- The validation core is already richer than the rest of the product.
- The backend persists a structured result rather than forcing the frontend to reconstruct state.
- Exporter already uses the strongest end-to-end path in the repo.

## Current weaknesses

- Auth, onboarding, and routing are still fragmented.
- Some frontend surfaces still rely on compatibility or fallback logic that can hide backend truth drift.
- Importer maturity still trails exporter.
- Combined, enterprise, and bank surfaces increase surface area without improving the launch-critical loop.

## Secondary-surface rule

A secondary surface can stay visible in beta only if it rides the same:

- auth system
- route resolution logic
- validation contract
- result-rendering path

If it forks any of those, it is not part of the launch spine.
