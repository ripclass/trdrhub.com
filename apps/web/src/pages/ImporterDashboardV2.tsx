/**
 * Importer dashboard — Phase 4/4 rewrite.
 *
 * Replaces the 953-line section-based shell (14 sidebar items, embedded
 * workflow components, AI assistance cards, shipment timelines, etc.) with
 * the shared skeleton the plan defines:
 *
 *   Stats strip · Start New (2 CTAs) · Recent Activity (ReviewsTable)
 *
 * The sidebar now has only 5 items (see Phase 4/2). Dashboard / Billing /
 * Settings render inline; Draft LC Review and Supplier Doc Review navigate
 * to their own routes (wired in Phase 2/6).
 */

import { useCallback, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { WorkspaceSwitcher } from "@/components/lcopilot/WorkspaceSwitcher";
import { EnterpriseGroupLink } from "@/components/lcopilot/EnterpriseGroupLink";
import {
  ImporterSidebar,
  type ImporterSidebarSection,
} from "@/components/importer/ImporterSidebar";
import {
  ReviewsTable,
  type ReviewsTableSession,
} from "@/components/lcopilot/ReviewsTable";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
import { BillingOverviewPage } from "./BillingOverviewPage";

// ---------------------------------------------------------------------------
// Data helpers
// ---------------------------------------------------------------------------

function sessionsToRows(sessions: ValidationSession[]): ReviewsTableSession[] {
  return sessions.slice(0, 10).map((s: any) => {
    const id = s.id ?? s.session_id ?? "";
    return {
      id: String(id),
      lcNumber:
        s.lc_number ??
        s.lcNumber ??
        (typeof id === "string" ? id.slice(0, 8) : ""),
      createdAt: s.created_at ?? s.createdAt ?? new Date().toISOString(),
      verdict: s.verdict ?? s.status ?? "pending",
      workflowType: s.workflow_type ?? "exporter_presentation",
      resultsHref: id ? `/lcopilot/results-v2/${id}` : undefined,
    };
  });
}

function countThisMonth(sessions: ValidationSession[]): number {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth();
  return sessions.filter((s: any) => {
    const raw = s.created_at ?? s.createdAt;
    if (!raw) return false;
    const d = new Date(raw);
    return d.getUTCFullYear() === year && d.getUTCMonth() === month;
  }).length;
}

function countByStatus(
  sessions: ValidationSession[],
  matcher: (status: string) => boolean,
): number {
  return sessions.filter((s: any) =>
    matcher(String(s.status ?? "").toLowerCase()),
  ).length;
}

// ---------------------------------------------------------------------------
// Sidebar section sync with URL
// ---------------------------------------------------------------------------

const LEGACY_SECTION_MAP: Record<string, ImporterSidebarSection | null> = {
  workspace: "dashboard",
  templates: "dashboard",
  upload: "dashboard",
  reviews: "dashboard",
  analytics: "dashboard",
  notifications: "dashboard",
  "ai-assistance": "dashboard",
  "content-library": "dashboard",
  "shipment-timeline": "dashboard",
  "billing-usage": "billing",
  help: "dashboard",
};

function parseSidebarSection(
  rawSection: string | null | undefined,
): ImporterSidebarSection {
  if (!rawSection) return "dashboard";
  const v = rawSection.toLowerCase();
  if (
    v === "dashboard" ||
    v === "draft-lc" ||
    v === "supplier-docs" ||
    v === "billing" ||
    v === "settings"
  ) {
    return v;
  }
  return LEGACY_SECTION_MAP[v] ?? "dashboard";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImporterDashboardV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const activeSection = useMemo(
    () => parseSidebarSection(searchParams.get("section")),
    [searchParams],
  );

  const handleSectionChange = useCallback(
    (next: ImporterSidebarSection) => {
      // The two moment routes are separate pages, not dashboard sections.
      if (next === "draft-lc") {
        navigate("/lcopilot/importer-dashboard/draft-lc");
        return;
      }
      if (next === "supplier-docs") {
        navigate("/lcopilot/importer-dashboard/supplier-docs");
        return;
      }
      const params = new URLSearchParams(searchParams);
      if (next === "dashboard") {
        params.delete("section");
      } else {
        params.set("section", next);
      }
      setSearchParams(params, { replace: true });
    },
    [navigate, searchParams, setSearchParams],
  );

  const { data: sessions = [] } = useQuery({
    queryKey: ["user-sessions"],
    queryFn: getUserSessions,
    staleTime: 5_000,
  });

  const rows = useMemo(() => sessionsToRows(sessions), [sessions]);
  const thisMonth = useMemo(() => countThisMonth(sessions), [sessions]);
  const completed = useMemo(
    () => countByStatus(sessions, (s) => s === "completed"),
    [sessions],
  );
  const attention = useMemo(
    () =>
      countByStatus(sessions, (s) =>
        ["failed", "error", "review", "reject"].includes(s),
      ),
    [sessions],
  );

  // -------------------------------------------------------------------------
  // Section body
  // -------------------------------------------------------------------------

  const body = (() => {
    if (activeSection === "billing") {
      return <BillingOverviewPage />;
    }
    if (activeSection === "settings") {
      return (
        <Card>
          <CardHeader>
            <CardTitle>Settings</CardTitle>
            <CardDescription>
              Account, team, and retention preferences live in the dedicated
              settings pages. This inline surface is a placeholder for
              importer-scoped switches added later.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            No importer-specific settings yet.
          </CardContent>
        </Card>
      );
    }

    // Default: Dashboard skeleton
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-bold">Importer Dashboard</h1>
          <p className="text-muted-foreground">
            Draft-LC risk analysis and supplier-document review.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardDescription>Reviews this month</CardDescription>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <CardTitle className="text-3xl">{thisMonth}</CardTitle>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardDescription>Completed</CardDescription>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <CardTitle className="text-3xl">{completed}</CardTitle>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardDescription>Attention needed</CardDescription>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <CardTitle className="text-3xl">{attention}</CardTitle>
            </CardContent>
          </Card>
        </section>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Last 10 reviews.</CardDescription>
            </div>
            <Link
              to="/reviews"
              className="text-sm text-primary hover:underline"
            >
              View all →
            </Link>
          </CardHeader>
          <CardContent>
            <ReviewsTable sessions={rows} />
          </CardContent>
        </Card>
      </div>
    );
  })();

  return (
    <DashboardLayout
      sidebar={
        <ImporterSidebar
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
        />
      }
      workspaceSwitcher={<WorkspaceSwitcher />}
      headerExtras={<EnterpriseGroupLink />}
    >
      <div className="container mx-auto p-6">{body}</div>
    </DashboardLayout>
  );
}

// Keep the named re-export in case any caller imported the component by name.
export { ImporterDashboardV2 };
