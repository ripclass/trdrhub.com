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
  loginWithAuth0: () => Promise<void>
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

  const loginWithAuth0 = async () => {
    // Direct Auth0 login - bypass Supabase
    const AUTH0_DOMAIN = import.meta.env.VITE_AUTH0_DOMAIN || 'dev-2zhljb8cf2kc2h5t.us.auth0.com'
    const AUTH0_CLIENT_ID = import.meta.env.VITE_AUTH0_CLIENT_ID
    const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE
    
    if (!AUTH0_CLIENT_ID) {
      throw new Error('Auth0 Client ID not configured. Please set VITE_AUTH0_CLIENT_ID environment variable.')
    }
    
    // Redirect to Auth0 login
    const redirectUri = typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined
    const auth0LoginUrl = `https://${AUTH0_DOMAIN}/authorize?` +
      `client_id=${AUTH0_CLIENT_ID}` +
      `&redirect_uri=${encodeURIComponent(redirectUri || '')}` +
      `&response_type=code` +
      `&scope=openid profile email` +
      (AUTH0_AUDIENCE ? `&audience=${encodeURIComponent(AUTH0_AUDIENCE)}` : '')
    
    if (typeof window !== 'undefined') {
      window.location.href = auth0LoginUrl
    }
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
      if (error) throw error

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

  const value = { user, isLoading, loginWithEmail, loginWithGoogle, loginWithAuth0, registerWithEmail, logout, hasRole, refreshUser }

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