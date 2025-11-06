# Admin Console Data Model, Feature Flags, and RBAC Reference

## Scope and Purpose

This reference accompanies the Admin Console V2 implementation. It documents the
client-side data contracts, feature-flag model, permissions grid, and primary
extension points required to swap the current mock layer for a real Admin API.
All types referenced below live in `apps/web/src/lib/admin`, and the spec is
kept intentionally lightweight so it can be refreshed alongside code changes.

---

## Core Data Model

### Operations & Runtime Health

| Entity | TypeScript interface | Notes |
|--------|----------------------|-------|
| Job orchestration | `OpsJob` | Tracks queue, status, timing metadata, retry counts. |
| Alerting | `OpsAlert` | Severity, source system, acknowledgement / resolution cadence. |
| KPI metrics | `KPIStat`, `OpsMetric` | Drives overview cards, supports trend and target analysis. |

### Audit & Compliance

| Entity | Interface | Notes |
|--------|-----------|-------|
| Audit trail | `AuditLogEntry`, `AdminAuditEvent` | `AuditLogEntry` powers timeline views, `AdminAuditEvent` stores console mutations captured via `useAdminAudit`. |
| Approvals | `ApprovalRequest` | 4-eyes workflow with before/after payloads and comment log. |
| Compliance status | `CompliancePolicyResult` | Badge + owner + exception counts per policy. |

### Security & Access

| Entity | Interface | Notes |
|--------|-----------|-------|
| Administrators | `AdminUser`, `RoleDefinition` | Role metadata used in invite / disable / role edit flows. |
| API credentials | `ApiKeyRecord` | Tracks scopes, environment, rotation history. |
| Sessions | `SessionRecord` | Device fingerprint, last activity, revocation support. |

### Billing & Finance

| Entity | Interface | Notes |
|--------|-----------|-------|
| Plans | `BillingPlan` | Tiered pricing, limits, status. |
| Manual adjustments | `BillingAdjustment` | Credit/charge payloads with currency-normalised `amount`. |
| Disputes | `BillingDispute` | Outcome workflow (won/lost/write-off) plus evidence deadlines. |

### Partners & Integrations

| Entity | Interface | Notes |
|--------|-----------|-------|
| Registry | `PartnerRecord` | Partner category, markets served, lifecycle state. |
| Connectors | `ConnectorConfig` | Endpoint health, auth type, secret handling. |
| Webhooks | `WebhookDelivery` | Delivery outcomes, retry counts, HTTP response metadata. |

### LLM Operations

| Entity | Interface | Notes |
|--------|-----------|-------|
| Prompt library | `PromptRecord`, `PromptVersion` | Versioned prompt history and diff summary for publishing. |
| Budgets | `LLMBudget` | Provider spend caps, forecasts, notification recipients. |
| Evaluations | `EvaluationRun` | Tracks dataset, status and metrics for model eval jobs. |

### Compliance & Legal

| Entity | Interface | Notes |
|--------|-----------|-------|
| Residency | `ResidencyPolicy` | Region-specific storage posture and owner. |
| Retention | `RetentionSchedule` | Lifecycle schedules with dry-run summaries. |
| Legal holds | `LegalHold` | Case tracking, affected objects, release workflow. |

### Platform & System

| Entity | Interface | Notes |
|--------|-----------|-------|
| Feature flags | `FeatureFlagRecord`, `FeatureFlagTargeting` | Live control-plane flags with environment / tenant targeting. |
| Releases | `ReleaseRecord` | Deployment history, linked services, PR references. |
| Settings | `AdminSettings` | Branding, authentication and notification defaults editable from UI. |

> Pagination helpers (`Pagination`, `PaginatedResult<T>`) wrap almost every
list endpoint so API responses stay consistent with the table components.

---

## Feature Flag Model

The console recognises two classes of feature flags:

1. **Platform flags** – returned by the Admin service via `listFeatureFlags()`
   and mutated with `setFeatureFlagStatus()` / `updateFeatureFlagTargeting()`.
   These represent remote kill-switches and are rendered in the “Platform
   flags” card. New providers must honour the `FeatureFlagRecord` contract and
   persist state server-side.
2. **Module toggles** – stored client-side through `apps/web/src/config/featureFlags.ts`.
   They gate optional modules (Billing, Partners, LLM, Compliance) without
   requiring API calls and are persisted in `localStorage` under
   `admin:featureFlags`. Integrators can extend this list by introducing new
   keys in `AdminFeatureFlag` and surfacing matching toggles in the Feature
   Flags card.

When migrating off the mock layer, replace `MockAdminService` implementations
for feature flag methods with real API calls and ensure the UI calls remain
`await`-ed so audit hooks continue to fire.

---

## RBAC & Permission Mapping

- **Permission vocabulary** is centralised in
  `apps/web/src/lib/admin/permissions.ts`. It enumerates the granular claims
  (`ops:read`, `billing_disputes:write`, etc.) consumed throughout the console.
- **Section gating** is defined through `SECTION_PERMISSIONS`, pairing each
  `AdminSection` with required view/action claims. Use `canViewSection()` and
  `canPerformAction()` helpers when wiring new modules to ensure consistent
  gating logic.

### Default Role Profiles

`MockAdminService` seeds the following roles (mirroring expected backend roles):

| Role | Permissions (excerpt) | Notes |
|------|------------------------|-------|
| `super_admin` | `*` | Full access, bypasses gating checks. |
| `admin` | `users:*`, `api_keys:*`, `sessions:*`, `feature_flags:*`, `settings:*` | Primary operator role. |
| `auditor` | `audit:read`, `approvals:read`, `compliance:read` | Read-only compliance + release visibility. |
| `support` | `jobs:*`, `alerts:*`, `sessions:*` | On-call focus, editable at runtime. |
| `billing` | `billing:*`, `billing_adjustments:write`, `billing_disputes:write` | Finance operations scope. |
| `viewer` | `admin:read`, `ops:read`, `audit:read` | Read-only dashboards. |

Backends should provide an endpoint that mirrors this structure so the console
can hydrate `RoleDefinition[]` dynamically.

---

## Audit Trail Instrumentation

All mutating UI paths must call `useAdminAudit(section)` before resolving to
surface a consistent audit trail. The hook pipes events through
`AdminService.recordAdminAudit`, attaching `section`, `action`, optional
`entityId`, and a metadata blob. The `AdminAuditEvent` interface mirrors the
expected payload for downstream storage or forwarding to a SIEM.

When adding new mutations:

1. Import `useAdminAudit` inside the section component.
2. Instantiate the hook with the owning `AdminSection` key.
3. `await audit("action_name", { entityId, metadata })` after a successful
   service invocation. The mock layer silently accepts writes; real
   implementations should persist and return a 2xx/4xx code accordingly.

---

## Service Layer Extension Points

The Admin Console talks to a single abstraction, `AdminService`, declared in
`apps/web/src/lib/admin/types.ts`. The default export
`getAdminService(source = "mock")` returns the current
`MockAdminService`, but the hook is intentionally split so a production build can
inject an API-backed implementation.

To integrate a real backend:

1. Create a new class (e.g., `ApiAdminService`) that implements every method on
   `AdminService` using your HTTP client of choice.
2. Update `getAdminService()` to return the API version when a `source === "api"`
   flag is provided (environment variable or dependency injection).
3. Ensure responses adhere to the existing interfaces (`PaginatedResult<T>`,
   `MutationResult`, etc.) to avoid UI regressions.
4. If your backend diverges on field names, normalise them inside the service
   layer rather than leaking changes into the component tree.

### Adding New Domains

1. Define the new type(s) in `apps/web/src/lib/admin/types.ts`.
2. Add permission strings and section mapping in
   `apps/web/src/lib/admin/permissions.ts`.
3. Extend `AdminService` with read/mutation methods and mirror those in the mock
   implementation so local development stays deterministic.
4. Gate UI routes via `AdminSidebar` / `AdminShell` with the new section id to
   guarantee breadcrumb support and audit coverage.

---

## Data Refresh & Mock Strategy

The mock service seeds deterministic datasets for every module. This keeps the
console fully navigable without backend dependencies while providing realistic
shapes (timestamps, nested metadata, before/after diffs). When implementing the
real service layer, you can reuse the mock as a fallback by passing
`getAdminService("mock")` in storybook or preview environments.

Whenever the TypeScript interfaces change, update this document alongside the
`MockAdminService` to prevent drift. A quick diff of `lib/admin/types.ts`
against the API OpenAPI contract is sufficient to spot gaps.

---

## Quick Reference

- **Types:** `apps/web/src/lib/admin/types.ts`
- **Permissions:** `apps/web/src/lib/admin/permissions.ts`
- **Mock data:** `apps/web/src/lib/admin/services/mock/mockAdminService.ts`
- **Feature toggles:** `apps/web/src/config/featureFlags.ts`
- **Audit hook:** `apps/web/src/lib/admin/useAdminAudit.ts`

Keep this sheet close when adding new admin modules or when preparing the Admin
API contract—every endpoint should map back to one of the interfaces enumerated
above.


