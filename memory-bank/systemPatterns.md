# TRDR Hub - System Patterns

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

