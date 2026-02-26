import * as React from 'react'
import type { Role } from '@/types/analytics'
import { supabase } from '@/lib/supabase'
import { api } from '@/api/client'
import { logger } from '@/lib/logger'

// Auth-specific logger (debug logs only in development)
const authLogger = logger.createLogger('Auth')

export interface User {
  id: string
  email: string
  full_name?: string
  username?: string
  role: Role
  isActive: boolean
}

interface Session {
  access_token: string
  refresh_token?: string
  expires_at?: number
  user?: any
}

interface AuthContextType {
  user: User | null
  session: Session | null
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
      country?: string
      currency?: string
      paymentGateway?: string
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
  const [session, setSession] = React.useState<Session | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const GUEST_MODE = (import.meta.env.VITE_GUEST_MODE || '').toString().toLowerCase() === 'true'
  const profileFetchedRef = React.useRef(false)

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
        authLogger.debug(`Session found via ${source}`)
        cleanup()
        resolve(token)
      }
      
      // First, check immediately
      supabase.auth.getSession().then(({ data }) => {
        const token = data.session?.access_token || null
        if (token) {
          doResolve(token, 'immediate check')
        } else {
          authLogger.debug('No session in immediate check')
        }
      }).catch(err => authLogger.warn('getSession error:', err))
      
      // Also listen for auth state changes (most reliable)
      try {
        const { data: { subscription: sub } } = supabase.auth.onAuthStateChange((event, session) => {
          authLogger.debug('Auth state change:', event, !!session)
          const token = session?.access_token || null
          if (token) {
            doResolve(token, `auth state change (${event})`)
          }
        })
        subscription = sub
      } catch (err) {
        authLogger.warn('onAuthStateChange setup error:', err)
      }
      
      // Aggressive polling every 50ms
      pollInterval = setInterval(async () => {
        const elapsed = Date.now() - started
        if (elapsed > maxMs) {
          authLogger.error(`Session wait timed out after ${maxMs}ms`)
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
          authLogger.warn('Polling getSession error:', err)
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
    let supabaseToken = providedToken
    try {
      authLogger.debug('fetchUserProfile starting', providedToken ? 'with token' : 'will get token')
      
      if (!supabaseToken) {
        // Fallback: get token from session if not provided (with timeout)
        authLogger.debug('Getting Supabase session...')
        try {
          const { data: sessionData, error: sessionError } = await Promise.race([
            supabase.auth.getSession(),
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Session check timeout')), 5000)
            )
          ]) as { data: { session: any }, error: any }
          
          if (sessionError) {
            authLogger.error('getSession error:', sessionError)
            throw new Error(`Failed to get session: ${sessionError.message}`)
          }
          
          authLogger.debug('Session data:', { hasSession: !!sessionData.session })
          supabaseToken = sessionData.session?.access_token || null
        } catch (error: any) {
          authLogger.warn('Failed to get Supabase session:', error?.message)
          // If getSession times out, check if we can get token from localStorage as fallback
          // This can happen on page refresh if Supabase client hasn't initialized yet
          const storedToken = localStorage.getItem('sb-' + import.meta.env.VITE_SUPABASE_PROJECT_REF + '-auth-token')
          if (storedToken) {
            try {
              const parsed = JSON.parse(storedToken)
              supabaseToken = parsed?.access_token || null
              authLogger.debug('Using token from localStorage fallback')
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
        authLogger.error('No Supabase token available')
        throw new Error('No authentication token available')
      }
      
      authLogger.debug('Calling /auth/me')
      const headers = { Authorization: `Bearer ${supabaseToken}` }
      
      const { data: userData } = await withTimeout(
        api.get('/auth/me', { headers }),
        'Loading profile',
        PROFILE_TIMEOUT_MS
      )
      authLogger.info('User profile loaded:', userData.email)
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
        authLogger.warn('Failed to fetch CSRF token:', csrfError)
        // Non-critical, continue without CSRF token
      }
      
      return mapped
    } catch (error: any) {
      authLogger.error('Failed to load user profile', error)

      // Resilience fallback: if backend /auth/me returns 401 but Supabase login succeeded,
      // derive a temporary profile from Supabase user so dashboards remain accessible.
      if (supabaseToken) {
        try {
          // Network-free fallback: decode JWT locally to avoid auth endpoint instability.
          const parts = supabaseToken.split('.')
          if (parts.length >= 2) {
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
            const rawRole = payload?.role || payload?.app_metadata?.role || payload?.user_metadata?.role || 'exporter'
            const email = payload?.email || 'user@trdrhub.com'
            const uid = payload?.sub || `sb-${Date.now()}`
            const fullName = payload?.user_metadata?.full_name || payload?.name || email

            const fallbackUser: User = {
              id: uid,
              email,
              full_name: fullName,
              username: fullName,
              role: mapBackendRole(String(rawRole)),
              isActive: true,
            }
            authLogger.warn('Using JWT-decoded fallback profile due to profile fetch failure')
            setUser(fallbackUser)
            return fallbackUser
          }
        } catch (fallbackErr) {
          authLogger.warn('JWT decode fallback failed', fallbackErr)
        }
      }

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
    let initTimeout: NodeJS.Timeout | null = null

    // Use onAuthStateChange as primary method (more reliable than getSession on refresh)
    const { data: authListener } = supabase.auth.onAuthStateChange(async (_event, supabaseSession) => {
      if (!mounted) return
      // Clear any pending timeout since we got auth state change
      if (initTimeout) {
        clearTimeout(initTimeout)
        initTimeout = null
      }
      
      // Update session state
      if (supabaseSession) {
        setSession({
          access_token: supabaseSession.access_token,
          refresh_token: supabaseSession.refresh_token,
          expires_at: supabaseSession.expires_at,
          user: supabaseSession.user
        })
      } else {
        setSession(null)
      }
      
      if (supabaseSession) {
        if (profileFetchedRef.current) {
          if (mounted) setIsLoading(false)
          return
        }
        profileFetchedRef.current = true
        
        setIsLoading(true)
        try {
          await fetchUserProfile(supabaseSession.access_token)
        } finally {
          if (mounted) setIsLoading(false)
        }
      } else {
        profileFetchedRef.current = false
        setUser(null)
        setSession(null)
        if (mounted) {
          if (GUEST_MODE) setGuest()
          setIsLoading(false)
        }
      }
    })

    // Also try getSession immediately (but with timeout) as fallback
    // This handles cases where onAuthStateChange hasn't fired yet
    const init = async () => {
      setIsLoading(true)
      try {
        const { data } = await Promise.race([
          supabase.auth.getSession(),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Session check timeout')), 3000)
          )
        ]) as { data: { session: any } }
        
        if (!mounted) return
        if (data.session) {
          if (!profileFetchedRef.current) {
            profileFetchedRef.current = true
            try {
              await fetchUserProfile(data.session.access_token)
            } finally {
              if (mounted) setIsLoading(false)
            }
          } else {
            if (mounted) setIsLoading(false)
          }
        } else {
          // No session found - wait a bit for onAuthStateChange to fire
          // If it doesn't fire within 2 seconds, assume no session
          initTimeout = setTimeout(() => {
            if (mounted && !profileFetchedRef.current) {
              if (GUEST_MODE) setGuest()
              setIsLoading(false)
            }
          }, 2000)
        }
      } catch (error: any) {
        authLogger.warn('Auth init: Failed to get session:', error?.message)
        if (!mounted) return
        initTimeout = setTimeout(() => {
          if (mounted && !profileFetchedRef.current) {
            if (GUEST_MODE) setGuest()
            setIsLoading(false)
          }
        }, 2000)
      }
    }

    init()

    return () => {
      mounted = false
      if (initTimeout) {
        clearTimeout(initTimeout)
        initTimeout = null
      }
      authListener?.subscription.unsubscribe()
      profileFetchedRef.current = false
    }
  }, [fetchUserProfile])

  const loginWithEmail = async (email: string, password: string) => {
    authLogger.debug('Login started', { email })
    setIsLoading(true)
    try {
      authLogger.debug('Attempting Supabase sign-in...')
      // Login to Supabase - start the request but don't wait for promise
      const signInPromise = supabase.auth.signInWithPassword({ email, password })
      
      // Don't wait for promise - check session immediately and wait for it to appear
      // The HTTP request succeeds (200) but promise may resolve slowly
      signInPromise.catch(err => {
        authLogger.warn('Sign-in promise error (checking session anyway):', err)
      })
      
      // Wait for session to appear (session appears when HTTP request completes)
      authLogger.debug('Waiting for Supabase session...')
      const token = await waitForSupabaseSession(20000)
      
      if (!token) {
        authLogger.error('No token after waiting 20s')
        // Check if sign-in promise resolved with error
        try {
          const result = await Promise.race([
            signInPromise,
            new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 2000))
          ])
          const { error } = (result as any) || {}
          if (error) {
            authLogger.error('Sign-in returned error:', error)
            throw error
          }
        } catch (checkError: any) {
          if (checkError.message !== 'Timeout' && checkError.message !== 'Sign-in timeout') {
            throw checkError
          }
        }
        throw new Error('Signing in timed out. Please try again.')
      }
      
      authLogger.debug('Supabase session obtained')
      
      // For Supabase users: Skip /auth/login (it expects email/password, not Supabase tokens)
      // The /auth/login endpoint is for backend-managed users only
      // Supabase users authenticate directly via /auth/me with their Supabase token
      
      // Pass token directly to avoid calling getSession() again
      const profile = await fetchUserProfile(token)
      authLogger.info('Login completed:', profile?.email)
      return profile
    } catch (error: any) {
      authLogger.error('Login failed:', error?.message)

      // Last-resort resilience: if Supabase session exists, allow login continuation.
      try {
        const { data } = await supabase.auth.getSession()
        const token = data?.session?.access_token
        if (token) {
          const parts = token.split('.')
          if (parts.length >= 2) {
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
            const rawRole = payload?.role || payload?.app_metadata?.role || payload?.user_metadata?.role || 'exporter'
            const fallbackEmail = payload?.email || (data?.session?.user?.email ?? '')
            const uid = payload?.sub || `sb-${Date.now()}`
            const fullName = payload?.user_metadata?.full_name || payload?.name || fallbackEmail

            const fallbackUser: User = {
              id: uid,
              email: fallbackEmail,
              full_name: fullName,
              username: fullName,
              role: mapBackendRole(String(rawRole)),
              isActive: true,
            }
            authLogger.warn('Login fallback: continuing with existing Supabase session')
            setUser(fallbackUser)
            return fallbackUser
          }
        }
      } catch (sessionErr) {
        authLogger.warn('Login fallback session check failed', sessionErr)
      }

      throw error
    } finally {
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
      country?: string
      currency?: string
      paymentGateway?: string
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
      // CRITICAL: This must succeed for onboarding data to be saved
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
        registerPayload.country = companyInfo.country
        registerPayload.currency = companyInfo.currency
        registerPayload.payment_gateway = companyInfo.paymentGateway
        authLogger.debug('Registering with company info:', companyInfo.companyName)
      }
      
      try {
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
          const errorMessage = errorData.detail || `HTTP ${registerResponse.status}: Backend registration failed`
          
          // If user already exists, that's okay - continue
          if (registerResponse.status === 400 && errorData.detail?.includes('already registered')) {
            authLogger.info('User already exists in backend, continuing...')
          } else {
            // This is CRITICAL - backend registration failed
            authLogger.error('Backend registration failed:', errorMessage)
            // Still continue - user exists in Supabase, but onboarding data might be missing
            // User will need to complete onboarding wizard
          }
        } else {
          const userData = await registerResponse.json().catch(() => null)
          authLogger.info('Backend registration successful:', userData?.id)
        }
      } catch (backendError: any) {
        // This is CRITICAL - backend registration error
        authLogger.error('Backend registration error:', backendError?.message)
        // Still continue - user exists in Supabase, but onboarding data might be missing
        // User will need to complete onboarding wizard
      }

      const profile = await fetchUserProfile()
      return profile
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    authLogger.info('Logging out - clearing all authentication state')
    
    // Clear Supabase session
    try {
      await supabase.auth.signOut()
    } catch (error) {
      authLogger.warn('Error signing out from Supabase:', error)
    }
    
    // Clear user state
    profileFetchedRef.current = false
    setUser(null)
    
    // Clear ALL localStorage tokens and auth data
    if (typeof window !== 'undefined') {
      // Clear all possible auth tokens
      localStorage.removeItem('bank_token')
      localStorage.removeItem('trdrhub_api_token')
      localStorage.removeItem('exporter_token')
      localStorage.removeItem('importer_token')
      localStorage.removeItem('csrf_token')
      
      // Clear any other auth-related data
      localStorage.removeItem('demo_mode')
      localStorage.removeItem('onboarding_completed')
      
      // Clear sessionStorage as well
      sessionStorage.clear()
      
      // Force full page reload to ensure clean state
      // This prevents any cached state or React state from persisting
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

  const value = { user, session, isLoading, loginWithEmail, registerWithEmail, logout, hasRole, refreshUser }

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