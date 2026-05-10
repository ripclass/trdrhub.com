/**
 * QuotaStrip — dashboard "X of Y LCs this month" bar.
 *
 * Polls /api/entitlements/current on mount; refreshes on focus so a
 * freshly-completed validation lights up. Reflects the 2026-05-10 pricing
 * restructure: 7 billing tiers across two tracks.
 *
 * Visibility / states:
 *   - Trader tiers with an included pool (solo 5 / business 25 /
 *     enterprise 100): a bar with used/limit, the overage rate, and an
 *     "Upgrade" CTA at 90%+.
 *   - PAYG (quota_limit 0): "Pay-as-you-go · $12 per LC" line, no bar.
 *   - Agency tiers (quota_limit null = unlimited within fair use): an
 *     "Unlimited LCs (fair use)" pill, no bar.
 *   - Lime at <70% used, amber 70–89%, rose 90%+.
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { TrendingUp, Infinity as InfinityIcon } from "lucide-react";
import {
  getCurrentEntitlements,
  type CurrentEntitlements,
} from "@/lib/lcopilot/entitlementsApi";
import {
  isAgencyBillingTier as isAgencyTier,
  tierDisplayName,
} from "@/lib/billing/tierDisplay";

const POLL_INTERVAL_MS = 60_000;

// Which tier you'd upgrade to from here (for the "or upgrade to X" hint).
const UPGRADE_HINT: Record<string, string> = {
  payg: "Solo",
  solo: "Business",
  business: "Enterprise",
  agency_starter: "Agency Pro",
};

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
    // Quota is informational, not load-bearing — fail quiet.
    return null;
  }
  if (data === null) return null;

  const tierName = tierDisplayName(data.tier);

  // Agency tiers — unlimited within fair use. Show a small pill, no bar.
  if (data.quota_limit == null) {
    if (!isAgencyTier(data.tier)) return null; // genuinely unbounded / unknown — nothing actionable
    return (
      <div
        className="flex items-center gap-2 rounded-md border border-border bg-[#B2F273]/10 px-3 py-2 text-xs"
        data-testid="quota-strip"
      >
        <InfinityIcon className="w-3.5 h-3.5 text-[#00382E] dark:text-[#B2F273]" />
        <span className="font-medium">Unlimited LC validations (fair use)</span>
        {tierName && <span className="text-muted-foreground">· {tierName} plan</span>}
      </div>
    );
  }

  // PAYG — no included pool; each validation is a per-use charge.
  if (data.quota_limit === 0) {
    return (
      <div
        className="flex items-center justify-between gap-3 rounded-md border border-border bg-[#B2F273]/10 px-3 py-2 text-xs"
        data-testid="quota-strip"
      >
        <span className="font-medium">
          Pay-as-you-go
          {data.overage_rate_usd != null && (
            <span className="text-muted-foreground font-normal"> · ${data.overage_rate_usd} per LC presentation</span>
          )}
        </span>
        <Button asChild size="sm" variant="outline">
          <Link to={data.upgrade_url || "/pricing"}>
            <TrendingUp className="w-3.5 h-3.5 mr-1" />
            See plans
          </Link>
        </Button>
      </div>
    );
  }

  const used = data.quota_used ?? 0;
  const limit = data.quota_limit;
  const pct = data.quota_pct_used ?? Math.min(1, used / Math.max(1, limit));
  const pctRounded = Math.round(pct * 100);

  const isCritical = pct >= 0.9;
  const isWarning = pct >= 0.7 && pct < 0.9;

  let barClass = "bg-[#B2F273]";
  let trackClass = "bg-[#B2F273]/15";
  if (isWarning) {
    barClass = "bg-amber-500";
    trackClass = "bg-amber-500/15";
  } else if (isCritical) {
    barClass = "bg-rose-500";
    trackClass = "bg-rose-500/15";
  }

  const overageHint =
    data.overage_rate_usd != null
      ? `Extra LCs $${data.overage_rate_usd} each${UPGRADE_HINT[data.tier ?? ""] ? ` · or upgrade to ${UPGRADE_HINT[data.tier ?? ""]}` : ""}`
      : null;

  return (
    <div
      className={`flex items-center gap-3 rounded-md border border-border ${trackClass} px-3 py-2`}
      data-testid="quota-strip"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium truncate">
            {used} of {limit} LCs this month
            {tierName && (
              <span className="ml-2 text-muted-foreground font-normal">· {tierName} plan</span>
            )}
            {overageHint && (
              <span className="ml-2 text-muted-foreground font-normal hidden sm:inline">· {overageHint}</span>
            )}
          </p>
          <p className="text-[10px] text-muted-foreground tabular-nums">{pctRounded}%</p>
        </div>
        <div className="mt-1 h-1.5 w-full rounded-full bg-[#00382E]/15 dark:bg-[#00382E]/40 overflow-hidden">
          <div className={`h-full ${barClass} transition-all`} style={{ width: `${pctRounded}%` }} />
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
