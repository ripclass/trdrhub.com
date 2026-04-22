/**
 * Importer results page — thin wrapper around the shared lcopilot tab shell.
 *
 * Phase 2/7 rewrite. The legacy ~2000-line version carried mock-data
 * structures (mockDraftLCResults / mockSupplierResults), local per-shape
 * transforms (transformApiToSupplierFormat / transformApiToDraftFormat),
 * and stubbed action dialogs (submit-to-bank / send-to-supplier / fix-pack)
 * that duplicated exporter plumbing. All of that is gone.
 *
 * What remains:
 *   - useCanonicalJobResult for the real API path (tests assert this)
 *   - buildValidationResponse from the shared lib/lcopilot/resultsMapper
 *   - The shared 4-tab shell (Verdict · Documents · Findings · Issues)
 *   - A moment-aware action slot that stays empty in Phase 2 and gets
 *     filled by <DraftLcActions /> or <SupplierDocActions /> in Phase 3
 *
 * Workflow resolution order (first match wins):
 *   1. structured_result.workflow_type or top-level workflow_type on the
 *      canonical response (set by the backend starting Phase 2/2)
 *   2. the `mode` prop passed by an embedder / the ?mode= query param
 *   3. "importer_supplier_docs" as a last-resort fallback
 */

import { useMemo } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useCanonicalJobResult } from "@/hooks/use-lcopilot";
import { buildValidationResponse } from "@/lib/lcopilot/resultsMapper";
import {
  VerdictTab,
  DocumentsTab,
  FindingsTab,
  IssuesTab,
} from "@/components/lcopilot/results/tabs";
import SummaryStrip from "@/components/lcopilot/SummaryStrip";
import { DraftLcActions } from "./importer/actions/DraftLcActions";
import { SupplierDocActions } from "./importer/actions/SupplierDocActions";

// ---------------------------------------------------------------------------
// Props + types
// ---------------------------------------------------------------------------

export type ImporterMode = "draft" | "supplier";

type ImportResultsProps = {
  embedded?: boolean;
  jobId?: string;
  lcNumber?: string;
  mode?: ImporterMode;
};

const MODE_TO_WORKFLOW: Record<ImporterMode, string> = {
  draft: "importer_draft_lc",
  supplier: "importer_supplier_docs",
};

const WORKFLOW_TITLES: Record<string, string> = {
  importer_draft_lc: "Draft LC Risk Analysis — Results",
  importer_supplier_docs: "Supplier Document Review — Results",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImportResults({
  embedded = false,
  jobId: jobIdOverride,
  lcNumber: lcNumberOverride,
  mode: modeOverride,
}: ImportResultsProps = {}) {
  const params = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const mode = (modeOverride ??
    (searchParams.get("mode") as ImporterMode | null) ??
    "supplier") as ImporterMode;

  const rawJobId =
    jobIdOverride ?? params.jobId ?? searchParams.get("jobId") ?? undefined;
  const jobId = rawJobId ?? `demo-${mode}`;
  const lcNumber = lcNumberOverride ?? searchParams.get("lc") ?? "";

  const isDemoJob = jobId.startsWith("demo-");
  const shouldUseAPI = !isDemoJob && !!rawJobId;

  // Keep the canonical hook wired unconditionally so React's hook order
  // stays stable across the loading→ready transition. The two passing
  // ImportResults tests assert exactly this.
  const {
    jobStatus,
    isPolling,
    results,
    isLoading: isLoadingResults,
    resultsError,
    refreshResults,
  } = useCanonicalJobResult(shouldUseAPI ? jobId : null);

  const mapped = useMemo(() => {
    if (!results) return null;
    try {
      return buildValidationResponse(results as any);
    } catch (err) {
      console.warn("[ImportResults] buildValidationResponse failed", err);
      return null;
    }
  }, [results]);

  // Workflow resolution: prefer what the backend said, fall back to the
  // component-level `mode` prop.
  const workflowType = useMemo(() => {
    const fromResults =
      (results as any)?.workflow_type ??
      (results as any)?.structured_result?.workflow_type ??
      (results as any)?.structured_result?.meta?.workflow_type;
    if (typeof fromResults === "string" && fromResults.length > 0) {
      return fromResults;
    }
    return MODE_TO_WORKFLOW[mode];
  }, [results, mode]);

  const pageTitle =
    WORKFLOW_TITLES[workflowType] ?? WORKFLOW_TITLES.importer_supplier_docs;

  const isLoadingRealData =
    shouldUseAPI && !results && (isPolling || isLoadingResults || !jobStatus);

  const jobFailed =
    jobStatus?.status === "failed" || jobStatus?.status === "error";

  // Moment-aware action palette. The action endpoints are all live after
  // Phase 3/1–3/4; these components wrap the use-importer-actions hooks.
  const actionSlot =
    workflowType === "importer_draft_lc" && rawJobId ? (
      <DraftLcActions sessionId={rawJobId} lcNumber={lcNumber || undefined} />
    ) : workflowType === "importer_supplier_docs" && rawJobId ? (
      <SupplierDocActions
        sessionId={rawJobId}
        lcNumber={lcNumber || undefined}
      />
    ) : undefined;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const content = (
    <>
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{pageTitle}</h1>
          {lcNumber && (
            <p className="text-sm text-muted-foreground">LC {lcNumber}</p>
          )}
        </div>
        {!embedded && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/lcopilot/importer-dashboard")}
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
        )}
      </header>

      {isLoadingRealData && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            Validation in progress — this typically takes 30–90 seconds.
          </CardContent>
        </Card>
      )}

      {jobFailed && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive font-medium">
              Validation failed. {resultsError ?? "Please try again."}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => refreshResults?.()}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {mapped && (
        <>
          <SummaryStrip results={mapped as any} />

          <Tabs defaultValue="verdict" className="space-y-4">
            <TabsList>
              <TabsTrigger value="verdict">Verdict</TabsTrigger>
              <TabsTrigger value="documents">Documents</TabsTrigger>
              <TabsTrigger value="findings">Findings</TabsTrigger>
              <TabsTrigger value="issues">Issues</TabsTrigger>
            </TabsList>

            <TabsContent value="verdict">
              <VerdictTab
                issueCards={(mapped as any).issueCards ?? []}
                documents={(mapped as any).documents ?? []}
                totalDocuments={(mapped as any).documents?.length ?? 0}
                complianceScore={
                  (mapped as any).structured_result?.analytics
                    ?.compliance_score ?? 0
                }
                lcNumber={lcNumber || (mapped as any).lcNumber || ""}
                actionSlot={actionSlot}
              />
            </TabsContent>

            <TabsContent value="documents">
              <DocumentsTab
                documents={(mapped as any).documents ?? []}
                results={mapped as any}
              />
            </TabsContent>

            <TabsContent value="findings">
              <FindingsTab
                issueCards={(mapped as any).issueCards ?? []}
                documents={(mapped as any).documents ?? []}
              />
            </TabsContent>

            <TabsContent value="issues">
              <IssuesTab
                issueCards={(mapped as any).issueCards ?? []}
                onFilterChange={() => {
                  // Placeholder — Phase 3 wires filter state.
                }}
              />
            </TabsContent>
          </Tabs>
        </>
      )}
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <div className="container mx-auto p-6 space-y-6">{content}</div>
  );
}
