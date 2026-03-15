import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '@/hooks/use-auth'
import {
  getOnboardingStatus,
  updateOnboardingProgress,
  type OnboardingProgressPayload,
  type OnboardingStatus,
} from '@/api/onboarding'

interface OnboardingContextType {
  status: OnboardingStatus | null
  isLoading: boolean
  needsOnboarding: boolean
  updateProgress: (payload: OnboardingProgressPayload) => Promise<void>
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

  const refreshStatus = async () => {
    await loadStatus()
  }

  const needsOnboarding = React.useMemo(() => {
    return Boolean(user && status && !status.completed)
  }, [status, user])

  const value: OnboardingContextType = {
    status,
    isLoading,
    needsOnboarding,
    updateProgress,
    refreshStatus,
  }

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}
