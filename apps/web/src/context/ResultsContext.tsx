import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ValidationResults } from "@/types/lcopilot";
import { useResults as useResultsHook, type ValidationError } from "@/hooks/use-lcopilot";

type ResultsContextValue = {
  jobId: string | null;
  setJobId: (jobId: string | null) => void;
  results: ValidationResults | null;
  isLoading: boolean;
  error: ValidationError | null;
  refresh: (jobId?: string) => Promise<ValidationResults | null>;
};

const ResultsContext = createContext<ResultsContextValue | undefined>(undefined);

export function ResultsProvider({ children }: { children: React.ReactNode }) {
  const { results, getResults, isLoading, error } = useResultsHook();
  const [jobId, setJobId] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }
    getResults(jobId).catch(() => {
      /* handled within hook */
    });
  }, [jobId, getResults]);

  const refresh = useCallback(
    async (targetId?: string) => {
      const nextId = targetId ?? jobId;
      if (!nextId) {
        return null;
      }
      return getResults(nextId);
    },
    [jobId, getResults],
  );

  const value = useMemo<ResultsContextValue>(
    () => ({
      jobId,
      setJobId,
      results,
      isLoading,
      error,
      refresh,
    }),
    [jobId, results, isLoading, error, refresh],
  );

  return <ResultsContext.Provider value={value}>{children}</ResultsContext.Provider>;
}

export function useResultsContext() {
  const context = useContext(ResultsContext);
  if (!context) {
    throw new Error("useResultsContext must be used within a ResultsProvider");
  }
  return context;
}

