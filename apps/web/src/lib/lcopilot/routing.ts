import type { OnboardingStatus } from '@/api/onboarding'
import type { User } from '@/hooks/use-auth'

export type LcopilotBetaDestination =
  | '/login'
  | '/onboarding'
  | '/hub'
  | '/admin'
  | '/lcopilot/exporter-dashboard'
  | '/lcopilot/importer-dashboard'
  | '/lcopilot/combined-dashboard'
  | '/lcopilot/enterprise-dashboard'

export type LcopilotBetaScope =
  | 'router'
  | 'onboarding'
  | 'exporter'
  | 'importer'
  | 'combined'
  | 'enterprise'

export interface LcopilotRouteDecision {
  destination: LcopilotBetaDestination
  reason:
    | 'unauthenticated'
    | 'missing_onboarding_status'
    | 'onboarding_incomplete'
    | 'system_admin'
    | 'bank_parked'
    | 'enterprise'
    | 'combined'
    | 'importer'
    | 'exporter'
}

const DASHBOARD_DESTINATIONS: Record<
  Exclude<LcopilotBetaScope, 'router' | 'onboarding'>,
  LcopilotBetaDestination
> = {
  exporter: '/lcopilot/exporter-dashboard',
  importer: '/lcopilot/importer-dashboard',
  combined: '/lcopilot/combined-dashboard',
  enterprise: '/lcopilot/enterprise-dashboard',
}

const COMBINED_COMPANY_TYPES = new Set([
  'both',
  'both_exporter_importer',
  'both exporter & importer',
  'both exporter and importer',
])

const ENTERPRISE_COMPANY_SIZES = new Set(['medium', 'large', 'enterprise', 'established'])
const BANK_ROLES = new Set(['bank_officer', 'bank_admin'])

function normalizeText(value: unknown): string {
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

function normalizeBusinessTypes(details: OnboardingStatus['details']): string[] {
  const source = details as Record<string, unknown> | undefined
  // Prefer the 3-question wizard's `activities` field (Day 2 onboarding shape).
  // Fall back to legacy `business_types` for users who completed the old wizard
  // before the Day 2 frontend landed. Backend mirrors activities into both keys
  // on POST /onboarding/complete, so steady state they agree.
  const raw = Array.isArray(source?.activities)
    ? (source!.activities as unknown[])
    : Array.isArray(source?.business_types)
      ? (source!.business_types as unknown[])
      : []
  return raw.map((value) => normalizeText(value)).filter(Boolean)
}

// Activity-keyed dashboard routing (Day 2 onboarding).
// agent/services don't have dedicated dashboards yet — map to exporter as the
// temporary landing page. Day 4 plans to create /lcopilot/agency-dashboard; at
// that point, swap the `agent` mapping.
const ACTIVITY_DESTINATIONS: Record<string, LcopilotBetaDestination> = {
  exporter: '/lcopilot/exporter-dashboard',
  importer: '/lcopilot/importer-dashboard',
  agent: '/lcopilot/exporter-dashboard',
  services: '/lcopilot/exporter-dashboard',
}

function destinationForPrimaryActivity(
  activities: string[],
): { destination: LcopilotBetaDestination; reason: LcopilotRouteDecision['reason'] } | null {
  for (const activity of activities) {
    const dest = ACTIVITY_DESTINATIONS[activity]
    if (dest) {
      const reason: LcopilotRouteDecision['reason'] =
        activity === 'importer' ? 'importer' : 'exporter'
      return { destination: dest, reason }
    }
  }
  return null
}

function hasNewOnboardingShape(details: OnboardingStatus['details']): boolean {
  const source = details as Record<string, unknown> | undefined
  return Array.isArray(source?.activities) && (source!.activities as unknown[]).length > 0
}

export function resolveLcopilotRoute(params: {
  user: User | null
  onboardingStatus: OnboardingStatus | null
}): LcopilotRouteDecision {
  const { user, onboardingStatus } = params

  if (!user) {
    return { destination: '/login', reason: 'unauthenticated' }
  }

  // When the onboarding API fails (cold-start timeout, 5xx, network error),
  // OnboardingProvider catches the error and sets status to null. Treat an
  // authenticated user with a legit backend role as already onboarded and
  // route them to their dashboard — do NOT force them into the onboarding
  // wizard just because the status endpoint was unreachable. The legitimate
  // "new user never onboarded" path sends a real status object with
  // completed:false, handled below.
  if (!onboardingStatus) {
    const fallbackRole = normalizeText(user.backendRole) || normalizeText(user.role)
    const isBank = BANK_ROLES.has(fallbackRole)
    const isSystemAdmin = fallbackRole === 'system_admin' || fallbackRole === 'admin' || user.role === 'admin'
    if (isSystemAdmin) {
      return { destination: '/admin', reason: 'system_admin' }
    }
    if (isBank) {
      return { destination: '/hub', reason: 'bank_parked' }
    }
    if (fallbackRole === 'importer') {
      return { destination: '/lcopilot/importer-dashboard', reason: 'importer' }
    }
    // Default authenticated users (including tenant_admin and anyone with an
    // unknown role) land on the exporter dashboard. If they really are a new
    // user that has never onboarded, the next status refresh will return a
    // real completed:false record and the next navigation will correctly
    // push them to /onboarding.
    return { destination: '/lcopilot/exporter-dashboard', reason: 'exporter' }
  }

  if (!onboardingStatus.completed) {
    return { destination: '/onboarding', reason: 'onboarding_incomplete' }
  }

  // Prefer onboarding role (raw backend role), fall back to user.backendRole
  // (also raw), then user.role (mapped). This ensures tenant_admin is preserved
  // for enterprise detection even when onboarding status lacks the role field.
  const role = normalizeText(onboardingStatus.role) || normalizeText(user.backendRole) || normalizeText(user.role)
  const details = onboardingStatus.details as Record<string, unknown> | undefined
  const company = (details?.company as Record<string, unknown> | undefined) ?? {}
  const companyType = normalizeText(company.type)
  const companySize = normalizeText(company.size)
  const businessTypes = normalizeBusinessTypes(onboardingStatus.details)

  const isSystemAdmin = role === 'system_admin' || role === 'admin' || user.role === 'admin'
  const isBank = BANK_ROLES.has(role)

  if (isSystemAdmin) {
    return { destination: '/admin', reason: 'system_admin' }
  }

  if (isBank) {
    // Bank remains parked for the public beta.
    return { destination: '/hub', reason: 'bank_parked' }
  }

  // Day 2 onboarding shape — activities[0] drives landing, per
  // memory/project_lcopilot_onboarding_redesign.md ("multi-activity -> first
  // activity's dashboard"). Day 3 will add the workspace switcher in the
  // header so users with 2+ activities can flip between workspaces.
  if (hasNewOnboardingShape(onboardingStatus.details)) {
    const primary = destinationForPrimaryActivity(businessTypes)
    if (primary) {
      return primary
    }
  }

  // Legacy fallback — users who completed the pre-Day-2 wizard still carry
  // the old shape (company.type/size + business_types only). Preserve the
  // combined/enterprise routing until Day 3 ships the 301 redirects.
  const hasExporter = businessTypes.includes('exporter')
  const hasImporter = businessTypes.includes('importer')
  const isCombinedCompanyType = COMBINED_COMPANY_TYPES.has(companyType)
  const isCombined = isCombinedCompanyType || (hasExporter && hasImporter)
  const isEnterprise = role === 'tenant_admin' || (isCombined && ENTERPRISE_COMPANY_SIZES.has(companySize))
  const isImporterOnly = role === 'importer' || (!isCombined && (companyType === 'importer' || hasImporter))

  if (isEnterprise) {
    return { destination: '/lcopilot/enterprise-dashboard', reason: 'enterprise' }
  }

  if (isCombined) {
    return { destination: '/lcopilot/combined-dashboard', reason: 'combined' }
  }

  if (isImporterOnly) {
    return { destination: '/lcopilot/importer-dashboard', reason: 'importer' }
  }

  return { destination: '/lcopilot/exporter-dashboard', reason: 'exporter' }
}

export function matchesLcopilotScope(
  scope: Exclude<LcopilotBetaScope, 'router' | 'onboarding'>,
  destination: LcopilotBetaDestination,
): boolean {
  return DASHBOARD_DESTINATIONS[scope] === destination
}
