import type {
  PaymentArrangement,
  TradeCaseDetail,
  TradeCaseDocument,
  TradeCaseParty,
  TradeCaseSummary,
} from '@shared/types'

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

export async function submitTradeCase(caseId: string): Promise<TradeCaseDetail> {
  const response = await api.post<TradeCaseDetail>(`/api/proofline/cases/${caseId}/submit`)
  return response.data
}

export async function updateTradeCase(
  caseId: string,
  input: Partial<TradeCaseCreateInput>,
): Promise<TradeCaseDetail> {
  const response = await api.patch<TradeCaseDetail>(`/api/proofline/cases/${caseId}`, input)
  return response.data
}

export async function createTradeCaseParty(
  caseId: string,
  input: { role: string; name: string; country_code?: string; identifiers?: Record<string, unknown> },
): Promise<TradeCaseParty> {
  const response = await api.post<TradeCaseParty>(`/api/proofline/cases/${caseId}/parties`, input)
  return response.data
}

export async function deleteTradeCaseParty(caseId: string, partyId: string): Promise<void> {
  await api.delete(`/api/proofline/cases/${caseId}/parties/${partyId}`)
}

export async function uploadTradeCaseDocument(
  caseId: string,
  input: {
    file: File
    logicalKey: string
    documentType?: string
    supersedesId?: string
    correctionRound?: number
  },
): Promise<TradeCaseDocument> {
  const body = new FormData()
  body.append('file', input.file)
  body.append('logical_key', input.logicalKey)
  if (input.documentType) body.append('document_type', input.documentType)
  if (input.supersedesId) body.append('supersedes_id', input.supersedesId)
  body.append('correction_round', String(input.correctionRound || 0))
  const response = await api.post<TradeCaseDocument>(
    `/api/proofline/cases/${caseId}/documents/upload`,
    body,
  )
  return response.data
}
