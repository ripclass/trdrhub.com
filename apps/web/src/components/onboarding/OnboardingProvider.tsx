import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useAuth } from '@/hooks/use-auth'
import {
  getOnboardingStatus,
  updateOnboardingProgress,
  completeOnboarding,
  resetOnboarding,
  type OnboardingStatus,
  type OnboardingProgress,
  type OnboardingProgressUpdate,
} from '@/api/onboarding'

interface OnboardingContextType {
  status: OnboardingStatus | null
  isLoading: boolean
  needsOnboarding: boolean
  updateProgress: (progress: OnboardingProgressUpdate) => Promise<void>
  markComplete: (completed?: boolean) => Promise<void>
  reset: () => Promise<void>
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
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      const onboardingStatus = await getOnboardingStatus()
      setStatus(onboardingStatus)
    } catch (error) {
      console.error('Failed to load onboarding status:', error)
      // Default to needing onboarding if we can't load status
      setStatus({
        needs_onboarding: true,
        onboarding_completed: false,
        current_progress: null,
        role: user.role || 'exporter',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [user])

  const updateProgress = async (progress: OnboardingProgressUpdate) => {
    try {
      const updatedProgress = await updateOnboardingProgress(progress)
      if (status) {
        setStatus({
          ...status,
          current_progress: updatedProgress,
        })
      }
    } catch (error) {
      console.error('Failed to update onboarding progress:', error)
      throw error
    }
  }

  const markComplete = async (completed: boolean = true) => {
    try {
      const updatedStatus = await completeOnboarding(completed)
      setStatus(updatedStatus)
    } catch (error) {
      console.error('Failed to complete onboarding:', error)
      throw error
    }
  }

  const reset = async () => {
    try {
      await resetOnboarding()
      await loadStatus()
    } catch (error) {
      console.error('Failed to reset onboarding:', error)
      throw error
    }
  }

  const refreshStatus = async () => {
    await loadStatus()
  }

  const needsOnboarding = status?.needs_onboarding ?? false

  const value: OnboardingContextType = {
    status,
    isLoading,
    needsOnboarding,
    updateProgress,
    markComplete,
    reset,
    refreshStatus,
  }

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}

