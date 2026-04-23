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

export type BusinessActivity = 'exporter' | 'importer' | 'agent' | 'services'
export type BusinessTier = 'solo' | 'sme' | 'enterprise'

/**
 * Canonical activity priority. activities[0] drives the landing dashboard
 * AND the default active workspace in sessionStorage. Order:
 *
 *   agent > exporter > importer > services
 *
 * Rationale:
 *   - Agents self-identify by that role — agency dashboard is their home.
 *   - Between exporter + importer (most common multi-activity combo), exporter
 *     wins because Tier-1 multi-activity customers are predominantly garment
 *     exporters with an import arm for raw materials (Meghna Group pattern).
 *   - Services is last: it's a niche activity that rarely stands alone.
 */
export const ACTIVITY_PRIORITY: readonly BusinessActivity[] = [
  'agent',
  'exporter',
  'importer',
  'services',
] as const

export function sortActivitiesByPriority(
  activities: BusinessActivity[],
): BusinessActivity[] {
  return [...activities].sort(
    (a, b) => ACTIVITY_PRIORITY.indexOf(a) - ACTIVITY_PRIORITY.indexOf(b),
  )
}
