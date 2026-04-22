# Phase 4 — Sidebar Slim-Down + Dashboard Wire-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring both portal sidebars to a 4/5-item minimum, fold dropped sections into dashboard + top-bar, and — most importantly — **verify the dashboard actually updates within 5 seconds** of a new validation completing (the test that must pass, not just "the code calls the endpoint").

**Architecture:** Sidebar components rewritten to minimum set. `ImporterDashboardV2` rebuilt on the shared skeleton (stats strip · start-new · recent-10 with view-all · quota). React Query invalidation wired into `useValidate` / `useResumeValidate` success handlers. Removed routes get 301 redirects. Dropped dashboard sections folded into top-bar (notifications, help) or merged into sibling pages (billing-usage into billing).

**Tech Stack:** React 18 + React Query v4 + Playwright. No backend changes (Phase 2 already added `workflow_type` which drives the type badges on recent-activity rows).

**Prereq:** Phases 1-3 complete.

**Spec:** `docs/superpowers/specs/2026-04-21-importer-parity-design.md` (Phase 4 section)

---

## Task 1: Rewrite `ExporterSidebar` — drop Validations, rename to Upload

**Files:**
- Modify: `apps/web/src/components/exporter/ExporterSidebar.tsx`
- Modify: `apps/web/src/lib/exporter/exporterSections.ts`

- [ ] **Step 1: Write failing test**

Create `apps/web/src/components/exporter/__tests__/ExporterSidebar.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ExporterSidebar } from "../ExporterSidebar";

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ user: { email: "e@x.com" }, logout: vi.fn() }),
}));

function renderSidebar() {
  return render(
    <MemoryRouter>
      <ExporterSidebar activeSection="dashboard" onSectionChange={vi.fn()} />
    </MemoryRouter>,
  );
}

describe("ExporterSidebar — minimum set", () => {
  it("renders exactly 4 main items: Dashboard, Upload, Billing, Settings", () => {
    renderSidebar();
    expect(screen.getByRole("button", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^upload$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /billing/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /settings/i })).toBeInTheDocument();
  });

  it("does NOT render Validations or New Validation", () => {
    renderSidebar();
    expect(screen.queryByRole("button", { name: /validations/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new validation/i })).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/web && npm run test -- ExporterSidebar`
Expected: FAIL (current sidebar has "New Validation" and "Validations").

- [ ] **Step 3: Edit the sidebar component**

Edit `apps/web/src/components/exporter/ExporterSidebar.tsx`:

- Remove the `<SidebarMenuItem>` block containing the "Validations" / `Clock` entry (currently ~lines 102-111 per the reading).
- Change `<span>New Validation</span>` to `<span>Upload</span>` (the button that maps to `activeSection === "upload"`).
- Change the `tooltip="New Validation"` to `tooltip="Upload"`.
- Update the TypeScript `ExporterSidebarSection` union: remove `"reviews"`.

Final section union:
```typescript
export type ExporterSidebarSection =
  | "dashboard"
  | "upload"
  | "billing"
  | "settings";
```

- [ ] **Step 4: Update `exporterSections.ts`**

Edit `apps/web/src/lib/exporter/exporterSections.ts`:

- Remove `"reviews"` from `SidebarSection` union (line ~102-107)
- Update `sectionToSidebar()` — map what previously went to `"reviews"` to `"dashboard"` instead
- Update `sidebarToSection()` — drop the `"reviews"` case

New `SidebarSection` type:
```typescript
export type SidebarSection =
  | "dashboard"
  | "upload"
  | "billing"
  | "settings";
```

Update any call sites that pass `"reviews"` as a sidebar section — they should now route to `"dashboard"` or to the `/reviews` page directly via URL.

- [ ] **Step 5: Type-check + tests**

Run: `cd apps/web && npm run type-check && npm run test -- ExporterSidebar`
Expected: all PASS.

- [ ] **Step 6: Smoke — exporter sidebar visually matches spec**

Start dev server, log in as exporter, confirm sidebar has exactly: Dashboard / Upload / Billing / Settings. Old "Validations" item is gone.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Slim exporter sidebar to 4 items: Dashboard · Upload · Billing · Settings"
```

---

## Task 2: Rewrite `ImporterSidebar` to 5-item minimum

**Files:**
- Modify: `apps/web/src/components/importer/ImporterSidebar.tsx`
- Create: `apps/web/src/components/importer/__tests__/ImporterSidebar.test.tsx`

- [ ] **Step 1: Read the current importer sidebar**

Run: `wc -l apps/web/src/components/importer/ImporterSidebar.tsx`
Expected: current size. Read the full file to understand the existing structure.

- [ ] **Step 2: Write failing test**

Create `apps/web/src/components/importer/__tests__/ImporterSidebar.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ImporterSidebar } from "../ImporterSidebar";

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ user: { email: "i@x.com" }, logout: vi.fn() }),
}));

function renderSidebar() {
  return render(
    <MemoryRouter>
      <ImporterSidebar activeSection="dashboard" onSectionChange={vi.fn()} />
    </MemoryRouter>,
  );
}

describe("ImporterSidebar — minimum set", () => {
  it("renders exactly 5 items: Dashboard, Draft LC Review, Supplier Doc Review, Billing, Settings", () => {
    renderSidebar();
    expect(screen.getByRole("button", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /draft lc review/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /supplier doc review/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /billing/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /settings/i })).toBeInTheDocument();
  });

  it("does NOT render dropped items", () => {
    renderSidebar();
    for (const label of [
      /workspace/i, /templates/i, /analytics/i, /notifications/i,
      /ai assistance/i, /content library/i, /shipment timeline/i, /help/i,
    ]) {
      expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
    }
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- ImporterSidebar`
Expected: FAIL.

- [ ] **Step 4: Rewrite the sidebar**

Replace `apps/web/src/components/importer/ImporterSidebar.tsx` with:

```typescript
import { BarChart3, FileText, ShieldCheck, Settings, Building2, CreditCard, LogOut, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export type ImporterSidebarSection =
  | "dashboard"
  | "draft-lc"
  | "supplier-docs"
  | "billing"
  | "settings";

interface ImporterSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeSection: ImporterSidebarSection;
  onSectionChange: (section: ImporterSidebarSection) => void;
  user?: { name?: string; email?: string; id?: string; role?: string };
}

export function ImporterSidebar({ activeSection, onSectionChange, user: propUser, ...props }: ImporterSidebarProps) {
  const { user: authUser, logout } = useAuth();
  const user = propUser || authUser;
  const displayName = propUser?.name || authUser?.full_name || authUser?.username || user?.email;

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="px-2 pt-2">
          <Link to="/hub" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-3 w-3" /> Back to Hub
          </Link>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-3">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-importer/10 text-importer">
                  <Building2 className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">LCopilot</span>
                  <span className="text-xs text-muted-foreground">Importer Portal</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeSection === "dashboard"} onClick={() => onSectionChange("dashboard")}>
                  <BarChart3 /> <span>Dashboard</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeSection === "draft-lc"} onClick={() => onSectionChange("draft-lc")} tooltip="Draft LC Review">
                  <FileText /> <span>Draft LC Review</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeSection === "supplier-docs"} onClick={() => onSectionChange("supplier-docs")} tooltip="Supplier Doc Review">
                  <ShieldCheck /> <span>Supplier Doc Review</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeSection === "billing"} onClick={() => onSectionChange("billing")} tooltip="Billing">
                  <CreditCard /> <span>Billing</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={activeSection === "settings"} onClick={() => onSectionChange("settings")} tooltip="Settings">
                  <Settings /> <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        {user && (
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2 py-1.5 w-full">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {displayName?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase() || "U"}
                </div>
                <div className="flex flex-col gap-0.5 leading-none flex-1 min-w-0">
                  <span className="truncate font-medium text-sm">{displayName || user.email}</span>
                  <span className="text-xs text-muted-foreground capitalize">
                    {user.role === "admin" ? "Admin" : "Importer"}
                  </span>
                </div>
                <Button variant="ghost" size="sm" onClick={async (e) => { e.preventDefault(); e.stopPropagation(); await logout(); }} className="h-8 w-8 p-0" title="Sign out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
```

- [ ] **Step 5: Run test to pass**

Run: `cd apps/web && npm run test -- ImporterSidebar`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Slim importer sidebar to 5 items: Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings"
```

---

## Task 3: Wire React Query invalidation on validation success

**Files:**
- Modify: `apps/web/src/hooks/use-lcopilot.ts`

- [ ] **Step 1: Locate `useValidate` and `useResumeValidate`**

Run: `grep -n "export function useValidate\|useResumeValidate\|useMutation" apps/web/src/hooks/use-lcopilot.ts | head -10`
Expected: multiple line numbers for the mutation hooks.

- [ ] **Step 2: Write failing test**

Append to `apps/web/src/hooks/__tests__/use-lcopilot.test.ts`:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { useValidate } from "../use-lcopilot";

describe("useValidate query invalidation", () => {
  it("invalidates user-sessions query on success", async () => {
    postSpy.mockReset().mockResolvedValue({ data: { job_id: "j1", documents: [] } });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const spy = vi.spyOn(qc, "invalidateQueries");

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useValidate(), { wrapper });
    result.current.mutate({ files: [new File(["x"], "x.pdf")] });

    await waitFor(() => expect(postSpy).toHaveBeenCalled());
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ["user-sessions"] }),
      ),
    );
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- use-lcopilot`
Expected: FAIL.

- [ ] **Step 4: Add invalidation**

In `apps/web/src/hooks/use-lcopilot.ts`, modify `useValidate`:

```typescript
import { useQueryClient } from "@tanstack/react-query";

export function useValidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: ValidateMutationVars) => { /* existing */ },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["user-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}
```

Do the same for `useResumeValidate`:
```typescript
export function useResumeValidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars) => { /* existing */ },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });
}
```

- [ ] **Step 5: Ensure session query uses `['user-sessions']` key**

Run: `grep -n "queryKey.*sessions\|useQuery.*sessions\|getUserSessions" apps/web/src -r --include="*.ts" --include="*.tsx" | head -10`

If current dashboards use a different queryKey (e.g., `['sessions']` or no key), update them to use `['user-sessions']` so invalidation hits. File to check: `pages/ExporterDashboard.tsx`, `pages/ImporterDashboardV2.tsx` — look for the `useEffect(() => { getUserSessions()... })` patterns and convert to `useQuery({ queryKey: ['user-sessions'], queryFn: getUserSessions })`.

- [ ] **Step 6: Convert at least the importer dashboard's session loader to useQuery**

In `apps/web/src/pages/ImporterDashboardV2.tsx`, find the imperative `getUserSessions()` call inside a `useEffect`. Replace with:

```typescript
import { useQuery } from "@tanstack/react-query";
// ...
const { data: sessions = [] } = useQuery({
  queryKey: ["user-sessions"],
  queryFn: getUserSessions,
  staleTime: 5_000, // allow fresh reload after invalidation
});
```

Do the same in `apps/web/src/pages/ExporterDashboard.tsx` if it uses imperative fetches.

- [ ] **Step 7: Run tests**

Run: `cd apps/web && npm run type-check && npm run test`
Expected: all PASS.

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Invalidate user-sessions query on validate success; convert dashboard fetches to useQuery"
```

---

## Task 4: Rewrite `ImporterDashboardV2` to shared skeleton

**Files:**
- Modify: `apps/web/src/pages/ImporterDashboardV2.tsx`
- Delete: `apps/web/src/pages/ImporterAnalytics.tsx`

- [ ] **Step 1: Write failing test**

Create `apps/web/src/pages/__tests__/ImporterDashboardV2.skeleton.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImporterDashboardV2 from "../ImporterDashboardV2";

vi.mock("@/api/sessions", () => ({
  getUserSessions: () => Promise.resolve([
    { id: "s1", status: "completed", workflow_type: "importer_draft_lc", lc_number: "LC-A", created_at: "2026-04-21T00:00:00Z" },
  ]),
}));
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ user: { email: "i@x.com" }, logout: vi.fn() }),
}));

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImporterDashboardV2 />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImporterDashboardV2 — skeleton", () => {
  it("renders Start New CTAs for both moments", async () => {
    renderDashboard();
    expect(await screen.findByRole("link", { name: /draft lc/i })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /supplier doc/i })).toBeInTheDocument();
  });

  it("renders Recent Activity with at least one session", async () => {
    renderDashboard();
    expect(await screen.findByText(/LC-A/i)).toBeInTheDocument();
  });

  it("renders View all reviews link", async () => {
    renderDashboard();
    expect(await screen.findByRole("link", { name: /view all/i })).toBeInTheDocument();
  });

  it("does NOT render dropped sections", () => {
    renderDashboard();
    expect(screen.queryByText(/ai assistance/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/content library/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/shipment timeline/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/web && npm run test -- ImporterDashboardV2.skeleton`
Expected: FAIL.

- [ ] **Step 3: Rewrite the dashboard**

Replace `apps/web/src/pages/ImporterDashboardV2.tsx` with:

```typescript
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ImporterSidebar } from "@/components/importer/ImporterSidebar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LcopilotQuotaBanner } from "@/components/billing/LcopilotQuotaBanner";
import { ReviewsTable, type ReviewsTableSession } from "@/components/lcopilot/ReviewsTable";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
import { FileText, ShieldCheck, TrendingUp, CheckCircle, AlertTriangle } from "lucide-react";

function sessionsToTableRows(sessions: ValidationSession[]): ReviewsTableSession[] {
  return sessions.slice(0, 10).map((s) => ({
    id: s.id,
    lcNumber: (s as any).lc_number ?? s.id.slice(0, 8),
    createdAt: s.created_at,
    verdict: (s as any).verdict ?? "pending",
    workflowType: (s as any).workflow_type ?? "exporter_presentation",
    resultsHref: `/lcopilot/importer-dashboard/results/${s.id}`,
  }));
}

function countThisMonth(sessions: ValidationSession[]): number {
  const now = new Date();
  return sessions.filter((s) => {
    const d = new Date(s.created_at);
    return d.getUTCFullYear() === now.getUTCFullYear() && d.getUTCMonth() === now.getUTCMonth();
  }).length;
}

function countAttentionNeeded(sessions: ValidationSession[]): number {
  return sessions.filter((s) => (s as any).verdict === "reject" || (s as any).verdict === "review").length;
}

export default function ImporterDashboardV2() {
  const { data: sessions = [] } = useQuery({
    queryKey: ["user-sessions"],
    queryFn: getUserSessions,
    staleTime: 5_000,
  });

  const rows = sessionsToTableRows(sessions);
  const thisMonth = countThisMonth(sessions);
  const attention = countAttentionNeeded(sessions);
  const completed = sessions.filter((s) => s.status === "completed").length;

  return (
    <DashboardLayout sidebar={<ImporterSidebar activeSection="dashboard" onSectionChange={() => {}} />}>
      <div className="container mx-auto p-6 space-y-6">
        <header>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Importer portal — draft LC review and supplier document review</p>
        </header>

        <LcopilotQuotaBanner />

        <section className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Reviews this month</CardDescription>
              <CardTitle className="text-3xl">{thisMonth}</CardTitle>
            </CardHeader>
            <CardContent><TrendingUp className="h-4 w-4 text-muted-foreground" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completed</CardDescription>
              <CardTitle className="text-3xl">{completed}</CardTitle>
            </CardHeader>
            <CardContent><CheckCircle className="h-4 w-4 text-muted-foreground" /></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Attention needed</CardDescription>
              <CardTitle className="text-3xl">{attention}</CardTitle>
            </CardHeader>
            <CardContent><AlertTriangle className="h-4 w-4 text-muted-foreground" /></CardContent>
          </Card>
        </section>

        <Card>
          <CardHeader>
            <CardTitle>Start New</CardTitle>
            <CardDescription>Pick the workflow that matches your current moment</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <Button asChild size="lg">
              <Link to="/lcopilot/importer-dashboard/draft-lc" aria-label="Draft LC">
                <FileText className="mr-2 h-5 w-5" />
                Review Draft LC
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link to="/lcopilot/importer-dashboard/supplier-docs" aria-label="Supplier Docs">
                <ShieldCheck className="mr-2 h-5 w-5" />
                Review Supplier Docs
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Last 10 reviews</CardDescription>
            </div>
            <Link to="/lcopilot/importer-dashboard/reviews" className="text-sm text-primary hover:underline">
              View all →
            </Link>
          </CardHeader>
          <CardContent>
            <ReviewsTable sessions={rows} />
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
```

- [ ] **Step 4: Delete ImporterAnalytics**

Run:
```
git rm apps/web/src/pages/ImporterAnalytics.tsx
```

Update `App.tsx` to remove the `/lcopilot/importer-analytics` route, or replace with a redirect (Task 6).

- [ ] **Step 5: Run tests**

Run: `cd apps/web && npm run type-check && npm run test -- ImporterDashboardV2.skeleton`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Rewrite ImporterDashboardV2 to shared skeleton + delete ImporterAnalytics"
```

---

## Task 5: Update `ExporterDashboard` with View-all link + stats strip

**Files:**
- Modify: `apps/web/src/pages/ExporterDashboard.tsx`

- [ ] **Step 1: Read current file**

Run: `wc -l apps/web/src/pages/ExporterDashboard.tsx`
Expected: current size.

- [ ] **Step 2: Locate recent validations section**

Run: `grep -n "Recent\|recentValidations\|validations.map" apps/web/src/pages/ExporterDashboard.tsx | head -10`

- [ ] **Step 3: Add View all link next to Recent Activity card**

Edit `apps/web/src/pages/ExporterDashboard.tsx`. In the CardHeader of the recent-validations Card, add:

```tsx
<CardHeader className="flex flex-row items-center justify-between">
  <div>
    <CardTitle>Recent Activity</CardTitle>
    <CardDescription>Last 10 validations</CardDescription>
  </div>
  <Link to="/lcopilot/exporter-dashboard?section=reviews" className="text-sm text-primary hover:underline">
    View all →
  </Link>
</CardHeader>
```

If a `<CardHeader>` already exists, augment with the flex row + Link. If no CardHeader, wrap the existing recent section in one.

- [ ] **Step 4: Confirm the dashboard uses `useQuery(['user-sessions'])`**

If still on imperative `useEffect(async () => { const data = await getUserSessions(); })`, refactor to:

```typescript
const { data: sessions = [] } = useQuery({
  queryKey: ["user-sessions"],
  queryFn: getUserSessions,
  staleTime: 5_000,
});
```

- [ ] **Step 5: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add View all link + ensure useQuery on exporter dashboard"
```

---

## Task 6: Route redirects for removed sections

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Locate the removed routes**

Run: `grep -n "importer-analytics\|section=workspace\|section=templates\|section=ai-assistance" apps/web/src -r --include="*.tsx" | head -10`

- [ ] **Step 2: Add redirect routes**

In `apps/web/src/App.tsx`, replace the old routes with `<Navigate>`:

```tsx
// Importer-side redirects
<Route path="/lcopilot/importer-analytics" element={<Navigate to="/lcopilot/importer-dashboard" replace />} />

// Legacy section params → dashboard (catch-all)
<Route
  path="/lcopilot/importer-dashboard"
  element={<LegacySectionRedirector />}
/>
```

Create a small redirector component:

```tsx
// Inside App.tsx or a small helper file:
import { useSearchParams, Navigate } from "react-router-dom";
import ImporterDashboardV2 from "./pages/ImporterDashboardV2";

const DROPPED_SECTIONS = new Set([
  "workspace", "templates", "analytics", "notifications",
  "billing-usage", "ai-assistance", "content-library", "shipment-timeline",
]);

function LegacySectionRedirector() {
  const [params] = useSearchParams();
  const section = params.get("section");
  if (section && DROPPED_SECTIONS.has(section)) {
    const newParams = new URLSearchParams(params);
    newParams.delete("section");
    // billing-usage → billing (merged)
    if (section === "billing-usage") newParams.set("section", "billing");
    return <Navigate to={`/lcopilot/importer-dashboard${newParams.toString() ? `?${newParams}` : ""}`} replace />;
  }
  return <ImporterDashboardV2 />;
}
```

Wire `<LegacySectionRedirector />` as the element of the existing `/lcopilot/importer-dashboard` route (replacing the direct `<ImporterDashboardV2 />`).

- [ ] **Step 3: Write a smoke test**

Create `apps/web/tests/e2e/lcopilot/legacy-redirects.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Legacy importer deep-link redirects", () => {
  test("/lcopilot/importer-analytics redirects to dashboard", async ({ page }) => {
    await page.goto("/lcopilot/importer-analytics");
    await page.waitForURL(/importer-dashboard/, { timeout: 5000 });
    expect(page.url()).toContain("/lcopilot/importer-dashboard");
  });

  test("?section=workspace redirects to plain dashboard", async ({ page }) => {
    await page.goto("/lcopilot/importer-dashboard?section=workspace");
    await page.waitForURL((url) => !url.search.includes("workspace"), { timeout: 5000 });
    expect(page.url()).not.toContain("workspace");
  });

  test("?section=billing-usage rewrites to ?section=billing", async ({ page }) => {
    await page.goto("/lcopilot/importer-dashboard?section=billing-usage");
    await page.waitForURL(/section=billing(?!-usage)/, { timeout: 5000 });
    expect(page.url()).toContain("section=billing");
    expect(page.url()).not.toContain("billing-usage");
  });
});
```

- [ ] **Step 4: Run**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/legacy-redirects.spec.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add -A
git commit -m "Add 301 redirects for dropped importer sections + ImporterAnalytics"
```

---

## Task 7: THE 5-second dashboard-update smoke test

**Files:**
- Create: `apps/web/tests/e2e/lcopilot/dashboard-updates-on-new-session.spec.ts`

This is the proof the user explicitly asked for: not "the code calls getUserSessions", but "a new validation appears on the dashboard within 5 seconds without manual reload". Both portals.

- [ ] **Step 1: Write the smoke spec**

Create `apps/web/tests/e2e/lcopilot/dashboard-updates-on-new-session.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Dashboard updates within 5s of a new validation (both portals)", () => {
  test("importer: new draft-lc session appears on dashboard within 5s", async ({ page }) => {
    await page.goto("/login");
    // ...auth (reuse existing helpers)...

    // Note the current count of rows on Recent Activity
    await page.goto("/lcopilot/importer-dashboard");
    const initialCount = await page.locator('[data-testid="recent-activity-row"]').count();

    // Start a new validation
    await page.goto("/lcopilot/importer-dashboard/draft-lc");
    const lcPath = path.resolve("tests/fixtures/ideal-sample/LC.pdf");
    await page.setInputFiles('input[type="file"]', lcPath);
    await page.getByRole("button", { name: /analyze lc risks/i }).click();

    // Wait for intake-only response (fast — < 30s)
    await expect(page.getByText(/review|extract/i).first()).toBeVisible({ timeout: 60000 });

    // Navigate back to dashboard
    await page.goto("/lcopilot/importer-dashboard");

    // Within 5 seconds (no manual reload), the new row should appear
    await expect(async () => {
      const newCount = await page.locator('[data-testid="recent-activity-row"]').count();
      expect(newCount).toBeGreaterThan(initialCount);
    }).toPass({ timeout: 5_000, intervals: [500, 500, 500, 500, 500] });
  });

  test("exporter: new validation session appears on dashboard within 5s", async ({ page }) => {
    await page.goto("/login");
    // ...auth...

    await page.goto("/lcopilot/exporter-dashboard");
    const initialCount = await page.locator('[data-testid="recent-activity-row"]').count();

    await page.goto("/lcopilot/exporter-dashboard?section=upload");
    const lcPath = path.resolve("tests/fixtures/ideal-sample/LC.pdf");
    await page.setInputFiles('input[type="file"]', lcPath);
    await page.getByRole("button", { name: /upload|start|validate/i }).click();

    await expect(page.getByText(/review|extract/i).first()).toBeVisible({ timeout: 60000 });

    await page.goto("/lcopilot/exporter-dashboard");
    await expect(async () => {
      const newCount = await page.locator('[data-testid="recent-activity-row"]').count();
      expect(newCount).toBeGreaterThan(initialCount);
    }).toPass({ timeout: 5_000, intervals: [500, 500, 500, 500, 500] });
  });
});
```

- [ ] **Step 2: Add `data-testid="recent-activity-row"` to the ReviewsTable rows**

Edit `apps/web/src/components/lcopilot/ReviewsTable.tsx`, add the test id:

```tsx
<li key={s.id} data-testid="recent-activity-row" className="flex items-center gap-3 py-2">
```

- [ ] **Step 3: Run the smoke (with dev server)**

Run:
```
cd apps/web && npm run dev &
npx playwright test tests/e2e/lcopilot/dashboard-updates-on-new-session.spec.ts
```
Expected: both pass.

If they fail, do NOT commit. This is the exact "nothing updates" complaint the user raised. Investigate:
- Is the query key actually `['user-sessions']` in all 3 places (useValidate, useResumeValidate, and both dashboards)?
- Is the session persisted on the backend by the time we return? Check via `psql` query.
- Is there a tenancy filter bug making the new session invisible to the logged-in user?

Fix the root cause before proceeding. Without a passing smoke here, Phase 4 is not done.

- [ ] **Step 4: Commit (only if smoke passes)**

```
git add -A
git commit -m "Add 5-second dashboard-update smoke test (both portals)"
```

---

## Task 8: Phase 4 final verification

**Files:**
- Verify: all

- [ ] **Step 1: Full test sweep (frontend)**

Run: `cd apps/web && npm run type-check && npm run lint && npm run test`
Expected: all PASS.

- [ ] **Step 2: Full Playwright sweep**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/`
Expected: ALL green — including the 5-second smoke from Task 7.

- [ ] **Step 3: Manual verification checklist**

With dev server running, log in as both roles and check:

**Exporter portal:**
- [ ] Sidebar has exactly: Dashboard · Upload · Billing · Settings
- [ ] "Validations" item is gone
- [ ] Dashboard has stats strip, Start New CTA, Recent Activity with "View all →" link
- [ ] Running a new validation and returning to dashboard shows new row within 5 seconds

**Importer portal:**
- [ ] Sidebar has exactly: Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings
- [ ] Dashboard has stats strip, two Start New CTAs, Recent Activity with "View all →" link + type badges
- [ ] Old URLs like `?section=workspace` redirect cleanly
- [ ] `/lcopilot/importer-analytics` redirects to dashboard
- [ ] Running a new draft-LC validation and returning to dashboard shows new row within 5 seconds

- [ ] **Step 4: Check log for unexpected console errors**

In browser devtools console during manual smoke, confirm no React errors / 404s / 500s in the update cycle.

- [ ] **Step 5: No commit — verification only**

---

## Phase 4 Exit Criteria

- [ ] Exporter sidebar = 4 items: Dashboard · Upload · Billing · Settings
- [ ] Importer sidebar = 5 items: Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings
- [ ] Both dashboards render the shared skeleton: stats · start-new · recent-10 · view-all · quota
- [ ] `ImporterAnalytics` deleted
- [ ] Legacy routes redirect cleanly (analytics, workspace, templates, etc.)
- [ ] React Query invalidation wired into `useValidate` + `useResumeValidate`
- [ ] **The 5-second dashboard-update smoke PASSES on both portals** — this is the real exit gate
- [ ] No regression in exporter golden path

---

## Project completion (after Phase 4)

Once this phase exits, the importer is at full parity with exporter on plumbing. The combined deliverables from Phases 1-4:

- `apps/web/src/components/lcopilot/` is the canonical home for LC-validation UI primitives
- Importer has two first-class workflows (Moment 1 + Moment 2) on the same modern spine as exporter
- Backend has `workflow_type` on `ValidationSession` with a 3-value enum
- 4 importer-specific action endpoints implemented with real side effects
- Both sidebars slim and symmetric
- Both dashboards wire-tested, not just code-tested

Flip `VITE_LCOPILOT_IMPORTER_V2=true` in production env to release. Watch analytics + error rates for the first 48 hours; if clean, remove the flag in a follow-up PR.
