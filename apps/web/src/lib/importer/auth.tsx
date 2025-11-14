/**
 * Importer Authentication Hook and Context
 *
 * Compatibility layer that proxies to the Supabase-backed AuthProvider.
 */

import React, { createContext, useContext, useMemo, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'

interface ImporterUser {
  id: string
  name: string
  email: string
  role: 'importer' | 'tenant_admin'
}

interface ImporterAuthContext {
  user: ImporterUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const ImporterAuthContext = createContext<ImporterAuthContext | undefined>(undefined)

interface ImporterAuthProviderProps {
  children: ReactNode
}

export function ImporterAuthProvider({ children }: ImporterAuthProviderProps) {
  const navigate = useNavigate()
  const auth = useAuth()

  const importerUser = useMemo<ImporterUser | null>(() => {
    if (!auth.user) return null

    const normalizedRole =
      auth.user.role === 'tenant_admin' ? 'tenant_admin' : 'importer'

    return {
      id: auth.user.id,
      name: auth.user.full_name || auth.user.email.split('@')[0],
      email: auth.user.email,
      role: normalizedRole,
    }
  }, [auth.user])

  const login = async (email: string, password: string) => {
    await auth.loginWithEmail(email, password)
    navigate('/lcopilot/importer-dashboard')
  }

  const logout = async () => {
    await auth.logout()
  }

  const value: ImporterAuthContext = {
    user: importerUser,
    isLoading: auth.isLoading,
    isAuthenticated: !!importerUser,
    login,
    logout,
  }

  return (
    <ImporterAuthContext.Provider value={value}>
      {children}
    </ImporterAuthContext.Provider>
  )
}

export function useImporterAuth(): ImporterAuthContext {
  const context = useContext(ImporterAuthContext)
  if (context === undefined) {
    throw new Error('useImporterAuth must be used within an ImporterAuthProvider')
  }
  return context
}