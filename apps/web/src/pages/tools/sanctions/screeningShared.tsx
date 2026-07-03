/**
 * Shared pieces for the sanctions screening pages — Phase 2 launch (2026-07).
 *
 * Screening now runs through the deterministic engine (RulHub) and is
 * FAIL-CLOSED: a failed screen must render as "unavailable — do not treat as
 * clear", never as an empty no-hits result. These helpers keep the four
 * screening surfaces (party / vessel / goods / batch) consistent about that.
 */

import { AlertTriangle, CheckCircle, ShieldAlert, XCircle, Shield } from "lucide-react";

/** Designated-party lists the engine actually screens. Codes match the
 *  engine's `list_source` values so per-list match chips line up. */
export const COVERED_LISTS = [
  { code: "ofac_sdn", name: "OFAC SDN", jurisdiction: "US", status: "active" },
  { code: "ofac_consolidated", name: "OFAC Consolidated (Non-SDN)", jurisdiction: "US", status: "active" },
  { code: "un_consolidated", name: "UN Security Council", jurisdiction: "UN", status: "active" },
  { code: "uk_ofsi", name: "UK OFSI", jurisdiction: "UK", status: "active" },
  { code: "eu_fsf", name: "EU Consolidated (pending)", jurisdiction: "EU", status: "pending" },
] as const;

export const ACTIVE_LIST_CODES = COVERED_LISTS.filter((l) => l.status === "active").map((l) => l.code);

export const FAIL_CLOSED_MESSAGE =
  "Screening is unavailable right now — do NOT treat this as a clear result. " +
  "Retry, or escalate to your compliance officer before proceeding.";

export const OFAC_50_CAVEAT =
  "Ownership structures are not resolved: an entity majority-owned by a designated party " +
  "(OFAC 50% rule) may not itself appear on any list.";

export type ScreeningStatus = "clear" | "potential_match" | "match" | "unavailable";

export interface SharedScreeningMatch {
  list_code: string;
  list_name: string;
  matched_name: string;
  matched_type: string;
  match_type: string;
  match_score: number; // 0..1 from the engine
  match_method: string;
  programs: string[];
  country?: string;
  source_id?: string;
  listed_date?: string;
  remarks?: string;
  action?: string; // block | review
  recommendation?: string;
  caveats?: string[];
}

export interface SharedScreeningResult {
  query: string;
  screening_type: string;
  screened_at: string;
  status: ScreeningStatus;
  risk_level: string;
  lists_screened: string[];
  matches: SharedScreeningMatch[];
  total_matches: number;
  highest_score: number;
  flags: string[];
  recommendation: string;
  certificate_id: string;
  processing_time_ms: number;
  rules_checked?: number;
  screening_scope?: string[];
  coverage_warning?: string | null;
  list_versions?: Record<string, string | null> | null;
}

/** Thrown by screenPost when the backend fails closed (503) or errors. */
export class ScreeningUnavailableError extends Error {
  constructor(message?: string) {
    super(message || FAIL_CLOSED_MESSAGE);
    this.name = "ScreeningUnavailableError";
  }
}

/** POST to a screening endpoint. Throws ScreeningUnavailableError on any
 *  failure — callers must render the fail-closed banner, never a clear state. */
export async function screenPost<T = SharedScreeningResult>(url: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ScreeningUnavailableError();
  }
  if (!response.ok) {
    let message = FAIL_CLOSED_MESSAGE;
    try {
      const payload = await response.json();
      message = payload?.detail?.message || message;
    } catch {
      /* keep default */
    }
    throw new ScreeningUnavailableError(message);
  }
  return (await response.json()) as T;
}

export const formatScore = (score: number): string => `${Math.round((score ?? 0) * 100)}%`;

export const statusColor = (status: string): string => {
  switch (status) {
    case "clear": return "emerald";
    case "potential_match": return "amber";
    case "match": return "red";
    case "unavailable": return "orange";
    default: return "slate";
  }
};

export const statusIcon = (status: string) => {
  switch (status) {
    case "clear": return CheckCircle;
    case "potential_match": return AlertTriangle;
    case "match": return XCircle;
    case "unavailable": return ShieldAlert;
    default: return Shield;
  }
};

export const statusHeadline = (status: string): string => {
  switch (status) {
    case "clear": return "✅ NO MATCHES FOUND";
    case "potential_match": return "⚠️ POTENTIAL MATCH — REVIEW REQUIRED";
    case "match": return "❌ MATCH FOUND — DO NOT PROCEED";
    case "unavailable": return "⛔ NOT SCREENED — DO NOT TREAT AS CLEAR";
    default: return status;
  }
};

/** Amber fail-closed banner shown when a screen could not be performed. */
export function ScreeningUnavailableBanner({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <div className="p-4 bg-orange-500/10 border border-orange-500/40 rounded-lg flex gap-3">
      <ShieldAlert className="w-5 h-5 text-orange-400 shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-orange-300">Screening unavailable — do not treat as clear</p>
        <p className="text-sm text-slate-400 mt-1">{message}</p>
      </div>
    </div>
  );
}

/** Advisory disclaimer block rendered under every screening surface. */
export function ScreeningDisclaimer() {
  return (
    <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-lg text-xs text-slate-500 space-y-2">
      <p>
        <span className="text-slate-400 font-medium">Lists covered:</span>{" "}
        OFAC SDN, OFAC Consolidated (Non-SDN), UN Security Council, UK OFSI. EU consolidated list
        is pending and not yet screened.
      </p>
      <p>{OFAC_50_CAVEAT}</p>
      <p>
        Screening is a compliance aid, not legal advice, and not a substitute for your own
        sanctions-compliance programme. Verify potential matches against the official list entry
        before acting.
      </p>
    </div>
  );
}
