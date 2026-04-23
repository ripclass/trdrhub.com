import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '@/hooks/use-auth'
import {
  completeOnboarding as completeOnboardingRequest,
  getOnboardingStatus,
  updateOnboardingProgress,
  type OnboardingCompletePayload,
  type OnboardingProgressPayload,
  type OnboardingStatus,
} from '@/api/onboarding'

interface OnboardingContextType {
  status: OnboardingStatus | null
  isLoading: boolean
  needsOnboarding: boolean
  updateProgress: (payload: OnboardingProgressPayload) => Promise<void>
  completeOnboarding: (payload: OnboardingCompletePayload) => Promise<OnboardingStatus>
  refreshStatus: () => Promise<void>
}

const OnboardingContext = createContext<OnboardingContextType | undefined>(undefined)

export function useOnboarding() {
  const context = useContext(OnboardingContext)
  if (context === undefined) {
    throw new Error('useOnboarding must be used within an OnboardingProvider')
  }
  return context
}

interface OnboardingProviderProps {
  children: ReactNode
}

export function OnboardingProvider({ children }: OnboardingProviderProps) {
  const { user } = useAuth()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const GUEST_MODE = (import.meta.env.VITE_GUEST_MODE || '').toString().toLowerCase() === 'true'

  const loadStatus = async () => {
    if (!user) {
      if (GUEST_MODE) {
        setStatus({
          user_id: 'guest',
          role: 'exporter',
          company_id: null,
          completed: true,
          step: null,
          status: 'active',
          kyc_status: 'none',
          required: {} as OnboardingStatus['required'],
          details: {},
        })
      } else {
        setStatus(null)
      }
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)

      if (GUEST_MODE) {
        setStatus({
          user_id: user.id,
          role: user.role,
          company_id: null,
          completed: true,
          step: null,
          status: 'active',
          kyc_status: 'none',
          required: {} as OnboardingStatus['required'],
          details: {},
        })
      } else {
        const onboardingStatus = await getOnboardingStatus()
        setStatus(onboardingStatus)
      }
    } catch (error) {
      console.error('Failed to load onboarding status:', error)
      setStatus(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [user])

  const updateProgress = async (payload: OnboardingProgressPayload) => {
    try {
      if (GUEST_MODE) {
        return
      }

      const updatedStatus = await updateOnboardingProgress(payload)
      setStatus(updatedStatus)
    } catch (error) {
      console.error('Failed to update onboarding progress:', error)
      throw error
    }
  }

  const completeOnboarding = async (
    payload: OnboardingCompletePayload,
  ): Promise<OnboardingStatus> => {
    if (GUEST_MODE) {
      // Guest mode is fully mocked — return the current status unchanged.
      return (
        status ?? {
          user_id: user?.id ?? 'guest',
          role: payload.activities[0],
          company_id: null,
          completed: true,
          step: null,
          status: 'active',
          kyc_status: 'none',
          required: { basic: [], legal: [], docs: [] },
          details: {
            activities: payload.activities,
            country: payload.country,
            tier: payload.tier,
          },
        }
      )
    }
    try {
      const updatedStatus = await completeOnboardingRequest(payload)
      setStatus(updatedStatus)
      return updatedStatus
    } catch (error) {
      console.error('Failed to complete onboarding:', error)
      throw error
    }
  }

  const refreshStatus = async () => {
    await loadStatus()
  }

  const needsOnboarding = React.useMemo(() => {
    return Boolean(user && status && !status.completed)
  }, [status, user])

  // Detect stale onboarding status: when user changes (login/logout/switch),
  // there's a render frame before the useEffect fires where user is set but
  // status still belongs to the previous user. Without this, the route guard
  // may redirect based on a stale status instead of showing a loading state.
  //
  // Important: only treat status as stale when a NON-NULL status exists for a
  // different user. If status is null (e.g. because the onboarding API failed
  // or timed out), we are done loading — route guards should fall through and
  // let the user reach the page rather than block them on a loading screen
  // forever.
  const statusIsStaleForCurrentUser =
    !!user && status !== null && status.user_id !== user.id
  const effectivelyLoading = isLoading || statusIsStaleForCurrentUser

  const value: OnboardingContextType = {
    status,
    isLoading: effectivelyLoading,
    needsOnboarding,
    updateProgress,
    completeOnboarding,
    refreshStatus,
  }

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}
