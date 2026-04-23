import { describe, expect, it } from 'vitest'
import { matchesLcopilotScope, resolveLcopilotRoute } from '@/lib/lcopilot/routing'
import type { OnboardingStatus } from '@/api/onboarding'
import type { User } from '@/hooks/use-auth'

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    email: 'user@example.com',
    full_name: 'Test User',
    username: 'test-user',
    role: 'exporter',
    isActive: true,
    ...overrides,
  }
}

function buildOnboardingStatus(overrides: Partial<OnboardingStatus> = {}): OnboardingStatus {
  return {
    user_id: 'user-1',
    role: 'exporter',
    company_id: 'company-1',
    completed: true,
    step: null,
    status: 'active',
    kyc_status: 'none',
    required: {
      basic: [],
      legal: [],
      docs: [],
    },
    details: {
      business_types: ['exporter'],
      company: {
        name: 'Acme Trade',
        type: 'exporter',
        size: 'sme',
      },
    },
    ...overrides,
  }
}

describe('resolveLcopilotRoute', () => {
  it('routes unauthenticated users to login', () => {
    expect(resolveLcopilotRoute({ user: null, onboardingStatus: null })).toEqual({
      destination: '/login',
      reason: 'unauthenticated',
    })
  })

  it('fails open to exporter dashboard when onboarding status is unavailable (cold-start / API failure)', () => {
    // A legit authenticated user should not be forced into the onboarding
    // wizard just because the status endpoint timed out. Their role tells us
    // where to land.
    expect(
      resolveLcopilotRoute({ user: buildUser(), onboardingStatus: null }),
    ).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('fails open to importer dashboard when onboarding status is unavailable for an importer', () => {
    expect(
      resolveLcopilotRoute({
        user: buildUser({ role: 'importer', backendRole: 'importer' }),
        onboardingStatus: null,
      }),
    ).toEqual({
      destination: '/lcopilot/importer-dashboard',
      reason: 'importer',
    })
  })

  it('routes incomplete onboarding to onboarding', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({ completed: false }),
    })

    expect(decision).toEqual({
      destination: '/onboarding',
      reason: 'onboarding_incomplete',
    })
  })

  it('routes exporter users to the exporter dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus(),
    })

    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('routes importer users to the importer dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser({ role: 'importer' }),
      onboardingStatus: buildOnboardingStatus({
        role: 'importer',
        details: {
          business_types: ['importer'],
          company: { name: 'Buyer Co', type: 'importer', size: 'sme' },
        },
      }),
    })

    expect(decision).toEqual({
      destination: '/lcopilot/importer-dashboard',
      reason: 'importer',
    })
  })

  it('routes combined SME users to the combined dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        details: {
          business_types: ['exporter', 'importer'],
          company: { name: 'Trade House', type: 'both', size: 'sme' },
        },
      }),
    })

    expect(decision).toEqual({
      destination: '/lcopilot/combined-dashboard',
      reason: 'combined',
    })
  })

  it('routes enterprise users to the enterprise dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        role: 'tenant_admin',
        details: {
          business_types: ['exporter', 'importer'],
          company: { name: 'Large Trade House', type: 'both', size: 'large' },
        },
      }),
    })

    expect(decision).toEqual({
      destination: '/lcopilot/enterprise-dashboard',
      reason: 'enterprise',
    })
  })

  it('parks bank users on the hub instead of hijacking the beta dashboard route', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser({ role: 'bank' }),
      onboardingStatus: buildOnboardingStatus({
        role: 'bank_officer',
        details: {
          business_types: ['bank'],
          company: { name: 'Example Bank', type: 'bank', size: 'large' },
        },
      }),
    })

    expect(decision).toEqual({
      destination: '/hub',
      reason: 'bank_parked',
    })
  })

  it('routes system admins away from LCopilot beta dashboards', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser({ role: 'admin' }),
      onboardingStatus: buildOnboardingStatus({ role: 'system_admin' }),
    })

    expect(decision).toEqual({
      destination: '/admin',
      reason: 'system_admin',
    })
  })

  // ---- Day 2 onboarding shape (details.activities) ----

  it('Day 2 shape: single-activity exporter lands on exporter dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        details: {
          activities: ['exporter'],
          country: 'BD',
          tier: 'sme',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('Day 2 shape: single-activity importer lands on importer dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser({ role: 'importer' }),
      onboardingStatus: buildOnboardingStatus({
        role: 'importer',
        details: {
          activities: ['importer'],
          country: 'IN',
          tier: 'sme',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/importer-dashboard',
      reason: 'importer',
    })
  })

  it('Day 2 shape: multi-activity lands on first activity\'s dashboard (NOT combined)', () => {
    // Core plan directive: "multi-activity -> first activity's dashboard". The
    // Day 3 workspace switcher will let the user flip to the other workspace.
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        details: {
          activities: ['exporter', 'importer'],
          country: 'BD',
          tier: 'sme',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('Day 2 shape: enterprise tier does NOT short-circuit to enterprise dashboard', () => {
    // Enterprise is a pricing tier, not a dashboard (per redesign). The
    // cross-SBU rollup surfaces on the activity dashboard as a KPI strip
    // (Day 4+). Landing must still go to the primary activity.
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        role: 'tenant_admin',
        details: {
          activities: ['exporter', 'importer'],
          country: 'BD',
          tier: 'enterprise',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('Day 2 shape: agent activity temp-routes to exporter until Day 4 ships agency dashboard', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        details: {
          activities: ['agent'],
          country: 'BD',
          tier: 'sme',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })

  it('Day 2 shape: services activity routes to exporter (no dedicated dashboard)', () => {
    const decision = resolveLcopilotRoute({
      user: buildUser(),
      onboardingStatus: buildOnboardingStatus({
        details: {
          activities: ['services'],
          country: 'GB',
          tier: 'solo',
        },
      }),
    })
    expect(decision).toEqual({
      destination: '/lcopilot/exporter-dashboard',
      reason: 'exporter',
    })
  })
})

describe('matchesLcopilotScope', () => {
  it('matches only the canonical dashboard for each scope', () => {
    expect(matchesLcopilotScope('exporter', '/lcopilot/exporter-dashboard')).toBe(true)
    expect(matchesLcopilotScope('importer', '/lcopilot/importer-dashboard')).toBe(true)
    expect(matchesLcopilotScope('combined', '/lcopilot/combined-dashboard')).toBe(true)
    expect(matchesLcopilotScope('enterprise', '/lcopilot/enterprise-dashboard')).toBe(true)
    expect(matchesLcopilotScope('exporter', '/lcopilot/importer-dashboard')).toBe(false)
  })
})
