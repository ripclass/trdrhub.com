import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getTradeCase, updateTradeCase } from '@/lib/proofline/api'
import ProoflineCaseDetail from '../ProoflineCaseDetail'

vi.mock('@/lib/proofline/api', () => ({
  deleteTradeCaseParty: vi.fn(), getTradeCase: vi.fn(), getProoflineQuote: vi.fn(),
  getProoflineReport: vi.fn(), resubmitTradeCase: vi.fn(), startProoflineCheckout: vi.fn(),
  submitTradeCase: vi.fn(), updateTradeCase: vi.fn(),
}))

const caseId = 'd88aa468-078c-4cd4-b1f1-ecb6dbbb61f7'
const draft = {
  id: caseId, company_id: '662de77b-077a-44fe-80d0-2ac79a463539', case_reference: 'PL-1',
  title: 'Credential evidence case', status: 'draft', payment_arrangement: 'open_account',
  service_package_id: 'proofline_managed', payment_status: null, credit_amount_cents: 0,
  recommended_decision: null, final_decision: null, currency: 'USD', amount: '1000.00',
  origin_country: 'BD', destination_country: 'US', document_count: 0, finding_counts: {},
  created_at: '2026-07-16T10:00:00Z', updated_at: '2026-07-16T10:00:00Z',
  transaction_details: {}, parties: [], documents: [], checks: [], findings: [], actions: [], decision_history: [],
}

describe('Proofline evidence capture', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getTradeCase).mockResolvedValue(draft as never)
    vi.mocked(updateTradeCase).mockResolvedValue({ ...draft, transaction_details: { ein_requested: true } } as never)
  })

  it('saves consented EIN presentation references without credential payloads', async () => {
    render(<MemoryRouter initialEntries={[`/proofline/cases/${caseId}`]}><Routes><Route path="/proofline/cases/:caseId" element={<ProoflineCaseDetail />} /></Routes></MemoryRouter>)

    await screen.findByRole('heading', { name: 'Credential evidence case' })
    fireEvent.change(screen.getByLabelText('EIN presentation reference'), { target: { value: 'vp-101' } })
    fireEvent.change(screen.getByLabelText('EIN consent reference'), { target: { value: 'consent-9' } })
    fireEvent.change(screen.getByLabelText('EIN credential type'), { target: { value: 'EnvironmentalClearance' } })
    fireEvent.click(screen.getByRole('button', { name: /share presentation reference/i }))

    await waitFor(() => expect(updateTradeCase).toHaveBeenCalledWith(caseId, {
      transaction_details: expect.objectContaining({
        ein_requested: true,
        ein_presentations: [expect.objectContaining({
          presentation_reference: 'vp-101', consent_reference: 'consent-9',
          credential_type: 'EnvironmentalClearance',
        })],
      }),
    }))
  })
})
