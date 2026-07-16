import type { PaymentArrangement, TradeCaseDetail, TradeCaseSummary } from '@shared/types'

import { api } from '@/api/client'

export interface TradeCaseCreateInput {
  title: string
  payment_arrangement: PaymentArrangement
  service_package_id?: string
  origin_country?: string
  destination_country?: string
  currency?: string
  amount?: number
  shipment_date?: string
  expected_payment_date?: string
  payment_terms?: string
  transaction_details?: Record<string, unknown>
}

export interface TradeCaseListResponse {
  items: TradeCaseSummary[]
  total: number
  offset: number
  limit: number
}

export async function createTradeCase(input: TradeCaseCreateInput): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>('/api/proofline/cases', input)
  return response.data
}

export async function listTradeCases(offset = 0, limit = 50): Promise<TradeCaseListResponse> {
  const response = await api.get<TradeCaseListResponse>('/api/proofline/cases', {
    params: { limit, offset },
  })
  return response.data
}

export async function getTradeCase(caseId: string): Promise<TradeCaseDetail> {
  const response = await api.get<TradeCaseDetail>(`/api/proofline/cases/${caseId}`)
  return response.data
}

export async function updateTradeCase(
  caseId: string,
  input: Partial<TradeCaseCreateInput>,
): Promise<TradeCaseDetail> {
  const response = await api.patch<TradeCaseDetail>(`/api/proofline/cases/${caseId}`, input)
  return response.data
}
