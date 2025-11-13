import axios from 'axios'
import { supabase } from '@/lib/supabase'
import { clearSupabaseSession } from './auth'
import { getCsrfToken, requiresCsrfToken } from '@/lib/csrf'

const API_BASE_URL_VALUE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GUEST_MODE = (import.meta.env.VITE_GUEST_MODE || '').toString().toLowerCase() === 'true'
const AUTH_FREE_PATHS = ['/auth/login', '/auth/register']

const api = axios.create({
  baseURL: API_BASE_URL_VALUE,
  timeout: 30000,
  withCredentials: true, // Include cookies for CSRF token
})

api.interceptors.request.use(
  async (config) => {
    const urlPath = (config.url || '').toLowerCase()
    if (AUTH_FREE_PATHS.some((path) => urlPath.startsWith(path))) {
      return config
    }

    // Try Supabase session first
    const session = await supabase.auth.getSession()
    let token = session.data.session?.access_token

    // Fallback to API token from localStorage (for testing/direct API auth)
    if (!token && typeof window !== 'undefined') {
      const apiToken = localStorage.getItem('trdrhub_api_token')
      if (apiToken) {
        token = apiToken
      }
    }

    if (token) {
      const headers = (config.headers ?? {}) as Record<string, string>
      headers.Authorization = `Bearer ${token}`
      config.headers = headers as any
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
    if (error?.response?.status === 401) {
      // In guest mode, do not redirect on 401; allow pages to continue.
      if (!GUEST_MODE) {
        clearSupabaseSession()
        if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login'
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
      } else {
        // Auth error - log for debugging
        console.error('403 Forbidden:', errorDetail || errorCode)
      }
    }
    return Promise.reject(error)
  }
)

export { api }
export const API_BASE_URL = api.defaults.baseURL || API_BASE_URL_VALUE
