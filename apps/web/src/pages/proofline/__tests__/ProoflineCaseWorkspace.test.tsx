import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProoflineCases from '../ProoflineCases'
import ProoflineCaseDetail from '../ProoflineCaseDetail'
import { getTradeCase, listTradeCases } from '@/lib/proofline/api'

vi.mock('@/lib/proofline/api', () => ({
  deleteTradeCaseParty: vi.fn(),
  getTradeCase: vi.fn(),
  getProoflineQuote: vi.fn(),
  listTradeCases: vi.fn(),
  resubmitTradeCase: vi.fn(),
  submitTradeCase: vi.fn(),
  startProoflineCheckout: vi.fn(),
  respondToRemediation: vi.fn(),
}))

const now = '2026-07-16T10:00:00Z'

describe('Proofline customer workspace', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists real cases and their current decisions', async () => {
    vi.mocked(listTradeCases).mockResolvedValue({
      items: [{
        id: 'd88aa468-078c-4cd4-b1f1-ecb6dbbb61f7', company_id: '662de77b-077a-44fe-80d0-2ac79a463539',
        case_reference: 'PL-2026-0001', title: 'US buyer July shipment', status: 'action_required',
        payment_arrangement: 'open_account', service_package_id: 'proofline_standard',
        payment_status: null, credit_amount_cents: 0,
        recommended_decision: 'ACTION_REQUIRED', final_decision: null, currency: 'USD', amount: '125000.00',
        origin_country: 'BD', destination_country: 'US', document_count: 5,
        finding_counts: { critical: 0, high: 2, medium: 1, low: 0, info: 0 }, created_at: now, updated_at: now,
      }], total: 1, offset: 0, limit: 50,
    })

    render(<MemoryRouter><ProoflineCases /></MemoryRouter>)

    expect(await screen.findByRole('heading', { name: 'US buyer July shipment' })).toBeInTheDocument()
    expect(screen.getByText('Action required')).toBeInTheDocument()
    expect(screen.getByText('5 documents')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open case/i })).toHaveAttribute('href', '/proofline/cases/d88aa468-078c-4cd4-b1f1-ecb6dbbb61f7')
  })

  it('shows the combined decision, applicable checks, and structured finding evidence', async () => {
    vi.mocked(getTradeCase).mockResolvedValue({
      id: 'd88aa468-078c-4cd4-b1f1-ecb6dbbb61f7', company_id: '662de77b-077a-44fe-80d0-2ac79a463539',
      case_reference: 'PL-2026-0001', title: 'US buyer July shipment', status: 'action_required',
      payment_arrangement: 'open_account', service_package_id: 'proofline_standard', recommended_decision: 'ACTION_REQUIRED',
      payment_status: 'paid', amount_paid_cents: 19900, credit_amount_cents: 0, payment_currency: 'USD',
      final_decision: null, currency: 'USD', amount: '125000.00', origin_country: 'BD', destination_country: 'US',
      document_count: 1, finding_counts: { critical: 0, high: 1, medium: 0, low: 0, info: 0 }, created_at: now, updated_at: now,
      transaction_details: {}, parties: [{ id: '98abdf5c-b9c9-49dd-be43-a47e8ddf2ea0', role: 'buyer', name: 'US Buyer Inc', country_code: 'US', identifiers: {} }],
      documents: [{ id: '6bb81236-09ed-4a44-87ce-787aa9100d12', document_id: 'cfd00f70-82d0-4ac8-afae-d955f6df644b', logical_key: 'invoice', document_type: 'commercial_invoice', filename: 'invoice-v2.pdf', version: 2, correction_round: 1, is_current: true, extraction_status: 'completed', created_at: now }],
      checks: [
        { id: 'f625c208-2f19-4aee-87ec-b68e2c154ea8', module: 'sanctions', state: 'clear', applicable: true, applicability_reason: 'Parties supplied', summary: 'No matches found', completed_at: now },
        { id: 'aafcdd11-b025-412e-9d54-f8ad1598680c', module: 'eudr', state: 'not_applicable', applicable: false, applicability_reason: 'Goods are outside EUDR scope', summary: null, completed_at: now },
      ],
      findings: [{
        id: '0494c122-68ed-420b-8baa-78bac28d9cef', source_module: 'open_account', source_finding_id: 'OA-PO-INVOICE-AMOUNT', category: 'value_consistency', severity: 'high',
        title: 'Invoice value differs from the purchase order', explanation: 'The submitted values do not match.', affected_field: 'amount',
        expected: 'USD 125,000.00 on purchase order', observed: 'USD 127,500.00 on invoice', suggested_correction: 'Correct the invoice or provide an approved order amendment.',
        automated: true, visibility: 'customer', status: 'customer_action_required', evidence_references: [], created_at: now, updated_at: now,
      }], actions: [], decision_history: [],
    })

    render(
      <MemoryRouter initialEntries={['/proofline/cases/d88aa468-078c-4cd4-b1f1-ecb6dbbb61f7']}>
        <Routes><Route path="/proofline/cases/:caseId" element={<ProoflineCaseDetail />} /></Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'US buyer July shipment' })).toBeInTheDocument()
    expect(screen.getByText('ACTION REQUIRED')).toBeInTheDocument()
    expect(screen.getByText('Sanctions')).toBeInTheDocument()
    expect(screen.getByText('Clear')).toBeInTheDocument()
    expect(screen.getByText('Not applicable')).toBeInTheDocument()
    expect(screen.getByText('Expected')).toBeInTheDocument()
    expect(screen.getByText('USD 125,000.00 on purchase order')).toBeInTheDocument()
    expect(screen.getByText('Found')).toBeInTheDocument()
    expect(screen.getByText('Suggested fix')).toBeInTheDocument()
    expect(screen.getByText('invoice-v2.pdf')).toBeInTheDocument()
    expect(screen.getByText(/Version 2/)).toBeInTheDocument()
  })
})
