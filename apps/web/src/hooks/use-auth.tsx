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
  registerWithEmail: (
    email: string,
    password: string,
    fullName: string,
    role: string,
    companyInfo?: {
      companyName?: string
      companyType?: string
      companySize?: string
      businessTypes?: string[]
    }
  ) => Promise<User>
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

  // Default timeouts
  const AUTH_TIMEOUT_MS = 10000
  const SIGNIN_TIMEOUT_MS = 45000
  const PROFILE_TIMEOUT_MS = 20000

  const waitForSupabaseSession = async (maxMs = 20000): Promise<string | null> => {
    return new Promise((resolve) => {
      const started = Date.now()
      let resolved = false
      let subscription: any = null
      let pollInterval: any = null
      
      const cleanup = () => {
        if (subscription) {
          try {
            subscription.unsubscribe()
          } catch (e) {
            // Ignore unsubscribe errors
          }
        }
        if (pollInterval) {
          clearInterval(pollInterval)
        }
      }
      
      const doResolve = (token: string, source: string) => {
        if (resolved) return
        resolved = true
        console.log(`✓ Session found via ${source}`)
        cleanup()
        resolve(token)
      }
      
      // First, check immediately
      supabase.auth.getSession().then(({ data }) => {
        const token = data.session?.access_token || null
        if (token) {
          doResolve(token, 'immediate check')
        } else {
          console.log('No session in immediate check')
        }
      }).catch(err => console.warn('getSession error:', err))
      
      // Also listen for auth state changes (most reliable)
      try {
        const { data: { subscription: sub } } = supabase.auth.onAuthStateChange((event, session) => {
          console.log('Auth state change event:', event, 'hasSession:', !!session)
          const token = session?.access_token || null
          if (token) {
            doResolve(token, `auth state change (${event})`)
          }
        })
        subscription = sub
      } catch (err) {
        console.warn('onAuthStateChange setup error:', err)
      }
      
      // Aggressive polling every 50ms
      pollInterval = setInterval(async () => {
        const elapsed = Date.now() - started
        if (elapsed > maxMs) {
          console.error(`✗ Session wait timed out after ${maxMs}ms`)
          cleanup()
          if (!resolved) resolve(null)
          return
        }
        
        try {
          const { data } = await supabase.auth.getSession()
          const token = data.session?.access_token || null
          if (token) {
            doResolve(token, `polling (${elapsed}ms)`)
          }
        } catch (err) {
          console.warn('Polling getSession error:', err)
        }
      }, 50)
    })
  }

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

  const fetchUserProfile = React.useCallback(async (providedToken?: string) => {
    try {
      console.log('fetchUserProfile: Starting...', providedToken ? 'with provided token' : 'will get token')
      
      let supabaseToken = providedToken
      
      if (!supabaseToken) {
        // Fallback: get token from session if not provided (with timeout)
        console.log('fetchUserProfile: Getting Supabase session...')
        try {
          const { data: sessionData, error: sessionError } = await Promise.race([
            supabase.auth.getSession(),
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Session check timeout')), 5000)
            )
          ]) as { data: { session: any }, error: any }
          
          if (sessionError) {
            console.error('fetchUserProfile: getSession error:', sessionError)
            throw new Error(`Failed to get session: ${sessionError.message}`)
          }
          
          console.log('fetchUserProfile: Session data:', { hasSession: !!sessionData.session, hasToken: !!sessionData.session?.access_token })
          supabaseToken = sessionData.session?.access_token || null
        } catch (error: any) {
          console.warn('fetchUserProfile: Failed to get Supabase session:', error?.message || error)
          // If getSession times out, check if we can get token from localStorage as fallback
          // This can happen on page refresh if Supabase client hasn't initialized yet
          const storedToken = localStorage.getItem('sb-' + import.meta.env.VITE_SUPABASE_PROJECT_REF + '-auth-token')
          if (storedToken) {
            try {
              const parsed = JSON.parse(storedToken)
              supabaseToken = parsed?.access_token || null
              console.log('fetchUserProfile: Using token from localStorage fallback')
            } catch {
              // Ignore parse errors
            }
          }
          if (!supabaseToken) {
            throw new Error('Session check timeout - please try logging in again')
          }
        }
      }
      
      if (!supabaseToken) {
        console.error('fetchUserProfile: No Supabase token available for /auth/me')
        throw new Error('No authentication token available')
      }
      
      console.log('fetchUserProfile: Calling /auth/me with token:', supabaseToken.substring(0, 20) + '...')
      const headers = { Authorization: `Bearer ${supabaseToken}` }
      
      console.log('fetchUserProfile: Making API request to /auth/me...')
      const { data: userData } = await withTimeout(
        api.get('/auth/me', { headers }),
        'Loading profile',
        PROFILE_TIMEOUT_MS
      )
      console.log('fetchUserProfile: API response received:', userData)
      console.log('Successfully fetched user profile:', userData.email)
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
    console.log('=== LOGIN START ===', { email })
    setIsLoading(true)
    try {
      console.log('Attempting Supabase sign-in...')
      // Login to Supabase - start the request but don't wait for promise
      const signInPromise = supabase.auth.signInWithPassword({ email, password })
      console.log('Sign-in request started, checking for session...')
      
      // Don't wait for promise - check session immediately and wait for it to appear
      // The HTTP request succeeds (200) but promise may resolve slowly
      signInPromise.catch(err => {
        console.warn('Sign-in promise error (checking session anyway):', err)
      })
      
      // Wait for session to appear (session appears when HTTP request completes)
      console.log('Waiting for Supabase session to appear...')
      const token = await waitForSupabaseSession(20000)
      
      if (!token) {
        console.error('No token after waiting 20s')
        // Check if sign-in promise resolved with error
        try {
          const result = await Promise.race([
            signInPromise,
            new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 2000))
          ])
          const { error } = (result as any) || {}
          if (error) {
            console.error('Sign-in returned error:', error)
            throw error
          }
        } catch (checkError: any) {
          if (checkError.message !== 'Timeout' && checkError.message !== 'Sign-in timeout') {
            throw checkError
          }
        }
        throw new Error('Signing in timed out. Please try again.')
      }
      
      console.log('Supabase session obtained, token:', token.substring(0, 20) + '...')
      
      // For Supabase users: Skip /auth/login (it expects email/password, not Supabase tokens)
      // The /auth/login endpoint is for backend-managed users only
      // Supabase users authenticate directly via /auth/me with their Supabase token
      
      console.log('Calling fetchUserProfile() with Supabase token...')
      console.log('Token available:', token ? 'YES' : 'NO')
      // Pass token directly to avoid calling getSession() again
      const profile = await fetchUserProfile(token)
      console.log('fetchUserProfile completed, profile:', profile?.email || 'NO PROFILE')
      return profile
    } catch (error: any) {
      console.error('=== LOGIN ERROR ===', error)
      console.error('Error message:', error?.message)
      console.error('Error stack:', error?.stack)
      throw error
    } finally {
      console.log('=== LOGIN FINALLY ===')
      setIsLoading(false)
    }
  }

  const registerWithEmail = async (
    email: string,
    password: string,
    fullName: string,
    role: string,
    companyInfo?: {
      companyName?: string
      companyType?: string
      companySize?: string
      businessTypes?: string[]
    }
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

      // Create user in backend database with company info
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const registerPayload: any = {
          email,
          password,
          full_name: fullName,
          role,
        }
        
        // Add company info if provided
        if (companyInfo?.companyName) {
          registerPayload.company_name = companyInfo.companyName
          registerPayload.company_type = companyInfo.companyType
          registerPayload.company_size = companyInfo.companySize
          registerPayload.business_types = companyInfo.businessTypes
        }
        
        const registerResponse = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(registerPayload),
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

  const value = { user, isLoading, loginWithEmail, registerWithEmail, logout, hasRole, refreshUser }

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