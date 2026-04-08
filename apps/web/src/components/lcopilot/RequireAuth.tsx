import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { useOnboarding } from '@/hooks/use-onboarding'
import { Loader2, FileCheck } from 'lucide-react'

interface RequireAuthProps {
  children: ReactNode
}

/**
 * Lightweight auth guard for beta routes that need authentication
 * but don't need dashboard-scope routing (upload, results, analytics, etc.).
 *
 * Checks:
 * 1. User is authenticated → redirect to /login if not
 * 2. Onboarding is complete → redirect to /onboarding if not
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const location = useLocation()
  const { user, isLoading: isLoadingAuth } = useAuth()
  const { status, isLoading: isLoadingOnboarding } = useOnboarding()
  const returnUrl = `${location.pathname}${location.search}`

  if (isLoadingAuth || (user && isLoadingOnboarding)) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/10 mb-6">
            <FileCheck className="w-8 h-8 text-blue-400" />
          </div>
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            <span className="text-lg text-white">Checking your session...</span>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to={`/login?returnUrl=${encodeURIComponent(returnUrl)}`} replace />
  }

  if (status && !status.completed) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}
