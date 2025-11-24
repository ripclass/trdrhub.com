import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useResultsContext } from "@/context/ResultsContext";

const SECTION_PARAM = "section";
const JOB_PARAM = "jobId";

const tabs = [
  { id: "overview", label: "Overview", requiresJob: false },
  { id: "upload", label: "Upload", requiresJob: false },
  { id: "reviews", label: "Reviews", requiresJob: true },
  { id: "documents", label: "Documents", requiresJob: true },
  { id: "issues", label: "Issues", requiresJob: true },
  { id: "analytics", label: "Analytics", requiresJob: true },
  { id: "customs", label: "Customs Pack", requiresJob: true },
] as const;

const parseSection = (value: string | null) => {
  if (!value) return "overview";
  const normalized = value.toLowerCase();
  return tabs.some((tab) => tab.id === normalized) ? normalized : "overview";
};

export default function DashboardNav() {
  const [searchParams, setSearchParams] = useSearchParams();
  const active = parseSection(searchParams.get(SECTION_PARAM));
  const urlJobId = searchParams.get(JOB_PARAM);
  const { jobId } = useResultsContext();

  const hasJob = useMemo(() => Boolean(jobId ?? urlJobId), [jobId, urlJobId]);

  const setSection = (next: string) => {
    const params = new URLSearchParams(searchParams);
    params.set(SECTION_PARAM, next);
    const persistedJob = jobId ?? urlJobId;
    if (persistedJob) {
      params.set(JOB_PARAM, persistedJob);
    } else {
      params.delete(JOB_PARAM);
    }
    setSearchParams(params, { replace: true });
  };

  return (
    <nav className="border-b bg-card">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap gap-2 px-6 py-3">
        {tabs.map((tab) => {
          const disabled = tab.requiresJob && !hasJob;
          const isActive = active === tab.id;
          return (
            <Button
              key={tab.id}
              variant={isActive ? "default" : "ghost"}
              size="sm"
              disabled={disabled}
              onClick={() => setSection(tab.id)}
            >
              {tab.label}
            </Button>
          );
        })}
      </div>
    </nav>
  );
}

