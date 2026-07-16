import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTradeCaseParty } from '@/lib/proofline/api'
import { ProoflinePartyForm } from './ProoflinePartyForm'

vi.mock('@/lib/proofline/api', () => ({ createTradeCaseParty: vi.fn() }))

describe('Proofline party form', () => {
  beforeEach(() => vi.clearAllMocks())

  it('stores the buyer policy reference as a party identifier', async () => {
    vi.mocked(createTradeCaseParty).mockResolvedValue({ id: 'party-1' } as never)
    render(<ProoflinePartyForm caseId="case-1" onSaved={vi.fn()} onCancel={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/legal or trading name/i), { target: { value: 'US Buyer Inc' } })
    fireEvent.change(screen.getByLabelText(/buyer policy reference/i), { target: { value: 'BUYER-US-1' } })
    fireEvent.click(screen.getByRole('button', { name: /add party/i }))

    await waitFor(() => expect(createTradeCaseParty).toHaveBeenCalledWith('case-1', expect.objectContaining({
      role: 'buyer',
      identifiers: { buyer_reference: 'BUYER-US-1' },
    })))
  })
})
