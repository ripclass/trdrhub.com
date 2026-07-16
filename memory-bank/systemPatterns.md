# TRDR Hub - System Patterns

## Proofline Architecture Pattern (July 2026)

Proofline is not a standalone platform and not another validation engine. It is a
tenant-owned `TradeCase` aggregate that orchestrates existing TRDR Hub services.

```text
TradeCase
  -> payment-arrangement applicability
  -> existing module adapters
  -> persisted check runs
  -> normalized findings with source references
  -> internal reviewer verification/remediation
  -> final decision and versioned report
```

### Reuse Boundaries

- LC present: reuse the existing LCopilot result/runner; never copy UCP600 logic.
- Documents: reuse `Document`, S3, OCR, and extraction; add case associations and
  immutable version lineage.
- Sanctions/CBAM/EUDR: invoke existing services and preserve source results.
- RulHub/EIN: external API adapters only; never copy corpora, wallets, identities,
  keys, credentials, or mocked production verification.
- Billing/reports/notifications/audit: use existing TRDR Hub rails.

### Tenant and Security Rules

- Customer queries require both `company_id` and case/resource ID.
- Internal analyst routes use the existing system-admin gate and audit actions.
- Customer response schemas never serialize internal notes or screening payloads.
- Report/document delivery uses tenant checks and expiring links.
- External requests send bounded context only; no document bodies in normal logs.
- Dependency failure or missing evidence maps to unable/pending/incomplete, not Clear.

### Lifecycle Rules

- All case status changes go through `services/proofline/state.py`.
- Status and final decision are separate concepts.
- Transitions append idempotent `TradeCaseEvent` rows with actor, reason, and time.
- Paid customer-facing final decisions require a qualified internal reviewer.
- Overrides retain the previous recommendation and require an override reason.
- Corrections create new document versions; originals are never overwritten.

### Contract Rules

- Shared customer contracts live in both `packages/shared-types/src/api.ts` and
  `packages/shared-types/python/schemas.py`; update them together.
- Normalized findings retain source module/ID/detail plus explicit `expected`,
  `observed`, and `suggested_correction` fields.
- Native module details remain in source records; Proofline stores bounded summaries
  and references instead of duplicating source payloads.
- Applicable-only module presentation uses Clear, Issue found, Evidence incomplete,
  Not applicable, Unable to assess, and Pending review semantics.

### Release and Operations Rules

- Backend flag: `PROOFLINE_ENABLED`; frontend flag: `VITE_PROOFLINE_ENABLED`.
- Checkout has an independent `PROOFLINE_CHECKOUT_ENABLED` switch.
- Packages and limits are database-backed; do not hardcode prices across the UI.
- Current background execution is persisted/idempotent but in-process. Add a
  deployed durable worker before high-volume unattended operation.
- Authoritative setup and verification: `docs/PROOFLINE_SETUP.md` and the Proofline
  repository audit.

---

## Historical System Patterns

## Critical: useAuth Hook
Located: `apps/web/src/hooks/use-auth.tsx`

**Returns:**
```typescript
{ user, isLoading, loginWithEmail, registerWithEmail, logout, hasRole, refreshUser }
```

**Does NOT return:** `session`, `token`, `access_token`

**User object:**
```typescript
{
  id: string,        // UUID or 'guest'
  email: string,
  full_name?: string,
  role: 'exporter' | 'bank' | 'admin',
  // ...
}
```

## Dashboard Layout Pattern
Both Price Verify and Tracking dashboards follow the same pattern.

**Reference: PriceVerifyDashboard** (`apps/web/src/pages/tools/price-verify/PriceVerifyDashboard.tsx`)

Key points:
1. NO auth checking in layout components
2. NO loading states or redirects
3. Just render the sidebar + Outlet
4. Auth handled at route level if needed

```typescript
export default function DashboardLayout() {
  const { user } = useAuth();  // Only destructure what you need
  const { isAdmin } = useUserRole();
  const [commandOpen, setCommandOpen] = useState(false);
  
  // NO conditional returns before hooks
  // NO isLoading checks
  // NO Navigate redirects
  
  useEffect(() => { /* keyboard shortcuts */ }, []);
  const runCommand = useCallback(() => { }, []);
  
  return (
    <SidebarProvider>
      <Sidebar>...</Sidebar>
      <SidebarInset>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  );
}
```

## API Calls Pattern
Use `credentials: "include"` for auth cookies. No need for Authorization headers.

```typescript
const response = await fetch(`${API_BASE}/endpoint`, {
  credentials: "include",
});
```

## File Structure
```
apps/
  web/                    # React frontend
    src/
      hooks/              # useAuth, useUserRole, useCurrency
      pages/
        hub/              # Main hub pages
        tools/
          price-verify/   # Price Verify tool
          tracking/       # Container/Vessel Tracker
      components/
        ui/               # shadcn components
  api/                    # FastAPI backend
    app/
      routers/            # API endpoints
      services/           # Business logic
      models/             # SQLAlchemy models
Data/                     # Rule JSON files
packages/
  shared-types/           # Shared TypeScript/Python types
```

## Route Structure
```
/hub                      # HubLayout with HubHome
/price-verify/dashboard   # PriceVerifyDashboard
/tracking/dashboard       # TrackingLayout
```

## Environment Variables
Frontend (`apps/web/.env`):
- VITE_API_URL
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY

Backend (`apps/api/.env`):
- DATABASE_URL
- SUPABASE_URL
- SUPABASE_SERVICE_KEY

