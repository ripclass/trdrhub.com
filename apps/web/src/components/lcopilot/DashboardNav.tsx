import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useResultsContext } from "@/context/ResultsContext";
import { DASHBOARD_TABS, DEFAULT_TAB, isResultsTab, type ResultsTab } from "./dashboardTabs";

type DashboardNavProps = {
  activeTab?: ResultsTab;
  onTabChange?: (tab: ResultsTab) => void;
  jobId?: string | null;
};

export default function DashboardNav({ activeTab, onTabChange, jobId: jobIdProp }: DashboardNavProps) {
  const { jobId: contextJobId } = useResultsContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlJobId = searchParams.get("jobId");
  const resolvedJobId = jobIdProp ?? contextJobId ?? urlJobId ?? null;
  const hasJob = useMemo(() => Boolean(resolvedJobId), [resolvedJobId]);

  const currentTab: ResultsTab = useMemo(() => {
    if (activeTab) return activeTab;
    const raw = searchParams.get("section") ?? searchParams.get("tab");
    if (isResultsTab(raw)) return raw;
    if (raw === "issues") return "discrepancies";
    return DEFAULT_TAB;
  }, [activeTab, searchParams]);

  const handleChange = (next: ResultsTab) => {
    const params = new URLSearchParams(searchParams);
    params.set("section", next);
    params.set("tab", next);
    if (resolvedJobId) {
      params.set("jobId", resolvedJobId);
    } else {
      params.delete("jobId");
    }
    setSearchParams(params, { replace: true });
    onTabChange?.(next);
  };

  return (
    <div className="flex flex-wrap gap-2">
      {DASHBOARD_TABS.map((tab) => {
        const disabled = tab.requiresJob && !hasJob;
        const isActive = currentTab === tab.id;
        return (
          <Button
            key={tab.id}
            variant={isActive ? "default" : "ghost"}
            size="sm"
            disabled={disabled}
            onClick={() => {
              if (disabled) return;
              handleChange(tab.id);
            }}
          >
            {tab.label}
          </Button>
        );
      })}
    </div>
  );
}

