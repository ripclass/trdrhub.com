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
  const businessTypes = (details as Record<string, unknown> | undefined)?.business_types
  if (!Array.isArray(businessTypes)) {
    return []
  }

  return businessTypes
    .map((value) => normalizeText(value))
    .filter(Boolean)
}

export function resolveLcopilotRoute(params: {
  user: User | null
  onboardingStatus: OnboardingStatus | null
}): LcopilotRouteDecision {
  const { user, onboardingStatus } = params

  if (!user) {
    return { destination: '/login', reason: 'unauthenticated' }
  }

  if (!onboardingStatus) {
    return { destination: '/onboarding', reason: 'missing_onboarding_status' }
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

  const hasExporter = businessTypes.includes('exporter')
  const hasImporter = businessTypes.includes('importer')
  const isCombinedCompanyType = COMBINED_COMPANY_TYPES.has(companyType)
  const isCombined = isCombinedCompanyType || (hasExporter && hasImporter)
  const isEnterprise = role === 'tenant_admin' || (isCombined && ENTERPRISE_COMPANY_SIZES.has(companySize))
  const isImporterOnly = role === 'importer' || (!isCombined && (companyType === 'importer' || hasImporter))
  const isBank = BANK_ROLES.has(role)
  const isSystemAdmin = role === 'system_admin' || role === 'admin' || user.role === 'admin'

  if (isSystemAdmin) {
    return { destination: '/admin', reason: 'system_admin' }
  }

  if (isBank) {
    // Bank remains parked for the public beta. Keep bank users out of LCopilot's default route.
    return { destination: '/hub', reason: 'bank_parked' }
  }

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
