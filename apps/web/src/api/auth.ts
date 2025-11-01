import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const TOKEN_STORAGE_KEY = import.meta.env.VITE_TOKEN_STORAGE_KEY || 'lcopilot_token'

const authApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: 'exporter' | 'importer' | 'bank_officer' | 'bank_admin' | 'system_admin' // Optional, defaults to 'exporter'
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  role: string
}

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export const login = async (credentials: LoginRequest): Promise<AuthResponse> => {
  const response = await authApi.post('/auth/login', credentials)
  return response.data
}

export const register = async (userInfo: RegisterRequest): Promise<UserResponse> => {
  const response = await authApi.post('/auth/register', userInfo)
  return response.data
}

export const getCurrentUser = async (): Promise<UserResponse> => {
  const token = getStoredToken()
  if (!token) {
    throw new Error('No token found')
  }
  const response = await authApi.get('/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  return response.data
}

// Development helper functions (guarded; never runs in production)
const enableDevBootstrap = (
  import.meta.env.MODE !== 'production' &&
  import.meta.env.VITE_ENABLE_DEV_BOOTSTRAP === 'true'
)

export const getDevToken = async (): Promise<string> => {
  if (!enableDevBootstrap) {
    throw new Error('Dev bootstrap disabled')
  }
  try {
    // Try to login with development user
    const response = await login({
      email: 'test2@example.com',
      password: 'password'
    })
    return response.access_token
  } catch (error) {
    // If login fails, create a new dev user
    try {
      await register({
        email: 'dev@lcopilot.com',
        password: 'devpassword',
        full_name: 'Development User',
        // role defaults to exporter
      })
      // Login with new user
      const response = await login({
        email: 'dev@lcopilot.com',
        password: 'devpassword'
      })
      return response.access_token
    } catch (registerError) {
      console.error('Failed to create development user:', registerError)
      throw new Error('Could not authenticate development user')
    }
  }
}

// Token storage utilities
export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export const storeToken = (token: string): void => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export const getValidToken = async (): Promise<string> => {
  const stored = getStoredToken()
  if (stored) {
    // TODO: Add token validation/expiry check
    return stored
  }

  // In production (or when dev bootstrap disabled), do not auto-create/login
  if (!enableDevBootstrap) {
    throw new Error('No token available')
  }

  // Get new development token (dev only)
  const token = await getDevToken()
  storeToken(token)
  return token
}
