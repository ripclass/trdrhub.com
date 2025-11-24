import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import DashboardNav from "@/components/lcopilot/DashboardNav";
import LcHeader from "@/components/lcopilot/LcHeader";
import RiskPanel from "@/components/lcopilot/RiskPanel";
import SummaryStrip from "@/components/lcopilot/SummaryStrip";
import { useResultsContext, ResultsProvider } from "@/context/ResultsContext";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExporterSidebar } from "@/components/exporter/ExporterSidebar";
import { useAuth } from "@/hooks/use-auth";

const normalizeDiscrepancySeverity = (
  severity?: string | null
): "critical" | "major" | "minor" => {
  const value = (severity ?? "").toLowerCase();
  if (["critical", "fail", "error", "high"].includes(value)) {
    return "critical";
  }
  if (["warning", "warn", "major", "medium"].includes(value)) {
    return "major";
  }
  return "minor";
};

const SECTION_PARAM = "section";
const JOB_PARAM = "jobId";

const sections = ["overview", "upload", "reviews", "documents", "issues", "analytics", "customs"] as const;
type Section = (typeof sections)[number];

const parseSection = (value: string | null): Section => {
  if (!value) return "overview";
  const normalized = value.toLowerCase();
  return sections.includes(normalized as Section) ? (normalized as Section) : "overview";
};

const DEFAULT_SECTION: Section = "overview";
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

const sectionToSidebarMap: Record<Section, SidebarSection> = {
  overview: "dashboard",
  upload: "upload",
  reviews: "reviews",
  documents: "workspace",
  issues: "notifications",
  analytics: "analytics",
  customs: "analytics",
};

const sidebarToSectionMap: Partial<Record<SidebarSection, Section>> = {
  dashboard: "overview",
  upload: "upload",
  reviews: "reviews",
  workspace: "documents",
  analytics: "analytics",
  notifications: "issues",
};

const sidebarSectionLabels: Record<SidebarSection, string> = {
  dashboard: "Dashboard",
  workspace: "Workspace",
  templates: "Templates",
  upload: "Upload Documents",
  reviews: "Review Results",
  analytics: "Analytics",
  notifications: "Notifications",
  billing: "Billing",
  "billing-usage": "Billing Usage",
  "ai-assistance": "AI Assistance",
  "content-library": "Content Library",
  "shipment-timeline": "Shipment Timeline",
  settings: "Settings",
  help: "Help & Support",
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
  const section = parseSection(searchParams.get(SECTION_PARAM));
  const urlJobId = searchParams.get(JOB_PARAM);
  const { jobId, setJobId } = useResultsContext();
  const { user: currentUser } = useAuth();
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
    setSection("reviews", payload.jobId);
  };

  const handleSidebarSectionChange = (next: SidebarSection) => {
    setSidebarSection(next);
    const mappedSection = sidebarToSectionMap[next];
    if (mappedSection) {
      setSection(mappedSection);
    }
  };

  const renderSection = (currentSection: Section): JSX.Element => {
    switch (currentSection) {
      case "overview":
        return <OverviewSection onNavigateUpload={() => setSection("upload")} />;
      case "upload":
        return <UploadSection onComplete={handleUploadComplete} />;
      case "reviews":
        return <ReviewsSection />;
      case "documents":
        return <DocumentsSection />;
      case "issues":
        return <IssuesSection />;
      case "analytics":
        return <AnalyticsSection />;
      case "customs":
        return <CustomsSection />;
      default:
        return <OverviewSection onNavigateUpload={() => setSection("upload")} />;
    }
  };

  const resolvedSection =
    sidebarSection === "analytics" && section === "customs"
      ? "customs"
      : sidebarToSectionMap[sidebarSection];

  const content =
    resolvedSection !== undefined ? (
      renderSection(resolvedSection)
    ) : (
      <FeaturePlaceholder
        label={sidebarSectionLabels[sidebarSection]}
        onNavigateUpload={() => setSection("upload")}
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
        {resolvedSection && <DashboardNav />}
        <div className="space-y-8">{content}</div>
      </div>
    </DashboardLayout>
  );
}

const OverviewSection = ({ onNavigateUpload }: { onNavigateUpload: () => void }) => {
  const { results } = useResultsContext();
  if (!results) {
    return (
      <Card className="border-dashed border-2">
        <CardContent className="py-10 text-center space-y-3">
          <CardTitle>No validation results yet</CardTitle>
          <p className="text-sm text-muted-foreground">
            Upload an LC package to see structured LC data, customs risk, and discrepancy insights.
          </p>
          <Button onClick={onNavigateUpload}>Start a Validation</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <LcHeader data={results} />
      <div className="grid gap-6 lg:grid-cols-2">
        <RiskPanel data={results} />
        <SummaryStrip data={results} />
      </div>
    </div>
  );
};

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

const ReviewsSection = () => {
  const { jobId } = useResultsContext();
  const [searchParams] = useSearchParams();
  const fallbackJobId = searchParams.get(JOB_PARAM);
  const activeJobId = jobId ?? fallbackJobId;

  if (!activeJobId) {
    return (
      <Card className="border border-dashed">
        <CardContent className="py-8 text-center space-y-3">
          <CardTitle>No review selected</CardTitle>
          <p className="text-sm text-muted-foreground">Upload a package or open a recent review to continue.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border/60">
      <CardContent className="p-0">
        <ExporterResults embedded jobId={activeJobId} />
      </CardContent>
    </Card>
  );
};

const DocumentsSection = () => {
  const { results } = useResultsContext();
  const docs =
    results?.structured_result?.documents_structured ??
    results?.structured_result?.lc_structured?.documents_structured ??
    [];

  if (!results) {
    return <ResultsRequiredCard />;
  }

  if (!docs.length) {
    return (
      <Card className="border border-dashed">
        <CardContent className="py-8 text-center text-sm text-muted-foreground">No documents available.</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents ({docs.length})</CardTitle>
        <CardDescription>Structured documents detected in this LC package</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3">
          {docs.map((doc, idx) => (
            <div
              key={doc.document_id ?? idx}
              className="flex flex-col gap-1 rounded-lg border border-border/60 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p className="font-semibold text-foreground">{doc.filename ?? `Document ${idx + 1}`}</p>
                <p className="text-sm text-muted-foreground">{doc.document_type ?? "supporting_document"}</p>
              </div>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>Status: {doc.extraction_status ?? "unknown"}</span>
                <span>
                  Fields: {doc.extracted_fields ? Object.keys(doc.extracted_fields).length : 0}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const IssuesSection = () => {
  const { results } = useResultsContext();
  if (!results) {
    return <ResultsRequiredCard />;
  }

  const issues = results.issues ?? [];

  const documents =
    results?.structured_result?.documents_structured ??
    results?.structured_result?.lc_structured?.documents_structured ??
    [];

  const documentStatusMap = useMemo(() => {
    const map = new Map<string, { status?: string; type?: string }>();
    documents.forEach((doc) => {
      if (doc.filename) {
        map.set(doc.filename, {
          status: doc.extraction_status ?? undefined,
          type: doc.document_type,
        });
      }
    });
    return map;
  }, [documents]);

  if (!issues.length) {
    return (
      <Card className="border border-success/40 bg-success/5 text-success">
        <CardContent className="py-8 text-center space-y-3">
          <CardTitle>All documents comply with LC terms.</CardTitle>
          <p className="text-sm text-success/80">No discrepancies detected across the submitted document set.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {issues.map((issue, index) => {
        const normalizedSeverity = normalizeDiscrepancySeverity(issue.severity);
        const fallbackId = issue.id ?? `issue-${index}`;
        return (
          <ExporterIssueCard
            key={fallbackId}
            issue={issue}
            normalizedSeverity={normalizedSeverity}
            documentStatusMap={documentStatusMap}
            fallbackId={fallbackId}
          />
        );
      })}
    </div>
  );
};

const AnalyticsSection = () => {
  const { results } = useResultsContext();
  const structured = results?.structured_result;
  const summary = structured?.processing_summary;
  const analytics = structured?.analytics;
  const documents =
    structured?.documents_structured ?? structured?.lc_structured?.documents_structured ?? [];
  const issues = structured?.issues ?? results?.issues ?? [];

  if (!structured || !summary) {
    return <ResultsRequiredCard />;
  }

  // Derive document status from summary fields
  const successful = summary.successful_extractions ?? 0;
  const failed = summary.failed_extractions ?? 0;
  const total = summary.total_documents ?? documents.length;
  const warning = Math.max(0, total - successful - failed);

  const complianceScore = analytics?.compliance_score ?? null;
  const customsRiskScore = (analytics as any)?.customs_risk?.score ?? null;
  const severityBreakdown = summary.severity_breakdown ?? {};

  const metrics = [
    {
      label: "Documents Processed",
      value: total,
      helper: `${successful} success / ${warning} warning / ${failed} error`,
    },
    {
      label: "Compliance Score",
      value: typeof complianceScore === "number" ? `${complianceScore}%` : "N/A",
      helper: "From structured_result.analytics.compliance_score",
    },
    {
      label: "Customs Risk",
      value: typeof customsRiskScore === "number" ? `${customsRiskScore}%` : "N/A",
      helper: "Customs risk score from analytics.customs_risk",
    },
    {
      label: "Severity Breakdown",
      value: `${severityBreakdown.critical ?? 0} critical / ${severityBreakdown.major ?? 0} major / ${severityBreakdown.minor ?? 0} minor`,
      helper: "Issue severity distribution",
    },
    {
      label: "Total Issues",
      value: summary.total_issues ?? issues.length,
      helper: `${issues.length} issues from structured_result.issues`,
    },
    {
      label: "Extraction Success Rate",
      value: total > 0 ? `${Math.round((successful / total) * 100)}%` : "N/A",
      helper: `${successful} of ${total} documents extracted successfully`,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analytics</CardTitle>
        <CardDescription>Option-E processing summary and readiness signals</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-lg border border-border/60 p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{metric.label}</p>
            <p className="text-xl font-semibold text-foreground mt-1">{metric.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{metric.helper}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

const CustomsSection = () => {
  const { results } = useResultsContext();
  if (!results) {
    return <ResultsRequiredCard />;
  }

  const customsPack = results.structured_result?.customs_pack;

  if (!customsPack) {
    return (
      <Card className="border border-dashed">
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Customs pack details will appear once validation completes.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Customs Pack</CardTitle>
        <CardDescription>Files included in the generated customs pack</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 text-sm">
          <Badge variant={customsPack.ready ? "default" : "outline"}>{customsPack.ready ? "Ready" : "Pending"}</Badge>
          <span className="text-muted-foreground">{customsPack.format}</span>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Manifest ({customsPack.manifest?.length ?? 0})</p>
          <ul className="text-sm text-muted-foreground space-y-1">
            {(customsPack.manifest ?? []).map((entry, idx) => (
              <li key={`${entry.name ?? "doc"}-${idx}`}>
                {entry.name ?? `Document ${idx + 1}`} - {entry.tag ?? "supporting_document"}
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};

const ResultsRequiredCard = () => (
  <Card className="border border-dashed">
    <CardContent className="py-8 text-center text-sm text-muted-foreground">
      Upload a package and run validation to unlock this view.
    </CardContent>
  </Card>
);

const FeaturePlaceholder = ({ label, onNavigateUpload }: { label: string; onNavigateUpload: () => void }) => (
  <Card className="border border-dashed">
    <CardHeader>
      <CardTitle>{label} workspace coming soon</CardTitle>
      <CardDescription>
        This area will return after the structured_result rollout completes. Use the LC workspace to keep validating documents.
      </CardDescription>
    </CardHeader>
    <CardContent className="space-y-4 text-sm text-muted-foreground">
      <p>
        The sidebar still keeps your navigation handy - switch back to the Overview, Upload, or Reviews tabs to continue working with Option-E data.
      </p>
      <Button variant="outline" onClick={onNavigateUpload}>
        Open LC workspace
      </Button>
    </CardContent>
  </Card>
);

