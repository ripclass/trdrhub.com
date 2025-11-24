import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import { ResultsProvider, useResultsContext } from "@/context/ResultsContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import DashboardNav from "@/components/lcopilot/DashboardNav";
import { useAuth } from "@/hooks/use-auth";
import { DEFAULT_TAB, isResultsTab, type ResultsTab } from "@/components/lcopilot/dashboardTabs";

type Section = ResultsTab | "upload";

const SECTION_PARAM = "section";
const TAB_PARAM = "tab";
const JOB_PARAM = "jobId";

type SidebarSection =
  | "dashboard"
  | "workspace"
  | "templates"
  | "upload"
  | "reviews"
  | "analytics"
  | "notifications"
  | "billing"
  | "billing-usage"
  | "ai-assistance"
  | "content-library"
  | "shipment-timeline"
  | "settings"
  | "help";

const parseSection = (value: string | null): Section => {
  if (!value) return DEFAULT_TAB;
  const normalized = value.toLowerCase();
  if (normalized === "issues") return "discrepancies";
  if (normalized === "upload") return "upload";
  if (isResultsTab(normalized)) return normalized;
  return DEFAULT_TAB;
};

const sectionToSidebarMap: Record<Section, SidebarSection> = {
  overview: "dashboard",
  documents: "workspace",
  discrepancies: "notifications",
  "extracted-data": "workspace",
  history: "reviews",
  analytics: "analytics",
  customs: "analytics",
  upload: "upload",
};

const sidebarToSectionMap: Partial<Record<SidebarSection, Section>> = {
  dashboard: "overview",
  workspace: "documents",
  reviews: "history",
  analytics: "analytics",
  notifications: "discrepancies",
  upload: "upload",
};

export default function ExporterDashboard() {
  return (
    <ResultsProvider>
      <DashboardContent />
    </ResultsProvider>
  );
}

function DashboardContent() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { jobId, setJobId } = useResultsContext();
  const { user: currentUser } = useAuth();
  const sectionParam = searchParams.get(SECTION_PARAM) ?? searchParams.get(TAB_PARAM);
  const section = parseSection(sectionParam);
  const urlJobId = searchParams.get(JOB_PARAM);
  const activeTab: ResultsTab = section === "upload" ? DEFAULT_TAB : (section as ResultsTab);
  const [sidebarSection, setSidebarSection] = useState<SidebarSection>(
    sectionToSidebarMap[section] ?? "dashboard",
  );
  const previousSectionRef = useRef<Section>(section);

  useEffect(() => {
    if (urlJobId && urlJobId !== jobId) {
      setJobId(urlJobId);
    }
  }, [urlJobId, jobId, setJobId]);

  useEffect(() => {
    if (previousSectionRef.current !== section) {
      previousSectionRef.current = section;
      setSidebarSection(sectionToSidebarMap[section] ?? "dashboard");
    }
  }, [section]);

  const setSection = (next: Section, jobOverride?: string | null) => {
    const params = new URLSearchParams(searchParams);
    params.set(SECTION_PARAM, next);
    if (next !== "upload") {
      params.set(TAB_PARAM, next);
    } else {
      params.delete(TAB_PARAM);
    }
    const targetJob = jobOverride ?? jobId ?? urlJobId ?? "";
    if (targetJob) {
      params.set(JOB_PARAM, targetJob);
    } else {
      params.delete(JOB_PARAM);
    }
    setSearchParams(params, { replace: true });
    setSidebarSection(sectionToSidebarMap[next] ?? "dashboard");
  };

  const handleUploadComplete = (payload: { jobId: string; lcNumber: string }) => {
    setJobId(payload.jobId);
    setSection("overview", payload.jobId);
  };

  const handleSidebarSectionChange = (next: SidebarSection) => {
    setSidebarSection(next);
    const mapped = sidebarToSectionMap[next];
    if (mapped) {
      setSection(mapped);
    }
  };

  const content =
    section === "upload" ? (
      <UploadSection onComplete={handleUploadComplete} />
    ) : (
      <ExporterResults
        embedded
        jobId={jobId ?? urlJobId ?? undefined}
        initialTab={activeTab}
        onTabChange={(tab) => setSection(tab)}
      />
    );

  return (
    <DashboardLayout
      title="Exporter Dashboard"
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Exporter Dashboard" },
      ]}
      sidebar={
        <ExporterSidebar
          activeSection={sidebarSection}
          onSectionChange={handleSidebarSectionChange}
          user={currentUser ?? undefined}
        />
      }
    >
      <div className="space-y-6 px-6 pb-12">
        <DashboardNav
          activeTab={activeTab}
          onTabChange={(tab) => setSection(tab)}
          jobId={jobId ?? urlJobId}
        />
        <div className="space-y-8">{content}</div>
      </div>
    </DashboardLayout>
  );
}

const UploadSection = ({ onComplete }: { onComplete: (payload: { jobId: string; lcNumber: string }) => void }) => (
  <Card>
    <CardHeader>
      <CardTitle>Upload LC Documents</CardTitle>
      <CardDescription>Run extraction, rule checks, and customs readiness against your LC package.</CardDescription>
    </CardHeader>
    <CardContent>
      <ExportLCUpload embedded onComplete={onComplete} />
    </CardContent>
  </Card>
);
