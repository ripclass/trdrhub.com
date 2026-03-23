import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type ReviewFindingCardData = {
  key: string;
  title: string;
  detail: string;
  severity: "critical" | "major";
  category: string;
  currentState?: string;
  expectedState?: string;
  whyItMatters: string;
  evidence: string;
  recommendedAction: string;
  sourceBasis: string;
  documentName?: string;
  documentType?: string;
  requirementText?: string;
};

const reviewFindingTone = (category: string) => {
  const normalized = category.toLowerCase();
  if (normalized.includes("missing required")) {
    return "border-destructive/30 bg-destructive/5 text-destructive";
  }
  if (normalized.includes("source-document")) {
    return "border-amber-500/30 bg-amber-500/5 text-amber-700";
  }
  if (normalized.includes("extraction")) {
    return "border-sky-500/30 bg-sky-500/5 text-sky-700";
  }
  if (normalized.includes("manual")) {
    return "border-violet-500/30 bg-violet-500/5 text-violet-700";
  }
  return "border-warning/30 bg-warning/10 text-warning";
};

type ReviewFindingCardProps = {
  finding: ReviewFindingCardData;
  variant?: "full" | "compact";
  className?: string;
};

export function ReviewFindingCard({
  finding,
  variant = "full",
  className,
}: ReviewFindingCardProps) {
  const compact = variant === "compact";
  const actionLabel =
    finding.category.toLowerCase().includes("extraction") || finding.category.toLowerCase().includes("manual")
      ? "Review guidance"
      : "How to fix";

  return (
    <Card className={cn("shadow-sm border border-border/70 bg-card", compact && "shadow-none", className)}>
      <CardHeader className={cn("space-y-2 pb-3", compact && "pb-2")}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <CardTitle className={cn("text-base", compact && "text-sm")}>{finding.title}</CardTitle>
            <div className="flex flex-wrap gap-2">
              <span
                className={cn(
                  "inline-flex rounded-full border px-2.5 py-1 text-xs font-medium",
                  reviewFindingTone(finding.category),
                )}
              >
                {finding.category}
              </span>
              <span
                className={
                  finding.severity === "critical"
                    ? "inline-flex rounded-full border border-destructive/30 bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive"
                    : "inline-flex rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-xs font-medium text-warning"
                }
              >
                {finding.severity === "critical" ? "Blocking review" : "Review required"}
              </span>
              {finding.documentName ? (
                <Badge variant="outline" className="text-xs">
                  {finding.documentType ? `${finding.documentType}: ` : ""}
                  {finding.documentName}
                </Badge>
              ) : null}
            </div>
          </div>
        </div>
        <CardDescription className="text-sm text-muted-foreground">{finding.detail}</CardDescription>
      </CardHeader>
      <CardContent className={cn("space-y-4", compact && "space-y-3")}>
        {compact ? (
          <div className="space-y-2 text-sm">
            {finding.expectedState ? (
              <div className="rounded-md border p-3">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Expected state</p>
                <p className="mt-1">{finding.expectedState}</p>
              </div>
            ) : null}
            <div className="rounded-md border p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Why it matters</p>
              <p className="mt-1">{finding.whyItMatters}</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Evidence / basis</p>
              <p className="mt-1">{finding.evidence}</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{actionLabel}</p>
              <p className="mt-1">{finding.recommendedAction}</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Current state</p>
              <p className="text-sm mt-1">{finding.currentState || finding.detail}</p>
            </div>
            {finding.expectedState ? (
              <div className="rounded-md border p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Expected state</p>
                <p className="text-sm mt-1">{finding.expectedState}</p>
              </div>
            ) : null}
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Why it matters</p>
              <p className="text-sm mt-1">{finding.whyItMatters}</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Evidence / basis</p>
              <p className="text-sm mt-1">{finding.evidence}</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{actionLabel}</p>
              <p className="text-sm mt-1">{finding.recommendedAction}</p>
            </div>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">
            Source basis: {finding.sourceBasis}
          </Badge>
          {finding.requirementText ? (
            <Badge variant="outline" className="text-xs">
              LC requirement
            </Badge>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
