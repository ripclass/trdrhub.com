/**
 * DiscrepancyActions — workflow buttons for a single finding card.
 *
 * Renders Accept / Reject / Waive / Re-paper. Behind
 * isDiscrepancyWorkflowEnabled() in FindingsTab, so legacy users see
 * read-only cards. The discrepancyId must be the persisted UUID that
 * the backend's finding_persistence helper stamps onto each finding;
 * see apps/api/app/services/finding_persistence.py.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, ShieldOff, Mail } from "lucide-react";
import {
  isPersistedDiscrepancyId,
  resolveDiscrepancy,
  type DiscrepancyResolveAction,
} from "@/lib/lcopilot/discrepancyApi";
import { RepaperModal } from "./RepaperModal";

interface DiscrepancyActionsProps {
  discrepancyId: string | null | undefined;
  /** Optional callback after a successful resolve action so the parent
   * can refresh state (e.g., dim the card or re-fetch). */
  onResolved?: (action: DiscrepancyResolveAction) => void;
  /** Optional callback after a re-paper request was created. */
  onRepaperCreated?: (recipientLink: string) => void;
}

const RESOLVE_BUTTONS: Array<{
  action: DiscrepancyResolveAction;
  label: string;
  Icon: typeof CheckCircle2;
  className: string;
}> = [
  {
    action: "accept",
    label: "Accept",
    Icon: CheckCircle2,
    className: "text-emerald-600 hover:bg-emerald-50",
  },
  {
    action: "reject",
    label: "Reject",
    Icon: XCircle,
    className: "text-rose-600 hover:bg-rose-50",
  },
  {
    action: "waive",
    label: "Waive",
    Icon: ShieldOff,
    className: "text-amber-600 hover:bg-amber-50",
  },
];

export function DiscrepancyActions({
  discrepancyId,
  onResolved,
  onRepaperCreated,
}: DiscrepancyActionsProps) {
  const [pending, setPending] = useState<DiscrepancyResolveAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolved, setResolved] = useState<DiscrepancyResolveAction | null>(
    null,
  );
  const [repaperOpen, setRepaperOpen] = useState(false);

  if (!isPersistedDiscrepancyId(discrepancyId)) {
    // Pre-persistence finding (legacy or stub path) — actions would 422
    // because the backend can't UUID-parse a rule name. Hide the row
    // entirely rather than render dead buttons.
    return null;
  }

  const id = discrepancyId as string;

  const handleResolve = async (action: DiscrepancyResolveAction) => {
    if (pending) return;
    setPending(action);
    setError(null);
    try {
      await resolveDiscrepancy(id, action);
      setResolved(action);
      onResolved?.(action);
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data
          ?.detail;
      setError(
        typeof message === "string"
          ? message
          : (err as Error).message ?? "Action failed",
      );
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="border-t border-neutral-200 pt-3 mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {RESOLVE_BUTTONS.map(({ action, label, Icon, className }) => (
          <Button
            key={action}
            size="sm"
            variant="outline"
            disabled={pending !== null || resolved !== null}
            onClick={() => handleResolve(action)}
            className={`text-xs h-7 ${className}`}
          >
            <Icon className="w-3.5 h-3.5 mr-1" />
            {pending === action ? `${label}…` : label}
          </Button>
        ))}
        <Button
          size="sm"
          variant="outline"
          disabled={pending !== null || resolved !== null}
          onClick={() => setRepaperOpen(true)}
          className="text-xs h-7 text-blue-600 hover:bg-blue-50"
        >
          <Mail className="w-3.5 h-3.5 mr-1" />
          Re-paper
        </Button>
      </div>

      {resolved && (
        <p className="text-xs text-emerald-700">
          Marked <strong>{resolved}</strong>. Reload to see updated state.
        </p>
      )}
      {error && (
        <p className="text-xs text-rose-600">{error}</p>
      )}

      <RepaperModal
        open={repaperOpen}
        onOpenChange={setRepaperOpen}
        discrepancyId={id}
        onCreated={onRepaperCreated}
      />
    </div>
  );
}
