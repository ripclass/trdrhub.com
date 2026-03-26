/**
 * Issues/Discrepancies Tab Component
 * Banker-grade issue review surface with bucketed findings
 */

import { ReactNode, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ShieldAlert, ShieldCheck, FileWarning } from "lucide-react";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
import { ReviewFindingCard, type ReviewFindingCardData } from "@/components/exporter/ReviewFindingCard";
import { type EmailDraftContext } from "@/components/exporter/HowToFixSection";
import { normalizeDiscrepancySeverity } from "../utils";
import type { IssueCard } from "@/types/lcopilot";

interface SeverityCounts {
  critical: number;
  major: number;
  minor: number;
}

interface LaneCounts {
  documentary: number;
  compliance: number;
  manual: number;
}

interface IssuesTabProps {
  hasIssueCards: boolean;
  issueCards: IssueCard[];
  filteredIssueCards: IssueCard[];
  reviewFindings: ReviewFindingCardData[];
  severityCounts: SeverityCounts;
  laneCounts: LaneCounts;
  issueFilter: "all" | "critical" | "major" | "minor";
  setIssueFilter: (filter: "all" | "critical" | "major" | "minor") => void;
  documentStatusMap: Map<string, { status?: string; type?: string }>;
  renderAIInsightsCard: () => ReactNode;
  renderReferenceIssuesCard: () => ReactNode;
  lcNumber?: string;
  companyName?: string;
  onDraftEmail?: (context: EmailDraftContext) => void;
  workflowStage?: {
    stage?: string;
    summary?: string;
    unresolved_documents?: number;
    unresolved_fields?: number;
  } | null;
}

const BUCKETS = [
  "Missing Required Documents",
  "LC Required Statements",
  "Document-Level Discrepancies",
  "Cross-Document Conditions",
  "Extraction / Manual Review",
] as const;

const renderReviewFindingCards = (reviewFindings: ReviewFindingCardData[]) => (
  <section className="space-y-3">
    <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
      Review Findings
    </h3>
    <div className="space-y-4">
      {reviewFindings.map((finding) => (
        <ReviewFindingCard key={finding.key} finding={finding} />
      ))}
    </div>
  </section>
);

export function IssuesTab({
  hasIssueCards,
  issueCards,
  filteredIssueCards,
  reviewFindings,
  severityCounts,
  issueFilter,
  setIssueFilter,
  documentStatusMap,
  renderAIInsightsCard,
  renderReferenceIssuesCard,
  lcNumber,
  companyName,
  onDraftEmail,
  workflowStage,
}: IssuesTabProps) {
  const grouped = useMemo(() => {
    const documentary = new Map<string, IssueCard[]>();
    BUCKETS.forEach((b) => documentary.set(b, []));
    const complianceRisk: IssueCard[] = [];

    filteredIssueCards.forEach((card) => {
      const bucket = (card as any).bucket || "Document-Level Discrepancies";
      if (bucket === "Compliance / Risk Review") {
        complianceRisk.push(card);
        return;
      }
      if (!documentary.has(bucket)) documentary.set(bucket, []);
      documentary.get(bucket)!.push(card);
    });

    return { documentary, complianceRisk };
  }, [filteredIssueCards]);
  const totalComplianceAlerts = useMemo(
    () => issueCards.filter((card) => ((card as any).bucket || "Document-Level Discrepancies") === "Compliance / Risk Review").length,
    [issueCards],
  );
  const totalDiscrepancyFindings = useMemo(() => Math.max(issueCards.length - totalComplianceAlerts, 0), [issueCards, totalComplianceAlerts]);

  const reviewFindingCounts = useMemo<SeverityCounts>(
    () =>
      reviewFindings.reduce(
        (acc, finding) => {
          if (finding.severity === "critical") acc.critical += 1;
          else acc.major += 1;
          return acc;
        },
        { critical: 0, major: 0, minor: 0 },
      ),
    [reviewFindings],
  );
  const overallValidationNote = useMemo(() => {
    if (workflowStage?.stage === "extraction_resolution") {
      return {
        tone: "warning" as const,
        title: "Provisional Validation Note",
        summary:
          workflowStage.summary ||
          "Validation is still provisional because extracted fields remain unresolved.",
        nextStep:
          "Confirm the unresolved fields from source evidence first. Any discrepancy or compliance findings shown below should be treated as provisional until extraction resolution is complete.",
        Icon: AlertTriangle,
      };
    }

    if (issueCards.length === 0 && reviewFindings.length === 0) {
      return {
        tone: "success" as const,
        title: "Overall Validation Note",
        summary: "No documentary discrepancies, review findings, or compliance alerts are open for this run.",
        nextStep: "The submitted document set appears in order for the checks performed in this validation run.",
        Icon: ShieldCheck,
      };
    }

    if (issueCards.length === 0 && reviewFindings.length > 0) {
      return {
        tone: "warning" as const,
        title: "Overall Validation Note",
        summary: "No formal discrepancy cards were generated, but unresolved review findings still need operator attention before this set should be treated as clean.",
        nextStep: "Work through the review findings below and confirm whether each item is a source-document gap, extraction uncertainty, or policy review step.",
        Icon: AlertTriangle,
      };
    }

    if (totalComplianceAlerts > 0 && totalDiscrepancyFindings === 0) {
      return {
        tone: "warning" as const,
        title: "Overall Validation Note",
        summary: "Compliance alerts were generated for this run and need internal review before the case should be treated as submission-ready.",
        nextStep: reviewFindings.length > 0
          ? "Resolve the review findings below and route the compliance alerts for disposition."
          : "Route the compliance alerts below and document the disposition before proceeding.",
        Icon: ShieldAlert,
      };
    }

    return {
      tone: "warning" as const,
      title: "Overall Validation Note",
      summary: reviewFindings.length > 0
        ? "Documentary discrepancies and review findings are both open for this run."
        : "Documentary discrepancies were generated in this run and should be resolved before submission.",
      nextStep: reviewFindings.length > 0
        ? "Resolve the discrepancy findings below first, then clear the remaining review findings before treating the case as clean."
        : "Resolve the discrepancy findings below before treating the case as ready for submission.",
      Icon: FileWarning,
    };
  }, [issueCards.length, reviewFindings.length, totalComplianceAlerts, totalDiscrepancyFindings, workflowStage]);
  const noteToneClass =
    overallValidationNote.tone === "success"
      ? "border-success/40 bg-success/5 text-success"
      : "border-warning/40 bg-warning/5";
  const isExtractionResolutionStage = workflowStage?.stage === "extraction_resolution";

  return (
    <>
      <Card className={`shadow-soft ${noteToneClass}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <overallValidationNote.Icon className={overallValidationNote.tone === "success" ? "w-5 h-5 text-success" : "w-5 h-5 text-warning"} />
            {overallValidationNote.title}
          </CardTitle>
          <p className="text-sm text-muted-foreground">{overallValidationNote.summary}</p>
          <p className="text-sm text-muted-foreground">{overallValidationNote.nextStep}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="p-3 rounded-lg bg-destructive/5 border border-destructive/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Discrepancy findings</p>
              <p className="text-2xl font-bold text-destructive">{totalDiscrepancyFindings}</p>
            </div>
            <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Review findings</p>
              <p className="text-2xl font-bold text-warning">{reviewFindings.length}</p>
            </div>
            <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Compliance alerts</p>
              <p className="text-2xl font-bold text-sky-700">{totalComplianceAlerts}</p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Total findings</p>
              <p className="text-2xl font-bold text-foreground">{issueCards.length + reviewFindings.length}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {issueCards.length > 0 && (
        <Card className="shadow-soft border border-border/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {isExtractionResolutionStage ? "Provisional Finding Filter" : "Discrepancy Filter"}
            </CardTitle>
            <CardDescription>
              {isExtractionResolutionStage
                ? "Filter provisional documentary findings by severity while extraction resolution is still open."
                : "Filter formal discrepancy cards by severity. Review findings stay visible separately because they are not discrepancy cards."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {[
                { value: "all" as const, label: `All (${issueCards.length})` },
                { value: "critical" as const, label: `High-likelihood (${severityCounts.critical})` },
                { value: "major" as const, label: `Likely (${severityCounts.major})` },
                { value: "minor" as const, label: `Review required (${severityCounts.minor})` },
              ].map((option) => (
                <Button
                  key={option.value}
                  size="sm"
                  variant={issueFilter === option.value ? "default" : "outline"}
                  onClick={() => setIssueFilter(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {Array.from(grouped.documentary.values()).some((cards) => cards.length > 0) && (
          <section className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                {isExtractionResolutionStage ? "Provisional Findings" : "Discrepancy Findings"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {isExtractionResolutionStage
                  ? "Candidate documentary findings generated before extraction resolution is complete. These will be re-evaluated after unresolved fields are confirmed."
                  : "Formal documentary findings backed by rule or discrepancy-card logic."}
              </p>
            </div>
            {Array.from(grouped.documentary.entries()).map(([bucket, cards]) => {
              if (!cards.length) return null;
              return (
                <section key={bucket} className="space-y-3">
                  <h4 className="text-sm font-semibold text-foreground">{bucket}</h4>
                  {cards.map((card, index) => {
                    const normalizedSeverity = normalizeDiscrepancySeverity(card.severity);
                    const fallbackId = card.id || `${card.rule ?? "rule"}-${card.title ?? index}`;
                    return (
                      <ExporterIssueCard
                        key={fallbackId}
                        issue={card}
                        normalizedSeverity={normalizedSeverity}
                        documentStatusMap={documentStatusMap}
                        fallbackId={fallbackId}
                        lcNumber={lcNumber}
                        companyName={companyName}
                        onDraftEmail={onDraftEmail}
                      />
                    );
                  })}
                </section>
              );
            })}
          </section>
        )}

        {reviewFindings.length > 0 && renderReviewFindingCards(reviewFindings)}

        {grouped.complianceRisk.length > 0 && (
          <section className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">Compliance Alerts</h3>
              <p className="text-sm text-muted-foreground">
                {isExtractionResolutionStage
                  ? "Compliance or internal risk findings that remain provisional until extraction resolution is complete."
                  : "Findings that should be routed through compliance or internal risk review rather than treated as ordinary documentary discrepancies."}
              </p>
            </div>
            {grouped.complianceRisk.map((card, index) => {
              const normalizedSeverity = normalizeDiscrepancySeverity(card.severity);
              const fallbackId = card.id || `${card.rule ?? "rule"}-${card.title ?? index}`;
              return (
                <ExporterIssueCard
                  key={fallbackId}
                  issue={card}
                  normalizedSeverity={normalizedSeverity}
                  documentStatusMap={documentStatusMap}
                  fallbackId={fallbackId}
                  lcNumber={lcNumber}
                  companyName={companyName}
                  onDraftEmail={onDraftEmail}
                />
              );
            })}
          </section>
        )}

        {filteredIssueCards.length === 0 && issueCards.length > 0 && (
          <Card className="shadow-soft border border-dashed">
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              No discrepancy cards match this severity filter.
            </CardContent>
          </Card>
        )}
      </div>
      {renderAIInsightsCard()}
      {renderReferenceIssuesCard()}
    </>
  );
}
