import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mockToast = vi.fn()
const mockLoginWithEmail = vi.fn()
const mockUseAuth = vi.fn()
const mockReadPendingExporterReviewRoute = vi.fn()
const mockClearPendingExporterReviewRoute = vi.fn()

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}))

vi.mock('@/lib/exporter/pendingReviewRoute', () => ({
  readPendingExporterReviewRoute: () => mockReadPendingExporterReviewRoute(),
  clearPendingExporterReviewRoute: () => mockClearPendingExporterReviewRoute(),
}))

import Login from '@/pages/Login'

function renderLogin(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/lcopilot/exporter-dashboard" element={<div data-testid="reviews-destination">Reviews</div>} />
        <Route path="/lcopilot/dashboard" element={<div data-testid="default-destination">Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Login redirect handoff', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      loginWithEmail: mockLoginWithEmail,
    })
    mockReadPendingExporterReviewRoute.mockReturnValue(null)
  })

  it('navigates to the encoded returnUrl after email login succeeds', async () => {
    mockLoginWithEmail.mockResolvedValue({
      id: 'user-1',
      email: 'imran@iec.com',
    })

    renderLogin('/login?returnUrl=%2Flcopilot%2Fexporter-dashboard%3Fsection%3Dreviews%26jobId%3Djob-123')

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'imran@iec.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'ripc0722' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByTestId('reviews-destination')).toBeInTheDocument()
    })

    expect(mockLoginWithEmail).toHaveBeenCalledWith('imran@iec.com', 'ripc0722')
    expect(mockClearPendingExporterReviewRoute).toHaveBeenCalled()
  })

  it('uses the pending review route fallback when no explicit returnUrl is present', async () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        email: 'imran@iec.com',
        full_name: 'Imran Ali',
        username: 'Imran Ali',
        role: 'exporter',
        isActive: true,
      },
      isLoading: false,
      loginWithEmail: mockLoginWithEmail,
    })
    mockReadPendingExporterReviewRoute.mockReturnValue('/lcopilot/exporter-dashboard?section=reviews&jobId=job-123')

    renderLogin('/login')

    await waitFor(() => {
      expect(screen.getByTestId('reviews-destination')).toBeInTheDocument()
    })

    expect(mockClearPendingExporterReviewRoute).toHaveBeenCalled()
  })
})
