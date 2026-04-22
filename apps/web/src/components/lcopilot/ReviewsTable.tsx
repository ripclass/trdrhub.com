import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";

export type ReviewsTableWorkflowType =
  | "exporter_presentation"
  | "importer_draft_lc"
  | "importer_supplier_docs";

export interface ReviewsTableSession {
  id: string;
  lcNumber: string;
  createdAt: string;
  verdict: "pass" | "review" | "reject" | "pending" | string;
  workflowType: ReviewsTableWorkflowType | string;
  resultsHref?: string;
}

export interface ReviewsTableProps {
  sessions: ReviewsTableSession[];
  emptyMessage?: string;
}

const TYPE_LABEL: Record<ReviewsTableWorkflowType, string> = {
  exporter_presentation: "PRESENTATION",
  importer_draft_lc: "DRAFT LC",
  importer_supplier_docs: "SHIPMENT",
};

function typeLabel(workflowType: string): string {
  return (TYPE_LABEL as Record<string, string>)[workflowType] ?? workflowType;
}

export function ReviewsTable({ sessions, emptyMessage = "No recent activity" }: ReviewsTableProps) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">{emptyMessage}</p>;
  }
  return (
    <ul className="divide-y">
      {sessions.map((s) => (
        <li
          key={s.id}
          data-testid="recent-activity-row"
          className="flex items-center gap-3 py-2"
        >
          <Badge variant="outline">{typeLabel(s.workflowType)}</Badge>
          <span className="font-medium">{s.lcNumber}</span>
          <span className="ml-auto text-xs text-muted-foreground">
            {new Date(s.createdAt).toLocaleDateString()}
          </span>
          {s.resultsHref && (
            <Link to={s.resultsHref} className="text-sm text-primary hover:underline">
              View →
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}
