import * as React from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApiGet = vi.fn()
const mockGetSession = vi.fn()
const mockOnAuthStateChange = vi.fn()
const mockSignInWithPassword = vi.fn()
const mockSignOut = vi.fn()
const mockSubscription = { unsubscribe: vi.fn() }

vi.mock('@/api/client', () => ({
  api: {
    get: (...args: any[]) => mockApiGet(...args),
  },
  API_BASE_URL: 'https://api.trdrhub.com',
}))

vi.mock('@/lib/logger', () => ({
  logger: {
    createLogger: () => ({
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }),
  },
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: (...args: any[]) => mockGetSession(...args),
      onAuthStateChange: (...args: any[]) => mockOnAuthStateChange(...args),
      signInWithPassword: (...args: any[]) => mockSignInWithPassword(...args),
      signOut: (...args: any[]) => mockSignOut(...args),
    },
  },
}))

import { AuthProvider, useAuth } from '@/hooks/use-auth'

function AuthProbe() {
  const { user, isLoading } = useAuth()
  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="email">{user?.email ?? 'none'}</div>
      <div data-testid="role">{user?.role ?? 'none'}</div>
    </div>
  )
}

describe('AuthProvider bootstrap recovery', () => {
  const session = {
    access_token: 'supabase-token',
    user: {
      id: 'user-123',
      email: 'imran@iec.com',
      role: 'authenticated',
      user_metadata: {
        full_name: 'Imran Ali',
        role: 'exporter',
      },
      app_metadata: {
        provider: 'email',
        role: 'exporter',
      },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    mockSubscription.unsubscribe.mockReset()
    mockSignOut.mockResolvedValue(undefined)
    mockSignInWithPassword.mockResolvedValue({ data: { session }, error: null })
    mockOnAuthStateChange.mockImplementation((callback) => {
      callback('INITIAL_SESSION', session)
      return { data: { subscription: mockSubscription } }
    })
  })

  it('uses a fallback authenticated user when /auth/me fails but a Supabase session exists', async () => {
    mockGetSession.mockResolvedValue({ data: { session } })
    mockApiGet.mockRejectedValue(new Error('Loading profile timed out. Please try again.'))

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
      expect(screen.getByTestId('email')).toHaveTextContent('imran@iec.com')
      expect(screen.getByTestId('role')).toHaveTextContent('exporter')
    })
  })

  it('resets the bootstrap latch so a later auth event can recover from an auth/me failure', async () => {
    const authFailure = { response: { status: 401 } }
    mockGetSession.mockResolvedValue({ data: { session } })
    mockApiGet.mockRejectedValueOnce(authFailure).mockResolvedValueOnce({
      data: {
        id: 'user-123',
        email: 'imran@iec.com',
        full_name: 'Imran Ali',
        role: 'exporter',
        is_active: true,
      },
    })

    let authCallback: ((event: string, session: any) => void) | null = null
    mockOnAuthStateChange.mockImplementation((callback) => {
      authCallback = callback
      return { data: { subscription: mockSubscription } }
    })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
      expect(screen.getByTestId('email')).toHaveTextContent('none')
    })

    expect(authCallback).not.toBeNull()
    await act(async () => {
      authCallback?.('TOKEN_REFRESHED', session)
    })

    await waitFor(() => {
      expect(screen.getByTestId('email')).toHaveTextContent('imran@iec.com')
      expect(screen.getByTestId('role')).toHaveTextContent('exporter')
    })
  })

  it('bootstraps from the stored Supabase session payload before getSession resolves', async () => {
    localStorage.setItem(
      'sb-live-project-auth-token',
      JSON.stringify({
        currentSession: {
          access_token: 'stored-token',
          refresh_token: 'stored-refresh',
          expires_at: Math.floor(Date.now() / 1000) + 3600,
          user: session.user,
        },
      }),
    )
    mockGetSession.mockImplementation(() => new Promise(() => {}))
    mockApiGet.mockRejectedValue(new Error('Loading profile timed out. Please try again.'))
    mockOnAuthStateChange.mockImplementation(() => ({ data: { subscription: mockSubscription } }))

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
      expect(screen.getByTestId('email')).toHaveTextContent('imran@iec.com')
      expect(screen.getByTestId('role')).toHaveTextContent('exporter')
    })
  })
})
