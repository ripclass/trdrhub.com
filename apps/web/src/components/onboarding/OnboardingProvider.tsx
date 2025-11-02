import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useAuth } from '@/hooks/use-auth'
import {
  getOnboardingStatus,
  updateOnboardingProgress,
  type OnboardingStatus,
  type OnboardingProgressPayload,
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

  const loadStatus = async () => {
    if (!user) {
      setStatus(null)
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      const onboardingStatus = await getOnboardingStatus()
      setStatus(onboardingStatus)
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
    if (!status) return false
    return !status.completed
  }, [status])

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

