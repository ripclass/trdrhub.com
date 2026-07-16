import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import {
  createTradeCase,
  getProoflineQuote,
  getProoflineReport,
  getTradeCase,
  listTradeCases,
  listProoflinePackages,
  respondToRemediation,
  resubmitTradeCase,
  submitTradeCase,
  startProoflineCheckout,
  upgradeLcopilotToProofline,
} from '../api'

vi.mock('@/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

describe('Proofline API client', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses the tenant-safe backend collection routes', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: 'case-1' } })
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { items: [], total: 0, offset: 0, limit: 50 } })
      .mockResolvedValueOnce({ data: { id: 'case-1' } })
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { amount_due_cents: 19900 } })
      .mockResolvedValueOnce({ data: { report_id: 'report-1', download_url: 'https://example.test/report' } })

    await createTradeCase({ title: 'Case one', payment_arrangement: 'open_account' })
    await listTradeCases()
    await getTradeCase('case-1')
    await listProoflinePackages()
    await getProoflineQuote('case-1')
    await getProoflineReport('case-1')
    await submitTradeCase('case-1')
    await startProoflineCheckout('case-1')
    await respondToRemediation('case-1', 'action-1', { response: 'Corrected' })
    await upgradeLcopilotToProofline('lc-session-1')
    await resubmitTradeCase('case-1')

    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases', {
      title: 'Case one', payment_arrangement: 'open_account',
    })
    expect(api.get).toHaveBeenNthCalledWith(1, '/api/proofline/cases', {
      params: { limit: 50, offset: 0 },
    })
    expect(api.get).toHaveBeenNthCalledWith(2, '/api/proofline/cases/case-1')
    expect(api.get).toHaveBeenNthCalledWith(3, '/api/proofline/packages')
    expect(api.get).toHaveBeenNthCalledWith(4, '/api/proofline/cases/case-1/quote')
    expect(api.get).toHaveBeenNthCalledWith(5, '/api/proofline/cases/case-1/report')
    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases/case-1/submit')
    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases/case-1/checkout')
    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases/case-1/actions/action-1/respond', {
      response: 'Corrected',
    })
    expect(api.post).toHaveBeenCalledWith('/api/proofline/upgrades/lcopilot/lc-session-1')
    expect(api.post).toHaveBeenLastCalledWith('/api/proofline/cases/case-1/resubmit')
  })
})
