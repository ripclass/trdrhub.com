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
  { id: "overview", label: "Verdict", description: "Pass/fail verdict and action items" },
  { id: "documents", label: "Documents", description: "Per-document compliance with field detail", requiresJob: true },
  { id: "discrepancies", label: "Findings", description: "Discrepancy cards in bank examiner voice", requiresJob: true },
  { id: "customs", label: "Customs Pack", description: "Compliance checklist & PDF download", requiresJob: true },
];

export const DEFAULT_TAB: ResultsTab = "overview";

export const isResultsTab = (value: string | null | undefined): value is ResultsTab => {
  if (!value) return false;
  return DASHBOARD_TABS.some((tab) => tab.id === value);
};
