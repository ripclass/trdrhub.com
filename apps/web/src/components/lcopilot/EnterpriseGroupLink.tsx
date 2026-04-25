/**
 * EnterpriseGroupLink — tier-gated link to the cross-SBU rollup page.
 *
 * Renders null for non-enterprise tiers. Sits next to the WorkspaceSwitcher
 * in the dashboard header as the single visible affordance the Day 4 refactor
 * ships for enterprise-tier customers. Deeper enterprise features (SSO,
 * audit log, RBAC) are deferred to a follow-up sprint.
 */

import { Link } from 'react-router-dom'
import { LayoutGrid } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useTier, isEnterpriseTier } from '@/lib/lcopilot/tier'

export function EnterpriseGroupLink() {
  const tier = useTier()
  if (!isEnterpriseTier(tier)) {
    return null
  }
  return (
    <Button asChild size="sm" variant="ghost" className="h-8">
      <Link to="/lcopilot/group-overview" data-testid="enterprise-group-link">
        <LayoutGrid className="mr-2 h-4 w-4" />
        Group overview
      </Link>
    </Button>
  )
}
