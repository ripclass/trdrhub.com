/**
 * Entitlements API client — Phase A4.
 *
 * Reads the per-company quota snapshot the dashboard strip + the
 * over-quota modal both render off of.
 */

import { api } from "@/api/client";

export interface CurrentEntitlements {
  tier: string | null;
  plan: string | null;
  quota_used: number;
  quota_limit: number | null;     // null = unlimited
  quota_remaining: number | null; // null = unlimited
  quota_pct_used: number | null;  // 0..1, null when unlimited
  period_start: string | null;
  seat_limit: number | null;      // null = unlimited
  upgrade_url: string;
}

export async function getCurrentEntitlements(): Promise<CurrentEntitlements> {
  const { data } = await api.get<CurrentEntitlements>("/api/entitlements/current");
  return data;
}
