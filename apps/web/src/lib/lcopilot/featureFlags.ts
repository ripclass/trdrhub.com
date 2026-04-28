/**
 * Client-side feature flags for LCopilot.
 *
 * LCOPILOT_IMPORTER_V2 gates the two new importer routes
 * (/lcopilot/importer-dashboard/draft-lc and /supplier-docs) and
 * the moment-aware action buttons that land in Phase 3. When the flag
 * is off, the refactored importer surface is invisible to users and
 * no one can reach the new action endpoints, which is the blast-radius
 * containment we rely on for Phase 3 rollback instead of per-endpoint
 * server flags.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_IMPORTER_V2=true
 */

export function isImporterV2Enabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_IMPORTER_V2 ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_DISCREPANCY_WORKFLOW gates the discrepancy resolution +
 * re-papering UI (Phase A2). When off, the results page shows the
 * read-only discrepancy cards we always had. When on, each card gets
 * Accept / Reject / Waive / Re-paper actions + a collapsed comment
 * thread.
 *
 * The /repaper/{token} recipient page is always available (it's the
 * link the back-end emails to non-platform users) — that surface
 * doesn't depend on the flag.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_DISCREPANCY_WORKFLOW=true
 */
export function isDiscrepancyWorkflowEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_DISCREPANCY_WORKFLOW ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_BULK_VALIDATION gates the customer-facing bulk LC validation
 * surface (Phase A1 part 2). v1 ships only the QA test page at
 * /lcopilot/_bulk-test; the full dashboard surface comes in a later
 * phase once we've smoke-tested the backend infra in the wild.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_BULK_VALIDATION=true
 */
export function isBulkValidationEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_BULK_VALIDATION ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_NOTIFICATIONS gates the bell icon + dropdown that surfaces
 * the in-app notification rows the backend writes (Phase A3 part 1).
 * Off by default — when disabled, the bell + the notifications API
 * calls are absent. The backend endpoints exist either way.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_NOTIFICATIONS=true
 */
export function isNotificationsEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_NOTIFICATIONS ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_AGENCY_REAL gates the rebuilt agency dashboard
 * (/lcopilot/agency-dashboard). Off by default — when disabled, the
 * page renders the legacy stub. When on, the agent gets the real
 * Dashboard / Suppliers / Foreign Buyers surfaces from Phase A5.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_AGENCY_REAL=true
 */
export function isAgencyRealEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_AGENCY_REAL ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_SERVICES_REAL gates the rebuilt services dashboard
 * (/lcopilot/services-dashboard) — Phase A8 + A9. Off by default.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_SERVICES_REAL=true
 */
export function isServicesRealEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_SERVICES_REAL ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}

/**
 * LCOPILOT_ENTERPRISE_TIER gates the enterprise group overview +
 * audit log + RBAC surfaces — Phase A10.
 *
 * Enable locally by adding to apps/web/.env:
 *   VITE_LCOPILOT_ENTERPRISE_TIER=true
 */
export function isEnterpriseTierEnabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_ENTERPRISE_TIER ?? "")
    .toString()
    .trim()
    .toLowerCase();
  return raw === "true" || raw === "1";
}
