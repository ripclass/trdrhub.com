# Auth / Onboarding / Routing Audit

_Last updated: 2025-11-14_

This document captures the current authentication, onboarding, and dashboard-routing behavior for the `trdrhub.com` stack (Supabase + FastAPI + React). It is split into:

1. Current architecture & codepaths
2. Observed root causes
3. Truth table & future data model
4. Implementation plan
5. Verification checklist

> **Data note** – I do **not** have direct access to the production Supabase project. Wherever the audit calls for concrete data (Supabase auth user, DB rows, `/auth/me` output, etc.) you or the assigned debugger must run the described queries/scripts against your environment.

---

## 1. Current architecture & codepaths

### 1.1 Frontend authentication flow

1. User opens `/login` and submits credentials.
2. `apps/web/src/hooks/use-auth.tsx` (`loginWithEmail`) calls `supabase.auth.signInWithPassword`, then waits for the Supabase session via `waitForSupabaseSession`.
3. Once a Supabase access token exists, `fetchUserProfile` calls `GET /auth/me` with `Authorization: Bearer <supabase_token>`. The backend validates the Supabase JWT (via JWKS) and returns a `UserProfile`.
4. `useAuth` stores a simplified `User` object (id, email, full_name, `role` mapped via `mapBackendRole`), sets CSRF token, and exposes `user`, `isLoading`, `loginWithEmail`, `logout`, etc.

Supporting code:

```apps/web/src/hooks/use-auth.tsx
const profile = await fetchUserProfile(token)
setUser({
  id: userData.id,
  email: userData.email,
  full_name: userData.full_name,
  role: mapBackendRole(userData.role),
  ...
})
```

### 1.2 Legacy / parallel auth contexts

Despite `useAuth`, two other auth providers remain active:

| Context | Location | Behavior |
| --- | --- | --- |
| `useExporterAuth` | `apps/web/src/lib/exporter/auth.tsx` | Maintains its own context backed by mock users, localStorage tokens (`exporter_token`, `trdrhub_api_token`), and even calls `/auth/login`. Still injected into `ExporterDashboard`, `ExporterSidebar`, and other exporter components. |
| `useBankAuth` | `apps/web/src/lib/bank/auth.tsx` | Similar mock-based context storing `bank_token`. Tries Supabase -> `/auth/me` fallback, but still supports local mock login and separate idle-timeout logic. Used by bank dashboards and login flows. |

Components such as `ExporterSidebar` import **both** `useExporterAuth` and `useAuth`, attempting to reconcile them, which is why cross-user identity bleeding happens:

```apps/web/src/components/exporter/ExporterSidebar.tsx
const { user: exporterAuthUser, logout: exporterLogout } = useExporterAuth()
const { logout: mainLogout } = useAuth()
const user = propUser || exporterAuthUser
```

### 1.3 Backend auth endpoints

* `POST /auth/register` (`apps/api/app/routers/auth.py`) – creates both Supabase and backend users. It saves:
  * `User.role` (whatever the frontend sends, e.g. `"exporter"`, `"importer"`, `"tenant_admin"`)
  * Optional `Company` row with `event_metadata.business_type` and `event_metadata.company_size`
  * `User.onboarding_data` seeded with `business_types` and `company` information if provided

* `POST /auth/login` – legacy password login (not used by Supabase email/password users, but still used by legacy exporter auth).
* `GET /auth/me` – uses Supabase JWT to retrieve `User`, normalizes role, and returns `UserProfile`.

### 1.4 Onboarding status flow

* Frontend `OnboardingProvider` (`apps/web/src/components/onboarding/OnboardingProvider.tsx`) calls `GET /onboarding/status` on load and caches the result.
* Backend `apps/api/app/routers/onboarding.py::get_status`:
  1. Checks if `current_user.onboarding_data` already exists.
  2. If missing, tries to link `current_user.company_id` -> `Company`, else looks up `Company.contact_email == current_user.email`, else auto-creates a default company.
  3. Restores `onboarding_data` from `Company.event_metadata`.
  4. Returns `OnboardingStatus` with `role = current_user.role`.

Key snippet:

```apps/api/app/routers/onboarding.py
if company_type == 'both':
    restored_data['business_types'] = ['exporter', 'importer']
elif company_type:
    restored_data['business_types'] = [company_type]

return OnboardingStatus(
    user_id=str(current_user.id),
    role=current_user.role,
    details=current_user.onboarding_data or {},
)
```

### 1.5 Routing logic

* `apps/web/src/pages/Login.tsx` now owns the routing decision immediately after `loginWithEmail`.
* It fetches `getOnboardingStatus()`, inspects `status.role`, `details.business_types`, `details.company.type`, and `details.company.size`, then sets `destination`.
* The code attempts multiple retries/fallbacks, but ultimately defaults to `/lcopilot/exporter-dashboard`.
* Separate dashboards also have their own guards:
  * `ExporterDashboard` uses `useExporterAuth`.
  * `CombinedDashboard` recently switched from `useExporterAuth` to `useAuth`, but still receives `user` via props in some places.
  * `EnterpriseDashboard` only recently started checking `useAuth`.
  * Bank dashboard uses `useBankAuth`.

---

## 2. Root causes (bugs)

| ID | Bug | Evidence / Files | Impact |
| --- | --- | --- | --- |
| **A** | **Multiple auth systems running in parallel** (`useAuth`, `useExporterAuth`, `useBankAuth`) | `apps/web/src/components/exporter/ExporterSidebar.tsx`, `apps/web/src/lib/exporter/auth.tsx`, `apps/web/src/lib/bank/auth.tsx` | Cross-user identity leakage, conflicting logout flows, “demo” tokens overriding Supabase session. |
| **B** | **`User.role` vs `business_types` ambiguity** | `apps/api/app/routers/auth.py` sets `role` = form input; SME “both” users still get `role='exporter'`. | Routing logic defaults to exporter dashboard even when `business_types` includes importer. |
| **C** | **Onboarding restoration relies on stale `Company.event_metadata`** | `apps/api/app/routers/onboarding.py` auto-creates companies and restores `onboarding_data` only if metadata exists. | Users created before company linking may get `details={}` + `company_id=null`, causing routing retries/fallback to fail. |
| **D** | **Logout is only “nuclear” in `useAuth`, not in the legacy contexts** | `useAuth.logout` clears tokens & reloads, but `useExporterAuth.logout` only removes `exporter_token`, and `useBankAuth.logout` only removes `bank_token`. | Logging out of one dashboard leaves other tokens intact → logging in as a different user re-hydrates stale context. |
| **E** | **Screens/dashboards subscribe to different auth sources** | Exporter/Combined dashboards still rely on `useExporterAuth` fallback user when `propUser` missing. | Sidebar & topbar may display different user data depending on which context resolves first (“intermingled names”). |
| **F** | **Backend `/onboarding/status` returns `role=current_user.role` even when `onboarding_data` suggests importer/tenant_admin** | No recomputation of role based on `business_types` or company size. | Frontend `Login.tsx` uses `status.role`, so importer accounts stored as `role='exporter'` never reach importer dashboard. |
| **G** | **Legacy `/auth/login` still enabled** | `apps/api/app/routers/auth.py::login_user` called by `useExporterAuth`. | Encourages storing backend JWTs in localStorage (`trdrhub_api_token`), bypassing Supabase session entirely. |

---

## 3. Truth table & desired model

| Email | Real-world type | Desired DB `users.role` | `onboarding_data.business_types` | `onboarding_data.company` | Target route |
| --- | --- | --- | --- | --- | --- |
| `imran@iec.com` | Exporter | `exporter` | `['exporter']` | `{ type: 'exporter', size: 'sme' }` | `/lcopilot/exporter-dashboard` |
| `rasel@ric.com` | Importer | `importer` | `['importer']` | `{ type: 'importer', size: 'sme' }` | `/lcopilot/importer-dashboard` |
| `monty@mei.com` | SME both | `exporter` (OK) | `['exporter','importer']` | `{ type: 'both', size: 'sme' }` | `/lcopilot/combined-dashboard` |
| `sumon@stl.com` | Medium both | `tenant_admin` | `['exporter','importer']` | `{ type: 'both', size: 'medium' }` | `/lcopilot/enterprise-dashboard` |
| `pavel@pth.com` | Large both | `tenant_admin` | `['exporter','importer']` | `{ type: 'both', size: 'large' }` | `/lcopilot/enterprise-dashboard` |
| `azam@sabl.com` | Bank | `bank_officer` or `bank_admin` | `['bank']` or empty | `{ type: 'bank' }` | `/lcopilot/bank-dashboard` |

Routing should be a pure function:

```ts
type Destination =
  | '/lcopilot/exporter-dashboard'
  | '/lcopilot/importer-dashboard'
  | '/lcopilot/combined-dashboard'
  | '/lcopilot/enterprise-dashboard'
  | '/lcopilot/bank-dashboard'

function decideRoute(profile: UserProfile, onboarding: OnboardingStatus): Destination
```

Rules:

1. Bank roles → `/lcopilot/bank-dashboard`
2. Tenant admin or (company.type === 'both' && company.size in ['medium','large']) → `/lcopilot/enterprise-dashboard`
3. Combined SME (business_types include exporter+importer) → `/lcopilot/combined-dashboard`
4. Importer → `/lcopilot/importer-dashboard`
5. Default → `/lcopilot/exporter-dashboard`

---

## 4. Implementation plan

### 4.1 Backend

1. **Audit users & companies** – Run the `verify_user_data` script/endpoint for each test account. Record actual `role`, `company_id`, `onboarding_data`, `event_metadata`.
2. **Migration** – Write an idempotent script to:
   - Ensure every `User` has `company_id`.
   - Ensure `Company.event_metadata.business_type` and `.company_size` match truth table.
   - Set `User.onboarding_data.business_types` and `.company` accordingly.
   - For importer-only users, set `User.role='importer'`.
3. **`/onboarding/status`** – Compute `role` using onboarding data (not `current_user.role`). E.g. if `business_types == ['importer']`, return `role='importer'`; if size medium/large with both types → `tenant_admin`.
4. **Disable legacy `/auth/login` for Supabase accounts** – Either remove it or limit it to system-admin-only users so the frontend stops storing `trdrhub_api_token`.

### 4.2 Frontend

1. **Remove `useExporterAuth` / `useBankAuth`** from production bundles:
   - Replace usages with `useAuth`.
   - If demo mode is needed, gate the legacy contexts behind an explicit feature flag.
2. **Centralize routing**:
   - Extract the `Login.tsx` routing block into `decideDestination(profile, onboardingStatus)` helper with unit tests.
   - Use the same helper inside any other guard (e.g. when refreshing session or doing auto-login).
3. **Dashboard guards**:
   - Each dashboard component should check `useAuth.user` and redirect if the route doesn’t match `decideDestination`.
   - Remove references to local tokens and `useExporterAuth`.
4. **Logout**:
   - Ensure all logout buttons call `useAuth.logout` only.
   - Remove secondary logout flows.

### 4.3 Documentation & telemetry

1. Update onboarding/register docs to clarify how `company_type`, `company_size`, and `business_types` should be populated.
2. Add logging to `/auth/me` and `/onboarding/status` to print user id + returned role so we can detect mismatches early.

---

## 5. Verification checklist

For each test user (`imran`, `rasel`, `monty`, `sumon`, `pavel`, `azam`):

1. Capture Supabase auth user (screenshot from Supabase dashboard).
2. Run `GET /auth/me` with their token, paste JSON.
3. Run `GET /onboarding/status`, paste JSON.
4. Login via UI → take screenshot showing:
   - Final URL
   - Dashboard breadcrumb/heading
   - Sidebar footer showing the correct name
5. Run Jest/Vitest tests for the routing helper.

All screenshots + JSON responses should be linked in the PR or attached to QA notes.

---

## Next steps

1. Assign a dedicated engineer to execute the migration + refactor plan above.
2. Freeze other feature work touching auth/onboarding/routing until the cleanup is done.
3. After the fix, document the final architecture in `/docs/AUTHENTICATION.md` and add regression tests (unit + Cypress/Playwright).


