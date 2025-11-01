import { api } from './client'

export interface OnboardingStatus {
  needs_onboarding: boolean
  onboarding_completed: boolean
  current_progress: OnboardingProgress | null
  role: string
}

export interface OnboardingProgress {
  current_step: string | null
  completed_steps: string[]
  skipped_steps: string[]
  tutorial_views: string[]
  sample_data_views: string[]
  last_accessed: string | null
}

export interface OnboardingContent {
  role: string
  steps: OnboardingStep[]
  welcome_message: string
  introduction: string
  key_features: string[]
  available_tutorials: Array<{
    id: string
    title: string
    duration: string
  }>
  sample_data_available: boolean
}

export interface OnboardingStep {
  step_id: string
  title: string
  description: string | null
  completed: boolean
  skipped: boolean
}

export interface OnboardingProgressUpdate {
  current_step?: string | null
  completed_steps?: string[]
  skipped_steps?: string[]
  tutorial_viewed?: string
  sample_data_viewed?: string
}

export interface OnboardingCompleteRequest {
  completed?: boolean
}

/**
 * Get onboarding status for current user
 */
export const getOnboardingStatus = async (): Promise<OnboardingStatus> => {
  const response = await api.get<OnboardingStatus>('/onboarding/status')
  return response.data
}

/**
 * Get role-specific onboarding content
 */
export const getOnboardingContent = async (role: string): Promise<OnboardingContent> => {
  const response = await api.get<OnboardingContent>(`/onboarding/content/${role}`)
  return response.data
}

/**
 * Update onboarding progress
 */
export const updateOnboardingProgress = async (
  progress: OnboardingProgressUpdate
): Promise<OnboardingProgress> => {
  const response = await api.put<OnboardingProgress>('/onboarding/progress', progress)
  return response.data
}

/**
 * Mark onboarding as completed
 */
export const completeOnboarding = async (
  completed: boolean = true
): Promise<OnboardingStatus> => {
  const response = await api.put<OnboardingStatus>('/onboarding/complete', { completed })
  return response.data
}

/**
 * Reset onboarding status (allow re-access)
 */
export const resetOnboarding = async (): Promise<{ message: string; onboarding_completed: boolean }> => {
  const response = await api.post<{ message: string; onboarding_completed: boolean }>('/onboarding/reset')
  return response.data
}

