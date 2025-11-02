import { supabase } from '@/lib/supabase'
import { api } from './client'

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export const signInWithEmail = async (email: string, password: string) => {
  const { error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) {
    throw error
  }
}

export const signUpWithEmail = async (email: string, password: string, fullName: string) => {
  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName },
    },
  })
  if (error) {
    throw error
  }
}

export const signInWithGoogle = async () => {
  const redirectTo = `${window.location.origin}/dashboard`
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  })
  if (error) {
    throw error
  }
}

export const signOut = async () => {
  await supabase.auth.signOut()
}

export const clearSupabaseSession = async () => {
  try {
    await supabase.auth.signOut()
  } catch (error) {
    console.error('Failed to clear Supabase session', error)
  }
}

export const getCurrentUser = async (): Promise<UserResponse> => {
  const response = await api.get<UserResponse>('/auth/me')
  return response.data
}
