/**
 * Issues/Discrepancies Tab Component
 * Shows validation issues with filtering and AI insights
 */

import { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldCheck } from "lucide-react";
import { ExporterIssueCard } from "@/components/exporter/ExporterIssueCard";
import { type EmailDraftContext } from "@/components/exporter/HowToFixSection";
import { normalizeDiscrepancySeverity } from "../utils";
import type { IssueCard } from "@/types/lcopilot";

interface SeverityCounts {
  critical: number;
  major: number;
  minor: number;
}

interface IssuesTabProps {
  hasIssueCards: boolean;
  issueCards: IssueCard[];
  filteredIssueCards: IssueCard[];
  severityCounts: SeverityCounts;
  issueFilter: "all" | "critical" | "major" | "minor";
  setIssueFilter: (filter: "all" | "critical" | "major" | "minor") => void;
  documentStatusMap: Map<string, { status?: string; type?: string }>;
  renderAIInsightsCard: () => ReactNode;
  renderReferenceIssuesCard: () => ReactNode;
  lcNumber?: string;
  companyName?: string;
  onDraftEmail?: (context: EmailDraftContext) => void;
}

export function IssuesTab({
  hasIssueCards,
  issueCards,
  filteredIssueCards,
  severityCounts,
  issueFilter,
  setIssueFilter,
  documentStatusMap,
  renderAIInsightsCard,
  renderReferenceIssuesCard,
  lcNumber,
  companyName,
  onDraftEmail,
}: IssuesTabProps) {
  if (!hasIssueCards) {
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

  return (
    <>
      <Card className="shadow-soft border border-border/60">
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="p-3 rounded-lg bg-destructive/5 border border-destructive/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Critical</p>
              <p className="text-2xl font-bold text-destructive">{severityCounts.critical}</p>
            </div>
            <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Major</p>
              <p className="text-2xl font-bold text-warning">{severityCounts.major}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30 border border-muted">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Minor</p>
              <p className="text-2xl font-bold text-foreground">{severityCounts.minor}</p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-secondary/60">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Total Issues</p>
              <p className="text-2xl font-bold text-foreground">{issueCards.length}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { value: "all" as const, label: `All (${issueCards.length})` },
              { value: "critical" as const, label: `Critical (${severityCounts.critical})` },
              { value: "major" as const, label: `Major (${severityCounts.major})` },
              { value: "minor" as const, label: `Minor (${severityCounts.minor})` },
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
        filteredIssueCards.map((card, index) => {
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
        })
      )}
      {renderAIInsightsCard()}
      {renderReferenceIssuesCard()}
    </>
  );
}
