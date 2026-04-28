/**
 * QuotaStrip — Phase A4.
 *
 * Small "X of Y LCs this month" bar for the dashboard. Polls
 * /api/entitlements/current on mount; refreshes when the page
 * regains focus so a freshly-completed validation lights up.
 *
 * Visibility rules:
 *   - Hidden on Enterprise tier (unlimited quota; nothing to show).
 *   - Solid amber at 70-89% used.
 *   - Solid rose at 90%+ used.
 *   - "Upgrade" CTA at 90%+.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { TrendingUp } from "lucide-react";
import {
  getCurrentEntitlements,
  type CurrentEntitlements,
} from "@/lib/lcopilot/entitlementsApi";

const POLL_INTERVAL_MS = 60_000;


function formatTier(tier: string | null): string {
  if (!tier) return "";
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

export function QuotaStrip() {
  const [data, setData] = useState<CurrentEntitlements | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getCurrentEntitlements();
      setData(next);
      setError(null);
    } catch (err) {
      setError((err as Error).message ?? "Failed to load quota");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [refresh]);

  if (error) {
    // Don't surface — quota is informational, not load-bearing.
    return null;
  }
  if (data === null) return null;

  // Unlimited tier — nothing actionable to show.
  if (data.quota_limit == null) {
    return null;
  }

  const used = data.quota_used ?? 0;
  const limit = data.quota_limit;
  const pct = data.quota_pct_used ?? Math.min(1, used / Math.max(1, limit));
  const pctRounded = Math.round(pct * 100);

  const isCritical = pct >= 0.9;
  const isWarning = pct >= 0.7 && pct < 0.9;

  let barClass = "bg-emerald-500";
  let trackClass = "bg-emerald-500/15";
  if (isWarning) {
    barClass = "bg-amber-500";
    trackClass = "bg-amber-500/15";
  } else if (isCritical) {
    barClass = "bg-rose-500";
    trackClass = "bg-rose-500/15";
  }

  return (
    <div
      className={`flex items-center gap-3 rounded-md border border-border ${trackClass} px-3 py-2`}
      data-testid="quota-strip"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium">
            {used} of {limit} LCs this month
            {data.tier && (
              <span className="ml-2 text-muted-foreground font-normal">
                · {formatTier(data.tier)} plan
              </span>
            )}
          </p>
          <p className="text-[10px] text-muted-foreground tabular-nums">
            {pctRounded}%
          </p>
        </div>
        <div className="mt-1 h-1.5 w-full rounded-full bg-neutral-200/60 dark:bg-neutral-700/40 overflow-hidden">
          <div
            className={`h-full ${barClass} transition-all`}
            style={{ width: `${pctRounded}%` }}
          />
        </div>
      </div>
      {isCritical && (
        <Button asChild size="sm" variant="outline">
          <Link to={data.upgrade_url || "/pricing"}>
            <TrendingUp className="w-3.5 h-3.5 mr-1" />
            Upgrade
          </Link>
        </Button>
      )}
    </div>
  );
}
