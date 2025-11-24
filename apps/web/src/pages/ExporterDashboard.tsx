import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
import ExportLCUpload from "./ExportLCUpload";
import ExporterResults from "./ExporterResults";
import ExporterDashboardLayout from "@/components/lcopilot/ExporterDashboardLayout";
import LcHeader from "@/components/lcopilot/LcHeader";
import RiskPanel from "@/components/lcopilot/RiskPanel";
import SummaryStrip from "@/components/lcopilot/SummaryStrip";
import { useResultsContext, ResultsProvider } from "@/context/ResultsContext";

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

const sections = ["overview", "upload", "reviews", "documents", "issues", "customs"] as const;
type Section = (typeof sections)[number];

const DEFAULT_SECTION: Section = "overview";

export default function ExporterDashboard() {
  return (
    <ResultsProvider>
      <ExporterDashboardLayout>
        <DashboardContent />
      </ExporterDashboardLayout>
    </ResultsProvider>
  );
}

function DashboardContent() {
  const [searchParams, setSearchParams] = useSearchParams();
  const section = (searchParams.get(SECTION_PARAM) as Section) || DEFAULT_SECTION;
  const urlJobId = searchParams.get(JOB_PARAM);
  const { jobId, setJobId, results } = useResultsContext();

  useEffect(() => {
    if (urlJobId && urlJobId !== jobId) {
      setJobId(urlJobId);
    }
  }, [urlJobId, jobId, setJobId]);

  const handleUploadComplete = (payload: { jobId: string; lcNumber: string }) => {
    const params = new URLSearchParams(searchParams);
    params.set(SECTION_PARAM, "reviews");
    params.set(JOB_PARAM, payload.jobId);
    setSearchParams(params, { replace: true });
    setJobId(payload.jobId);
  };

  const setSection = (next: Section) => {
    const params = new URLSearchParams(searchParams);
    params.set(SECTION_PARAM, next);
    if (jobId || urlJobId) {
      params.set(JOB_PARAM, jobId ?? urlJobId ?? "");
    } else {
      params.delete(JOB_PARAM);
    }
    setSearchParams(params, { replace: true });
  };

  let content: JSX.Element;
  switch (section) {
    case "overview":
      content = <OverviewSection onNavigateUpload={() => setSection("upload")} />;
      break;
    case "upload":
      content = <UploadSection onComplete={handleUploadComplete} />;
      break;
    case "reviews":
      content = <ReviewsSection />;
      break;
    case "documents":
      content = <DocumentsSection />;
      break;
    case "issues":
      content = <IssuesSection />;
      break;
    case "customs":
      content = <CustomsSection />;
      break;
    default:
      content = <OverviewSection onNavigateUpload={() => setSection("upload")} />;
  }

  return (
    <div className="space-y-8">{content}</div>
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
                {entry.name ?? `Document ${idx + 1}`} · {entry.tag ?? "supporting_document"}
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

