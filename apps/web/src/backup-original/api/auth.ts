import axios from 'axios'

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

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
  organization: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  full_name: string
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

// Development helper functions
export const getDevToken = async (): Promise<string> => {
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
        organization: 'LCopilot Dev'
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
  return localStorage.getItem('lcopilot_token')
}

export const storeToken = (token: string): void => {
  localStorage.setItem('lcopilot_token', token)
}

export const clearToken = (): void => {
  localStorage.removeItem('lcopilot_token')
}

export const getValidToken = async (): Promise<string> => {
  const stored = getStoredToken()
  if (stored) {
    // TODO: Add token validation/expiry check
    return stored
  }
  
  // Get new development token
  const token = await getDevToken()
  storeToken(token)
  return token
}