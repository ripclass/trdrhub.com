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

  it('routes authenticated users without onboarding status to onboarding', () => {
    expect(
      resolveLcopilotRoute({ user: buildUser(), onboardingStatus: null }),
    ).toEqual({
      destination: '/onboarding',
      reason: 'missing_onboarding_status',
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
