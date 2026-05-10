import type { ReactNode } from 'react'
import { FileCheck, Loader2 } from 'lucide-react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { useOnboarding } from '@/hooks/use-onboarding'
import { persistPendingExporterReviewRoute } from '@/lib/exporter/pendingReviewRoute'
import {
  matchesLcopilotScope,
  resolveLcopilotRoute,
  type LcopilotBetaScope,
} from '@/lib/lcopilot/routing'

interface LcopilotBetaRouteProps {
  scope: LcopilotBetaScope
  children: ReactNode
}

function LcopilotRouteLoading({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-[#00261C] flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#B2F273]/10 mb-6">
          <FileCheck className="w-8 h-8 text-[#B2F273]" />
        </div>
        <div className="flex items-center justify-center gap-3 mb-4">
          <Loader2 className="w-5 h-5 text-[#B2F273] animate-spin" />
          <span className="text-lg text-white">{message}</span>
        </div>
        <p className="text-sm text-[#EDF5F2]/60">Please wait...</p>
      </div>
    </div>
  )
}

export function LcopilotBetaRoute({ scope, children }: LcopilotBetaRouteProps) {
  const location = useLocation()
  const { user, isLoading: isLoadingAuth } = useAuth()
  const { status, isLoading: isLoadingOnboarding } = useOnboarding()
  const returnUrl = `${location.pathname}${location.search}`

  if (isLoadingAuth || (user && isLoadingOnboarding)) {
    return (
      <LcopilotRouteLoading
        message={scope === 'router' ? 'Loading your dashboard...' : 'Checking your session...'}
      />
    )
  }

  if (!user) {
    persistPendingExporterReviewRoute(returnUrl)
    return <Navigate to={`/login?returnUrl=${encodeURIComponent(returnUrl)}`} replace />
  }

  const decision = resolveLcopilotRoute({ user, onboardingStatus: status })

  if (scope === 'onboarding') {
    if (decision.destination !== '/onboarding') {
      return <Navigate to={decision.destination} replace />
    }

    return <>{children}</>
  }

  if (decision.destination === '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }

  if (scope === 'router') {
    return <Navigate to={decision.destination} replace />
  }

  if (!matchesLcopilotScope(scope, decision.destination)) {
    return <Navigate to={decision.destination} replace />
  }

  return <>{children}</>
}
