import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { reportTradeCaseOutcome } from '@/lib/proofline/api'
import { ProoflineOutcomeFeedback } from './ProoflineOutcomeFeedback'

vi.mock('@/lib/proofline/api', () => ({ reportTradeCaseOutcome: vi.fn() }))

describe('Proofline voluntary outcomes', () => {
  beforeEach(() => vi.clearAllMocks())

  it('submits explicit answers and labels them as customer reported', async () => {
    vi.mocked(reportTradeCaseOutcome).mockResolvedValue({ id: 'outcome-1' } as never)
    render(<ProoflineOutcomeFeedback caseId="case-1" />)

    fireEvent.change(screen.getByLabelText('Were the documents accepted?'), { target: { value: 'yes' } })
    fireEvent.change(screen.getByLabelText('Was payment delayed?'), { target: { value: 'no' } })
    fireEvent.click(screen.getByRole('button', { name: /share outcome/i }))

    await waitFor(() => expect(reportTradeCaseOutcome).toHaveBeenCalledWith('case-1', {
      documents_accepted: true,
      payment_delayed: false,
      notes: undefined,
    }))
    expect(screen.getByText(/customer-reported outcome/i)).toBeInTheDocument()
  })
})
