/**
 * Active workspace (per-tab) for multi-activity companies.
 *
 * Multi-activity companies (e.g. Meghna Group — both export and import desks)
 * share one login but want to pivot between activity dashboards. We persist
 * the active workspace in sessionStorage so each browser tab can hold a
 * different activity (export in one tab, import in another) without colliding
 * across tabs.
 *
 * Storage contract:
 *   key:   "lcopilot.activeWorkspace"
 *   value: BusinessActivity string ("exporter" | "importer" | "agent" | "services")
 *
 * If the stored value is stale (not in the user's current activities list),
 * we silently fall back to activities[0] — the primary activity.
 *
 * Paired with <WorkspaceSwitcher /> which renders the UI and
 * resolveLcopilotRoute which picks the landing page on login.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { BusinessActivity } from '@/api/onboarding'

const STORAGE_KEY = 'lcopilot.activeWorkspace'

// Pre-launch scope-down (2026-04-25): agent + services have no dedicated
// dashboard. Stale stored values fall through the lookup and resolve to
// exporter via the dashboardForActivity nullish fallback. Keep in sync
// with ACTIVITY_DESTINATIONS in lib/lcopilot/routing.ts.
const ACTIVITY_DASHBOARD: Partial<Record<BusinessActivity, string>> = {
  exporter: '/lcopilot/exporter-dashboard',
  importer: '/lcopilot/importer-dashboard',
}

export function dashboardForActivity(activity: BusinessActivity): string {
  return ACTIVITY_DASHBOARD[activity] ?? '/lcopilot/exporter-dashboard'
}

function readStoredWorkspace(): BusinessActivity | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    // 'agent' / 'services' from stale sessionStorage entries are still
    // type-valid as BusinessActivity but routing falls them back to
    // exporter via dashboardForActivity above.
    if (
      raw === 'exporter' ||
      raw === 'importer' ||
      raw === 'agent' ||
      raw === 'services'
    ) {
      return raw
    }
    return null
  } catch {
    // sessionStorage may be unavailable (SSR, strict-mode iframes). Degrade.
    return null
  }
}

function writeStoredWorkspace(value: BusinessActivity): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(STORAGE_KEY, value)
  } catch {
    // Non-fatal — the switcher will still render, it just won't remember.
  }
}

export interface UseActiveWorkspaceResult {
  active: BusinessActivity
  activities: BusinessActivity[]
  switchTo: (activity: BusinessActivity) => void
}

/**
 * Per-tab active workspace state.
 *
 * When `activities` has <2 items, this still works — it just tracks the only
 * activity and switchTo() is effectively a no-op + navigate. Callers that
 * only want UI for multi-activity users should guard on `activities.length`.
 */
export function useActiveWorkspace(activities: BusinessActivity[]): UseActiveWorkspaceResult {
  const navigate = useNavigate()
  const fallback: BusinessActivity = activities[0] ?? 'exporter'

  const [active, setActive] = useState<BusinessActivity>(() => {
    const stored = readStoredWorkspace()
    if (stored && activities.includes(stored)) return stored
    return fallback
  })

  // If the activities list changes (rare — onboarding edit in another tab),
  // reconcile: keep `active` if still valid, else reset to fallback.
  useEffect(() => {
    if (activities.length === 0) return
    if (!activities.includes(active)) {
      setActive(fallback)
      writeStoredWorkspace(fallback)
    }
  }, [activities, active, fallback])

  const switchTo = useCallback(
    (activity: BusinessActivity) => {
      if (!activities.includes(activity)) return
      setActive(activity)
      writeStoredWorkspace(activity)
      navigate(dashboardForActivity(activity))
    },
    [activities, navigate],
  )

  return { active, activities, switchTo }
}
