import { api } from './client'

export interface OnboardingStatus {
  user_id: string
  role?: string
  company_id?: string | null
  completed: boolean
  step?: string | null
  status?: string | null
  kyc_status?: string | null
  required: {
    basic: string[]
    legal: string[]
    docs: string[]
  }
  details: Record<string, unknown>
}

export interface CompanyPayload {
  name: string
  type?: string
  legal_name?: string
  registration_number?: string
  regulator_id?: string
  country?: string
}

export interface OnboardingProgressPayload {
  role?: string
  business_types?: string[]
  onboarding_step?: string
  company?: CompanyPayload
  submit_for_review?: boolean
  complete?: boolean
  approved?: boolean
}

export const getOnboardingStatus = async (): Promise<OnboardingStatus> => {
  const response = await api.get<OnboardingStatus>('/onboarding/status')
  return response.data
}

export const updateOnboardingProgress = async (
  payload: OnboardingProgressPayload
): Promise<OnboardingStatus> => {
  const response = await api.put<OnboardingStatus>('/onboarding/progress', payload)
  return response.data
}

export const approveOnboarding = async (userId: string): Promise<OnboardingStatus> => {
  const response = await api.post<OnboardingStatus>(`/onboarding/approve/${userId}`)
  return response.data
}

