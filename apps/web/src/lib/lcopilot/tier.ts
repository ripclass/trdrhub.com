/**
 * useTier — exposes the user's Company.tier from the onboarding status.
 *
 * Mirrors apps/api/app/models/company.py::BusinessTier. Drives feature
 * gating for the enterprise affordances (Group overview link, future
 * SSO / audit log / RBAC panels). DOES NOT drive which dashboard the user
 * sees — activities do that (see lib/lcopilot/routing.ts).
 *
 * Reading order:
 *   1. details.tier (Day 2 onboarding shape — canonical)
 *   2. details.company.size (legacy shape — only 'enterprise' maps cleanly)
 *   3. default 'sme'
 */

import { useMemo } from 'react'
import { useOnboarding } from '@/hooks/use-onboarding'
import type { BusinessTier } from '@/api/onboarding'

const VALID_TIERS = new Set<BusinessTier>(['solo', 'sme', 'enterprise'])

function normalizeTier(raw: unknown): BusinessTier | null {
  if (typeof raw !== 'string') return null
  const normalized = raw.trim().toLowerCase() as BusinessTier
  return VALID_TIERS.has(normalized) ? normalized : null
}

function tierFromLegacyCompanySize(size: unknown): BusinessTier | null {
  // Legacy company.size values: 'sme', 'medium', 'large', 'enterprise',
  // 'established'. Only 'enterprise' is a semantic match for the new tier
  // enum; the rest collapse to 'sme' since they conflate pricing with role.
  if (typeof size !== 'string') return null
  const normalized = size.trim().toLowerCase()
  if (normalized === 'enterprise') return 'enterprise'
  if (normalized === 'sme') return 'sme'
  return null
}

export function useTier(): BusinessTier {
  const { status } = useOnboarding()
  return useMemo(() => {
    const details = status?.details as Record<string, unknown> | undefined
    const company = details?.company as Record<string, unknown> | undefined

    const fromNewShape = normalizeTier(details?.tier)
    if (fromNewShape) return fromNewShape

    const fromLegacy = tierFromLegacyCompanySize(company?.size)
    if (fromLegacy) return fromLegacy

    return 'sme'
  }, [status])
}

export function isEnterpriseTier(tier: BusinessTier): boolean {
  return tier === 'enterprise'
}
