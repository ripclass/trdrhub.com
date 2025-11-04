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

    const session = await supabase.auth.getSession()
    const token = session.data.session?.access_token

    if (token) {
      const headers = (config.headers ?? {}) as Record<string, string>
      headers.Authorization = `Bearer ${token}`
      config.headers = headers as any
    }

    // Add CSRF token for state-changing methods
    if (config.method && requiresCsrfToken(config.method)) {
      const csrfToken = getCsrfToken()
      if (csrfToken) {
        const headers = (config.headers ?? {}) as Record<string, string>
        headers['X-CSRF-Token'] = csrfToken
        config.headers = headers as any
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
    } else if (error?.response?.status === 403 && error?.response?.data?.code?.startsWith('csrf_')) {
      // CSRF token error - try to refresh token
      const { fetchCsrfToken } = await import('@/lib/csrf')
      try {
        await fetchCsrfToken(API_BASE_URL_VALUE)
        // Retry the original request
        const config = error.config
        if (config) {
          const csrfToken = getCsrfToken()
          if (csrfToken && config.method && requiresCsrfToken(config.method)) {
            config.headers = config.headers || {}
            config.headers['X-CSRF-Token'] = csrfToken
            return api.request(config)
          }
        }
      } catch (csrfError) {
        console.error('Failed to refresh CSRF token:', csrfError)
      }
    }
    return Promise.reject(error)
  }
)

export { api }
export const API_BASE_URL = api.defaults.baseURL || API_BASE_URL_VALUE
