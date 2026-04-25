/**
 * Pure activity + tier constants and helpers.
 *
 * Kept separate from @/api/onboarding so that importing the priority helper
 * doesn't drag in the axios client / Supabase auth runtime — critical for
 * unit tests that exercise pure logic without initialising the whole
 * auth stack.
 *
 * Mirrors apps/api/app/services/onboarding_service.py::_ACTIVITY_PRIORITY
 * and apps/api/app/models/company.py::BusinessActivity. Keep in lockstep.
 */

// `agent` and `services` remain in the union so legacy DB rows + stored
// sessionStorage values still type-check during read paths. Wizard +
// backend validator reject them — see ACTIVITY_OPTIONS in the wizard /
// Register and BUSINESS_ACTIVITY_VALUES in apps/api/app/models/company.py.
// Routing falls them back to /lcopilot/exporter-dashboard.
export type BusinessActivity = 'exporter' | 'importer' | 'agent' | 'services'
export type BusinessTier = 'solo' | 'sme' | 'enterprise'

/**
 * Canonical activity priority. activities[0] drives the landing dashboard
 * AND the default active workspace in sessionStorage.
 *
 * Pre-launch scope-down (2026-04-25): only exporter + importer are
 * actively sold. Between the two (most common multi-activity combo),
 * exporter wins because Tier-1 multi-activity customers are predominantly
 * garment exporters with an import arm for raw materials (Meghna Group
 * pattern). Stale 'agent' / 'services' values from old DB rows are not
 * in this priority list and fall through to the routing.ts fallback
 * (exporter dashboard).
 */
export const ACTIVITY_PRIORITY: readonly BusinessActivity[] = [
  'exporter',
  'importer',
] as const

export function sortActivitiesByPriority(
  activities: BusinessActivity[],
): BusinessActivity[] {
  // Unknown values (legacy 'agent' / 'services' from pre-2026-04-25 DB
  // rows) sort to the END, mirroring the Python version's
  // `rank.get(a, len(_ACTIVITY_PRIORITY))` semantics. indexOf returns
  // -1 for unknowns, which would put them FIRST without this guard.
  const rank = (a: BusinessActivity): number => {
    const idx = ACTIVITY_PRIORITY.indexOf(a)
    return idx === -1 ? ACTIVITY_PRIORITY.length : idx
  }
  return [...activities].sort((a, b) => rank(a) - rank(b))
}
