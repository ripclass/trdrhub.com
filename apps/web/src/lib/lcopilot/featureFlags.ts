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
