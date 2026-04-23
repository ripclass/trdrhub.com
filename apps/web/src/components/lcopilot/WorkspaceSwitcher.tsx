/**
 * WorkspaceSwitcher — header affordance for multi-activity companies.
 *
 * Renders a Select dropdown when the user's Company has 2+ business
 * activities (e.g. both "exporter" and "importer"). Single-activity users
 * see nothing — the switcher renders null.
 *
 * Derives activities from the onboarding details payload. Prefers the Day 2
 * shape (details.activities) and falls back to details.business_types for
 * legacy-shape users who haven't re-onboarded since the wizard rewrite.
 */

import { useMemo } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useOnboarding } from '@/hooks/use-onboarding'
import type { BusinessActivity } from '@/api/onboarding'
import { useActiveWorkspace } from '@/lib/lcopilot/activeWorkspace'

const ACTIVITY_LABELS: Record<BusinessActivity, string> = {
  exporter: 'Export workspace',
  importer: 'Import workspace',
  agent: 'Agency workspace',
  services: 'Services workspace',
}

const VALID_ACTIVITIES = new Set<BusinessActivity>(['exporter', 'importer', 'agent', 'services'])

function extractActivities(details: Record<string, unknown> | undefined): BusinessActivity[] {
  if (!details) return []
  const raw = Array.isArray(details.activities)
    ? details.activities
    : Array.isArray(details.business_types)
      ? details.business_types
      : []
  const out: BusinessActivity[] = []
  for (const value of raw) {
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase() as BusinessActivity
      if (VALID_ACTIVITIES.has(normalized) && !out.includes(normalized)) {
        out.push(normalized)
      }
    }
  }
  return out
}

export function WorkspaceSwitcher() {
  const { status } = useOnboarding()
  const activities = useMemo(
    () => extractActivities(status?.details as Record<string, unknown> | undefined),
    [status?.details],
  )
  const { active, switchTo } = useActiveWorkspace(activities)

  if (activities.length < 2) {
    return null
  }

  return (
    <Select value={active} onValueChange={(value) => switchTo(value as BusinessActivity)}>
      <SelectTrigger
        className="h-8 w-[180px] text-sm"
        aria-label="Switch workspace"
        data-testid="workspace-switcher"
      >
        <SelectValue placeholder="Select workspace" />
      </SelectTrigger>
      <SelectContent>
        {activities.map((activity) => (
          <SelectItem key={activity} value={activity}>
            {ACTIVITY_LABELS[activity]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
