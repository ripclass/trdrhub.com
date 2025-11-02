import * as React from 'react'
import type { Role } from '@/types/analytics'
import {
  getCurrentUser,
  signInWithEmail,
  signInWithGoogle,
  signOut as supabaseSignOut,
} from '@/api/auth'
import { supabase } from '@/lib/supabase'

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

  const fetchUserProfile = React.useCallback(async () => {
    try {
      const userData = await getCurrentUser()
      const mapped: User = {
        id: userData.id,
        email: userData.email,
        full_name: userData.full_name,
        username: userData.full_name,
        role: mapBackendRole(userData.role),
        isActive: userData.is_active,
      }
      setUser(mapped)
      return mapped
    } catch (error) {
      console.error('Failed to load user profile', error)
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
      await signInWithEmail(email, password)
      const profile = await fetchUserProfile()
      return profile
    } finally {
      setIsLoading(false)
    }
  }

  const loginWithGoogle = async () => {
    await signInWithGoogle()
  }

  const logout = async () => {
    await supabaseSignOut()
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

  const value = { user, isLoading, loginWithEmail, loginWithGoogle, logout, hasRole, refreshUser }

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