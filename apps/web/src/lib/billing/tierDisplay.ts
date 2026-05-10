/**
 * Single source of truth for billing-tier *display names*.
 *
 * The backend's `company.tier` is the 7-value billing enum from the 2026-05-10
 * pricing restructure (`payg` / `solo` / `business` / `enterprise` /
 * `agency_starter` / `agency_pro` / `agency_enterprise`). The legacy
 * frontend `PlanType` enum only has FREE / STARTER / PROFESSIONAL / ENTERPRISE,
 * so anything that renders a label off `PlanType` mislabels (e.g. "Business"
 * shows as "Professional", "Pay-as-you-go" shows as "Solo"). Render labels off
 * the raw `company.tier` via {@link tierDisplayName} instead; keep `PlanType`
 * only for the (approximate, pre-self-serve-checkout) gating logic.
 */

export const BILLING_TIER_DISPLAY_NAMES: Record<string, string> = {
  // 2026-05-10 billing tiers
  payg: "Pay-as-you-go",
  solo: "Solo",
  business: "Business",
  enterprise: "Enterprise",
  agency_starter: "Agency Starter",
  agency_pro: "Agency Pro",
  agency_enterprise: "Agency Enterprise",
  // legacy / fallbacks still seen on older rows
  sme: "Business",
  free: "Free",
  pay_per_check: "Pay-as-you-go",
  monthly_basic: "Solo",
  monthly_pro: "Business",
  // smoke-test exemption (reference_smoke_quota_bypass)
  smoke_bypass: "Smoke test",
};

/** Human label for a raw `company.tier` string. Falls back to a Title-Cased
 * form of the raw value so an unknown tier never renders as a blank or a
 * snake_case slug. */
export function tierDisplayName(tier: string | null | undefined): string {
  if (!tier) return "";
  const key = String(tier).trim().toLowerCase();
  if (!key) return "";
  return (
    BILLING_TIER_DISPLAY_NAMES[key] ||
    key
      .split("_")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

/** True for the agency/services per-seat tracks (the ones that show
 * "Unlimited (fair use)" rather than a numeric quota). */
export function isAgencyBillingTier(tier: string | null | undefined): boolean {
  return !!tier && String(tier).trim().toLowerCase().startsWith("agency");
}
