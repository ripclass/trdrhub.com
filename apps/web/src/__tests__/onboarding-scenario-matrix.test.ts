/**
 * Onboarding scenario matrix — validates the full decision table of
 * activity x tier x (legacy shape) against the live routing logic.
 *
 * Complements lcopilotRouting.test.ts's hand-picked cases with an exhaustive
 * enumeration so any future change to resolveLcopilotRoute is caught as a
 * table-level diff, and Ripon can read the matrix to confirm intent.
 *
 * Also emits a console.table summary at the end for quick eyeball review.
 */

import { afterAll, describe, expect, it } from 'vitest'
import { resolveLcopilotRoute } from '@/lib/lcopilot/routing'
import {
  ACTIVITY_PRIORITY,
  sortActivitiesByPriority,
  type BusinessActivity,
  type BusinessTier,
} from '@/lib/lcopilot/activities'
import type { OnboardingStatus } from '@/api/onboarding'
import type { User } from '@/hooks/use-auth'

// Mirror of the WorkspaceSwitcher gate (>=2 activities)
const showsSwitcher = (activities: BusinessActivity[]): boolean => activities.length >= 2

// Mirror of the EnterpriseGroupLink gate
const showsGroupLink = (tier: BusinessTier): boolean => tier === 'enterprise'

// Dashboard the activity maps to, per ACTIVITY_DESTINATIONS in routing.ts.
const ACTIVITY_DASHBOARDS: Record<BusinessActivity, string> = {
  exporter: '/lcopilot/exporter-dashboard',
  importer: '/lcopilot/importer-dashboard',
  agent: '/lcopilot/agency-dashboard',
  services: '/lcopilot/exporter-dashboard',
}

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 'sim-user',
    email: 'sim@example.com',
    full_name: 'Sim User',
    username: 'sim',
    role: 'exporter',
    isActive: true,
    ...overrides,
  }
}

function buildStatus(
  activities: BusinessActivity[],
  country: string,
  tier: BusinessTier,
): OnboardingStatus {
  return {
    user_id: 'sim-user',
    role: activities[0] ?? 'exporter',
    company_id: 'sim-company',
    completed: true,
    step: null,
    status: 'active',
    kyc_status: 'none',
    required: { basic: [], legal: [], docs: [] },
    details: { activities, country, tier },
  }
}

interface Scenario {
  label: string
  activities: BusinessActivity[]
  tier: BusinessTier
  country: string
  userRole?: string // override for tenant_admin cases
}

const NEW_SHAPE_SCENARIOS: Scenario[] = [
  // Single activity × each tier
  { label: 'exporter / solo',       activities: ['exporter'],             tier: 'solo',       country: 'BD' },
  { label: 'exporter / sme',        activities: ['exporter'],             tier: 'sme',        country: 'BD' },
  { label: 'exporter / enterprise', activities: ['exporter'],             tier: 'enterprise', country: 'BD' },
  { label: 'importer / solo',       activities: ['importer'],             tier: 'solo',       country: 'IN' },
  { label: 'importer / sme',        activities: ['importer'],             tier: 'sme',        country: 'IN' },
  { label: 'importer / enterprise', activities: ['importer'],             tier: 'enterprise', country: 'IN' },
  { label: 'agent / sme',           activities: ['agent'],                tier: 'sme',        country: 'BD' },
  { label: 'agent / enterprise',    activities: ['agent'],                tier: 'enterprise', country: 'BD' },
  { label: 'services / sme',        activities: ['services'],             tier: 'sme',        country: 'GB' },
  { label: 'services / enterprise', activities: ['services'],             tier: 'enterprise', country: 'GB' },

  // Multi-activity — first activity wins
  { label: 'exp+imp / sme',         activities: ['exporter', 'importer'], tier: 'sme',        country: 'BD' },
  { label: 'imp+exp / sme',         activities: ['importer', 'exporter'], tier: 'sme',        country: 'VN' },
  { label: 'exp+imp / enterprise',  activities: ['exporter', 'importer'], tier: 'enterprise', country: 'BD' },
  { label: 'imp+exp / enterprise',  activities: ['importer', 'exporter'], tier: 'enterprise', country: 'VN' },
  { label: 'agent+exp / sme',       activities: ['agent', 'exporter'],    tier: 'sme',        country: 'BD' },
  { label: 'exp+agent / sme',       activities: ['exporter', 'agent'],    tier: 'sme',        country: 'BD' },
  { label: 'all-four / enterprise', activities: ['exporter', 'importer', 'agent', 'services'], tier: 'enterprise', country: 'US' },
]

interface RunResult {
  label: string
  primary: BusinessActivity
  dashboard: string
  dashboardMatchesPrimary: boolean
  switcher: boolean
  groupLink: boolean
  reason: string
}

const collected: RunResult[] = []

describe('onboarding scenario matrix — new Day 2 shape', () => {
  it.each(NEW_SHAPE_SCENARIOS)('$label routes correctly', (s) => {
    const user = buildUser({ role: s.userRole ?? s.activities[0] })
    const status = buildStatus(s.activities, s.country, s.tier)
    const decision = resolveLcopilotRoute({ user, onboardingStatus: status })

    const primary = s.activities[0]
    const expectedDashboard = ACTIVITY_DASHBOARDS[primary]

    expect(decision.destination).toBe(expectedDashboard)

    collected.push({
      label: s.label,
      primary,
      dashboard: decision.destination,
      dashboardMatchesPrimary: decision.destination === expectedDashboard,
      switcher: showsSwitcher(s.activities),
      groupLink: showsGroupLink(s.tier),
      reason: decision.reason,
    })
  })
})

// Legacy shape (pre-Day-2 users) — we kept the fallback alive so existing
// customers still route cleanly until they re-onboard.
describe('onboarding scenario matrix — legacy shape fallback', () => {
  const LEGACY_SCENARIOS = [
    { label: 'legacy exporter / sme',    businessTypes: ['exporter'],             companyType: 'exporter', companySize: 'sme',        expected: '/lcopilot/exporter-dashboard' },
    { label: 'legacy importer / sme',    businessTypes: ['importer'],             companyType: 'importer', companySize: 'sme',        expected: '/lcopilot/importer-dashboard' },
    { label: 'legacy both / sme',        businessTypes: ['exporter', 'importer'], companyType: 'both',     companySize: 'sme',        expected: '/lcopilot/exporter-dashboard' }, // first wins, combined-dashboard retired
    { label: 'legacy both / large',      businessTypes: ['exporter', 'importer'], companyType: 'both',     companySize: 'large',      expected: '/lcopilot/exporter-dashboard' }, // enterprise-dashboard retired
    { label: 'legacy logistics / sme',   businessTypes: ['exporter'],             companyType: 'logistics', companySize: 'sme',       expected: '/lcopilot/exporter-dashboard' }, // legacy logistics collapsed to exporter
  ] as const

  it.each(LEGACY_SCENARIOS)('$label routes to $expected', (s) => {
    const user = buildUser()
    const status: OnboardingStatus = {
      user_id: 'sim-user',
      role: 'exporter',
      company_id: 'sim-company',
      completed: true,
      step: null,
      status: 'active',
      kyc_status: 'none',
      required: { basic: [], legal: [], docs: [] },
      details: {
        business_types: [...s.businessTypes],
        company: { name: 'Legacy Co', type: s.companyType, size: s.companySize },
      },
    }
    const decision = resolveLcopilotRoute({ user, onboardingStatus: status })
    expect(decision.destination).toBe(s.expected)
  })
})

// Edge / degenerate cases
describe('onboarding scenario matrix — edge cases', () => {
  it('missing onboarding status + role=importer -> importer dashboard (fail-open)', () => {
    const user = buildUser({ role: 'importer', backendRole: 'importer' })
    const decision = resolveLcopilotRoute({ user, onboardingStatus: null })
    expect(decision.destination).toBe('/lcopilot/importer-dashboard')
  })

  it('missing onboarding status + bank role -> /hub (parked)', () => {
    const user = buildUser({ role: 'bank', backendRole: 'bank_officer' })
    const decision = resolveLcopilotRoute({ user, onboardingStatus: null })
    expect(decision.destination).toBe('/hub')
  })

  it('completed=false -> /onboarding', () => {
    const user = buildUser()
    const status = buildStatus(['exporter'], 'BD', 'sme')
    const decision = resolveLcopilotRoute({
      user,
      onboardingStatus: { ...status, completed: false },
    })
    expect(decision.destination).toBe('/onboarding')
  })

  it('system_admin role overrides activities', () => {
    const user = buildUser({ role: 'admin' })
    const status = buildStatus(['exporter'], 'BD', 'sme')
    const decision = resolveLcopilotRoute({
      user,
      onboardingStatus: { ...status, role: 'system_admin' },
    })
    expect(decision.destination).toBe('/admin')
  })
})

describe('activity priority sort', () => {
  it('sorts any click order into canonical priority (agent > exporter > importer > services)', () => {
    expect(sortActivitiesByPriority(['importer', 'exporter'])).toEqual(['exporter', 'importer'])
    expect(sortActivitiesByPriority(['services', 'agent'])).toEqual(['agent', 'services'])
    expect(
      sortActivitiesByPriority(['services', 'importer', 'exporter', 'agent']),
    ).toEqual(['agent', 'exporter', 'importer', 'services'])
  })

  it('is idempotent', () => {
    const input: BusinessActivity[] = ['exporter', 'agent']
    const once = sortActivitiesByPriority(input)
    const twice = sortActivitiesByPriority(once)
    expect(once).toEqual(twice)
  })

  it('does not mutate the input array', () => {
    const input: BusinessActivity[] = ['services', 'agent']
    const sorted = sortActivitiesByPriority(input)
    expect(input).toEqual(['services', 'agent'])
    expect(sorted).toEqual(['agent', 'services'])
  })

  it('ACTIVITY_PRIORITY contains every BusinessActivity value exactly once', () => {
    const all: BusinessActivity[] = ['exporter', 'importer', 'agent', 'services']
    expect([...ACTIVITY_PRIORITY].sort()).toEqual(all.sort())
  })
})

afterAll(() => {
  // eslint-disable-next-line no-console
  console.log('\n=== Onboarding routing scenario matrix ===\n')
  // eslint-disable-next-line no-console
  console.table(
    collected.map((r) => ({
      scenario: r.label,
      dashboard: r.dashboard.replace('/lcopilot/', ''),
      switcher: r.switcher ? 'shown' : '—',
      'group overview': r.groupLink ? 'shown' : '—',
      reason: r.reason,
    })),
  )
})
