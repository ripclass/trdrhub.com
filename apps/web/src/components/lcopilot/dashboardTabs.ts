export type ResultsTab =
  | "overview"
  | "documents"
  | "discrepancies"
  | "customs";

export type DashboardTabDefinition = {
  id: ResultsTab;
  label: string;
  description: string;
  requiresJob?: boolean;
};

export const DASHBOARD_TABS: DashboardTabDefinition[] = [
  { id: "overview", label: "Overview", description: "Processing summary, analytics & compliance" },
  { id: "documents", label: "Documents", description: "Document status & extracted data", requiresJob: true },
  { id: "discrepancies", label: "Issues", description: "Deterministic + AI issue review", requiresJob: true },
  { id: "customs", label: "Customs Pack", description: "Manifest, customs files & submission history", requiresJob: true },
];

export const DEFAULT_TAB: ResultsTab = "overview";

export const isResultsTab = (value: string | null | undefined): value is ResultsTab => {
  if (!value) return false;
  return DASHBOARD_TABS.some((tab) => tab.id === value);
};
