import * as React from 'react'
import type { Role } from '@/types/analytics'
import { supabase } from '@/lib/supabase'
import { api } from '@/api/client'

export interface User {
  id: string
  email: string
  full_name?: string
  username?: string
  role: Role
  isActive: boolean
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  loginWithEmail: (email: string, password: string) => Promise<User>
  loginWithGoogle: () => Promise<void>
  registerWithEmail: (email: string, password: string, fullName: string, role: string) => Promise<User>
  logout: () => Promise<void>
  hasRole: (role: Role | Role[]) => boolean
  refreshUser: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | null>(null)

// Map backend roles to frontend roles
const mapBackendRole = (backendRole: string): Role => {
  const roleMap: Record<string, Role> = {
    'exporter': 'exporter',
    'importer': 'importer',
    'tenant_admin': 'exporter',
    'bank_officer': 'bank',
    'bank_admin': 'bank',
    'system_admin': 'admin',
    'admin': 'admin',
  }
  return roleMap[backendRole] || 'exporter'
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const GUEST_MODE = (import.meta.env.VITE_GUEST_MODE || '').toString().toLowerCase() === 'true'

  const setGuest = () => {
    setUser({
      id: 'guest',
      email: 'guest@trdrhub.com',
      full_name: 'Guest',
      username: 'Guest',
      role: 'exporter',
      isActive: true,
    })
  }

  const AUTH_TIMEOUT_MS = 10000

  const withTimeout = async <T,>(promise: Promise<T>, label: string, ms = AUTH_TIMEOUT_MS): Promise<T> => {
    let timer: any
    const timeout = new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timed out. Please try again.`)), ms)
    })
    try {
      const result = await Promise.race([promise, timeout])
      return result as T
    } finally {
      clearTimeout(timer)
    }
  }

  const fetchUserProfile = React.useCallback(async () => {
    try {
      const { data: userData } = await withTimeout(api.get('/auth/me'), 'Loading profile')
      const mapped: User = {
        id: userData.id,
        email: userData.email,
        full_name: userData.full_name,
        username: userData.full_name,
        role: mapBackendRole(userData.role),
        isActive: userData.is_active,
      }
      setUser(mapped)
      
      // Fetch CSRF token after successful profile fetch
      try {
        const { fetchCsrfToken } = await import('@/lib/csrf')
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        await fetchCsrfToken(API_BASE_URL)
      } catch (csrfError) {
        console.warn('Failed to fetch CSRF token:', csrfError)
        // Non-critical, continue without CSRF token
      }
      
      return mapped
    } catch (error) {
      console.error('Failed to load user profile', error)
      if (GUEST_MODE) {
        setGuest()
        return {
          id: 'guest', email: 'guest@trdrhub.com', full_name: 'Guest', username: 'Guest', role: 'exporter', isActive: true,
        }
      }
      setUser(null)
      throw error
    }
  }, [])

  React.useEffect(() => {
    let mounted = true

    const init = async () => {
      setIsLoading(true)
      const { data } = await supabase.auth.getSession()
      if (!mounted) return
      if (data.session) {
        try {
          await fetchUserProfile()
        } finally {
          if (mounted) setIsLoading(false)
        }
      } else {
        if (GUEST_MODE) setGuest()
        setIsLoading(false)
      }
    }

    init()

    const { data: authListener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (!mounted) return
      if (session) {
        setIsLoading(true)
        try {
          await fetchUserProfile()
        } finally {
          if (mounted) setIsLoading(false)
        }
      } else {
        setUser(null)
        setIsLoading(false)
      }
    })

    return () => {
      mounted = false
      authListener?.subscription.unsubscribe()
    }
  }, [fetchUserProfile])

  const loginWithEmail = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      // Login to Supabase first
      const { error } = await withTimeout(
        supabase.auth.signInWithPassword({ email, password }),
        'Signing in'
      )
      if (error) throw error
      
      // Also login to backend API to get JWT token for admin endpoints
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ email, password }),
        })
        
        if (loginResponse.ok) {
          const tokenData = await loginResponse.json()
          if (tokenData.access_token) {
            // Store backend JWT token for admin API calls
            localStorage.setItem('trdrhub_api_token', tokenData.access_token)
          }
        }
      } catch (backendLoginError) {
        // Non-critical - Supabase login succeeded, backend login is optional
        console.warn('Backend login failed (non-critical):', backendLoginError)
      }
      
      const profile = await fetchUserProfile()
      return profile
    } finally {
      setIsLoading(false)
    }
  }

  const loginWithGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined,
      },
    })
  }

  const registerWithEmail = async (
    email: string,
    password: string,
    fullName: string,
    role: string
  ): Promise<User> => {
    setIsLoading(true)
    try {
      // Create user in Supabase with metadata
      const { data, error } = await withTimeout(
        supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName, role },
        },
        }),
        'Sign up'
      )
      if (error) {
        // Handle specific Supabase error codes
        if (error.message?.includes('signup_disabled') || error.message?.includes('Signup is disabled')) {
          throw new Error('User registration is currently disabled. Please contact support or enable signup in Supabase settings.')
        }
        throw error
      }

      // Ensure we have a session (if confirm email is off this should exist; else sign in)
      let session = (await supabase.auth.getSession()).data.session
      if (!session) {
        const { error: signInErr } = await withTimeout(
          supabase.auth.signInWithPassword({ email, password }),
          'Signing in'
        )
        if (signInErr) throw signInErr
        session = (await supabase.auth.getSession()).data.session
      }

      if (!session) throw new Error('Authentication session not established after sign up')

      // Create user in backend database
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const registerResponse = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            role,
          }),
        })

        if (!registerResponse.ok) {
          const errorData = await registerResponse.json().catch(() => ({ detail: 'Backend registration failed' }))
          // If user already exists, that's okay - continue
          if (registerResponse.status !== 400 || !errorData.detail?.includes('already registered')) {
            console.warn('Backend registration failed (non-critical):', errorData.detail || 'Unknown error')
            // Continue anyway - user might have been created via webhook or already exists
          }
        }
      } catch (backendError) {
        // Non-critical - Supabase user is created, backend user might exist or be created later
        console.warn('Backend registration error (non-critical):', backendError)
      }

      const profile = await fetchUserProfile()
      return profile
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    await supabase.auth.signOut()
    setUser(null)
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  const refreshUser = async () => {
    setIsLoading(true)
    try {
      await fetchUserProfile()
    } finally {
      setIsLoading(false)
    }
  }

  const hasRole = (role: Role | Role[]) => {
    if (!user) return false
    if (Array.isArray(role)) {
      return role.includes(user.role)
    }
    return user.role === role
  }

  const value = { user, isLoading, loginWithEmail, loginWithGoogle, registerWithEmail, logout, hasRole, refreshUser }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = React.useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}