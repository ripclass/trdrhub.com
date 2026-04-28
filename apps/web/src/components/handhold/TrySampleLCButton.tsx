/**
 * TrySampleLCButton — Phase A3 part 5.
 *
 * Pairs with /api/handhold/sample-lc. Click → POST → navigate to the
 * results page for the new validation_session_id. The session shows
 * "validation in progress" and lights up once the BackgroundTask
 * pipeline run completes (existing results-page polling handles the
 * transition).
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";
import { api } from "@/api/client";

interface SampleLCResponse {
  job_id: string;
  validation_session_id: string;
  status: string;
  message: string;
}

interface Props {
  /** "outline" matches the existing empty-state CTA; "default" makes
   *  the button the primary action on a fresh dashboard. */
  variant?: "default" | "outline" | "ghost";
  className?: string;
}

export function TrySampleLCButton({
  variant = "default",
  className,
}: Props) {
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const { data } = await api.post<SampleLCResponse>(
        "/api/handhold/sample-lc",
      );
      if (data?.validation_session_id) {
        navigate(`/exporter/results/${data.validation_session_id}`);
      } else {
        setError("Sample run started but no session id returned.");
      }
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : (detail as { message?: string } | undefined)?.message
            ?? (err as Error).message
            ?? "Failed to start sample validation";
      setError(message);
    } finally {
      setPending(false);
    }
  };

  return (
    <div className={className}>
      <Button
        variant={variant}
        onClick={handleClick}
        disabled={pending}
      >
        <Sparkles className="w-4 h-4 mr-2" />
        {pending ? "Preparing sample…" : "Try a sample LC"}
      </Button>
      {error && (
        <p className="mt-2 text-xs text-rose-600">{error}</p>
      )}
    </div>
  );
}
