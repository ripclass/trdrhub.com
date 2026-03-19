/**
 * Issues/Discrepancies Tab Component
 * Banker-grade issue review surface with bucketed findings
 */

import { ReactNode, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
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

interface ReviewFinding {
  key: string;
  title: string;
  detail: string;
  severity: "critical" | "major";
}

interface IssuesTabProps {
  hasIssueCards: boolean;
  issueCards: IssueCard[];
  filteredIssueCards: IssueCard[];
  reviewFindings: ReviewFinding[];
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
}

const BUCKETS = [
  "Missing Required Documents",
  "Document-Level Discrepancies",
  "Cross-Document Conditions",
  "Extraction / Manual Review",
] as const;

export function IssuesTab({
  hasIssueCards,
  issueCards,
  filteredIssueCards,
  reviewFindings,
  severityCounts,
  laneCounts,
  issueFilter,
  setIssueFilter,
  documentStatusMap,
  renderAIInsightsCard,
  renderReferenceIssuesCard,
  lcNumber,
  companyName,
  onDraftEmail,
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

  if (!hasIssueCards && reviewFindings.length === 0) {
    return (
      <>
        <Card className="border border-success/40 bg-success/5 text-success">
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <ShieldCheck className="w-8 h-8" />
            <div>
              <p className="text-lg font-semibold">All documents comply with LC terms.</p>
              <p className="text-sm text-success/80">
                No discrepancies detected across the submitted document set.
              </p>
            </div>
          </CardContent>
        </Card>
        {renderAIInsightsCard()}
        {renderReferenceIssuesCard()}
      </>
    );
  }

  if (!hasIssueCards && reviewFindings.length > 0) {
    return (
      <>
        <Card className="shadow-soft border border-warning/40 bg-warning/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base text-warning">
              <AlertTriangle className="w-5 h-5" />
              Review findings still need attention
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              No discrepancy cards were generated for this run, but unresolved checklist reviews still prevent the document set from being treated as fully compliant.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="p-3 rounded-lg bg-destructive/5 border border-destructive/20">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Blocking review items</p>
                <p className="text-2xl font-bold text-destructive">{reviewFindingCounts.critical}</p>
              </div>
              <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Review required</p>
                <p className="text-2xl font-bold text-warning">{reviewFindingCounts.major}</p>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Compliance alerts</p>
                <p className="text-2xl font-bold text-foreground">{laneCounts.compliance}</p>
              </div>
              <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Total review findings</p>
                <p className="text-2xl font-bold text-foreground">{reviewFindings.length}</p>
              </div>
            </div>

            <div className="space-y-3">
              {reviewFindings.map((finding) => (
                <div key={finding.key} className="rounded-lg border border-border/60 bg-card/50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{finding.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">{finding.detail}</p>
                    </div>
                    <span
                      className={
                        finding.severity === "critical"
                          ? "inline-flex rounded-full border border-destructive/30 bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive"
                          : "inline-flex rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-xs font-medium text-warning"
                      }
                    >
                      {finding.severity === "critical" ? "Blocking review" : "Review required"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        {renderAIInsightsCard()}
        {renderReferenceIssuesCard()}
      </>
    );
  }

  return (
    <>
      <Card className="shadow-soft border border-border/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Issue Review Summary</CardTitle>
          <p className="text-sm text-muted-foreground">
            Documentary findings are separated from compliance/risk alerts. Resolve documentary discrepancies before presentation and route compliance alerts to internal review instead of treating them as ordinary LC discrepancies.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-6">
            <div className="p-3 rounded-lg bg-destructive/5 border border-destructive/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">High-likelihood discrepancy</p>
              <p className="text-2xl font-bold text-destructive">{severityCounts.critical}</p>
            </div>
            <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Likely discrepancy</p>
              <p className="text-2xl font-bold text-warning">{severityCounts.major}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30 border border-muted">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Review required</p>
              <p className="text-2xl font-bold text-foreground">{severityCounts.minor}</p>
            </div>
            <div className="p-3 rounded-lg bg-sky-500/5 border border-sky-500/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Compliance alerts</p>
              <p className="text-2xl font-bold text-sky-700">{laneCounts.compliance}</p>
            </div>
            <div className="p-3 rounded-lg bg-violet-500/5 border border-violet-500/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Manual review items</p>
              <p className="text-2xl font-bold text-violet-700">{laneCounts.manual}</p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Total Issues</p>
              <p className="text-2xl font-bold text-foreground">{issueCards.length}</p>
            </div>
          </div>
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

      {filteredIssueCards.length === 0 ? (
        <Card className="shadow-soft border border-dashed">
          <CardContent className="py-6 text-center text-sm text-muted-foreground">
            No issues match this severity filter.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Array.from(grouped.documentary.entries()).map(([bucket, cards]) => {
            if (!cards.length) return null;
            return (
              <section key={bucket} className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">{bucket}</h3>
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

          {grouped.complianceRisk.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">Compliance / Risk Review</h3>
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
        </div>
      )}
      {renderAIInsightsCard()}
      {renderReferenceIssuesCard()}
    </>
  );
}
