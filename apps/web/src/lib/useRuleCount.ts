/**
 * Live rule count for marketing surfaces — launch honesty checklist item
 * ("live-fetched counts working"). Fetches GET /api/public/stats once per
 * page load (module-level memo, all consumers share one request) and formats
 * e.g. 21437 → "21,000+". Any failure falls back to the safe FLOOR "4,000+"
 * — under-claiming beats lying while the stats API is unreachable.
 */

import { useEffect, useState } from "react";

const FALLBACK = "4,000+";

let cached: string | null = null;
let inFlight: Promise<string> | null = null;

function format(total: number): string {
  // Round DOWN to a clean floor so the claim is always true.
  const floor =
    total >= 10_000 ? Math.floor(total / 1000) * 1000 : Math.floor(total / 500) * 500;
  return `${floor.toLocaleString()}+`;
}

async function fetchRuleCount(): Promise<string> {
  try {
    const res = await fetch("/api/public/stats");
    if (!res.ok) return FALLBACK;
    const data = await res.json();
    const total = data?.rules_total;
    if (typeof total === "number" && total >= 4000) return format(total);
    return FALLBACK;
  } catch {
    return FALLBACK;
  }
}

export function useRuleCount(): string {
  const [value, setValue] = useState<string>(cached ?? FALLBACK);

  useEffect(() => {
    if (cached) return;
    if (!inFlight) {
      inFlight = fetchRuleCount().then((v) => {
        cached = v;
        return v;
      });
    }
    let mounted = true;
    void inFlight.then((v) => {
      if (mounted) setValue(v);
    });
    return () => {
      mounted = false;
    };
  }, []);

  return value;
}
