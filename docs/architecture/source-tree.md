# Source Tree

## Monorepo ownership

### `apps/api`

Primary backend ownership for beta:

- auth and role normalization
- onboarding state and requirements
- LC validation pipeline
- result persistence
- result serving

Important runtime surfaces:

- `app/routers/auth.py`
- `app/routers/onboarding.py`
- `app/routers/validate.py`
- `app/routers/jobs_public.py`

### `apps/web`

Primary frontend ownership for beta:

- login and route entry
- exporter and importer dashboards
- upload workflows
- results rendering
- paywall and quota UX

Important runtime surfaces:

- `src/hooks/use-auth.tsx`
- `src/hooks/use-lcopilot.ts`
- `src/lib/exporter/resultsMapper.ts`
- `src/pages/ExporterDashboard.tsx`
- `src/pages/ImporterDashboardV2.tsx`
- `src/pages/ExporterResults.tsx`
- `src/pages/ImportResults.tsx`

### `packages/shared-types`

Shared contract ownership:

- TypeScript and Python schemas for result payloads
- runtime schema validation for frontend consumption

## Documentation rule

When documenting LCopilot beta behavior, start from:

1. `apps/api` for runtime truth
2. `packages/shared-types` for contract shape
3. `apps/web` for actual user-facing consumption

That order matters because the frontend should not redefine the contract.
