/**
 * RepaperingPanel — Phase A7 slice 1.
 *
 * Lists every re-papering request created against discrepancies on
 * sessions in the agent's company. Status badge, recipient, dates,
 * follow-up email + cancel actions. Resolved + cancelled items can
 * be hidden via the "Open only" toggle (default on).
 */

import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Ban,
  Copy,
  Mail,
  Mailbox,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  cancelAgencyRepaperRequest,
  listAgencyRepaperRequests,
  resendAgencyRepaperEmail,
  type AgencyRepaperingRequest,
} from "@/lib/lcopilot/agencyApi";

const STATE_PILL: Record<string, string> = {
  requested: "text-amber-700 bg-amber-100",
  in_progress: "text-blue-700 bg-blue-100",
  corrected: "text-violet-700 bg-violet-100",
  resolved: "text-emerald-700 bg-emerald-100",
  cancelled: "text-neutral-700 bg-neutral-200",
};

function StatePill({ state }: { state: string }) {
  const cls =
    STATE_PILL[state.toLowerCase()] ?? "text-muted-foreground bg-neutral-200/40";
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${cls}`}
    >
      {state}
    </span>
  );
}

function recipientLink(token: string | null): string | null {
  if (!token) return null;
  if (typeof window === "undefined") return `/repaper/${token}`;
  return `${window.location.origin}/repaper/${token}`;
}

export function RepaperingPanel() {
  const queryClient = useQueryClient();
  const [onlyOpen, setOnlyOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["agency", "repaper-requests", onlyOpen],
    queryFn: () => listAgencyRepaperRequests({ onlyOpen }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["agency", "repaper-requests"] });
  };

  const resendMutation = useMutation({
    mutationFn: resendAgencyRepaperEmail,
    onSuccess: (r) => {
      setInfo(
        r.sent
          ? `Reminder email sent to ${r.recipient}.`
          : `SMTP not configured — share the link manually with ${r.recipient}.`,
      );
      setError(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to resend"),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelAgencyRepaperRequest,
    onSuccess: () => {
      invalidate();
      setInfo("Request cancelled.");
      setError(null);
    },
    onError: (err: Error) => setError(err.message ?? "Failed to cancel"),
  });

  const handleCopy = useCallback(async (token: string | null) => {
    const link = recipientLink(token);
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setInfo("Link copied.");
      setError(null);
    } catch {
      setError("Couldn't copy. Manually copy the URL from the supplier link column.");
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Re-papering coordination</h2>
          <p className="text-sm text-muted-foreground">
            Track outstanding re-paper requests across all your suppliers and
            buyers. Send a reminder if a recipient hasn&rsquo;t responded.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Open only</span>
          <Switch checked={onlyOpen} onCheckedChange={setOnlyOpen} />
        </label>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}
      {info && !error && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {info}
        </div>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      ) : rows.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Mailbox className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">
              {onlyOpen
                ? "No open re-papering requests. Toggle off to see resolved + cancelled."
                : "No re-papering requests yet. Send one from the Findings tab on a results page."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted-foreground border-b">
                <tr>
                  <th className="px-4 py-3 font-medium">Supplier</th>
                  <th className="px-4 py-3 font-medium">Recipient</th>
                  <th className="px-4 py-3 font-medium">Discrepancy</th>
                  <th className="px-4 py-3 font-medium">State</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {rows.map((r: AgencyRepaperingRequest) => {
                  const terminal =
                    r.state === "resolved" || r.state === "cancelled";
                  return (
                    <tr key={r.id} className="border-t border-border">
                      <td className="px-4 py-3">
                        {r.supplier_name ?? (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm">
                          {r.recipient_display_name ?? r.recipient_email}
                        </div>
                        {r.recipient_display_name && (
                          <div className="text-xs text-muted-foreground">
                            {r.recipient_email}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground line-clamp-2 max-w-[40ch]">
                        {r.discrepancy_description ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <StatePill state={r.state} />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        {!terminal && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Copy recipient link"
                              onClick={() => handleCopy(r.access_token)}
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Resend reminder email"
                              disabled={resendMutation.isPending}
                              onClick={() => resendMutation.mutate(r.id)}
                            >
                              <Mail className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Cancel request"
                              disabled={cancelMutation.isPending}
                              onClick={() => {
                                if (
                                  confirm(
                                    `Cancel re-paper request to ${r.recipient_email}?`,
                                  )
                                ) {
                                  cancelMutation.mutate(r.id);
                                }
                              }}
                            >
                              <Ban className="w-3.5 h-3.5" />
                            </Button>
                          </>
                        )}
                        {r.replacement_session_id && (
                          <Button
                            asChild
                            size="sm"
                            variant="ghost"
                            title="Open replacement validation session"
                          >
                            <Link
                              to={`/exporter/results/${r.replacement_session_id}`}
                            >
                              Open
                            </Link>
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
