import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import {
  createTradeCase,
  getTradeCase,
  listTradeCases,
  respondToRemediation,
  resubmitTradeCase,
  submitTradeCase,
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

    await createTradeCase({ title: 'Case one', payment_arrangement: 'open_account' })
    await listTradeCases()
    await getTradeCase('case-1')
    await submitTradeCase('case-1')
    await respondToRemediation('case-1', 'action-1', { response: 'Corrected' })
    await resubmitTradeCase('case-1')

    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases', {
      title: 'Case one', payment_arrangement: 'open_account',
    })
    expect(api.get).toHaveBeenNthCalledWith(1, '/api/proofline/cases', {
      params: { limit: 50, offset: 0 },
    })
    expect(api.get).toHaveBeenNthCalledWith(2, '/api/proofline/cases/case-1')
    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases/case-1/submit')
    expect(api.post).toHaveBeenCalledWith('/api/proofline/cases/case-1/actions/action-1/respond', {
      response: 'Corrected',
    })
    expect(api.post).toHaveBeenLastCalledWith('/api/proofline/cases/case-1/resubmit')
  })
})
