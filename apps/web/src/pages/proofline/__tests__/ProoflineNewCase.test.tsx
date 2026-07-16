import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProoflineNewCase from '../ProoflineNewCase'
import { createTradeCase, listProoflinePackages } from '@/lib/proofline/api'

vi.mock('@/lib/proofline/api', () => ({
  createTradeCase: vi.fn(),
  listProoflinePackages: vi.fn(),
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

describe('Proofline new case', () => {
  beforeEach(() => {
    navigate.mockReset()
    vi.mocked(createTradeCase).mockReset()
    vi.mocked(listProoflinePackages).mockReset()
    vi.mocked(listProoflinePackages).mockResolvedValue([])
  })

  it('starts with payment arrangement and offers every supported route', () => {
    render(<MemoryRouter><ProoflineNewCase /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: /payment arrangement/i })).toBeInTheDocument()
    for (const option of [
      'Letter of credit', 'Open account / sales contract', 'Advance TT',
      'Partial advance + balance', 'Documents against payment',
      'Documents against acceptance', 'Buyer-led supply-chain finance',
      'Factoring / receivables finance', 'Consignment', 'Other',
    ]) {
      expect(screen.getByRole('radio', { name: option })).toBeInTheDocument()
    }
  })

  it('explains the applicable evidence when open account is selected', () => {
    render(<MemoryRouter><ProoflineNewCase /></MemoryRouter>)
    fireEvent.click(screen.getByRole('radio', { name: 'Open account / sales contract' }))

    expect(screen.getByText(/purchase order, sales contract, invoice approval conditions/i)).toBeInTheDocument()
    expect(screen.getByText(/payment undertaking, insurance, or receivables-finance evidence/i)).toBeInTheDocument()
  })

  it('creates a draft through the authenticated API client', async () => {
    vi.mocked(createTradeCase).mockResolvedValue({
      id: 'd88aa468-078c-4cd4-b1f1-ecb6dbbb61f7',
      case_reference: 'PL-2026-0001',
    } as never)

    render(<MemoryRouter><ProoflineNewCase /></MemoryRouter>)
    fireEvent.click(screen.getByRole('radio', { name: 'Open account / sales contract' }))
    fireEvent.click(screen.getByRole('button', { name: /continue to trade details/i }))
    fireEvent.change(screen.getByLabelText(/case title/i), {
      target: { value: 'US buyer July shipment' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save draft/i }))

    await waitFor(() => expect(createTradeCase).toHaveBeenCalledWith(expect.objectContaining({
      title: 'US buyer July shipment',
      payment_arrangement: 'open_account',
    })))
    expect(navigate).toHaveBeenCalledWith('/proofline/cases/d88aa468-078c-4cd4-b1f1-ecb6dbbb61f7')
  })
})
