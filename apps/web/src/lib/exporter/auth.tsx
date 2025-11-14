/**
 * Exporter Authentication Hook and Context
 *
 * Compatibility layer that proxies to the primary Supabase-powered AuthProvider.
 * This prevents legacy components from managing their own tokens / mock users.
 */

import React, { createContext, useContext, useMemo, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'

interface ExporterUser {
  id: string
  name: string
  email: string
  role: 'exporter' | 'tenant_admin'
}

interface ExporterAuthContext {
  user: ExporterUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const ExporterAuthContext = createContext<ExporterAuthContext | undefined>(undefined)

interface ExporterAuthProviderProps {
  children: ReactNode
}

export function ExporterAuthProvider({ children }: ExporterAuthProviderProps) {
  const navigate = useNavigate()
  const auth = useAuth()

  const exporterUser = useMemo<ExporterUser | null>(() => {
    if (!auth.user) return null
    // Treat tenant_admin as exporter admins, everything else as exporter
    const normalizedRole =
      auth.user.role === 'admin'
        ? 'tenant_admin'
        : auth.user.role === 'tenant_admin'
          ? 'tenant_admin'
          : 'exporter'

    return {
      id: auth.user.id,
      name: auth.user.full_name || auth.user.email.split('@')[0],
      email: auth.user.email,
      role: normalizedRole,
    }
  }, [auth.user])

  const login = async (email: string, password: string) => {
    await auth.loginWithEmail(email, password)
    navigate('/lcopilot/exporter-dashboard')
  }

  const logout = async () => {
    await auth.logout()
  }

  const value: ExporterAuthContext = {
    user: exporterUser,
    isLoading: auth.isLoading,
    isAuthenticated: !!exporterUser,
    login,
    logout,
  }

  return (
    <ExporterAuthContext.Provider value={value}>
      {children}
    </ExporterAuthContext.Provider>
  )
}

export function useExporterAuth(): ExporterAuthContext {
  const context = useContext(ExporterAuthContext)
  if (context === undefined) {
    throw new Error('useExporterAuth must be used within an ExporterAuthProvider')
  }
  return context
}