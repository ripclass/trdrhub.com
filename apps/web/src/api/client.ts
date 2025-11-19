import axios from 'axios'
import { supabase } from '@/lib/supabase'
import { clearSupabaseSession } from './auth'
import { getCsrfToken, requiresCsrfToken } from '@/lib/csrf'

const resolveApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl
  }

  if (typeof window !== 'undefined') {
    const { hostname, protocol } = window.location
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1'

    if (isLocalhost) {
      // Local development fallback
      return 'http://localhost:8000'
    }

    // Production/previews fallback
    if (hostname.endsWith('trdrhub.com') || hostname.endsWith('.vercel.app')) {
      return 'https://trdrhub-api.onrender.com'
    }

    // Generic HTTPS fallback to avoid mixed-content issues
    if (protocol === 'https:') {
      return 'https://trdrhub-api.onrender.com'
    }
  }

  // Default fallback (node/server contexts)
  return 'https://trdrhub-api.onrender.com'
}

const API_BASE_URL_VALUE = resolveApiBaseUrl()
const GUEST_MODE = (import.meta.env.VITE_GUEST_MODE || '').toString().toLowerCase() === 'true'
const AUTH_FREE_PATHS = ['/auth/login', '/auth/register']

const DEFAULT_TIMEOUT_MS = 30000
const LONG_REQUEST_TIMEOUT_MS = 180000
const LONG_REQUEST_PATHS = ['/api/validate', '/api/legacy_validate', '/api/legacy-validate']

const api = axios.create({
  baseURL: API_BASE_URL_VALUE,
  timeout: DEFAULT_TIMEOUT_MS,
  withCredentials: true, // Include cookies for CSRF token
})

api.interceptors.request.use(
  async (config) => {
    const urlPath = (config.url || '').toLowerCase()
    
    // If Authorization header is already provided by the caller, skip token resolution
    const existingAuth =
      (config.headers as any)?.Authorization ||
      (config.headers as any)?.authorization
    if (existingAuth) {
      return config
    }
    
    if (AUTH_FREE_PATHS.some((path) => urlPath.startsWith(path))) {
      return config
    }

    if (LONG_REQUEST_PATHS.some((path) => urlPath.startsWith(path))) {
      config.timeout = LONG_REQUEST_TIMEOUT_MS
    }

    // For admin endpoints, prefer backend JWT token over Supabase token
    // Admin endpoints require backend JWT tokens, not Supabase tokens
    let token: string | null = null
    
    if (typeof window !== 'undefined') {
      // Check if this is an admin endpoint
      const isAdminEndpoint = urlPath.startsWith('/admin')
      
      if (isAdminEndpoint) {
        // For admin endpoints, prioritize backend JWT token
        const apiToken = localStorage.getItem('trdrhub_api_token')
        if (apiToken) {
          token = apiToken
        } else {
          // Fallback to Supabase token if backend token not available
          const session = await supabase.auth.getSession()
          token = session.data.session?.access_token || null
        }
      } else {
        // For non-admin endpoints, try Supabase first, then backend token
        const session = await supabase.auth.getSession()
        token = session.data.session?.access_token || null
        
        if (!token) {
          const apiToken = localStorage.getItem('trdrhub_api_token')
          if (apiToken) {
            token = apiToken
          }
        }
      }
    }

    if (token) {
      const headers = (config.headers ?? {}) as Record<string, string>
      headers.Authorization = `Bearer ${token}`
      config.headers = headers as any
    } else if (urlPath.startsWith('/admin')) {
      // Log warning for admin endpoints without token
      console.warn('Admin endpoint called without authentication token:', config.url)
      console.warn('Please log in via /login page to get backend JWT token')
    }

    // Add org param for bank endpoints
    if (urlPath.startsWith('/bank') && typeof window !== 'undefined') {
      const url = new URL(window.location.href)
      const orgParam = url.searchParams.get('org')
      if (orgParam && config.params) {
        config.params = { ...config.params, org: orgParam }
      } else if (orgParam) {
        config.params = { org: orgParam }
      }
    }

    // Add locale header for i18n
    if (typeof window !== 'undefined') {
      const lang = localStorage.getItem('i18nextLng') || 'en'
      const headers = (config.headers ?? {}) as Record<string, string>
      headers['Accept-Language'] = lang
      config.headers = headers as any
    }

    // Add CSRF token for state-changing methods
    if (config.method && requiresCsrfToken(config.method)) {
      let csrfToken = getCsrfToken()
      
      // If no CSRF token found, try to fetch one before making the request
      if (!csrfToken) {
        try {
          const { fetchCsrfToken } = await import('@/lib/csrf')
          csrfToken = await fetchCsrfToken(API_BASE_URL_VALUE)
        } catch (error) {
          console.warn('Failed to fetch CSRF token:', error)
        }
      }
      
      if (csrfToken) {
        const headers = (config.headers ?? {}) as Record<string, string>
        headers['X-CSRF-Token'] = csrfToken
        config.headers = headers as any
      } else {
        console.warn('CSRF token not available for', config.method, config.url)
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const urlPath = (error?.config?.url || '').toLowerCase()
    const isAdminEndpoint = urlPath.startsWith('/admin')

    if (error?.response?.status === 401) {
      // In guest mode, do not redirect on 401; allow pages to continue.
      if (!GUEST_MODE) {
        const currentPath = typeof window !== 'undefined' ? window.location.pathname : ''
        const onAdminRoute = currentPath.startsWith('/admin')

        if (isAdminEndpoint || onAdminRoute) {
          // Admin endpoints use backend JWT, so clear that token specifically
          if (typeof window !== 'undefined') {
            localStorage.removeItem('trdrhub_api_token')
            if (!currentPath.startsWith('/admin/login')) {
              window.location.href = '/admin/login'
            }
          }
        } else {
          clearSupabaseSession()
          if (typeof window !== 'undefined' && !currentPath.startsWith('/login')) {
            window.location.href = '/login'
          }
        }
      }
    } else if (error?.response?.status === 403) {
      // Check if it's a CSRF error or auth error
      const errorCode = error?.response?.data?.code || ''
      const errorDetail = error?.response?.data?.detail || ''
      
      if (errorCode.startsWith('csrf_') || errorDetail.includes('CSRF')) {
        // CSRF token error - try to refresh token and retry
        const { fetchCsrfToken } = await import('@/lib/csrf')
        try {
          const newToken = await fetchCsrfToken(API_BASE_URL_VALUE)
          // Retry the original request
          const config = error.config
          if (config && newToken) {
            config.headers = config.headers || {}
            if (config.method && requiresCsrfToken(config.method)) {
              config.headers['X-CSRF-Token'] = newToken
            }
            return api.request(config)
          }
        } catch (csrfError) {
          console.error('Failed to refresh CSRF token:', csrfError)
        }
      } else if (errorDetail.includes('Not authenticated') || errorDetail.includes('Authentication failed')) {
        // Authentication error - redirect to login if not already there
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          console.error('403 Forbidden: Not authenticated. Please log in.')
          // Don't auto-redirect for admin pages - let the component handle it
          // window.location.href = '/login'
        }
      } else {
        // Other 403 error - log for debugging
        console.error('403 Forbidden:', errorDetail || errorCode)
      }
    }
    return Promise.reject(error)
  }
)

export { api }
export const API_BASE_URL = api.defaults.baseURL || API_BASE_URL_VALUE
