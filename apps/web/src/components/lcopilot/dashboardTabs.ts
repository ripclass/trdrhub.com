export type ResultsTab =
  | "overview"
  | "documents"
  | "discrepancies"
  | "extracted-data"
  | "history"
  | "analytics"
  | "customs";

export type DashboardTabDefinition = {
  id: ResultsTab;
  label: string;
  description: string;
  requiresJob?: boolean;
};

export const DASHBOARD_TABS: DashboardTabDefinition[] = [
  { id: "overview", label: "Overview", description: "Processing summary & LC header" },
  { id: "documents", label: "Documents", description: "Document status & extraction health", requiresJob: true },
  { id: "discrepancies", label: "Issues", description: "Deterministic + AI issue review", requiresJob: true },
  { id: "extracted-data", label: "Extracted Data", description: "Structured MT700 + document fields", requiresJob: true },
  { id: "history", label: "Submission History", description: "Bank submission timeline", requiresJob: true },
  { id: "analytics", label: "Analytics", description: "Compliance, customs, readiness", requiresJob: true },
  { id: "customs", label: "Customs Pack", description: "Manifest & customs-ready files", requiresJob: true },
];

export const DEFAULT_TAB: ResultsTab = "overview";

export const isResultsTab = (value: string | null | undefined): value is ResultsTab => {
  if (!value) return false;
  return DASHBOARD_TABS.some((tab) => tab.id === value);
};

